import asyncio
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from PIL import Image
from starlette.datastructures import UploadFile

from backend.api.prelogs import (
    export_prelog,
    filter_playlist_files,
    inspect_playlist_file,
    playlist_filter_options,
)
from backend.api.postlogs import export_postlog, filter_postlog_events
from backend.services.traffic.prelog_export import generate_prelog_workbook
from openpyxl import load_workbook
from backend.services.traffic.playlist import (
    filter_playlist_events,
    inspect_playlist,
    parse_playlist_events,
)


SAMPLE_PLAYLIST = Path("tests/sample_playlist.csv")


def test_playlist_inspection_uses_embedded_metadata():
    result = inspect_playlist(SAMPLE_PLAYLIST.read_bytes())

    assert result["metadata"]["date"] == "2026-07-25"
    assert result["metadata"]["start_time"] == "06:00:00"
    assert result["metadata"]["channel_name"] == "Comercio TV"
    assert result["header_row"] == 2


def test_playlist_inspection_detects_columns_and_assets():
    result = inspect_playlist(SAMPLE_PLAYLIST.read_bytes())

    assert result["detected_columns"] == {
        "asset_id": "ASSET ID",
        "time": "HOUR",
        "duration": "DURATION",
    }
    assert result["rows"] == 5
    assert result["asset_occurrences"] == 5
    assert result["unique_assets"] == 4
    assert result["prefixes"][0] == {
        "prefix": "promo_",
        "occurrences": 2,
    }


def test_playlist_endpoint_ignores_filename():
    upload = UploadFile(
        filename="meaningless-name.csv",
        file=BytesIO(SAMPLE_PLAYLIST.read_bytes()),
    )
    result = asyncio.run(inspect_playlist_file(upload))

    assert result["filename"] == "meaningless-name.csv"
    assert result["metadata"]["channel_name"] == "Comercio TV"
    assert result["metadata"]["date"] == "2026-07-25"


def test_playlist_requires_detectable_or_mapped_headers():
    try:
        inspect_playlist(b"one,two,three\n1,2,3\n")
    except ValueError as exc:
        assert "Manual column mapping" in str(exc)
    else:
        raise AssertionError("Expected an unmapped playlist to be rejected.")


def test_playlist_rolls_events_into_the_next_day():
    content = SAMPLE_PLAYLIST.read_text().replace(
        "06:00:00,0:00:30,promo_open",
        "23:59:30,0:00:30,promo_open",
    ).replace(
        "06:00:30,0:00:45,client_spot_a",
        "00:00:00,0:00:45,client_spot_a",
    )
    _, events = parse_playlist_events(content.encode())

    assert events[2].air_datetime.isoformat() == "2026-07-26T00:00:00"


def test_small_time_regression_does_not_advance_the_date():
    content = SAMPLE_PLAYLIST.read_text().replace(
        "06:01:15,0:00:45,client_spot_a",
        "05:59:00,0:00:45,client_spot_a",
    )
    _, events = parse_playlist_events(content.encode())

    assert events[3].air_datetime.date().isoformat() == "2026-07-25"


def test_twelve_hour_playlist_cycles_infer_am_pm_and_next_day():
    content = b"""2026-07-26,06:00:00,,Tarima TV
HOUR,DURATION,ASSET ID
11:59:00,0:00:30,morning
12:00:00,0:00:30,noon
01:00:00,0:00:30,afternoon
11:59:00,0:00:30,night
12:00:00,0:00:30,midnight
01:00:00,0:00:30,overnight
"""
    _, events = parse_playlist_events(content)

    assert events[2].air_datetime.isoformat() == "2026-07-26T13:00:00"
    assert events[4].air_datetime.isoformat() == "2026-07-27T00:00:00"
    assert events[5].air_datetime.isoformat() == "2026-07-27T01:00:00"


def test_filter_builder_supports_prefix_exact_and_contains():
    _, events = parse_playlist_events(SAMPLE_PLAYLIST.read_bytes())

    prefix_matches = filter_playlist_events(
        events,
        filter_mode="prefix",
        filter_value="promo_",
    )
    exact_matches = filter_playlist_events(
        events,
        filter_mode="exact",
        filter_value="client_spot_a",
    )
    contains_matches = filter_playlist_events(
        events,
        filter_mode="contains",
        filter_value="spot",
    )

    assert len(prefix_matches) == 2
    assert len(exact_matches) == 2
    assert len(contains_matches) == 2


def test_filter_builder_supports_date_and_overnight_time_ranges():
    _, events = parse_playlist_events(SAMPLE_PLAYLIST.read_bytes())
    matches = filter_playlist_events(
        events,
        start_date="2026-07-25",
        end_date="2026-07-25",
        start_time="06:00:30",
        end_time="06:01:15",
    )

    assert [event.asset_id for event in matches] == [
        "client_spot_a",
        "client_spot_a",
    ]


def test_filter_endpoint_combines_multiple_files():
    uploads = [
        UploadFile(
            filename=f"playlist-{position}.csv",
            file=BytesIO(SAMPLE_PLAYLIST.read_bytes()),
        )
        for position in range(2)
    ]
    result = asyncio.run(
        filter_playlist_files(
            uploads,
            "prefix",
            "promo_",
            None,
            None,
            None,
            None,
            "06:00:00",
            None,
        )
    )

    assert result["files_processed"] == 2
    assert result["events_received"] == 10
    assert result["matching_events"] == 4
    assert result["unique_assets"] == 2


def test_filter_options_combine_assets_and_dates():
    uploads = [
        UploadFile(
            filename="anything.csv",
            file=BytesIO(SAMPLE_PLAYLIST.read_bytes()),
        )
    ]
    result = asyncio.run(playlist_filter_options(uploads, None))

    assert result["channels"] == ["Comercio TV"]
    assert result["start_date"] == "2026-07-25"
    assert result["end_date"] == "2026-07-25"
    assert result["assets"][0]["asset_id"] == "Morning Programming"
    assert any(
        item["prefix"] == "promo_"
        for item in result["prefixes"]
    )


def test_broadcast_date_includes_overnight_events_until_next_six_am():
    content = b"""2026-07-26,06:00:00,,Tarima TV
HOUR,DURATION,ASSET ID
11:59:00,0:00:30,day
12:00:00,0:00:30,noon
01:00:00,0:00:30,afternoon
11:59:00,0:00:30,night
12:00:00,0:00:30,midnight
05:59:59,0:00:30,last_event
06:00:00,0:00:30,next_broadcast_day
"""
    _, events = parse_playlist_events(content)
    matches = filter_playlist_events(
        events,
        start_date="2026-07-26",
        end_date="2026-07-26",
        broadcast_day_start="06:00:00",
    )

    assert matches[-1].asset_id == "last_event"
    assert "next_broadcast_day" not in {
        event.asset_id
        for event in matches
    }


def test_auto_timezone_requires_playlist_metadata():
    try:
        parse_playlist_events(
            SAMPLE_PLAYLIST.read_bytes(),
            source_timezone="auto",
        )
    except ValueError as exc:
        assert "does not declare a time zone" in str(exc)
    else:
        raise AssertionError("Expected manual time zone selection.")


def test_selected_timezone_is_attached_to_events():
    _, events = parse_playlist_events(
        SAMPLE_PLAYLIST.read_bytes(),
        source_timezone="America/New_York",
    )

    assert events[0].air_datetime.utcoffset() is not None
    assert events[0].air_datetime.isoformat().endswith("-04:00")


def test_prelog_workbook_uses_requested_language_and_columns():
    _, events = parse_playlist_events(SAMPLE_PLAYLIST.read_bytes())
    content = generate_prelog_workbook(
        events[:2],
        channel_name="Comercio TV",
        language="es",
        product="Campaña institucional",
    )
    workbook = load_workbook(BytesIO(content))
    worksheet = workbook["Pre Log"]

    assert worksheet["A5"].value == "Nombre del canal"
    assert worksheet["B5"].value == "Producto"
    assert worksheet["C5"].value == "Identificador del elemento"
    assert worksheet["D5"].value == "Fecha"
    assert worksheet["E5"].value == "Hora"
    assert worksheet["F5"].value == "Duración"
    assert worksheet["A6"].value == "Comercio TV"
    assert worksheet["B6"].value == "Campaña institucional"
    assert worksheet["D6"].number_format == "mm/dd/yyyy"
    assert worksheet["E6"].number_format == "hh:mm:ss"
    assert "Pago" not in {
        cell.value
        for cell in worksheet[5]
    }


def test_prelog_export_endpoint_downloads_xlsx():
    upload = UploadFile(
        filename="ignored.csv",
        file=BytesIO(SAMPLE_PLAYLIST.read_bytes()),
    )
    response = asyncio.run(export_prelog(
        [upload],
        "prefix",
        "promo_",
        "2026-07-25",
        "2026-07-25",
        "06:00:00",
        "America/New_York",
        "Comercio TV",
        "en",
        None,
        None,
        None,
    ))

    assert response.media_type.endswith("spreadsheetml.sheet")
    workbook = load_workbook(BytesIO(response.body))
    assert workbook["Pre Log"]["A6"].value == "Comercio TV"


def test_prelog_workbook_embeds_jpg_logo():
    _, events = parse_playlist_events(SAMPLE_PLAYLIST.read_bytes())
    logo = BytesIO()
    Image.new("RGB", (160, 60), "#808080").save(logo, format="JPEG")
    content = generate_prelog_workbook(
        events[:2],
        channel_name="Tarima TV",
        logo_content=logo.getvalue(),
    )

    with ZipFile(BytesIO(content)) as archive:
        media_files = [
            name
            for name in archive.namelist()
            if name.startswith("xl/media/")
        ]

    assert len(media_files) == 1


def test_postlog_filters_actual_airings():
    upload = UploadFile(
        filename="as-run.csv",
        file=BytesIO(SAMPLE_PLAYLIST.read_bytes()),
    )
    result = asyncio.run(filter_postlog_events(
        [upload],
        "exact",
        "client_spot_a",
        "2026-07-25",
        "2026-07-25",
        "06:00:00",
        "America/New_York",
    ))

    assert result["matching_events"] == 2
    assert result["unique_assets"] == 1


def test_postlog_export_is_a_broadcast_certification():
    upload = UploadFile(
        filename="as-run.csv",
        file=BytesIO(SAMPLE_PLAYLIST.read_bytes()),
    )
    response = asyncio.run(export_postlog(
        [upload],
        "exact",
        "client_spot_a",
        "2026-07-25",
        "2026-07-25",
        "06:00:00",
        "America/New_York",
        "Comercio TV",
        "en",
        "Campaign A",
        None,
        None,
    ))
    workbook = load_workbook(BytesIO(response.body))
    worksheet = workbook["Pre Log"]

    assert worksheet["A1"].value == "Post Log — Broadcast Certification"
    assert worksheet["B5"].value == "Product"
    assert "Total Airings: 2" in worksheet["A9"].value
    assert "postlog-comercio-tv" in response.headers["content-disposition"]
