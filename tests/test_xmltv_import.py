import asyncio
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from starlette.datastructures import UploadFile

from backend.api.xmltv import import_schedule


def import_file(path: Path) -> dict:
    upload = UploadFile(
        filename=path.name,
        file=BytesIO(path.read_bytes()),
    )
    return asyncio.run(import_schedule(upload))


def test_sample_csv_import_is_valid():
    result = import_file(Path("tests/sample_schedule.csv"))

    assert result["success"] is True
    assert result["rows_received"] == 2
    assert result["programmes_imported"] == 2
    assert result["validation"]["score"] == 100
    assert result["validation"]["ready_to_generate"] is True


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
