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
        "program_description": "Daily morning news.",
        "original_title": "Morning News",
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


def test_duplicate_and_overlap_are_critical():
    programmes = [
        make_programme(duration="01:00:00"),
        make_programme(source_row=6, program_title="Market Update"),
    ]

    report = ValidationEngine().validate(programmes)
    rule_ids = {issue.rule_id for issue in report.issues}

    assert "VAL-005" in rule_ids
    assert "VAL-008" in rule_ids
    assert report.critical == 2


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
