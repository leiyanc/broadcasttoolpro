from collections import Counter
from datetime import timedelta
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from backend.api.prelogs import _filtered_events
from backend.api.auth import access_for_user, current_user, require_module
from backend.services.traffic.playlist import parse_playlist_file
from backend.services.traffic.prelog_export import (
    generate_prelog_workbook,
    safe_prelog_filename,
)
from backend.services.traffic.report_pdf import generate_report_pdf
from backend.services.report_history import record_report


router = APIRouter(
    prefix="/api/postlogs",
    tags=["Post Logs"],
    dependencies=[Depends(require_module("postlogs"))],
)


@router.post("/options")
async def postlog_filter_options(
    as_run_files: list[UploadFile] = File(...),
    source_timezone: str | None = Form(None),
):
    events = []
    files = []

    try:
        for as_run_file in as_run_files:
            structure, parsed_events = parse_playlist_file(
                as_run_file.filename or "",
                await as_run_file.read(),
                source_timezone=source_timezone,
            )
            events.extend(parsed_events)
            files.append({
                "filename": as_run_file.filename or "",
                "metadata": structure["metadata"],
                "events": len(parsed_events),
            })
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    asset_counts = Counter(event.asset_id for event in events)
    prefix_counts = Counter(
        (
            event.asset_id.split("_", 1)[0].lower() + "_"
            if "_" in event.asset_id
            else "(no prefix)"
        )
        for event in events
    )
    return {
        "files_processed": len(files),
        "events_received": len(events),
        "channels": sorted({
            event.channel_name
            for event in events
            if event.channel_name
        }),
        "start_date": (
            min(event.air_datetime for event in events).date().isoformat()
            if events
            else None
        ),
        "end_date": (
            (
                max(event.air_datetime for event in events)
                - timedelta(hours=6)
            ).date().isoformat()
            if events
            else None
        ),
        "source_timezone": source_timezone,
        "assets": [
            {"asset_id": asset, "occurrences": count}
            for asset, count in sorted(asset_counts.items())
        ],
        "prefixes": [
            {"prefix": prefix, "occurrences": count}
            for prefix, count in prefix_counts.most_common()
        ],
    }


@router.post("/filter")
async def filter_postlog_events(
    as_run_files: list[UploadFile] = File(...),
    filter_mode: str = Form("all"),
    filter_value: str | None = Form(None),
    start_date: str | None = Form(None),
    end_date: str | None = Form(None),
    broadcast_day_start: str = Form("06:00:00"),
    source_timezone: str | None = Form(None),
):
    try:
        files, events, matches = await _filtered_events(
            as_run_files,
            filter_mode,
            filter_value,
            start_date,
            end_date,
            None,
            None,
            broadcast_day_start,
            source_timezone,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "files_processed": len(files),
        "events_received": len(events),
        "matching_events": len(matches),
        "unique_assets": len({event.asset_id for event in matches}),
        "matches": [event.to_dict() for event in matches[:200]],
        "matches_truncated": len(matches) > 200,
    }


