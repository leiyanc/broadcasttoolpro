import ipaddress
import socket
import ssl
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
)


MAX_PLAYLIST_SIZE = 2 * 1024 * 1024
MAX_VARIANTS_TO_INSPECT = 10


class HlsValidationError(ValueError):
    pass


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def _https_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    verify_paths = ssl.get_default_verify_paths()

    if verify_paths.cafile is None:
        system_bundle = Path("/etc/ssl/cert.pem")
        if system_bundle.is_file():
            context.load_verify_locations(cafile=system_bundle)

    return context


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HlsValidationError("Use a complete HTTP or HTTPS playlist URL.")
    if parsed.username or parsed.password:
        raise HlsValidationError("Playlist URLs cannot include credentials.")

    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        }
    except socket.gaierror as exc:
        raise HlsValidationError("The playlist host could not be resolved.") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise HlsValidationError(
                "Private, loopback, and local network URLs are not allowed."
            )


def fetch_playlist(url: str) -> str:
    _validate_public_url(url)
    request = Request(
        url,
        headers={
            "Accept": (
                "application/vnd.apple.mpegurl, application/x-mpegURL, "
                "text/plain;q=0.8"
            ),
            "User-Agent": "BroadcastToolPro-HLSValidator/1.0",
        },
    )

    try:
        opener = build_opener(
            _NoRedirects(),
            HTTPSHandler(context=_https_context()),
        )
        with opener.open(request, timeout=10) as response:
            content = response.read(MAX_PLAYLIST_SIZE + 1)
    except HTTPError as exc:
        raise HlsValidationError(
            f"The playlist server returned HTTP {exc.code}."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise HlsValidationError("The playlist could not be reached.") from exc

    if len(content) > MAX_PLAYLIST_SIZE:
        raise HlsValidationError("The playlist exceeds the 2 MB validation limit.")

    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HlsValidationError("The playlist must use UTF-8 encoding.") from exc


def _attributes(value: str) -> dict[str, str]:
    attributes: dict[str, str] = {}
    current = ""
    quoted = False
    parts = []

    for character in value:
        if character == '"':
            quoted = not quoted
        if character == "," and not quoted:
            parts.append(current)
            current = ""
        else:
            current += character
    parts.append(current)

    for part in parts:
        key, separator, item = part.partition("=")
        if separator:
            attributes[key.strip()] = item.strip().strip('"')
    return attributes


def _issue(severity: str, rule_id: str, message: str) -> dict:
    return {
        "severity": severity,
        "rule_id": rule_id,
        "message": message,
    }


def _trigger_duration(value: str | None) -> float | None:
    if not value:
        return None
    candidate = value.split(":", 1)[-1]
    attributes = _attributes(candidate)
    candidate = (
        attributes.get("DURATION")
        or attributes.get("Duration")
        or candidate.split(",", 1)[0]
    )
    try:
        return float(candidate)
    except ValueError:
        return None


def _detect_triggers(lines: list[str]) -> tuple[list[dict], list[dict]]:
    triggers = []
    issues = []
    cue_outs = 0
    cue_ins = 0

    for line_number, line in enumerate(lines, 1):
        if line.startswith("#EXT-X-DATERANGE:"):
            attributes = _attributes(line.split(":", 1)[1])
            scte_fields = {
                key: value
                for key, value in attributes.items()
                if key.startswith("SCTE35-")
            }
            is_ad_trigger = bool(scte_fields) or any(
                word in attributes.get("CLASS", "").lower()
                for word in ("ad", "scte", "interstitial")
            )
            triggers.append({
                "line": line_number,
                "type": "SCTE-35 DATERANGE"
                if scte_fields
                else "DATERANGE",
                "id": attributes.get("ID"),
                "class": attributes.get("CLASS"),
                "start_date": attributes.get("START-DATE"),
                "duration": _trigger_duration(
                    attributes.get("DURATION")
                    or attributes.get("PLANNED-DURATION")
                ),
                "payload": next(iter(scte_fields.values()), None),
                "ad_trigger": is_ad_trigger,
            })
            continue

        trigger_type = None
        if line.startswith("#EXT-X-CUE-OUT-CONT"):
            trigger_type = "CUE-OUT-CONT"
        elif line.startswith("#EXT-X-CUE-OUT"):
            trigger_type = "CUE-OUT"
            cue_outs += 1
        elif line.startswith("#EXT-X-CUE-IN"):
            trigger_type = "CUE-IN"
            cue_ins += 1
        elif line.startswith("#EXT-OATCLS-SCTE35"):
            trigger_type = "OATCLS-SCTE35"
        elif line.startswith("#EXT-X-SPLICEPOINT-SCTE35"):
            trigger_type = "SPLICEPOINT-SCTE35"
        elif line.startswith("#EXT-X-ASSET"):
            trigger_type = "ASSET"

        if trigger_type:
            value = line.split(":", 1)[1] if ":" in line else None
            triggers.append({
                "line": line_number,
                "type": trigger_type,
                "id": None,
                "class": None,
                "start_date": None,
                "duration": (
                    _trigger_duration(value)
                    if trigger_type.startswith("CUE-OUT")
                    else None
                ),
                "payload": value,
                "ad_trigger": True,
            })

    if cue_ins > cue_outs:
        issues.append(_issue(
            "warning",
            "HLS-012",
            "The playlist contains more CUE-IN than CUE-OUT markers.",
        ))

    return triggers, issues


def _inspect_media_playlist(
    text: str,
    url: str,
) -> tuple[dict, list[dict]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    issues = []
    triggers, trigger_issues = _detect_triggers(lines)
    issues.extend(trigger_issues)
    segment_uris = [
        line
        for line in lines
        if not line.startswith("#")
    ]
    durations = []

    for line in lines:
        if not line.startswith("#EXTINF:"):
            continue
        raw_duration = line.split(":", 1)[1].split(",", 1)[0]
        try:
            durations.append(float(raw_duration))
        except ValueError:
            issues.append(_issue(
                "critical",
                "HLS-006",
                f'Invalid segment duration: "{raw_duration}".',
            ))

    target_duration = None
    for line in lines:
        if line.startswith("#EXT-X-TARGETDURATION:"):
            try:
                target_duration = int(line.split(":", 1)[1])
            except ValueError:
                issues.append(_issue(
                    "critical",
                    "HLS-007",
                    "EXT-X-TARGETDURATION must be a whole number.",
                ))
            break

    if not segment_uris:
        issues.append(_issue(
            "critical",
            "HLS-004",
            "The media playlist does not reference any segments.",
        ))
    if len(durations) != len(segment_uris):
        issues.append(_issue(
            "warning",
            "HLS-005",
            "The number of EXTINF entries does not match the segment count.",
        ))
    if target_duration is None:
        issues.append(_issue(
            "critical",
            "HLS-008",
            "The media playlist is missing EXT-X-TARGETDURATION.",
        ))
    elif durations and max(durations) > target_duration:
        issues.append(_issue(
            "critical",
            "HLS-009",
            "A segment duration exceeds EXT-X-TARGETDURATION.",
        ))

    return {
        "url": url,
        "segments": len(segment_uris),
        "target_duration": target_duration,
        "total_duration": round(sum(durations), 3),
        "live": "#EXT-X-ENDLIST" not in lines,
        "encrypted": any(
            line.startswith("#EXT-X-KEY:")
            and "METHOD=NONE" not in line
            for line in lines
        ),
        "discontinuities": lines.count("#EXT-X-DISCONTINUITY"),
        "triggers": triggers,
        "trigger_count": len(triggers),
        "scte35_detected": any(
            "SCTE" in trigger["type"] or trigger["type"].startswith("CUE-")
            for trigger in triggers
        ),
        "first_segment_url": (
            urljoin(url, segment_uris[0])
            if segment_uris
            else None
        ),
    }, issues


def validate_hls(
    url: str,
    fetcher: Callable[[str], str] = fetch_playlist,
) -> dict:
    normalized_url = url.strip()
    if not normalized_url:
        raise HlsValidationError("An HLS playlist URL is required.")

    text = fetcher(normalized_url)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    issues = []

    if not lines or lines[0] != "#EXTM3U":
        issues.append(_issue(
            "critical",
            "HLS-001",
            "The resource is not a valid M3U8 playlist.",
        ))
        return {
            "valid": False,
            "url": normalized_url,
            "playlist_type": "unknown",
            "variants": [],
            "media": None,
            "issues": issues,
        }

    variants = []
    for index, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF:"):
            continue
        if index + 1 >= len(lines) or lines[index + 1].startswith("#"):
            issues.append(_issue(
                "critical",
                "HLS-002",
                "A stream variant is missing its playlist URI.",
            ))
            continue
        attributes = _attributes(line.split(":", 1)[1])
        variants.append({
            "url": urljoin(normalized_url, lines[index + 1]),
            "bandwidth": int(attributes["BANDWIDTH"])
            if attributes.get("BANDWIDTH", "").isdigit()
            else None,
            "average_bandwidth": int(attributes["AVERAGE-BANDWIDTH"])
            if attributes.get("AVERAGE-BANDWIDTH", "").isdigit()
            else None,
            "resolution": attributes.get("RESOLUTION"),
            "frame_rate": attributes.get("FRAME-RATE"),
            "codecs": attributes.get("CODECS"),
            "audio_group": attributes.get("AUDIO"),
            "subtitle_group": attributes.get("SUBTITLES"),
        })

    media = None
    if variants:
        for variant in variants[:MAX_VARIANTS_TO_INSPECT]:
            if variant["bandwidth"] is None:
                issues.append(_issue(
                    "warning",
                    "HLS-003",
                    f'Variant {variant["url"]} does not declare BANDWIDTH.',
                ))
            try:
                variant_text = fetcher(variant["url"])
            except HlsValidationError as exc:
                variant["valid"] = False
                issues.append(_issue(
                    "critical",
                    "HLS-010",
                    f'Variant {variant["url"]} could not be inspected: {exc}',
                ))
                continue

            variant_lines = [
                line.strip()
                for line in variant_text.splitlines()
                if line.strip()
            ]
            if not variant_lines or variant_lines[0] != "#EXTM3U":
                variant["valid"] = False
                issues.append(_issue(
                    "critical",
                    "HLS-011",
                    f'Variant {variant["url"]} is not a valid M3U8 playlist.',
                ))
                continue

            variant_media, variant_issues = _inspect_media_playlist(
                variant_text,
                variant["url"],
            )
            variant.update({
                "valid": not any(
                    issue["severity"] == "critical"
                    for issue in variant_issues
                ),
                "segments": variant_media["segments"],
                "target_duration": variant_media["target_duration"],
                "live": variant_media["live"],
                "trigger_count": variant_media["trigger_count"],
                "scte35_detected": variant_media["scte35_detected"],
                "triggers": variant_media["triggers"],
            })
            for issue in variant_issues:
                issues.append({
                    **issue,
                    "message": (
                        f'Variant {variant["url"]}: {issue["message"]}'
                    ),
                })
    else:
        media, media_issues = _inspect_media_playlist(text, normalized_url)
        issues.extend(media_issues)

    critical = sum(issue["severity"] == "critical" for issue in issues)
    warnings = sum(issue["severity"] == "warning" for issue in issues)
    trigger_count = (
        sum(variant.get("trigger_count", 0) for variant in variants)
        if variants
        else (media or {}).get("trigger_count", 0)
    )
    return {
        "valid": critical == 0,
        "url": normalized_url,
        "playlist_type": "master" if variants else "media",
        "variants": variants[:MAX_VARIANTS_TO_INSPECT],
        "variant_count": len(variants),
        "inspected_variants": min(
            len(variants),
            MAX_VARIANTS_TO_INSPECT,
        ),
        "media": media,
        "trigger_count": trigger_count,
        "scte35_detected": (
            any(variant.get("scte35_detected") for variant in variants)
            if variants
            else bool((media or {}).get("scte35_detected"))
        ),
        "critical": critical,
        "warnings": warnings,
        "issues": issues,
    }
