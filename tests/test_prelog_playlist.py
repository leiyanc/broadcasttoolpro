import asyncio
from io import BytesIO
from pathlib import Path

from starlette.datastructures import UploadFile

from backend.api.prelogs import (
    filter_playlist_files,
    inspect_playlist_file,
    playlist_filter_options,
)
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
    result = asyncio.run(playlist_filter_options(uploads))

    assert result["channels"] == ["Comercio TV"]
    assert result["start_date"] == "2026-07-25"
    assert result["end_date"] == "2026-07-25"
    assert result["assets"][0]["asset_id"] == "Morning Programming"
    assert any(
        item["prefix"] == "promo_"
        for item in result["prefixes"]
    )
