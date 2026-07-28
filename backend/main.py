from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.xmltv import router as xmltv_router
from backend.api.prelogs import router as prelogs_router
from backend.api.postlogs import router as postlogs_router
from backend.api.history import router as history_router
from backend.api.hls import router as hls_router
from backend.api.platform import router as platform_router
from backend.api.auth import router as auth_router
from backend.api.admin import router as admin_router
from backend.api.billing import router as billing_router


app = FastAPI(
    title="Broadcast Tool Pro",
    version="0.1.0",
)


app.include_router(xmltv_router)
app.include_router(prelogs_router)
app.include_router(postlogs_router)
app.include_router(history_router)
app.include_router(hls_router)
app.include_router(platform_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(billing_router)

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }
