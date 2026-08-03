"""Read-only smoke checks for a Broadcast Tool Pro deployment."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import certifi


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _fetch(base_url: str, path: str) -> tuple[int, bytes, str]:
    url = urljoin(f"{base_url.rstrip('/')}/", path.lstrip("/"))
    request = Request(
        url,
        headers={"User-Agent": "BroadcastToolPro-ReleaseReadiness/1.0"},
    )
    tls_context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=20, context=tls_context) as response:
        return response.status, response.read(), response.headers.get_content_type()


def check_deployment(base_url: str) -> list[CheckResult]:
    results: list[CheckResult] = []

    try:
        status, body, _ = _fetch(base_url, "/health")
        health: dict[str, Any] = json.loads(body)
        required = {
            "status": "healthy",
            "backup": "healthy",
            "email_delivery": "enabled",
            "temporary_storage": "healthy",
        }
        mismatches = [
            f"{key}={health.get(key)!r}"
            for key, expected in required.items()
            if health.get(key) != expected
        ]
        results.append(
            CheckResult(
                "Application health",
                status == 200 and not mismatches,
                ", ".join(mismatches) if mismatches else "all required health signals passed",
            )
        )
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        results.append(CheckResult("Application health", False, str(exc)))

    for path, label, marker in (
        ("/privacy", "Privacy Policy", b"Privacy Policy"),
        ("/terms", "Terms of Service", b"Terms of Service"),
        ("/email-policy", "Email Policy", b"Transactional Email Policy"),
    ):
        try:
            status, body, content_type = _fetch(base_url, path)
            passed = status == 200 and content_type == "text/html" and marker in body
            results.append(
                CheckResult(
                    label,
                    passed,
                    "public page available" if passed else "unexpected response content",
                )
            )
        except (HTTPError, URLError, TimeoutError) as exc:
            results.append(CheckResult(label, False, str(exc)))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Deployment origin, for example https://example.com")
    args = parser.parse_args()

    results = check_deployment(args.base_url)
    for result in results:
        state = "PASS" if result.passed else "FAIL"
        print(f"[{state}] {result.name}: {result.detail}")
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
