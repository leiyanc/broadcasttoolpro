import asyncio
from io import BytesIO

from fastapi import HTTPException
from starlette.datastructures import UploadFile

from backend.api.xmltv import (
    download_repaired_xmltv,
    preview_xmltv_repair,
)
from backend.services.xmltv.feed_repair import repair_xmltv


REPAIRABLE_XMLTV = b"""<tv>
  <channel id=" news ">
    <display-name>News</display-name>
  </channel>
  <programme
    start="2026-07-18 12:00:00 +0000"
    channel=" news "
  >
    <title>Morning News</title>
    <desc />
  </programme>
  <programme
    start="20260718123000+0000"
    stop="20260718130000+0000"
    channel="news"
  >
    <title>Market Update</title>
  </programme>
</tv>"""


def repair_upload() -> UploadFile:
    return UploadFile(
        filename="schedule.xml",
        file=BytesIO(REPAIRABLE_XMLTV),
    )


def test_safe_repairs_preserve_missing_metadata_findings():
    result = repair_xmltv(REPAIRABLE_XMLTV)
    rule_ids = {change["rule_id"] for change in result["changes"]}
    validation_rule_ids = {
        issue["rule_id"]
        for issue in result["validation"]["validation"]["issues"]
    }

    assert result["changes_count"] == 7
    assert {
        "REPAIR-001",
        "REPAIR-002",
        "REPAIR-003",
        "REPAIR-004",
    } <= rule_ids
    assert result["validation"]["valid"] is False
    assert {"XMLTV-017", "XMLTV-018"} <= validation_rule_ids
    assert b'stop="20260718123000 +0000"' in result["xml"]


def test_repair_preview_lists_changes_without_returning_xml():
    result = asyncio.run(preview_xmltv_repair(repair_upload()))

    assert result["filename"] == "schedule.xml"
    assert result["changes_count"] == 7
    assert "xml" not in result


def test_repair_download_requires_authorization():
    try:
        asyncio.run(download_repaired_xmltv(repair_upload(), False))
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["changes_count"] == 7
    else:
        raise AssertionError("Expected repair authorization to be required.")


def test_authorized_repair_returns_downloadable_xml():
    response = asyncio.run(download_repaired_xmltv(repair_upload(), True))

    assert response.media_type == "application/xml"
    assert "schedule-repaired.xml" in response.headers[
        "content-disposition"
    ]
    assert b"<desc" not in response.body


def test_malformed_xml_cannot_be_repaired():
    try:
        repair_xmltv(b"<tv><channel></tv>")
    except ValueError as exc:
        assert "not well formed" in str(exc)
    else:
        raise AssertionError("Expected malformed XML to be rejected.")


def test_bare_ampersand_is_repaired_without_changing_displayed_text():
    content = b"""<tv>
  <channel id="news"><display-name>News &amp; Analysis</display-name></channel>
  <programme start="20260718120000 +0000" stop="20260718123000 +0000" channel="news">
    <title>Markets & Business</title><desc>News & analysis</desc>
    <category>News</category><episode-num system="assetID">markets</episode-num>
    <rating system="VCHIP"><value>TV-G</value></rating>
  </programme>
</tv>"""
    result = repair_xmltv(content)

    assert result["repairable"] is True
    assert sum(
        change["rule_id"] == "REPAIR-005"
        for change in result["changes"]
    ) == 2
    assert b"Markets &amp; Business" in result["xml"]
    assert result["validation"]["valid"] is True
