from fastapi import APIRouter, Body, Depends, Form, HTTPException
from fastapi.responses import Response

from backend.services.hls.validator import (
    HlsValidationError,
    validate_hls,
)
from backend.services.hls.report import generate_hls_report
from backend.api.auth import require_active_organization


router = APIRouter(
    prefix="/api/hls",
    tags=["HLS"],
    dependencies=[Depends(require_active_organization)],
)


@router.post("/validate")
def validate_hls_url(
    playlist_url: str = Form(...),
    inspect_segments: bool = Form(True),
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
):
    content = generate_hls_report(report)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'attachment; filename="broadcast-tool-pro-hls-report.pdf"'
            ),
        },
    )
