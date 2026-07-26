import asyncio
from io import BytesIO

from starlette.datastructures import UploadFile

from backend.api.xmltv import validate_xmltv_file
from backend.services.xmltv.feed_validator import validate_xmltv


VALID_XMLTV = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="news">
    <display-name>News</display-name>
  </channel>
  <programme
    start="20260718120000 +0000"
    stop="20260718123000 +0000"
    channel="news"
  >
    <title>Morning News</title>
  </programme>
</tv>
"""


def test_valid_xmltv_passes():
    result = validate_xmltv(VALID_XMLTV)

    assert result["valid"] is True
    assert result["well_formed"] is True
    assert result["channels"] == 1
    assert result["programmes"] == 1
    assert result["validation"]["score"] == 100


def test_malformed_xml_reports_source_line():
    result = validate_xmltv(b"<tv>\n<channel></tv>")
    issue = result["validation"]["issues"][0]

    assert result["valid"] is False
    assert result["well_formed"] is False
    assert issue["rule_id"] == "XMLTV-003"
    assert issue["row"] == 2


def test_missing_attributes_unknown_channel_and_title_are_critical():
    xml = b"""<tv>
  <channel id="news"><display-name>News</display-name></channel>
  <programme start="invalid" channel="sports"><title /></programme>
</tv>"""
    result = validate_xmltv(xml)
    rule_ids = {
        issue["rule_id"]
        for issue in result["validation"]["issues"]
    }

    assert result["valid"] is False
    assert {"XMLTV-009", "XMLTV-010", "XMLTV-011", "XMLTV-013"} <= rule_ids


def test_duplicate_channel_and_invalid_duration_are_critical():
    xml = b"""<tv>
  <channel id="news"><display-name>News</display-name></channel>
  <channel id="news"><display-name>News Duplicate</display-name></channel>
  <programme
    start="20260718130000 +0000"
    stop="20260718120000 +0000"
    channel="news"
  ><title>News</title></programme>
</tv>"""
    result = validate_xmltv(xml)
    rule_ids = {
        issue["rule_id"]
        for issue in result["validation"]["issues"]
    }

    assert {"XMLTV-006", "XMLTV-012"} <= rule_ids


def test_validate_endpoint_returns_report():
    upload = UploadFile(
        filename="schedule.xml",
        file=BytesIO(VALID_XMLTV),
    )
    result = asyncio.run(validate_xmltv_file(upload))

    assert result["filename"] == "schedule.xml"
    assert result["valid"] is True
