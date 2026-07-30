import asyncio
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from starlette.datastructures import UploadFile

from backend.api.xmltv import download_programming_grid
from backend.services.xmltv.programming_grid import (
    LIVE_BACKGROUND,
    GRID_LEGEND_LABELS,
    _live_color,
    _show_color,
    generate_programming_grid,
)


def make_programme(start: datetime, title: str, genre: str) -> dict:
    stop = start + timedelta(hours=1)
    return {
        "program_title": title,
        "genre": genre,
        "live": False,
        "start_utc": start.astimezone(timezone.utc).isoformat(),
        "stop_utc": stop.astimezone(timezone.utc).isoformat(),
    }


def test_programming_grid_creates_a_pdf():
    programmes = [
        make_programme(
            datetime(2026, 7, 27, 10, tzinfo=timezone.utc),
            "Morning News",
            "News",
        ),
        make_programme(
            datetime(2026, 7, 28, 15, tzinfo=timezone.utc),
            "Business Report",
            "Business",
        ),
    ]

    content = generate_programming_grid(
        programmes,
        channel_name="Comercio TV",
        timezone_name="America/New_York",
    )

    assert content.startswith(b"%PDF")
    assert len(content) > 1_000
    assert GRID_LEGEND_LABELS == ("Live", "Premiere", "Replay")


def test_equal_show_titles_use_the_same_light_background():
    first = _show_color("Morning News")
    repeated = _show_color("  MORNING   NEWS ")

    assert first.hexval() == repeated.hexval()
    assert first.hexval() != LIVE_BACKGROUND.hexval()


def test_different_live_shows_use_different_dark_backgrounds():
    buenos_dias = _live_color("Buenos Días Wall Street")
    pulso = _live_color("Pulso Del Mercado")

    assert buenos_dias.hexval() != pulso.hexval()


def test_programming_grid_endpoint_uses_the_original_epg_upload():
    path = Path("tests/sample_schedule.csv")
    content = path.read_text().replace(
        ",morning-news-s01e01,",
        ",,",
    ).encode()
    upload = UploadFile(
        filename=path.name,
        file=BytesIO(content),
    )

    response = asyncio.run(
        download_programming_grid(
            upload,
            "America/New_York",
            "Comercio TV",
            False,
        )
    )

    assert response.media_type == "application/pdf"
    assert response.body.startswith(b"%PDF")
    assert "comercio-tv-programming-grid.pdf" in response.headers[
        "content-disposition"
    ]
