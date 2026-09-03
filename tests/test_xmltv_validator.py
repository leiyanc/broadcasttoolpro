from datetime import date, timedelta

from backend.models.programme import Programme
from backend.services.xmltv.validator import ValidationEngine


def make_programme(**overrides) -> Programme:
    values = {
        "source_row": 5,
        "channel": None,
        "air_date": "2026-07-18",
        "start_time": "08:00:00",
        "program_title": "Morning News",
        "duration": "00:30:00",
        "parental_rating": "TV-PG",
        "rating_system": "VCHIP",
        "program_description": "Daily morning news.",
        "original_title": "Morning News",
        "original_language": "en",
        "cast": [],
        "season_number": 1,
        "episode_number": 1,
        "original_episode_title": None,
        "episode_description": None,
        "genre": "News",
        "country_of_production": "United States",
        "production_year": 2026,
        "premiere": False,
        "live": True,
        "new": True,
        "asset_id": "morning-news-s01e01",
        "original_air_date": "2026-07-18",
    }
    values.update(overrides)
    return Programme(**values)


def test_valid_schedule_is_ready_to_generate():
    programmes = [
        make_programme(),
        make_programme(
            source_row=6,
            start_time="08:30:00",
            program_title="Market Update",
        ),
    ]

    report = ValidationEngine().validate(programmes)

    assert report.score == 100
    assert report.critical == 0
    assert report.errors == 0


def test_incomplete_rating_metadata_is_a_warning():
    report = ValidationEngine().validate([
        make_programme(rating_system=None),
    ])

    issue = next(item for item in report.issues if item.rule_id == "VAL-013")
    assert report.warnings == 1
    assert report.score == 98
    assert issue.severity == "warning"
    assert issue.row is None
    assert issue.field == "Parental Rating / Rating System"


def test_missing_channel_rating_system_is_reported_once_for_many_programmes():
    programmes = [
        make_programme(
            source_row=row,
            air_date=(date(2026, 1, 1) + timedelta(days=row - 5)).isoformat(),
            rating_system=None,
        )
        for row in range(5, 252)
    ]

    report = ValidationEngine().validate(programmes)

    rating_issues = [
        issue for issue in report.issues if issue.rule_id == "VAL-013"
    ]
    assert report.warnings == 1
    assert report.score == 98
    assert len(rating_issues) == 1
    assert rating_issues[0].row is None


def test_duplicate_start_is_critical_without_repeated_overlap():
    programmes = [
        make_programme(duration="01:00:00"),
        make_programme(source_row=6, program_title="Market Update"),
    ]

    report = ValidationEngine().validate(programmes)
    rule_ids = {issue.rule_id for issue in report.issues}

    assert "VAL-005" in rule_ids
    assert "VAL-008" not in rule_ids
    assert report.critical == 1


def test_overlap_is_critical():
    programmes = [
        make_programme(duration="01:00:00"),
        make_programme(
            source_row=6,
            start_time="08:30:00",
            program_title="Market Update",
        ),
    ]

    report = ValidationEngine().validate(programmes)

    assert any(issue.rule_id == "VAL-008" for issue in report.issues)
    assert report.critical == 1


def test_invalid_duration_and_year_are_reported():
    programme = make_programme(
        duration="30 minutes",
        production_year=1800,
    )

    report = ValidationEngine().validate([programme])
    issues = {issue.rule_id: issue for issue in report.issues}

    assert issues["VAL-007"].severity == "critical"
    assert issues["VAL-006"].severity == "warning"


def test_out_of_order_rows_are_reported():
    programmes = [
        make_programme(start_time="09:00:00"),
        make_programme(source_row=6, start_time="08:00:00"),
    ]

    report = ValidationEngine().validate(programmes)

    assert any(issue.rule_id == "VAL-004" for issue in report.issues)


def test_final_programme_without_duration_is_critical():
    programmes = [
        make_programme(duration=None),
    ]

    report = ValidationEngine().validate(programmes)

    assert any(issue.rule_id == "VAL-009" for issue in report.issues)
    assert report.critical == 1
