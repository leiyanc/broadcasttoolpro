from collections import defaultdict
from datetime import datetime
from re import fullmatch
from typing import Any

from lxml import etree

from backend.models.validation import ValidationIssue, ValidationReport
from backend.services.xmltv.feed_validator import MAX_XMLTV_SIZE


XMLTV_TIMESTAMP = r"\d{4}(?:\d{2}){0,5}(?: [+-]\d{4})?"
XMLTV_PRECISE = r"\d{14} [+-]\d{4}"
ISO_PRECISE = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?[+-]\d{4}"


def _issue(rule_id, severity, message, element=None, field=None):
    return ValidationIssue(
        rule_id=rule_id,
        severity=severity,
        message=message,
        row=element.sourceline if element is not None else None,
        field=field,
    )


def _text(element):
    return element is not None and bool("".join(element.itertext()).strip())


def _timestamp(value):
    try:
        if fullmatch(XMLTV_PRECISE, value):
            return True, datetime.strptime(value, "%Y%m%d%H%M%S %z")
        if fullmatch(ISO_PRECISE, value):
            return True, datetime.fromisoformat(value)
        if fullmatch(XMLTV_TIMESTAMP, value):
            raw = value.split(" ", 1)[0]
            if len(raw) == 14:
                datetime.strptime(raw, "%Y%m%d%H%M%S")
            return True, None
    except ValueError:
        pass
    return False, None


def validate_public_xmltv(content: bytes) -> dict[str, Any]:
    universal, operational, profile = [], [], []
    if not content:
        universal.append(_issue("XMLTV-001", "critical", "The XMLTV file is empty.", field="File"))
        return _result(universal, operational, profile)
    if len(content) > MAX_XMLTV_SIZE:
        universal.append(_issue("XMLTV-002", "critical", "The XMLTV file exceeds the 10 MB validation limit.", field="File"))
        return _result(universal, operational, profile)

    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, recover=False, huge_tree=False)
    try:
        root = etree.fromstring(content, parser=parser)
    except etree.XMLSyntaxError as exc:
        message = f"XML is not well formed: {exc.msg}"
        if "EntityRef" in exc.msg:
            message = "XML is not well formed: an ampersand (&) must be escaped as &amp;."
        universal.append(ValidationIssue(rule_id="XMLTV-003", severity="critical", message=message, row=exc.lineno, field="XML Syntax"))
        return _result(universal, operational, profile)
    if root.tag != "tv":
        universal.append(_issue("XMLTV-004", "critical", 'The root element must be "tv".', root, "Root Element"))
        return _result(universal, operational, profile)

    channels = root.findall("channel")
    programmes = root.findall("programme")
    channel_ids, referenced = set(), set()
    schedules = defaultdict(list)
    for channel in channels:
        channel_id = (channel.get("id") or "").strip()
        if not channel_id:
            universal.append(_issue("XMLTV-005", "critical", "Channel is missing the required id attribute.", channel, "Channel ID"))
        elif channel_id in channel_ids:
            operational.append(_issue("XMLTV-006", "error", f'Duplicate channel id "{channel_id}".', channel, "Channel ID"))
        else:
            channel_ids.add(channel_id)
        if not any(_text(name) for name in channel.findall("display-name")):
            universal.append(_issue("XMLTV-007", "critical", f'Channel "{channel_id or "unknown"}" requires a display-name.', channel, "Display Name"))

    for position, programme in enumerate(programmes, 1):
        label = f"Programme #{position}"
        channel_id = (programme.get("channel") or "").strip()
        start_value = (programme.get("start") or "").strip()
        stop_value = (programme.get("stop") or "").strip()
        for attribute, value in (("start", start_value), ("channel", channel_id)):
            if not value:
                universal.append(_issue("XMLTV-009", "critical", f"{label} is missing the required {attribute} attribute.", programme, attribute))
        if channel_id:
            referenced.add(channel_id)
            if channel_ids and channel_id not in channel_ids:
                operational.append(_issue("XMLTV-010", "error", f'{label} references unknown channel "{channel_id}".', programme, "channel"))
        parsed = {}
        for attribute, value in (("start", start_value), ("stop", stop_value)):
            if not value:
                continue
            valid, precise = _timestamp(value)
            if not valid:
                universal.append(_issue("XMLTV-011", "critical", f"{label} has an invalid {attribute} timestamp.", programme, attribute))
            parsed[attribute] = precise
        if not stop_value:
            operational.append(_issue("XMLTV-019", "warning", f"{label} has no stop time; its duration cannot be verified.", programme, "stop"))
        if parsed.get("start") and parsed.get("stop") and parsed["stop"] <= parsed["start"]:
            operational.append(_issue("XMLTV-012", "error", f"{label} stop time must be later than its start time.", programme, "stop"))
        if not any(_text(title) for title in programme.findall("title")):
            universal.append(_issue("XMLTV-013", "critical", f"{label} requires a non-empty title.", programme, "title"))
        for description in programme.findall("desc"):
            if not _text(description):
                operational.append(_issue("XMLTV-014", "warning", f"{label} contains an empty description.", description, "desc"))
        for tag, label_text in (("desc", "description"), ("category", "category"), ("rating", "rating")):
            if not any(_text(item) for item in programme.findall(tag)):
                profile.append(_issue("XMLTV-017", "recommendation", f"{label} has no {label_text}; add one for the BTP delivery profile.", programme, tag))
        asset_ids = programme.xpath('./episode-num[@system="assetID"]')
        if not any(_text(item) for item in asset_ids):
            profile.append(_issue("XMLTV-018", "recommendation", f"{label} has no Asset ID; add one for the BTP delivery profile.", programme, "episode-num"))
        if channel_id and parsed.get("start"):
            schedules[channel_id].append((parsed["start"], parsed.get("stop"), programme))

    if not programmes:
        operational.append(_issue("XMLTV-015", "warning", "The XMLTV file does not contain any programmes.", root, "Programme"))
    for channel_id in sorted(channel_ids - referenced):
        operational.append(_issue("XMLTV-016", "warning", f'Channel "{channel_id}" has no programmes.', field="Channel"))
    for channel_id, entries in schedules.items():
        if [x[0] for x in entries] != sorted(x[0] for x in entries):
            operational.append(_issue("XMLTV-020", "warning", f'Programmes for channel "{channel_id}" are not in chronological order.', field="start"))
        ordered = sorted(entries, key=lambda x: x[0])
        for previous, current in zip(ordered, ordered[1:]):
            if current[0] == previous[0]:
                operational.append(_issue("XMLTV-021", "error", f'Channel "{channel_id}" has duplicate programme start times.', current[2], "start"))
            if previous[1] and current[0] < previous[1]:
                operational.append(_issue("XMLTV-022", "warning", f'Channel "{channel_id}" has overlapping programmes.', current[2], "start"))
    return _result(universal, operational, profile, len(channels), len(programmes))


def _result(universal, operational, profile, channels=0, programmes=0):
    xmltv = ValidationReport.from_issues(universal)
    operations = ValidationReport.from_issues(operational)
    return {
        "valid": xmltv.critical == 0 and xmltv.errors == 0,
        "operational_ready": operations.critical == 0 and operations.errors == 0,
        "well_formed": not any(issue.rule_id == "XMLTV-003" for issue in universal),
        "channels": channels,
        "programmes": programmes,
        "xmltv": xmltv.to_dict(),
        "operational": operations.to_dict(),
        "btp_profile": {
            "score": max(0, 100 - min(100, len(profile) * 5)),
            "recommendations": len(profile),
            "issues": [issue.to_dict() for issue in profile],
        },
    }
