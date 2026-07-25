from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from backend.models.validation import ValidationIssue, ValidationReport
from backend.services.xmltv.parser import (
    EXPECTED_COLUMNS,
    build_programme,
    read_schedule_file,
)
from backend.services.xmltv.generator import generate_xmltv
from backend.services.xmltv.normalizer import collapse_continuation_rows
from backend.services.xmltv.timezone import (
    ScheduleConversionError,
    build_utc_schedule,
)
from backend.services.xmltv.validator import ValidationEngine


router = APIRouter(
    prefix="/api/xmltv",
    tags=["XMLTV"],
)

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
EXCEL_TEMPLATE = ASSETS_DIR / "Broadcast_Tool_Pro_XMLTV_Template.xlsx"


@router.get("/template/excel", response_class=FileResponse)
def download_excel_template():
    return FileResponse(
        EXCEL_TEMPLATE,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        filename="Broadcast_Tool_Pro_XMLTV_Template.xlsx",
    )


@router.get("/template/csv", response_class=Response)
def download_csv_template():
    content = ",".join(EXPECTED_COLUMNS) + "\n"
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                'attachment; filename="Broadcast_Tool_Pro_XMLTV_Template.csv"'
            ),
        },
    )


async def process_schedule(
    schedule_file: UploadFile,
    channel_timezone: str,
) -> dict:
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
    auto_fixes = []

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
            programme = build_programme(
                row,
                source_row,
                auto_fixes=auto_fixes,
            )
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

    programmes = collapse_continuation_rows(
        programmes,
        auto_fixes,
    )

    report = ValidationEngine().validate(
        programmes,
        parsing_issues,
        auto_fixed=len(auto_fixes),
    )
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
                auto_fixed=len(auto_fixes),
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
        "auto_fixes": auto_fixes,
        "programmes": utc_schedule,
    }


@router.post("/import")
async def import_schedule(
    schedule_file: UploadFile = File(...),
    channel_timezone: str = Form(...),
):
    return await process_schedule(schedule_file, channel_timezone)


@router.post("/generate", response_class=Response)
async def generate_schedule(
    schedule_file: UploadFile = File(...),
    channel_timezone: str = Form(...),
    channel_id: str = Form(...),
    channel_name: str = Form(...),
    primary_language: str = Form("en"),
    original_language: str = Form("en"),
    rating_system: str = Form("VCHIP"),
):
    result = await process_schedule(schedule_file, channel_timezone)

    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail=result["validation"],
        )

    if not channel_id.strip() or not channel_name.strip():
        raise HTTPException(
            status_code=422,
            detail="Channel ID and Channel Name are required.",
        )

    xml = generate_xmltv(
        programmes=result["programmes"],
        channel_id=channel_id.strip(),
        channel_name=channel_name.strip(),
        primary_language=primary_language.strip(),
        original_language=original_language.strip(),
        rating_system=rating_system.strip(),
    )

    return Response(
        content=xml,
        media_type="application/xml",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{channel_id.strip()}-xmltv.xml"'
            ),
        },
    )
