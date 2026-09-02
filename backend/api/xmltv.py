from pathlib import Path
from collections import Counter
from datetime import date
import re
import unicodedata

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from backend.models.validation import ValidationIssue, ValidationReport
from backend.services.xmltv.parser import (
    EXPECTED_COLUMNS,
    build_programme,
    read_schedule_file,
)
from backend.services.xmltv.generator import generate_xmltv
from backend.services.xmltv.programming_grid import generate_programming_grid
from backend.services.xmltv.feed_validator import validate_xmltv
from backend.services.xmltv.feed_repair import repair_xmltv
from backend.services.xmltv.normalizer import collapse_continuation_rows
from backend.services.xmltv.timezone import (
    ScheduleConversionError,
    build_utc_schedule,
)
from backend.services.xmltv.validator import ValidationEngine
from backend.services.xmltv.validation_report import (
    generate_xmltv_validation_report,
)
from backend.api.auth import (
    access_for_user,
    current_user,
    registered_channel_for_user,
    require_active_organization,
    require_module,
)


router = APIRouter(
    prefix="/api/xmltv",
    tags=["XMLTV"],
    dependencies=[Depends(require_active_organization)],
)

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
EXCEL_TEMPLATE = ASSETS_DIR / "Broadcast_Tool_Pro_XMLTV_Template.xlsx"


def _filename_channel(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", ascii_value.lower()) or "channel"


def xmltv_output_filename(
    channel_name: str,
    channel_id: str,
    programmes: list[dict],
) -> str:
    dates = sorted(
        date.fromisoformat(str(programme["air_date"]))
        for programme in programmes
    )
    channel = _filename_channel(channel_name or channel_id)
    period = (
        f"{dates[0].strftime('%m%d%Y')}-"
        f"{dates[-1].strftime('%m%d%Y')}"
    )
    return f"{channel}_{period}.xml"


def fix_category(fix: dict) -> tuple[str, str]:
    message = fix["message"]

    if fix["field"] in {"Duration (Optional)", "Duration (Conditional)"}:
        return "duration", "Convert numeric durations to HH:MM:SS."

    if fix["field"] in {"Premiere", "Live", "New"}:
        return "boolean", "Normalize localized Yes/No values."

    if message.startswith("Continuation row"):
        return "continuation", "Merge continuation rows into one programme."

    if message.startswith("Exact duplicate"):
        return "duplicate", "Remove exact duplicate rows."

    return "other", message


@router.get("/template/excel", response_class=FileResponse)
def download_excel_template(
    _user: dict = Depends(require_module("xmltv_generator")),
):
    return FileResponse(
        EXCEL_TEMPLATE,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        filename="Broadcast_Tool_Pro_XMLTV_Template.xlsx",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/template/csv", response_class=Response)
def download_csv_template(
    _user: dict = Depends(require_module("xmltv_generator")),
):
    content = ",".join(EXPECTED_COLUMNS) + "\n"
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Content-Disposition": (
                'attachment; filename="Broadcast_Tool_Pro_XMLTV_Template.csv"'
            ),
        },
    )


async def process_schedule(
    schedule_file: UploadFile,
    channel_timezone: str,
    apply_fixes: bool = False,
    expected_channel_name: str | None = None,
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
    missing_channel_rows = []
    mismatched_channel_rows = []
    mismatched_channel_values = {}

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

        row_channel = str(row.get("Channel") or "").strip()
        if not row_channel:
            missing_channel_rows.append(source_row)
            parsing_issues.append(
                ValidationIssue(
                    rule_id="VAL-011",
                    row=source_row,
                    field="Channel",
                    severity="warning",
                    message=(
                        "Channel is required. Select the registered channel "
                        "and enter its name on every programme row."
                    ),
                )
            )
        elif (
            expected_channel_name
            and row_channel.casefold() != expected_channel_name.strip().casefold()
        ):
            mismatched_channel_rows.append(source_row)
            mismatched_channel_values[source_row] = row_channel
            parsing_issues.append(
                ValidationIssue(
                    rule_id="VAL-012",
                    row=source_row,
                    field="Channel",
                    severity="warning",
                    message=(
                        f'Channel must match the selected registered channel '
                        f'"{expected_channel_name}".'
                    ),
                )
            )

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
        auto_fixed=len(auto_fixes) if apply_fixes else 0,
    )
    utc_schedule = []

    channel_identity_blocked = bool(
        missing_channel_rows or mismatched_channel_rows
    )

    if report.critical == 0 and not channel_identity_blocked:
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
                auto_fixed=len(auto_fixes) if apply_fixes else 0,
            )

    fix_counts = Counter(fix_category(fix) for fix in auto_fixes)
    fix_summary = [
        {"code": code, "message": message, "count": count}
        for (code, message), count in fix_counts.items()
    ]

    validation = report.to_dict()
    for issue in validation["issues"]:
        if issue["rule_id"] in {"VAL-011", "VAL-012"}:
            issue["expected_channel"] = expected_channel_name
        if issue["rule_id"] == "VAL-012":
            issue["actual_channel"] = mismatched_channel_values.get(
                issue["row"],
                "",
            )
    if channel_identity_blocked:
        validation["ready_to_generate"] = False
        validation["processing_blocked"] = True

    return {
        "success": report.critical == 0 and not channel_identity_blocked,
        "filename": filename,
        "file_type": extension,
        "rows_received": len(rows),
        "programmes_imported": len(programmes),
        "channel_timezone": channel_timezone,
        "validation": validation,
        "missing_columns": [],
        "unknown_columns": unknown_columns,
        "suggested_fixes": len(auto_fixes),
        "requires_authorization": bool(auto_fixes) and not apply_fixes,
        "fixes_applied": apply_fixes,
        "fix_summary": fix_summary,
        "auto_fixes": auto_fixes,
        "programmes": utc_schedule if not channel_identity_blocked else [],
    }


@router.post("/import")
async def import_schedule(
    schedule_file: UploadFile = File(...),
    channel_timezone: str = Form(...),
    channel_id: str = Form(...),
    user: dict = Depends(require_module("xmltv_generator")),
):
    channel = (
        registered_channel_for_user(user, channel_id)
        if isinstance(user, dict)
        else None
    )
    return await process_schedule(
        schedule_file,
        channel["timezone"] if channel else channel_timezone,
        apply_fixes=False,
        expected_channel_name=channel["name"] if channel else None,
    )


@router.post("/validate")
async def validate_xmltv_file(
    xmltv_file: UploadFile = File(...),
    _user: dict = Depends(require_module("xmltv_validator")),
):
    filename = xmltv_file.filename or ""

    if Path(filename).suffix.lower() != ".xml":
        raise HTTPException(
            status_code=400,
            detail="Only .xml files are supported.",
        )

    result = validate_xmltv(await xmltv_file.read())

    return {
        **result,
        "filename": filename,
    }


@router.post("/validate/report/pdf", response_class=Response)
def download_xmltv_validation_report(
    report: dict,
    user: dict = Depends(current_user),
    _module_user: dict = Depends(require_module("xmltv_validator")),
):
    content = generate_xmltv_validation_report(report)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'attachment; filename="xmltv-validation-report.pdf"'
            ),
        },
    )


async def process_xmltv_repair(xmltv_file: UploadFile) -> tuple[str, dict]:
    filename = xmltv_file.filename or ""

    if Path(filename).suffix.lower() != ".xml":
        raise HTTPException(
            status_code=400,
            detail="Only .xml files are supported.",
        )

    try:
        result = repair_xmltv(await xmltv_file.read())
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return filename, result


@router.post("/repair/preview")
async def preview_xmltv_repair(
    xmltv_file: UploadFile = File(...),
    _user: dict = Depends(require_module("xmltv_repair")),
):
    filename, result = await process_xmltv_repair(xmltv_file)

    return {
        "filename": filename,
        "repairable": result["repairable"],
        "changes_count": result["changes_count"],
        "changes": result["changes"],
        "validation": result["validation"],
    }


@router.post("/repair", response_class=Response)
async def download_repaired_xmltv(
    xmltv_file: UploadFile = File(...),
    accept_repairs: bool = Form(False),
    _user: dict = Depends(require_module("xmltv_repair")),
):
    filename, result = await process_xmltv_repair(xmltv_file)

    if result["changes_count"] and not accept_repairs:
        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    f"{result['changes_count']} safe repairs require "
                    "authorization before download."
                ),
                "changes_count": result["changes_count"],
                "changes": result["changes"],
            },
        )

    output_name = f"{Path(filename).stem}-repaired.xml"

    return Response(
        content=result["xml"],
        media_type="application/xml",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{output_name}"'
            ),
        },
    )


