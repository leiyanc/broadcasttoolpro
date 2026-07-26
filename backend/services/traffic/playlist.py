import csv
from collections import Counter
from datetime import date, datetime, time
from io import StringIO
from re import match
from typing import Any


MAX_PLAYLIST_SIZE = 20 * 1024 * 1024
HEADER_ALIASES = {
    "asset_id": {
        "asset id",
        "asset",
        "program name",
        "programme name",
        "event id",
        "clip id",
        "media id",
    },
    "time": {
        "hour",
        "time",
        "start time",
        "air time",
    },
    "duration": {
        "duration",
        "chrono",
        "length",
    },
}


def _normalized(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _decode_csv(content: bytes) -> str:
    if not content:
        raise ValueError("The playlist file is empty.")

    if len(content) > MAX_PLAYLIST_SIZE:
        raise ValueError("The playlist file exceeds the 20 MB import limit.")

    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The playlist CSV must use UTF-8 encoding.") from exc


def _header_score(row: list[str]) -> int:
    normalized = {_normalized(value) for value in row if value.strip()}
    return sum(
        any(alias in normalized for alias in aliases)
        for aliases in HEADER_ALIASES.values()
    )


def _detect_header(rows: list[list[str]]) -> int:
    candidates = [
        (_header_score(row), position)
        for position, row in enumerate(rows[:25])
    ]
    score, position = max(candidates, default=(0, 0))

    if score < 2:
        raise ValueError(
            "The playlist header could not be detected. "
            "Manual column mapping is required."
        )

    return position


def _detect_columns(headers: list[str]) -> dict[str, str | None]:
    detected: dict[str, str | None] = {
        "asset_id": None,
        "time": None,
        "duration": None,
    }

    for header in headers:
        normalized = _normalized(header)
        for field, aliases in HEADER_ALIASES.items():
            if detected[field] is None and normalized in aliases:
                detected[field] = header

    return detected


def _parse_date(value: str) -> str | None:
    text = value.strip()
    formats = (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d-%m-%Y",
    )

    for value_format in formats:
        try:
            return datetime.strptime(text, value_format).date().isoformat()
        except ValueError:
            continue

    return None


def _parse_time(value: str) -> str | None:
    text = value.strip()
    formats = (
        "%H:%M:%S",
        "%H:%M",
        "%I:%M:%S %p",
        "%I:%M %p",
    )

    for value_format in formats:
        try:
            return datetime.strptime(text, value_format).time().isoformat()
        except ValueError:
            continue

    return None


def _metadata(rows: list[list[str]]) -> dict[str, Any]:
    embedded_date = None
    embedded_time = None
    channel_name = None

    for row in rows:
        for value in row:
            if not value.strip():
                continue

            if embedded_date is None:
                embedded_date = _parse_date(value)
                if embedded_date is not None:
                    continue

            if embedded_time is None:
                embedded_time = _parse_time(value)
                if embedded_time is not None:
                    continue

            if channel_name is None:
                channel_name = value.strip()

    return {
        "date": embedded_date,
        "start_time": embedded_time,
        "channel_name": channel_name,
    }


def _prefix(asset_id: str) -> str:
    result = match(r"^[A-Za-z]+_", asset_id)
    return result.group(0).lower() if result else "(no prefix)"


def inspect_playlist(content: bytes) -> dict[str, Any]:
    text = _decode_csv(content)
    rows = [
        [str(value).strip() for value in row]
        for row in csv.reader(StringIO(text))
    ]

    if not any(any(value for value in row) for row in rows):
        raise ValueError("The playlist does not contain any data.")

    header_index = _detect_header(rows)
    headers = rows[header_index]
    detected_columns = _detect_columns(headers)
    metadata = _metadata(rows[:header_index])
    data_rows = [
        row
        for row in rows[header_index + 1:]
        if any(value for value in row)
    ]

    asset_column = detected_columns["asset_id"]
    asset_index = headers.index(asset_column) if asset_column else None
    assets = [
        row[asset_index].strip()
        for row in data_rows
        if asset_index is not None
        and asset_index < len(row)
        and row[asset_index].strip()
    ]
    asset_counts = Counter(assets)
    prefix_counts = Counter(_prefix(asset) for asset in assets)

    sample_rows = [
        {
            header: row[position] if position < len(row) else ""
            for position, header in enumerate(headers)
            if header
        }
        for row in data_rows[:10]
    ]

    return {
        "header_row": header_index + 1,
        "headers": [header for header in headers if header],
        "detected_columns": detected_columns,
        "metadata": metadata,
        "rows": len(data_rows),
        "asset_occurrences": len(assets),
        "unique_assets": len(asset_counts),
        "assets": [
            {
                "asset_id": asset,
                "occurrences": count,
            }
            for asset, count in sorted(asset_counts.items())
        ],
        "prefixes": [
            {
                "prefix": prefix,
                "occurrences": count,
            }
            for prefix, count in prefix_counts.most_common()
        ],
        "sample_rows": sample_rows,
    }
