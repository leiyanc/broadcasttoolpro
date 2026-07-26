import asyncio
from io import BytesIO
from pathlib import Path

from starlette.datastructures import UploadFile

from backend.api.prelogs import inspect_playlist_file
from backend.services.traffic.playlist import inspect_playlist


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
