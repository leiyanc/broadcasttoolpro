from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from backend.services.report_history import get_report, list_reports
from backend.api.auth import require_active_organization


router = APIRouter(
    prefix="/api/history",
    tags=["Report History"],
    dependencies=[Depends(require_active_organization)],
)


@router.get("")
def report_history(limit: int = 100):
    return {
        "reports": list_reports(limit),
    }


@router.get("/{report_id}/download")
def download_historical_report(report_id: str):
    report = get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    file_path = Path(report["file_path"])
    if not file_path.is_file():
        raise HTTPException(
            status_code=410,
            detail="The archived report file is no longer available.",
        )

    return FileResponse(
        file_path,
        media_type=report["media_type"],
        filename=report["filename"],
    )
