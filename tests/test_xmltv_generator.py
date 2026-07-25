import asyncio
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

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
        )
    )
    root = ElementTree.fromstring(response.body)

    assert response.media_type == "application/xml"
    assert "comercio-tv-xmltv.xml" in response.headers[
        "content-disposition"
    ]
    assert len(root.findall("./programme")) == 2
