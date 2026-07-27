import asyncio
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from starlette.datastructures import UploadFile

from backend.api.xmltv import import_schedule
from backend.services.xmltv.parser import parse_date, parse_time


def import_file(
    path: Path,
    channel_timezone: str = "America/New_York",
) -> dict:
    upload = UploadFile(
        filename=path.name,
        file=BytesIO(path.read_bytes()),
    )
    return asyncio.run(import_schedule(upload, channel_timezone))


def test_sample_csv_import_is_valid():
    result = import_file(Path("tests/sample_schedule.csv"))

    assert result["success"] is True
    assert result["rows_received"] == 2
    assert result["programmes_imported"] == 2
    assert result["validation"]["score"] == 100
    assert result["validation"]["ready_to_generate"] is True
    assert result["suggested_fixes"] == 0
    assert result["programmes"][0]["xmltv_start"] == "20260718120000 +0000"
    assert result["programmes"][0]["xmltv_stop"] == "20260718123000 +0000"


def test_asset_id_is_generated_when_blank():
    lines = Path("tests/sample_schedule.csv").read_text().splitlines()
    row = lines[1].replace(",morning-news-s01e01,", ",,")

    with TemporaryDirectory() as directory:
        path = Path(directory) / "automatic_asset_id.csv"
        path.write_text("\n".join([lines[0], row]))
        result = import_file(path)

    assert result["success"] is True
    assert result["programmes"][0]["asset_id"] == "morning-news-s01e01"


def test_excel_serial_dates_and_times_are_supported():
    assert parse_date(46230) == "2026-07-27"
    assert parse_date("2026-07-27 00:00:00") == "2026-07-27"
    assert parse_time(0.25) == "06:00:00"


def test_empty_schedule_is_not_ready_to_generate():
    headers = Path("tests/sample_schedule.csv").read_text().splitlines()[0]

    with TemporaryDirectory() as directory:
        path = Path(directory) / "empty_schedule.csv"
        path.write_text(f"{headers}\n")
        result = import_file(path)

    assert result["success"] is False
    assert result["validation"]["critical"] == 1
    assert result["validation"]["ready_to_generate"] is False


def test_invalid_csv_reports_source_row():
    lines = Path("tests/sample_schedule.csv").read_text().splitlines()
    invalid_row = lines[1].replace("Morning News", "", 1)

    with TemporaryDirectory() as directory:
        path = Path(directory) / "invalid_schedule.csv"
        path.write_text("\n".join([lines[0], invalid_row]))
        result = import_file(path)

    issue = result["validation"]["issues"][0]
    assert result["success"] is False
    assert issue["row"] == 2
    assert issue["rule_id"] == "VAL-002"


def test_invalid_timezone_is_critical():
    result = import_file(
        Path("tests/sample_schedule.csv"),
        channel_timezone="Not/A_Timezone",
    )

    assert result["success"] is False
    assert result["validation"]["issues"][0]["rule_id"] == "VAL-010"


def test_spanish_booleans_and_minute_durations_are_normalized():
    lines = Path("tests/sample_schedule.csv").read_text().splitlines()
    row = lines[1].replace("00:30:00", "60").replace(",Yes,Yes,Yes", ",Sí,Sí,Sí")

    with TemporaryDirectory() as directory:
        path = Path(directory) / "localized_schedule.csv"
        path.write_text("\n".join([lines[0], row]))
        result = import_file(path)

    assert result["success"] is True
    assert result["validation"]["auto_fixed"] == 0
    assert result["suggested_fixes"] == 4
    assert result["programmes"][0]["duration"] == "01:00:00"
    assert result["programmes"][0]["premiere"] is True
