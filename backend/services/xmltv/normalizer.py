from dataclasses import astuple
from datetime import timedelta

from backend.models.programme import Programme
from backend.services.xmltv.validator import parse_duration, programme_start


def programme_metadata(programme: Programme) -> tuple:
    values = astuple(programme)
    return values[1:2] + values[4:]


def collapse_continuation_rows(
    programmes: list[Programme],
    auto_fixes: list[dict],
) -> list[Programme]:
    if not programmes:
        return []

    normalized = []

    for programme in programmes:
        if not normalized:
            normalized.append(programme)
            continue

        previous = normalized[-1]
        previous_start = programme_start(previous)
        current_start = programme_start(programme)

        try:
            previous_stop = previous_start + parse_duration(
                previous.duration or ""
            )
        except ValueError:
            normalized.append(programme)
            continue

        is_continuation = (
            current_start > previous_start
            and current_start < previous_stop
            and programme_metadata(programme)
            == programme_metadata(previous)
        )

        if not is_continuation:
            normalized.append(programme)
            continue

        auto_fixes.append({
            "row": programme.source_row,
            "field": "Programme",
            "original_value": programme.program_title,
            "normalized_value": previous.program_title,
            "message": (
                "Continuation row was merged into the programme "
                f"starting on row {previous.source_row}."
            ),
        })

    return normalized
