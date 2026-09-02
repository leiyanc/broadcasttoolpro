import asyncio
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from fastapi import HTTPException
from starlette.datastructures import UploadFile

from backend.api.xmltv import generate_schedule, xmltv_output_filename
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
    assert programme.find("rating").attrib["system"] == "VCHIP"
    assert programme.findtext("orig-language") == "en"


def test_generator_omits_incomplete_rating_and_original_language():
    programme = make_programme(
        parental_rating="TV-PG",
        rating_system=None,
        original_language=None,
    ).to_dict()
    programme.update({
        "xmltv_start": "20260718120000 +0000",
        "xmltv_stop": "20260718123000 +0000",
        "iso_start": "2026-07-18T12:00:00.000+0000",
        "iso_stop": "2026-07-18T12:30:00.000+0000",
    })
    root = ElementTree.fromstring(generate_xmltv(
        [programme],
        channel_id="global-tv",
        channel_name="Global TV",
        primary_language="es",
    ))

    assert root.find("./programme/rating") is None
    assert root.find("./programme/orig-language") is None


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
            "sample-tv",
            "Sample TV",
            False,
        )
    )
    root = ElementTree.fromstring(response.body)

    assert response.media_type == "application/xml"
    assert "sampletv_07182026-07182026.xml" in response.headers[
        "content-disposition"
    ]
    assert len(root.findall("./programme")) == 2


def test_output_filename_uses_safe_channel_name_and_local_date_period():
    filename = xmltv_output_filename(
        "Televisión Ñandú 24/7",
        "fallback-channel",
        [
            {"air_date": "2026-08-23"},
            {"air_date": "2026-08-17"},
            {"air_date": "2026-08-20"},
        ],
    )

    assert filename == "televisionnandu247_08172026-08232026.xml"


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
                "sample-tv",
                "Sample TV",
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
            "sample-tv",
            "Sample TV",
            True,
        )
    )
    root = ElementTree.fromstring(response.body)

    assert root.find("./programme").attrib["stop"] == "20260718130000 +0000"


def test_generate_uses_registered_channel_language():
    registered_channel = {
        "name": "TARIMA TV",
        "slug": "tarima-tv",
        "channel_code": "tarima-tv",
        "timezone": "UTC",
        "primary_language": "es",
    }
    with patch(
        "backend.api.xmltv.registered_channel_for_user",
        return_value=registered_channel,
    ):
        response = asyncio.run(generate_schedule(
            UploadFile(
                filename="sample_schedule.csv",
                file=BytesIO(
                    Path("tests/sample_schedule.csv").read_bytes().replace(
                        b"Sample TV",
                        b"TARIMA TV",
                    )
                ),
            ),
            "UTC",
            "channel-record-id",
            "TARIMA TV",
            False,
            user={"id": "user-id"},
        ))

    root = ElementTree.fromstring(response.body)
    assert root.find("./channel/display-name").attrib["lang"] == "es"
    assert root.find("./programme/title").attrib["lang"] == "es"
    assert root.findtext("./programme/language") == "es"
    assert root.findtext("./programme/orig-language") == "en"
    assert root.find("./programme/rating").attrib["system"] == "VCHIP"


def test_generate_blocks_undefined_registered_channel_language():
    channel = {
        "name": "Legacy TV",
        "slug": "legacy-tv",
        "channel_code": "legacy-tv",
        "timezone": "UTC",
        "primary_language": "und",
    }
    with patch(
        "backend.api.xmltv.registered_channel_for_user",
        return_value=channel,
    ):
        try:
            asyncio.run(generate_schedule(
                UploadFile(
                    filename="sample_schedule.csv",
                    file=BytesIO(Path("tests/sample_schedule.csv").read_bytes()),
                ),
                "UTC",
                "channel-record-id",
                "Legacy TV",
                False,
                user={"id": "user-id"},
            ))
        except HTTPException as exc:
            assert exc.status_code == 422
            assert exc.detail["issues"][0]["rule_id"] == "CHANNEL-LANGUAGE"
        else:
            raise AssertionError("Expected undefined channel language to block export.")
