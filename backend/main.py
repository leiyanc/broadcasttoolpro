from fastapi import FastAPI

from backend.api.xmltv import router as xmltv_router


app = FastAPI(
    title="Broadcast Tool Pro",
    version="0.1.0",
)


app.include_router(xmltv_router)


@app.get("/")
def home():
    return {
        "message": "Broadcast Tool Pro is running",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }
