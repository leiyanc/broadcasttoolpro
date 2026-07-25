from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.models.validation import ValidationIssue, ValidationReport
from backend.services.xmltv.parser import (
    EXPECTED_COLUMNS,
    build_programme,
    read_schedule_file,
)
from backend.services.xmltv.timezone import (
    ScheduleConversionError,
    build_utc_schedule,
)
from backend.services.xmltv.validator import ValidationEngine


router = APIRouter(
    prefix="/api/xmltv",
    tags=["XMLTV"],
)


@router.post("/import")
async def import_schedule(
    schedule_file: UploadFile = File(...),
    channel_timezone: str = Form(...),
):
    filename = schedule_file.filename or ""
    content = await schedule_file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    headers, rows = read_schedule_file(filename, content)

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in headers
    ]

    unknown_columns = [
        column
        for column in headers
        if column and column not in EXPECTED_COLUMNS
    ]

    if missing_columns:
        report = ValidationReport.from_issues([
            ValidationIssue(
                rule_id="VAL-001",
                row=4,
                field=column,
                severity="critical",
                message=f"Missing template column: {column}",
            )
            for column in missing_columns
        ])

        return {
            "success": False,
            "filename": filename,
            "file_type": Path(filename).suffix.lower(),
            "missing_columns": missing_columns,
            "unknown_columns": unknown_columns,
            "programmes": [],
            "validation": report.to_dict(),
        }

    programmes = []
    parsing_issues = []

    extension = Path(filename).suffix.lower()
    first_data_row = 5 if extension == ".xlsx" else 2

    if not rows:
        parsing_issues.append(
            ValidationIssue(
                rule_id="VAL-002",
                row=None,
                field="Programme",
                severity="critical",
                message="The schedule does not contain any programme rows.",
            )
        )

    parsing_issues.extend(
        ValidationIssue(
            rule_id="VAL-003",
            row=4 if extension == ".xlsx" else 1,
            field=column,
            severity="warning",
            message=f"Unknown template column: {column}",
        )
        for column in unknown_columns
    )

    for position, row in enumerate(rows):
        source_row = first_data_row + position

        try:
            programme = build_programme(row, source_row)
            programmes.append(programme)
        except (ValueError, TypeError) as exc:
            parsing_issues.append(
                ValidationIssue(
                    rule_id="VAL-002",
                    row=source_row,
                    field="Programme",
                    severity="critical",
                    message=str(exc),
                )
            )

    report = ValidationEngine().validate(programmes, parsing_issues)
    utc_schedule = []

    if report.critical == 0:
        try:
            utc_schedule = build_utc_schedule(
                programmes,
                channel_timezone,
            )
        except ScheduleConversionError as exc:
            parsing_issues.append(
                ValidationIssue(
                    rule_id="VAL-010",
                    row=None,
                    field="Channel Time Zone",
                    severity="critical",
                    message=str(exc),
                )
            )
            report = ValidationEngine().validate(
                programmes,
                parsing_issues,
            )

    return {
        "success": report.critical == 0,
        "filename": filename,
        "file_type": extension,
        "rows_received": len(rows),
        "programmes_imported": len(programmes),
        "channel_timezone": channel_timezone,
        "validation": report.to_dict(),
        "missing_columns": [],
        "unknown_columns": unknown_columns,
        "programmes": utc_schedule[:10],
    }
