from datetime import datetime
from re import fullmatch
from typing import Any

from lxml import etree

from backend.models.validation import ValidationIssue, ValidationReport


MAX_XMLTV_SIZE = 10 * 1024 * 1024
XMLTV_TIMESTAMP_PATTERN = r"\d{14} [+-]\d{4}"
ISO_TIMESTAMP_PATTERN = (
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?[+-]\d{4}"
)


def _issue(
    rule_id: str,
    severity: str,
    message: str,
    element: etree._Element | None = None,
    field: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        rule_id=rule_id,
        severity=severity,
        message=message,
        row=element.sourceline if element is not None else None,
        field=field,
    )


def _parse_timestamp(value: str) -> datetime:
    if fullmatch(XMLTV_TIMESTAMP_PATTERN, value):
        return datetime.strptime(value, "%Y%m%d%H%M%S %z")
    if fullmatch(ISO_TIMESTAMP_PATTERN, value):
        return datetime.fromisoformat(value)
    raise ValueError


def _has_text(element: etree._Element | None) -> bool:
    return element is not None and bool("".join(element.itertext()).strip())


def validate_xmltv(content: bytes) -> dict[str, Any]:
    issues: list[ValidationIssue] = []

    if not content:
        issues.append(_issue(
            "XMLTV-001",
            "critical",
            "The XMLTV file is empty.",
            field="File",
        ))
        return _result(issues)

    if len(content) > MAX_XMLTV_SIZE:
        issues.append(_issue(
            "XMLTV-002",
            "critical",
            "The XMLTV file exceeds the 10 MB validation limit.",
            field="File",
        ))
        return _result(issues)

    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        recover=False,
        huge_tree=False,
    )

    try:
        root = etree.fromstring(content, parser=parser)
    except etree.XMLSyntaxError as exc:
        issues.append(ValidationIssue(
            rule_id="XMLTV-003",
            severity="critical",
            message=f"XML is not well formed: {exc.msg}",
            row=exc.lineno,
            field="XML Syntax",
        ))
        return _result(issues)

    if root.tag != "tv":
        issues.append(_issue(
            "XMLTV-004",
            "critical",
            'The root element must be "tv".',
            root,
            "Root Element",
        ))
        return _result(issues)

    channels = root.findall("channel")
    programmes = root.findall("programme")
    channel_ids: set[str] = set()

    for channel in channels:
        channel_id = (channel.get("id") or "").strip()

        if not channel_id:
            issues.append(_issue(
                "XMLTV-005",
                "critical",
                "Channel is missing the required id attribute.",
                channel,
                "Channel ID",
            ))
        elif channel_id in channel_ids:
            issues.append(_issue(
                "XMLTV-006",
                "critical",
                f'Duplicate channel id "{channel_id}".',
                channel,
                "Channel ID",
            ))
        else:
            channel_ids.add(channel_id)

        if not any(_has_text(name) for name in channel.findall("display-name")):
            issues.append(_issue(
                "XMLTV-007",
                "warning",
                f'Channel "{channel_id or "unknown"}" has no display-name.',
                channel,
                "Display Name",
            ))

    if not channels:
        issues.append(_issue(
            "XMLTV-008",
            "critical",
            "The XMLTV file does not define any channels.",
            root,
            "Channel",
        ))

    referenced_channels: set[str] = set()

    for position, programme in enumerate(programmes, start=1):
        channel_id = (programme.get("channel") or "").strip()
        start_value = (programme.get("start") or "").strip()
        stop_value = (programme.get("stop") or "").strip()
        label = f"Programme #{position}"

        for attribute, value in (
            ("start", start_value),
            ("stop", stop_value),
            ("channel", channel_id),
        ):
            if not value:
                issues.append(_issue(
                    "XMLTV-009",
                    "critical",
                    f"{label} is missing the required {attribute} attribute.",
                    programme,
                    attribute,
                ))

        if channel_id:
            referenced_channels.add(channel_id)
            if channel_id not in channel_ids:
                issues.append(_issue(
                    "XMLTV-010",
                    "critical",
                    f'{label} references unknown channel "{channel_id}".',
                    programme,
                    "channel",
                ))

        start_time = None
        stop_time = None

        for attribute, value in (("start", start_value), ("stop", stop_value)):
            if not value:
                continue

            try:
                parsed = _parse_timestamp(value)
            except ValueError:
                issues.append(_issue(
                    "XMLTV-011",
                    "critical",
                    (
                        f"{label} has an invalid {attribute} timestamp. "
                        "Use YYYYMMDDHHMMSS +0000 or "
                        "YYYY-MM-DDTHH:MM:SS.fff+0000."
                    ),
                    programme,
                    attribute,
                ))
                continue

            if attribute == "start":
                start_time = parsed
            else:
                stop_time = parsed

        if start_time is not None and stop_time is not None and stop_time <= start_time:
            issues.append(_issue(
                "XMLTV-012",
                "critical",
                f"{label} stop time must be later than its start time.",
                programme,
                "stop",
            ))

        if not any(_has_text(title) for title in programme.findall("title")):
            issues.append(_issue(
                "XMLTV-013",
                "critical",
                f"{label} requires a non-empty title.",
                programme,
                "title",
            ))

        required_elements = (
            ("desc", "description"),
            ("category", "category"),
            ("rating", "rating"),
        )
        for tag, field_label in required_elements:
            if any(_has_text(item) for item in programme.findall(tag)):
                continue
            issues.append(_issue(
                "XMLTV-017",
                "critical",
                f"{label} requires a non-empty {field_label}.",
                programme,
                tag,
            ))

        asset_ids = programme.xpath(
            './episode-num[@system="assetID"]'
        )
        if not any(_has_text(item) for item in asset_ids):
            issues.append(_issue(
                "XMLTV-018",
                "critical",
                f"{label} requires an Asset ID.",
                programme,
                "episode-num",
            ))

        for description in programme.findall("desc"):
            if not _has_text(description):
                issues.append(_issue(
                    "XMLTV-014",
                    "warning",
                    f"{label} contains an empty description.",
                    description,
                    "desc",
                ))

    if not programmes:
        issues.append(_issue(
            "XMLTV-015",
            "warning",
            "The XMLTV file does not contain any programmes.",
            root,
            "Programme",
        ))

    for channel_id in sorted(channel_ids - referenced_channels):
        issues.append(_issue(
            "XMLTV-016",
            "warning",
            f'Channel "{channel_id}" has no programmes.',
            field="Channel",
        ))

    return _result(
        issues,
        channels=len(channels),
        programmes=len(programmes),
    )


def _result(
    issues: list[ValidationIssue],
    channels: int = 0,
    programmes: int = 0,
) -> dict[str, Any]:
    report = ValidationReport.from_issues(issues)

    return {
        "valid": report.critical == 0 and report.errors == 0,
        "well_formed": not any(
            issue.rule_id == "XMLTV-003"
            for issue in issues
        ),
        "channels": channels,
        "programmes": programmes,
        "validation": report.to_dict(),
    }
