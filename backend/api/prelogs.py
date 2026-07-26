from collections import Counter

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.services.traffic.playlist import (
    filter_playlist_events,
    inspect_playlist,
    parse_playlist_events,
)


router = APIRouter(
    prefix="/api/prelogs",
    tags=["Pre Logs"],
)


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
):
    events = []
    files = []

    try:
        for playlist_file in playlist_files:
            structure, parsed_events = parse_playlist_events(
                await playlist_file.read()
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
        },
        "matches": [
            event.to_dict()
            for event in matches[:200]
        ],
        "matches_truncated": len(matches) > 200,
    }


@router.post("/options")
async def playlist_filter_options(
    playlist_files: list[UploadFile] = File(...),
):
    events = []
    files = []

    try:
        for playlist_file in playlist_files:
            structure, parsed_events = parse_playlist_events(
                await playlist_file.read()
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
            max(event.air_datetime for event in events).date().isoformat()
            if events
            else None
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
