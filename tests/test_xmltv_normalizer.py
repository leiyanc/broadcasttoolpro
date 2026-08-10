from backend.services.xmltv.normalizer import collapse_continuation_rows
from tests.test_xmltv_validator import make_programme


def test_continuation_row_is_merged():
    programmes = [
        make_programme(
            source_row=5,
            start_time="09:00:00",
            duration="02:00:00",
            program_title="Morning Show",
        ),
        make_programme(
            source_row=6,
            start_time="10:00:00",
            duration="02:00:00",
            program_title="Morning Show",
        ),
        make_programme(
            source_row=7,
            start_time="11:00:00",
            duration="01:00:00",
            program_title="Market Update",
        ),
    ]
    fixes = []

    normalized = collapse_continuation_rows(programmes, fixes)

    assert len(normalized) == 2
    assert normalized[0].source_row == 5
    assert normalized[1].source_row == 7
    assert fixes[0]["row"] == 6


def test_exact_duplicate_start_is_removed():
    programmes = [
        make_programme(),
        make_programme(source_row=6),
    ]
    fixes = []

    normalized = collapse_continuation_rows(programmes, fixes)

    assert len(normalized) == 1
    assert fixes[0]["row"] == 6
    assert fixes[0]["message"].startswith("Exact duplicate")


def test_same_start_with_different_metadata_keeps_first_airing():
    programmes = [
        make_programme(),
        make_programme(
            source_row=6,
            program_description="A different event.",
        ),
    ]
    fixes = []

    normalized = collapse_continuation_rows(programmes, fixes)

    assert len(normalized) == 1
    assert fixes[0]["row"] == 6
    assert "first programme" in fixes[0]["message"]


def test_first_duration_controls_following_continuation_rows():
    programmes = [
        make_programme(duration="02:00:00"),
        make_programme(
            source_row=6,
            start_time="08:30:00",
            duration="02:00:00",
            program_description="A different episode.",
        ),
    ]
    fixes = []

    normalized = collapse_continuation_rows(programmes, fixes)

    assert len(normalized) == 1
    assert fixes[0]["row"] == 6
    assert "duration entered on row 5" in fixes[0]["message"]


def test_first_duration_controls_even_when_following_title_differs():
    programmes = [
        make_programme(
            duration="01:30:00",
            program_title="Juan Luis Guerra 4.40",
        ),
        make_programme(
            source_row=6,
            start_time="08:30:00",
            duration="01:30:00",
            program_title="Juan Luis Guerra 4.41",
        ),
        make_programme(
            source_row=7,
            start_time="09:00:00",
            duration="01:30:00",
            program_title="Juan Luis Guerra 4.42",
        ),
        make_programme(
            source_row=8,
            start_time="09:30:00",
            duration="00:30:00",
            program_title="Next Programme",
        ),
    ]
    fixes = []

    normalized = collapse_continuation_rows(programmes, fixes)

    assert [item.source_row for item in normalized] == [5, 8]
    assert [fix["row"] for fix in fixes] == [6, 7]


def test_blank_genre_inherits_latest_channel_genre_until_changed():
    programmes = [
        make_programme(genre="Concert"),
        make_programme(
            source_row=6,
            start_time="09:00:00",
            genre=None,
        ),
        make_programme(
            source_row=7,
            start_time="10:00:00",
            genre="Music",
        ),
        make_programme(
            source_row=8,
            start_time="11:00:00",
            genre=None,
        ),
    ]
    fixes = []

    normalized = collapse_continuation_rows(programmes, fixes)

    assert [item.genre for item in normalized] == [
        "Concert",
        "Concert",
        "Music",
        "Music",
    ]
    assert [fix["field"] for fix in fixes] == ["Genre", "Genre"]
