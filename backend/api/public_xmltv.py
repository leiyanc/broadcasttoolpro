from io import BytesIO

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.services.xmltv.feed_validator import MAX_XMLTV_SIZE
from backend.services.xmltv.public_validation_report import generate_public_xmltv_report
from backend.services.xmltv.public_validator import validate_public_xmltv


router = APIRouter(prefix="/api/public/xmltv", tags=["public-xmltv"])


async def _read_xml(file: UploadFile) -> bytes:
    filename = file.filename or ""
    if not filename.lower().endswith(".xml"):
        raise HTTPException(status_code=400, detail="Please upload an XML file.")
    content = await file.read(MAX_XMLTV_SIZE + 1)
    if len(content) > MAX_XMLTV_SIZE:
        raise HTTPException(status_code=413, detail="The XMLTV file exceeds the 10 MB limit.")
    return content


@router.post("/validate")
async def validate_public_file(file: UploadFile = File(...)):
    content = await _read_xml(file)
    return {"filename": file.filename, **validate_public_xmltv(content)}


@router.post("/report/pdf")
async def download_public_report(
    file: UploadFile = File(...),
    language: str = Form("en"),
):
    content = await _read_xml(file)
    payload = {"filename": file.filename, **validate_public_xmltv(content)}
    report = generate_public_xmltv_report(payload, "es" if language == "es" else "en")
    return StreamingResponse(
        BytesIO(report),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="btp-xmltv-validation-report.pdf"'},
    )
