from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.services.xmltv.parser import (
    EXPECTED_COLUMNS,
    build_programme,
    read_schedule_file,
)


router = APIRouter(
    prefix="/api/xmltv",
    tags=["XMLTV"],
)


@router.post("/import")
async def import_schedule(
    schedule_file: UploadFile = File(...),
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
        return {
            "success": False,
            "filename": filename,
            "file_type": Path(filename).suffix.lower(),
            "missing_columns": missing_columns,
            "unknown_columns": unknown_columns,
            "programmes": [],
            "issues": [
                {
                    "row": 4,
                    "field": column,
                    "severity": "critical",
                    "message": f"Missing template column: {column}",
                }
                for column in missing_columns
            ],
        }

    programmes = []
    issues = []

    first_data_row = 5

    for position, row in enumerate(rows):
        source_row = first_data_row + position

        try:
            programme = build_programme(row, source_row)
            programmes.append(programme.to_dict())
        except (ValueError, TypeError) as exc:
            issues.append({
                "row": source_row,
                "field": "Programme",
                "severity": "critical",
                "message": str(exc),
            })

    critical_count = sum(
        issue["severity"] == "critical"
        for issue in issues
    )

    return {
        "success": critical_count == 0,
        "filename": filename,
        "file_type": Path(filename).suffix.lower(),
        "rows_received": len(rows),
        "programmes_imported": len(programmes),
        "validation": {
            "critical": critical_count,
            "errors": 0,
            "warnings": 0,
        },
        "missing_columns": [],
        "unknown_columns": unknown_columns,
        "issues": issues,
        "programmes": programmes[:10],
    }
