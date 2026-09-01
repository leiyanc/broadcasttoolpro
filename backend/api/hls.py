import json

from fastapi import APIRouter, Body, Depends, Form, HTTPException, status
from fastapi.responses import Response

from backend.services.hls.validator import (
    HlsValidationError,
    validate_hls,
)
from backend.services.hls.report import generate_hls_report
from backend.services.hls.loudness import (
    LoudnessAnalysisError,
    loudness_jobs,
)
from backend.api.auth import (
    access_for_user,
    current_user,
    registered_channel_for_user,
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
    monitor_mode: bool = Form(False),
    inspected_segment_urls: str = Form("[]"),
    _user: dict = Depends(require_module("hls_validator")),
):
    try:
        try:
            parsed_urls = json.loads(inspected_segment_urls)
        except json.JSONDecodeError as exc:
            raise HlsValidationError(
                "Inspected segment history must be valid JSON."
            ) from exc
        if not isinstance(parsed_urls, list) or not all(
            isinstance(item, str) for item in parsed_urls
        ):
            raise HlsValidationError(
                "Inspected segment history must be a list of URLs."
            )
        return validate_hls(
            playlist_url,
            inspect_segments=inspect_segments,
            max_variants_to_inspect=1 if monitor_mode else 10,
            inspected_segment_urls=set(parsed_urls[-500:]),
        )
    except HlsValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.post("/loudness/jobs", status_code=status.HTTP_202_ACCEPTED)
def start_loudness_analysis(
    playlist_url: str = Form(...),
    duration_minutes: int = Form(5),
    user: dict = Depends(require_module("media_qc")),
):
    try:
        validate_hls(
            playlist_url,
            inspect_segments=False,
            max_variants_to_inspect=1,
        )
        access = access_for_user(user)
        return loudness_jobs.start(
            organization_id=access["organization"]["id"],
            user_id=user["id"],
            playlist_url=playlist_url,
            duration_minutes=duration_minutes,
        )
    except (HlsValidationError, LoudnessAnalysisError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/loudness/jobs/{job_id}")
def loudness_analysis_status(
    job_id: str,
    user: dict = Depends(require_module("media_qc")),
):
    try:
        access = access_for_user(user)
        return loudness_jobs.public(job_id, access["organization"]["id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/loudness/jobs/{job_id}")
def cancel_loudness_analysis(
    job_id: str,
    user: dict = Depends(require_module("media_qc")),
):
    try:
        access = access_for_user(user)
        return loudness_jobs.cancel(job_id, access["organization"]["id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/report/pdf", response_class=Response)
def download_hls_report(
    report: dict = Body(...),
    user: dict = Depends(current_user),
    _module_user: dict = Depends(require_module("hls_validator")),
):
    channel = (
        registered_channel_for_user(user, str(report.get("channel_id", "")))
        if isinstance(user, dict)
        else {
            "name": report.get("channel_name"),
            "slug": report.get("channel_id") or "channel",
            "channel_code": report.get("channel_id"),
            "timezone": report.get("report_timezone"),
        }
    )
    trusted_report = {
        **report,
        "channel_id": channel.get("channel_code") or channel["slug"],
        "channel_name": channel["name"],
        "client_name": (
            access_for_user(user)["organization"]["name"]
            if isinstance(user, dict)
            else report.get("client_name")
        ),
        "report_timezone": channel["timezone"],
    }
    content = generate_hls_report(trusted_report)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'attachment; filename="broadcast-tool-pro-hls-report.pdf"'
            ),
        },
    )
