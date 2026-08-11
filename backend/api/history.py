from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from backend.services.report_history import get_report, list_reports
from backend.api.auth import access_for_user, require_active_organization


router = APIRouter(
    prefix="/api/history",
    tags=["Report History"],
    dependencies=[Depends(require_active_organization)],
)


@router.get("")
def report_history(
    limit: int = 100,
    user: dict = Depends(require_active_organization),
):
    organization_id = access_for_user(user)["organization"]["id"]
    entitlements = access_for_user(user)["entitlements"]
    if not entitlements["access"]["active"]:
        raise HTTPException(status_code=403, detail="Complete payment to access report history.")
    return {
        "reports": list_reports(organization_id, limit),
    }


@router.get("/{report_id}/download")
def download_historical_report(
    report_id: str,
    user: dict = Depends(require_active_organization),
):
    organization_id = access_for_user(user)["organization"]["id"]
    entitlements = access_for_user(user)["entitlements"]
    if not entitlements["access"]["active"]:
        raise HTTPException(status_code=403, detail="Complete payment to download reports.")
    report = get_report(report_id, organization_id)
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
