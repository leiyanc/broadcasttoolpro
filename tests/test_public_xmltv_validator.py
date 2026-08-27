from backend.services.xmltv.public_validation_report import generate_public_xmltv_report
from backend.services.xmltv.public_validator import validate_public_xmltv


def _xml(programme_metadata: str = "", stop: str = ' stop="20260827130000 -0400"') -> bytes:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="sample"><display-name>Sample TV</display-name></channel>
  <programme start="20260827120000 -0400"{stop} channel="sample">
    <title>News</title>{programme_metadata}
  </programme>
</tv>'''.encode()


def test_public_validator_separates_xmltv_from_btp_profile():
    result = validate_public_xmltv(_xml())

    assert result["valid"] is True
    assert result["operational_ready"] is True
    assert result["xmltv"]["critical"] == 0
    assert result["btp_profile"]["recommendations"] == 4
    assert {issue["rule_id"] for issue in result["btp_profile"]["issues"]} == {
        "XMLTV-017",
        "XMLTV-018",
    }


def test_public_validator_allows_optional_stop_but_flags_readiness():
    result = validate_public_xmltv(_xml(stop=""))

    assert result["valid"] is True
    assert result["operational_ready"] is True
    assert result["operational"]["warnings"] == 1
    assert result["operational"]["issues"][0]["rule_id"] == "XMLTV-019"


def test_public_validator_rejects_missing_required_title():
    result = validate_public_xmltv(b'''<tv><channel id="a"><display-name>A</display-name></channel><programme start="20260827120000 -0400" channel="a" /></tv>''')

    assert result["valid"] is False
    assert any(issue["rule_id"] == "XMLTV-013" for issue in result["xmltv"]["issues"])


def test_public_basic_report_is_btp_branded():
    payload = {"filename": "sample.xml", **validate_public_xmltv(_xml())}
    report = generate_public_xmltv_report(payload, "en")
    text = report.decode("latin-1")

    assert "Broadcast Tool Pro" in text
    assert "Free XMLTV Validator" in text
    assert "XMLTV FORMAT" in text
    assert "OPERATIONAL READINESS" in text
    assert "BTP DELIVERY PROFILE" in text
