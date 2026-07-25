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


def test_exact_duplicate_start_is_not_merged():
    programmes = [
        make_programme(),
        make_programme(source_row=6),
    ]
    fixes = []

    normalized = collapse_continuation_rows(programmes, fixes)

    assert len(normalized) == 2
    assert fixes == []


def test_same_title_with_different_metadata_is_not_merged():
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

    assert len(normalized) == 2
    assert fixes == []
