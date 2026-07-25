from backend.services.xmltv.timezone import (
    ScheduleConversionError,
    build_utc_schedule,
)
from tests.test_xmltv_validator import make_programme


def test_new_york_summer_schedule_converts_to_utc():
    schedule = build_utc_schedule(
        [make_programme(start_time="20:00:00")],
        "America/New_York",
    )

    assert schedule[0]["xmltv_start"] == "20260719000000 +0000"
    assert schedule[0]["xmltv_stop"] == "20260719003000 +0000"


def test_stop_time_can_be_inferred_from_next_programme():
    schedule = build_utc_schedule(
        [
            make_programme(duration=None),
            make_programme(source_row=6, start_time="08:45:00"),
        ],
        "America/New_York",
    )

    assert schedule[0]["xmltv_stop"] == "20260718124500 +0000"


def test_nonexistent_daylight_saving_time_is_rejected():
    programme = make_programme(
        air_date="2026-03-08",
        start_time="02:30:00",
    )

    try:
        build_utc_schedule([programme], "America/New_York")
    except ScheduleConversionError as exc:
        assert "does not exist" in str(exc)
    else:
        raise AssertionError("Expected a daylight-saving conversion error.")


def test_ambiguous_daylight_saving_time_is_rejected():
    programme = make_programme(
        air_date="2026-11-01",
        start_time="01:30:00",
    )

    try:
        build_utc_schedule([programme], "America/New_York")
    except ScheduleConversionError as exc:
        assert "ambiguous" in str(exc)
    else:
        raise AssertionError("Expected a daylight-saving conversion error.")
