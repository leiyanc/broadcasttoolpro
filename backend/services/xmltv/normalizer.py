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
    previous_by_channel: dict[str, Programme] = {}
    genre_by_channel: dict[str, str] = {}

    for programme in programmes:
        channel = programme.channel or "__default__"
        previous = previous_by_channel.get(channel)

        if previous is not None:
            previous_start = programme_start(previous)
            current_start = programme_start(programme)
            metadata_matches = (
                programme_metadata(programme)
                == programme_metadata(previous)
            )

            if current_start == previous_start:
                auto_fixes.append({
                    "row": programme.source_row,
                    "field": "Programme",
                    "original_value": programme.program_title,
                    "normalized_value": previous.program_title,
                    "message": (
                        "Exact duplicate row was removed; it matches "
                        f"row {previous.source_row}."
                        if metadata_matches
                        else (
                            "Conflicting row with the same start time was "
                            "ignored; the first programme on row "
                            f"{previous.source_row} controls the airing."
                        )
                    ),
                })
                continue

            try:
                previous_stop = previous_start + parse_duration(
                    previous.duration or ""
                )
            except ValueError:
                previous_stop = None

            if (
                previous_stop is not None
                and current_start > previous_start
                and current_start < previous_stop
            ):
                auto_fixes.append({
                    "row": programme.source_row,
                    "field": "Programme",
                    "original_value": programme.program_title,
                    "normalized_value": previous.program_title,
                    "message": (
                        "Continuation row was ignored; the duration entered "
                        f"on row {previous.source_row} controls the complete "
                        "programme."
                    ),
                })
                continue

        if programme.genre:
            genre_by_channel[channel] = programme.genre
        elif channel in genre_by_channel:
            inherited_genre = genre_by_channel[channel]
            programme.genre = inherited_genre
            auto_fixes.append({
                "row": programme.source_row,
                "field": "Genre",
                "original_value": "",
                "normalized_value": inherited_genre,
                "message": (
                    "Blank Genre inherited the most recent genre for "
                    "this channel."
                ),
            })

        normalized.append(programme)
        previous_by_channel[channel] = programme

    return normalized
