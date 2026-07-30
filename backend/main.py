import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env.local")

from backend.api.xmltv import router as xmltv_router
from backend.api.prelogs import router as prelogs_router
from backend.api.postlogs import router as postlogs_router
from backend.api.history import router as history_router
from backend.api.hls import router as hls_router
from backend.api.platform import router as platform_router
from backend.api.auth import router as auth_router
from backend.api.admin import router as admin_router
from backend.api.billing import router as billing_router
from backend.api.support import router as support_router
from backend.api.email_events import router as email_events_router
from backend.services.backup_manager import backup_manager
from backend.services.google_drive_backup import google_drive_backup
from backend.services.email_delivery import email_delivery_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop_event = asyncio.Event()

    async def backup_loop():
        while not stop_event.is_set():
            try:
                backup = await asyncio.to_thread(
                    backup_manager.create_if_due
                )
                if backup and google_drive_backup.is_authorized():
                    await asyncio.to_thread(
                        google_drive_backup.upload_safely,
                        backup_directory=backup_manager.backup_directory,
                        manifest=backup,
                    )
            except Exception:
                pass
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=60 * 60)
            except TimeoutError:
                continue

    async def email_delivery_loop():
        while not stop_event.is_set():
            try:
                await asyncio.to_thread(email_delivery_service.deliver_due)
            except Exception:
                pass
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=30)
            except TimeoutError:
                continue

    backup_task = asyncio.create_task(backup_loop())
    email_delivery_task = asyncio.create_task(email_delivery_loop())
    yield
    stop_event.set()
    await asyncio.gather(backup_task, email_delivery_task)


app = FastAPI(
    title="Broadcast Tool Pro",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    if request.url.path.startswith("/api/auth"):
        response.headers["Cache-Control"] = "no-store"
    if (
        os.getenv("BTP_ENV", "").lower() != "production"
        and (
            request.url.path.startswith("/static/")
            or request.url.path in {"/", "/app"}
        )
    ):
        response.headers["Cache-Control"] = "no-store"
    if os.getenv("BTP_ENV", "").lower() == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


app.include_router(xmltv_router)
app.include_router(prelogs_router)
app.include_router(postlogs_router)
app.include_router(history_router)
app.include_router(hls_router)
app.include_router(platform_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(billing_router)
app.include_router(support_router)
app.include_router(email_events_router)

FRONTEND_DIR = PROJECT_ROOT / "frontend"
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "landing.html")


@app.get("/app")
def application():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "backup": backup_manager.status()["status"],
        "email_delivery": (
            "enabled" if email_delivery_service.is_enabled() else "disabled"
        ),
    }
