from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from lxml import etree

from backend.services.xmltv.feed_validator import (
    MAX_XMLTV_SIZE,
    validate_xmltv,
)


@dataclass(frozen=True)
class RepairChange:
    rule_id: str
    line: int | None
    field: str
    original_value: str | None
    repaired_value: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_xml(content: bytes) -> etree._Element:
    if not content:
        raise ValueError("The XMLTV file is empty.")

    if len(content) > MAX_XMLTV_SIZE:
        raise ValueError("The XMLTV file exceeds the 10 MB repair limit.")

    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        recover=False,
        remove_blank_text=False,
        huge_tree=False,
    )

    try:
        root = etree.fromstring(content, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise ValueError(
            f"XML is not well formed on line {exc.lineno}: {exc.msg}"
        ) from exc

    if root.tag != "tv":
        raise ValueError('The root element must be "tv".')

    return root


def _normalize_timestamp(value: str) -> str | None:
    compact = value.strip()
    formats = (
        "%Y%m%d%H%M%S%z",
        "%Y-%m-%d %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
    )

    for value_format in formats:
        try:
            parsed = datetime.strptime(compact, value_format)
        except ValueError:
            continue

        return parsed.strftime("%Y%m%d%H%M%S %z")

    return None


def repair_xmltv(content: bytes) -> dict[str, Any]:
    root = _parse_xml(content)
    changes: list[RepairChange] = []

    for element in root.findall("channel") + root.findall("programme"):
        attributes = ("id",) if element.tag == "channel" else (
            "start",
            "stop",
            "channel",
        )

        for attribute in attributes:
            original = element.get(attribute)
            if original is None:
                continue

            stripped = original.strip()
            if stripped != original:
                element.set(attribute, stripped)
                changes.append(RepairChange(
                    rule_id="REPAIR-001",
                    line=element.sourceline,
                    field=attribute,
                    original_value=original,
                    repaired_value=stripped,
                    message=f'Trimmed whitespace from the "{attribute}" attribute.',
                ))

    for programme in root.findall("programme"):
        for attribute in ("start", "stop"):
            original = programme.get(attribute)
            if not original:
                continue

            normalized = _normalize_timestamp(original)
            if normalized is not None and normalized != original:
                programme.set(attribute, normalized)
                changes.append(RepairChange(
                    rule_id="REPAIR-002",
                    line=programme.sourceline,
                    field=attribute,
                    original_value=original,
                    repaired_value=normalized,
                    message=f'Normalized the "{attribute}" timestamp.',
                ))

    for description in list(root.findall("programme/desc")):
        if "".join(description.itertext()).strip():
            continue

        programme = description.getparent()
        programme.remove(description)
        changes.append(RepairChange(
            rule_id="REPAIR-003",
            line=description.sourceline,
            field="desc",
            original_value="",
            repaired_value=None,
            message="Removed an empty optional description.",
        ))

    programmes_by_channel: dict[str, list[etree._Element]] = defaultdict(list)

    for programme in root.findall("programme"):
        channel_id = (programme.get("channel") or "").strip()
        start = programme.get("start")
        if channel_id and start:
            programmes_by_channel[channel_id].append(programme)

    for channel_programmes in programmes_by_channel.values():
        ordered = sorted(
            channel_programmes,
            key=lambda item: item.get("start") or "",
        )

        for current, following in zip(ordered, ordered[1:]):
            if current.get("stop") or not following.get("start"):
                continue

            inferred_stop = following.get("start")
            current.set("stop", inferred_stop)
            changes.append(RepairChange(
                rule_id="REPAIR-004",
                line=current.sourceline,
                field="stop",
                original_value=None,
                repaired_value=inferred_stop,
                message="Inferred the stop time from the next programme.",
            ))

    repaired_xml = etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    )
    validation = validate_xmltv(repaired_xml)

    return {
        "repairable": True,
        "changes_count": len(changes),
        "changes": [change.to_dict() for change in changes],
        "validation": validation,
        "xml": repaired_xml,
    }
