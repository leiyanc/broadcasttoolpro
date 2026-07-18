import csv
from datetime import date, datetime, time
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from openpyxl import load_workbook

from backend.models.programme import Programme


EXPECTED_COLUMNS = [
    "Channel (Optional)",
    "Air Date",
    "Start Time",
    "Program Title",
    "Duration (Optional)",
    "Parental Rating",
    "Program Description",
    "Original Title",
    "Cast",
    "Season Number",
    "Episode Number",
    "Original Episode Title",
    "Episode Description",
    "Genre",
    "Country of Production",
    "Production Year",
    "Premiere",
    "Live",
    "New",
]


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def parse_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    text = clean_text(value)

    if not text:
        raise ValueError("Air Date is required.")

    accepted_formats = (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
    )

    for date_format in accepted_formats:
        try:
            return datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue

    raise ValueError("Air Date must use YYYY-MM-DD or MM/DD/YYYY.")


def parse_time(value: Any) -> str:
    if isinstance(value, datetime):
        return value.time().replace(microsecond=0).isoformat()

    if isinstance(value, time):
        return value.replace(microsecond=0).isoformat()

    text = clean_text(value)

    if not text:
        raise ValueError("Start Time is required.")

    accepted_formats = (
        "%H:%M:%S",
        "%H:%M",
        "%I:%M %p",
        "%I:%M:%S %p",
    )

    for time_format in accepted_formats:
        try:
            return datetime.strptime(text.upper(), time_format).time().isoformat()
        except ValueError:
            continue

    raise ValueError("Start Time is invalid.")


def parse_integer(value: Any) -> int | None:
    text = clean_text(value)

    if text is None:
        return None

    number = int(float(text))

    if number < 0:
        raise ValueError("Numeric values cannot be negative.")

    return number


def parse_boolean(value: Any) -> bool:
    text = clean_text(value)

    if text is None:
        return False

    normalized = text.lower()

    if normalized in {"yes", "true", "1", "y"}:
        return True

    if normalized in {"no", "false", "0", "n"}:
        return False

    raise ValueError("Use Yes or No.")


def parse_cast(value: Any) -> list[str]:
    text = clean_text(value)

    if not text:
        return []

    return [
        name.strip()
        for name in text.replace(",", ";").split(";")
        if name.strip()
    ]


def read_csv_rows(content: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="The CSV file must use UTF-8 encoding.",
        ) from exc

    reader = csv.DictReader(StringIO(text))

    if not reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="The CSV file does not contain headers.",
        )

    headers = [str(header).strip() for header in reader.fieldnames]
    rows = [
        dict(row)
        for row in reader
        if any(clean_text(value) for value in row.values())
    ]

    return headers, rows


def read_excel_rows(content: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        workbook = load_workbook(
            filename=BytesIO(content),
            read_only=True,
            data_only=True,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="The Excel file could not be opened.",
        ) from exc

    if "Programming" not in workbook.sheetnames:
        raise HTTPException(
            status_code=400,
            detail='The Excel file must contain a sheet named "Programming".',
        )

    worksheet = workbook["Programming"]

    headers = [
        str(cell.value).strip() if cell.value is not None else ""
        for cell in worksheet[4]
    ]

    rows: list[dict[str, Any]] = []

    for values in worksheet.iter_rows(min_row=5, values_only=True):
        if not any(clean_text(value) for value in values):
            continue

        rows.append(dict(zip(headers, values)))

    return headers, rows


def read_schedule_file(
    filename: str,
    content: bytes,
) -> tuple[list[str], list[dict[str, Any]]]:
    extension = Path(filename).suffix.lower()

    if extension == ".csv":
        return read_csv_rows(content)

    if extension == ".xlsx":
        return read_excel_rows(content)

    raise HTTPException(
        status_code=400,
        detail="Only .xlsx and .csv files are supported.",
    )


def build_programme(
    row: dict[str, Any],
    source_row: int,
) -> Programme:
    title = clean_text(row.get("Program Title"))

    if not title:
        raise ValueError("Program Title is required.")

    return Programme(
        source_row=source_row,
        channel=clean_text(row.get("Channel (Optional)")),
        air_date=parse_date(row.get("Air Date")),
        start_time=parse_time(row.get("Start Time")),
        program_title=title,
        duration=clean_text(row.get("Duration (Optional)")),
        parental_rating=clean_text(row.get("Parental Rating")),
        program_description=clean_text(row.get("Program Description")),
        original_title=clean_text(row.get("Original Title")),
        cast=parse_cast(row.get("Cast")),
        season_number=parse_integer(row.get("Season Number")),
        episode_number=parse_integer(row.get("Episode Number")),
        original_episode_title=clean_text(
            row.get("Original Episode Title")
        ),
        episode_description=clean_text(
            row.get("Episode Description")
        ),
        genre=clean_text(row.get("Genre")),
        country_of_production=clean_text(
            row.get("Country of Production")
        ),
        production_year=parse_integer(row.get("Production Year")),
        premiere=parse_boolean(row.get("Premiere")),
        live=parse_boolean(row.get("Live")),
        new=parse_boolean(row.get("New")),
    )
