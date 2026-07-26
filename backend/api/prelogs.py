from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.services.traffic.playlist import inspect_playlist


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
