"""Boot a previous Git revision in isolation and verify its health."""

from __future__ import annotations

import argparse
import io
import json
import os
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def _available_port() -> int:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def _export_revision(repository: Path, revision: str, target: Path) -> str:
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    archive = subprocess.run(
        ["git", "archive", "--format=tar", resolved],
        cwd=repository,
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        bundle.extractall(target, filter="data")
    return resolved


def rehearse(repository: Path, revision: str, timeout: int = 30) -> dict:
    with tempfile.TemporaryDirectory(prefix="btp-rollback-rehearsal-") as work:
        work_path = Path(work)
        source_path = work_path / "source"
        data_path = work_path / "data"
        source_path.mkdir()
        resolved = _export_revision(repository, revision, source_path)
        port = _available_port()
        environment = {
            **os.environ,
            "BTP_ENV": "test",
            "BTP_DATA_DIR": str(data_path),
            "BTP_EMAIL_PROVIDER": "disabled",
            "BTP_COOKIE_SECURE": "false",
        }
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--workers",
                "1",
            ],
            cwd=source_path,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        health_url = f"http://127.0.0.1:{port}/health"
        deadline = time.monotonic() + timeout
        health: dict | None = None
        try:
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    stderr = process.stderr.read() if process.stderr else ""
                    raise RuntimeError(
                        f"Rollback candidate stopped during startup: {stderr}"
                    )
                try:
                    with urlopen(health_url, timeout=2) as response:
                        health = json.loads(response.read())
                    break
                except (URLError, TimeoutError, json.JSONDecodeError):
                    time.sleep(0.5)
            if health is None:
                raise TimeoutError(
                    f"Rollback candidate did not become healthy in {timeout}s."
                )
            if health.get("status") != "healthy":
                raise RuntimeError(f"Unexpected health response: {health}")
            return {
                "revision": resolved,
                "health": health,
                "isolated_data": str(data_path),
                "live_environment_touched": False,
            }
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision", nargs="?", default="HEAD^")
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    args = parser.parse_args()
    result = rehearse(args.repository.resolve(), args.revision)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
