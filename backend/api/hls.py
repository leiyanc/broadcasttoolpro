from fastapi import APIRouter, Body, Depends, Form, HTTPException
from fastapi.responses import Response

from backend.services.hls.validator import (
    HlsValidationError,
    validate_hls,
)
from backend.services.hls.report import generate_hls_report
from backend.api.auth import (
    current_user,
    is_trial_user,
    require_active_organization,
    require_module,
)


router = APIRouter(
    prefix="/api/hls",
    tags=["HLS"],
    dependencies=[Depends(require_active_organization)],
)


@router.post("/validate")
def validate_hls_url(
    playlist_url: str = Form(...),
    inspect_segments: bool = Form(True),
    _user: dict = Depends(require_module("hls_validator")),
):
    try:
        return validate_hls(
            playlist_url,
            inspect_segments=inspect_segments,
        )
    except HlsValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.post("/report/pdf", response_class=Response)
def download_hls_report(
    report: dict = Body(...),
    user: dict = Depends(current_user),
    _module_user: dict = Depends(require_module("hls_validator")),
):
    content = generate_hls_report(
        report,
        trial_watermark=is_trial_user(user),
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'attachment; filename="broadcast-tool-pro-hls-report.pdf"'
            ),
        },
    )
