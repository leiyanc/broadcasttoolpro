from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.models.programme import Programme
from backend.services.xmltv.validator import parse_duration, programme_start


class ScheduleConversionError(ValueError):
    pass


def get_timezone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ScheduleConversionError(
            "Use a valid IANA time zone, such as America/New_York."
        ) from exc


def localize(local_datetime: datetime, channel_timezone: ZoneInfo) -> datetime:
    localized = local_datetime.replace(tzinfo=channel_timezone)
    alternate = local_datetime.replace(tzinfo=channel_timezone, fold=1)
    localized_round_trip = (
        localized.astimezone(timezone.utc)
        .astimezone(channel_timezone)
        .replace(tzinfo=None)
    )
    alternate_round_trip = (
        alternate.astimezone(timezone.utc)
        .astimezone(channel_timezone)
        .replace(tzinfo=None)
    )
    localized_is_valid = localized_round_trip == local_datetime
    alternate_is_valid = alternate_round_trip == local_datetime

    if not localized_is_valid and not alternate_is_valid:
        raise ScheduleConversionError(
            f"{local_datetime.isoformat()} does not exist in "
            f"{channel_timezone.key} because of a daylight-saving transition."
        )

    if (
        localized_is_valid
        and alternate_is_valid
        and localized.utcoffset() != alternate.utcoffset()
    ):
        raise ScheduleConversionError(
            f"{local_datetime.isoformat()} is ambiguous in "
            f"{channel_timezone.key} because of a daylight-saving transition."
        )

    return localized


def to_xmltv_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S +0000")


def build_utc_schedule(
    programmes: list[Programme],
    timezone_name: str,
) -> list[dict]:
    channel_timezone = get_timezone(timezone_name)
    by_channel: dict[str, list[Programme]] = defaultdict(list)
    result = []

    for programme in programmes:
        by_channel[programme.channel or "__default__"].append(programme)

    for channel_programmes in by_channel.values():
        ordered = sorted(channel_programmes, key=programme_start)

        for index, programme in enumerate(ordered):
            local_start = programme_start(programme)

            if programme.duration is not None:
                local_stop = local_start + parse_duration(programme.duration)
            elif index + 1 < len(ordered):
                local_stop = programme_start(ordered[index + 1])
            else:
                raise ScheduleConversionError(
                    "The final programme requires a duration."
                )

            start = localize(local_start, channel_timezone)
            stop = localize(local_stop, channel_timezone)

            result.append({
                **programme.to_dict(),
                "start_utc": start.astimezone(timezone.utc).isoformat(),
                "stop_utc": stop.astimezone(timezone.utc).isoformat(),
                "xmltv_start": to_xmltv_utc(start),
                "xmltv_stop": to_xmltv_utc(stop),
            })

    return sorted(result, key=lambda item: item["start_utc"])
