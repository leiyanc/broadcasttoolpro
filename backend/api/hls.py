from fastapi import APIRouter, Form, HTTPException

from backend.services.hls.validator import (
    HlsValidationError,
    validate_hls,
)


router = APIRouter(
    prefix="/api/hls",
    tags=["HLS"],
)


@router.post("/validate")
def validate_hls_url(
    playlist_url: str = Form(...),
):
    try:
        return validate_hls(playlist_url)
    except HlsValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
