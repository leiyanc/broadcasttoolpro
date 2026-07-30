from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from backend.services.traffic.prelog_export import (
    generate_prelog_workbook,
    safe_prelog_filename,
)
from backend.services.traffic.report_pdf import generate_report_pdf
from backend.services.report_history import record_report
from backend.services.traffic.playlist import (
    filter_playlist_events,
    inspect_playlist,
    parse_playlist_file,
)
from backend.api.auth import current_user, is_trial_user, require_module


router = APIRouter(
    prefix="/api/prelogs",
    tags=["Pre Logs"],
    dependencies=[Depends(require_module("prelogs"))],
)


async def _filtered_events(
    playlist_files: list[UploadFile],
    filter_mode: str,
    filter_value: str | None,
    start_date: str | None,
    end_date: str | None,
    start_time: str | None,
    end_time: str | None,
    broadcast_day_start: str,
    source_timezone: str | None,
):
    events = []
    files = []

    for playlist_file in playlist_files:
        structure, parsed_events = parse_playlist_file(
            playlist_file.filename or "",
            await playlist_file.read(),
            source_timezone=source_timezone,
            operational_date=start_date,
        )
        events.extend(parsed_events)
        files.append({
            "filename": playlist_file.filename or "",
            "metadata": structure["metadata"],
            "events": len(parsed_events),
        })

    matches = filter_playlist_events(
        events,
        filter_mode=filter_mode,
        filter_value=filter_value,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        broadcast_day_start=broadcast_day_start,
    )
    return files, events, matches


@router.post("/inspect")
async def inspect_playlist_file(
    playlist_file: UploadFile = File(...),
):
    filename = playlist_file.filename or ""

    try:
        result = inspect_playlist(await playlist_file.read())
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return {
        **result,
        "filename": filename,
    }


@router.post("/filter")
async def filter_playlist_files(
    playlist_files: list[UploadFile] = File(...),
    filter_mode: str = Form("all"),
    filter_value: str | None = Form(None),
    start_date: str | None = Form(None),
    end_date: str | None = Form(None),
    start_time: str | None = Form(None),
    end_time: str | None = Form(None),
    broadcast_day_start: str = Form("06:00:00"),
    source_timezone: str | None = Form(None),
):
    try:
        files, events, matches = await _filtered_events(
            playlist_files,
            filter_mode,
            filter_value,
            start_date,
            end_date,
            start_time,
            end_time,
            broadcast_day_start,
            source_timezone,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return {
        "files_processed": len(files),
        "files": files,
        "events_received": len(events),
        "matching_events": len(matches),
        "unique_assets": len({
            event.asset_id
            for event in matches
        }),
        "filters": {
            "mode": filter_mode,
            "value": filter_value,
            "start_date": start_date,
            "end_date": end_date,
            "start_time": start_time,
            "end_time": end_time,
            "broadcast_day_start": broadcast_day_start,
            "source_timezone": source_timezone,
        },
        "matches": [
            event.to_dict()
            for event in matches[:200]
        ],
        "matches_truncated": len(matches) > 200,
    }


@router.post("/export")
async def export_prelog(
    playlist_files: list[UploadFile] = File(...),
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
    is_trial = is_trial_user(user)
    if is_trial and output_format != "pdf":
        raise HTTPException(
            status_code=403,
            detail="Free Trial reports can only be downloaded as PDF.",
        )
    try:
        _, _, matches = await _filtered_events(
            playlist_files,
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
                "No scheduled events match the selected filters."
            )

        logo_content = None
        if logo_file and logo_file.filename:
            allowed_logo_extensions = (".png", ".jpg", ".jpeg")
            if not logo_file.filename.lower().endswith(
                allowed_logo_extensions
            ):
                raise ValueError(
                    "The channel logo must be a PNG, JPG, or JPEG file."
                )
            logo_content = await logo_file.read()
            if len(logo_content) > 2 * 1024 * 1024:
                raise ValueError("The channel logo must be 2 MB or smaller.")

        if output_format == "xlsx":
            content = generate_prelog_workbook(
                matches,
                channel_name=channel_name,
                language=report_language,
                product=product,
                agency=agency,
                client_name=client_name if isinstance(client_name, str) else None,
                logo_content=logo_content,
            )
            media_type = (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        elif output_format == "pdf":
            content = generate_report_pdf(
                matches,
                channel_name=channel_name,
                language=report_language,
                product=product,
                agency=agency,
                client_name=client_name if isinstance(client_name, str) else None,
                logo_content=logo_content,
                report_type="prelog",
                trial_watermark=is_trial,
            )
            media_type = "application/pdf"
        else:
            raise ValueError("Output format must be XLSX or PDF.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    filename = safe_prelog_filename(channel_name, start_date, end_date)
    if output_format == "pdf":
        filename = filename.replace(".xlsx", ".pdf")
    report_id = record_report(
        report_type="prelog",
        client_name=client_name if isinstance(client_name, str) else None,
        channel_name=channel_name,
        product=product,
        agency=agency,
        asset_ids=[event.asset_id for event in matches],
        start_date=start_date,
        end_date=end_date,
        output_format=output_format,
        filename=filename,
        media_type=media_type,
        content=content,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-ID": report_id,
        },
    )


@router.post("/options")
async def playlist_filter_options(
    playlist_files: list[UploadFile] = File(...),
    source_timezone: str | None = Form(None),
    start_date: str | None = Form(None),
):
    events = []
    files = []

    try:
        for playlist_file in playlist_files:
            structure, parsed_events = parse_playlist_file(
                playlist_file.filename or "",
                await playlist_file.read(),
                source_timezone=source_timezone,
                operational_date=start_date,
            )
            events.extend(parsed_events)
            files.append({
                "filename": playlist_file.filename or "",
                "metadata": structure["metadata"],
                "events": len(parsed_events),
            })
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

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
        "files": files,
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
        "source_timezone": (
            source_timezone
            or next(
                (
                    item["metadata"]["source_timezone"]
                    for item in files
                    if item["metadata"]["source_timezone"]
                ),
                None,
            )
        ),
        "assets": [
            {
                "asset_id": asset_id,
                "occurrences": count,
            }
            for asset_id, count in sorted(asset_counts.items())
        ],
        "prefixes": [
            {
                "prefix": prefix,
                "occurrences": count,
            }
            for prefix, count in prefix_counts.most_common()
        ],
    }
