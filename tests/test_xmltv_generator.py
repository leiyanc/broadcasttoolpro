import asyncio
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

from fastapi import HTTPException
from starlette.datastructures import UploadFile

from backend.api.xmltv import generate_schedule
from backend.services.xmltv.generator import generate_xmltv
from backend.services.xmltv.timezone import build_utc_schedule
from tests.test_xmltv_validator import make_programme


def test_generator_creates_valid_xmltv_structure():
    programmes = build_utc_schedule(
        [make_programme()],
        "America/New_York",
    )
    xml = generate_xmltv(
        programmes,
        channel_id="comercio-tv",
        channel_name="Comercio TV",
    )
    root = ElementTree.fromstring(xml)

    assert root.tag == "tv"
    assert root.find("./channel").attrib["id"] == "comercio-tv"
    programme = root.find("./programme")
    assert programme is not None
    assert programme.attrib["start"] == "20260718120000 +0000"
    assert programme.findtext("title") == "Morning News"
    assert programme.findtext("language") == "en"
    assert programme.findtext("episode-num[@system='assetID']")
    assert programme.findtext("length") == "1800"
    assert programme.findtext("episode-num[@system='onscreen']") == "S01E01"
    assert programme.find("live") is not None


def test_generate_endpoint_returns_downloadable_xml():
    path = Path("tests/sample_schedule.csv")
    upload = UploadFile(
        filename=path.name,
        file=BytesIO(path.read_bytes()),
    )
    response = asyncio.run(
        generate_schedule(
            upload,
            "America/New_York",
            "comercio-tv",
            "Comercio TV",
            "en",
            "en",
            "VCHIP",
            False,
        )
    )
    root = ElementTree.fromstring(response.body)

    assert response.media_type == "application/xml"
    assert "comercio-tv-xmltv.xml" in response.headers[
        "content-disposition"
    ]
    assert len(root.findall("./programme")) == 2


def localized_upload() -> UploadFile:
    lines = Path("tests/sample_schedule.csv").read_text().splitlines()
    row = (
        lines[1]
        .replace("00:30:00", "60")
        .replace(",Yes,Yes,Yes", ",Sí,Sí,Sí")
    )
    content = "\n".join([lines[0], row]).encode()
    return UploadFile(
        filename="localized_schedule.csv",
        file=BytesIO(content),
    )


def test_generate_requires_authorization_for_safe_corrections():
    try:
        asyncio.run(
            generate_schedule(
                localized_upload(),
                "America/New_York",
                "comercio-tv",
                "Comercio TV",
                "es",
                "es",
                "VCHIP",
                False,
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["issues"][0]["rule_id"] == "AUTH-001"
    else:
        raise AssertionError("Expected correction authorization to be required.")


def test_generate_applies_authorized_safe_corrections():
    response = asyncio.run(
        generate_schedule(
            localized_upload(),
            "America/New_York",
            "comercio-tv",
            "Comercio TV",
            "es",
            "es",
            "VCHIP",
            True,
        )
    )
    root = ElementTree.fromstring(response.body)

    assert root.find("./programme").attrib["stop"] == "20260718130000 +0000"