@router.post("/generate", response_class=Response)
async def generate_schedule(
    schedule_file: UploadFile = File(...),
    channel_timezone: str = Form(...),
    channel_id: str = Form(...),
    channel_name: str = Form(""),
    accept_auto_fixes: bool = Form(False),
    timestamp_format: str = Form("xmltv"),
    user: dict = Depends(require_module("xmltv_generator")),
):
    if not isinstance(timestamp_format, str):
        timestamp_format = "xmltv"

    channel = (
        registered_channel_for_user(user, channel_id)
        if isinstance(user, dict)
        else {
            "name": channel_name,
            "slug": channel_id,
            "channel_code": channel_id,
            "timezone": channel_timezone,
            "primary_language": "en",
        }
    )
    if not channel.get("primary_language") or channel["primary_language"] == "und":
        raise HTTPException(
            status_code=422,
            detail={
                "score": 0,
                "critical": 1,
                "errors": 0,
                "warnings": 0,
                "ready_to_generate": False,
                "issues": [{
                    "rule_id": "CHANNEL-LANGUAGE",
                    "severity": "critical",
                    "message": (
                        "Set the active channel's primary language in Channel "
                        "Settings before generating XMLTV."
                    ),
                    "row": None,
                    "field": "Channel Primary Language",
                }],
            },
        )
    result = await process_schedule(
        schedule_file,
        channel["timezone"],
        apply_fixes=accept_auto_fixes,
        expected_channel_name=channel["name"],
    )

    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail=result["validation"],
        )

    if result["suggested_fixes"] and not accept_auto_fixes:
        raise HTTPException(
            status_code=422,
            detail={
                **result["validation"],
                "ready_to_generate": False,
                "suggested_fixes": result["suggested_fixes"],
                "issues": [{
                    "rule_id": "AUTH-001",
                    "severity": "critical",
                    "message": (
                        f"{result['suggested_fixes']} safe corrections "
                        "require authorization before XMLTV generation."
                    ),
                    "row": None,
                    "field": "Authorization",
                }],
            },
        )

    xml = generate_xmltv(
        programmes=result["programmes"],
        channel_id=(channel.get("channel_code") or channel["slug"]),
        channel_name=channel["name"],
        primary_language=channel["primary_language"],
        timestamp_format=timestamp_format.strip(),
    )
    output_name = xmltv_output_filename(
        channel["name"],
        channel.get("channel_code") or channel["slug"],
        result["programmes"],
    )

    return Response(
        content=xml,
        media_type="application/xml",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{output_name}"'
            ),
        },
    )


@router.post("/programming-grid", response_class=Response)
async def download_programming_grid(
    schedule_file: UploadFile = File(...),
    channel_timezone: str = Form(...),
    channel_name: str = Form(""),
    channel_id: str = Form(...),
    accept_auto_fixes: bool = Form(False),
    channel_logo: UploadFile | None = File(None),
    user: dict = Depends(require_module("programming_grid")),
):
    channel = (
        registered_channel_for_user(user, channel_id)
        if isinstance(user, dict)
        else {
            "name": channel_name,
            "slug": "channel",
            "channel_code": "channel",
            "timezone": channel_timezone,
        }
    )
    access = access_for_user(user) if isinstance(user, dict) else None
    result = await process_schedule(
        schedule_file,
        channel["timezone"],
        apply_fixes=accept_auto_fixes,
        expected_channel_name=channel["name"],
    )

    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail=result["validation"],
        )

    if result["suggested_fixes"] and not accept_auto_fixes:
        raise HTTPException(
            status_code=422,
            detail={
                **result["validation"],
                "ready_to_generate": False,
                "suggested_fixes": result["suggested_fixes"],
                "issues": [{
                    "rule_id": "AUTH-001",
                    "severity": "critical",
                    "message": (
                        f"{result['suggested_fixes']} safe corrections "
                        "require authorization before PDF generation."
                    ),
                    "row": None,
                    "field": "Authorization",
                }],
            },
        )

    clean_channel_name = channel["name"]

    logo_content = None
    if channel_logo and getattr(channel_logo, "filename", None):
        logo_extension = Path(channel_logo.filename).suffix.lower()
        if logo_extension not in {".png", ".jpg", ".jpeg"}:
            raise HTTPException(
                status_code=422,
                detail="The channel logo must be a PNG, JPG, or JPEG image.",
            )
        logo_content = await channel_logo.read()

    try:
        pdf = generate_programming_grid(
            programmes=result["programmes"],
            channel_name=clean_channel_name,
            channel_code=channel.get("channel_code") or channel["slug"],
            organization_name=(
                access["organization"]["name"] if access else "Organization"
            ),
            timezone_name=channel["timezone"],
            logo_content=logo_content,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    output_name = (
        clean_channel_name.lower().replace(" ", "-")
        + "-programming-grid.pdf"
    )

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{output_name}"'
            ),
        },
    )