@router.post("/export")
async def export_postlog(
    as_run_files: list[UploadFile] = File(...),
    filter_mode: str = Form("all"),
    filter_value: str | None = Form(None),
    start_date: str | None = Form(None),
    end_date: str | None = Form(None),
    broadcast_day_start: str = Form("06:00:00"),
    source_timezone: str | None = Form(None),
    channel_name: str = Form(...),
    report_language: str = Form("en"),
    product: str | None = Form(None),
    agency: str | None = Form(None),
    logo_file: UploadFile | None = File(None),
    output_format: str = Form("xlsx"),
    client_name: str | None = Form(None),
    user: dict = Depends(current_user),
):
    report_owner = access_for_user(user) if isinstance(user, dict) else None
    try:
        _, _, matches = await _filtered_events(
            as_run_files,
            filter_mode,
            filter_value,
            start_date,
            end_date,
            None,
            None,
            broadcast_day_start,
            source_timezone,
        )
        if not matches:
            raise ValueError(
                "No actual airings match the selected filters."
            )

        logo_content = None
        if logo_file and logo_file.filename:
            if not logo_file.filename.lower().endswith(
                (".png", ".jpg", ".jpeg")
            ):
                raise ValueError(
                    "The channel logo must be a PNG, JPG, or JPEG file."
                )
            logo_content = await logo_file.read()
            if len(logo_content) > 2 * 1024 * 1024:
                raise ValueError("The channel logo must be 2 MB or smaller.")

        grouped_matches = {}
        for event in matches:
            grouped_matches.setdefault(event.asset_id, []).append(event)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if len(grouped_matches) == 1:
        asset_id, asset_events = next(iter(grouped_matches.items()))
        if output_format == "xlsx":
            content = generate_prelog_workbook(
                asset_events,
                channel_name=channel_name,
                language=report_language,
                product=product,
                agency=agency,
                client_name=client_name if isinstance(client_name, str) else None,
                logo_content=logo_content,
                report_type="postlog",
            )
            extension = ".xlsx"
            media_type = (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        elif output_format == "pdf":
            content = generate_report_pdf(
                asset_events,
                channel_name=channel_name,
                language=report_language,
                product=product,
                agency=agency,
                client_name=client_name if isinstance(client_name, str) else None,
                logo_content=logo_content,
                report_type="postlog",
            )
            extension = ".pdf"
            media_type = "application/pdf"
        else:
            raise HTTPException(
                status_code=422,
                detail="Output format must be XLSX or PDF.",
            )
        filename = safe_prelog_filename(
            f"postlog-{channel_name}-{asset_id}",
            start_date,
            end_date,
        ).replace("prelog-postlog-", "postlog-", 1).replace(
            ".xlsx",
            extension,
        )
    else:
        if output_format not in {"xlsx", "pdf"}:
            raise HTTPException(
                status_code=422,
                detail="Output format must be XLSX or PDF.",
            )
        archive = BytesIO()
        with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
            for asset_id, asset_events in sorted(grouped_matches.items()):
                if output_format == "xlsx":
                    report = generate_prelog_workbook(
                        asset_events,
                        channel_name=channel_name,
                        language=report_language,
                        product=product,
                        agency=agency,
                        client_name=(
                            client_name if isinstance(client_name, str) else None
                        ),
                        logo_content=logo_content,
                        report_type="postlog",
                    )
                    extension = ".xlsx"
                else:
                    report = generate_report_pdf(
                        asset_events,
                        channel_name=channel_name,
                        language=report_language,
                        product=product,
                        agency=agency,
                        client_name=(
                            client_name if isinstance(client_name, str) else None
                        ),
                        logo_content=logo_content,
                        report_type="postlog",
                    )
                    extension = ".pdf"
                workbook_name = safe_prelog_filename(
                    f"postlog-{channel_name}-{asset_id}",
                    start_date,
                    end_date,
                ).replace("prelog-postlog-", "postlog-", 1).replace(
                    ".xlsx",
                    extension,
                )
                bundle.writestr(workbook_name, report)
        content = archive.getvalue()
        filename = safe_prelog_filename(
            f"postlogs-{channel_name}",
            start_date,
            end_date,
        ).replace("prelog-postlogs-", "postlogs-", 1).replace(
            ".xlsx",
            ".zip",
        )
        media_type = "application/zip"

    report_id = record_report(
        report_type="postlog",
        client_name=client_name if isinstance(client_name, str) else None,
        channel_name=channel_name,
        product=product,
        agency=agency,
        asset_ids=list(grouped_matches),
        start_date=start_date,
        end_date=end_date,
        output_format=output_format,
        filename=filename,
        media_type=media_type,
        content=content,
        organization_id=(
            report_owner["organization"]["id"] if report_owner else None
        ),
        created_by=user["id"] if isinstance(user, dict) else None,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-ID": report_id,
        },
    )
