import json
import os
import re
import shutil
import subprocess
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable


ALLOWED_DURATIONS = {5, 10, 15}
TARGET_LKFS = -24.0
TOLERANCE_LU = 2.0
TRUE_PEAK_LIMIT_DBTP = -2.0

_INTEGRATED_PATTERN = re.compile(
    r"^\s*I:\s*(-?\d+(?:\.\d+)?)\s+LUFS",
    re.MULTILINE,
)
_PEAK_PATTERN = re.compile(
    r"^\s*Peak:\s*(-?\d+(?:\.\d+)?)\s+dBFS",
    re.MULTILINE,
)


class LoudnessAnalysisError(RuntimeError):
    pass


@dataclass
class LoudnessResult:
    profile: str
    integrated_lkfs: float
    true_peak_dbtp: float
    target_lkfs: float
    tolerance_lu: float
    true_peak_limit_dbtp: float
    status: str
    findings: list[dict]
    legal_disclaimer: str


def evaluate_atsc_a85(
    integrated_lkfs: float,
    true_peak_dbtp: float,
) -> LoudnessResult:
    findings = []
    loudness_delta = integrated_lkfs - TARGET_LKFS
    if abs(loudness_delta) > TOLERANCE_LU:
        findings.append({
            "rule_id": "LOUD-001",
            "severity": "fail",
            "message": (
                f"Integrated loudness is {integrated_lkfs:.1f} LKFS; the "
                f"ATSC A/85 assessment range is {TARGET_LKFS - TOLERANCE_LU:.1f} "
                f"to {TARGET_LKFS + TOLERANCE_LU:.1f} LKFS."
            ),
        })
    if true_peak_dbtp > TRUE_PEAK_LIMIT_DBTP:
        findings.append({
            "rule_id": "LOUD-002",
            "severity": "fail",
            "message": (
                f"True peak is {true_peak_dbtp:.1f} dBTP; the configured "
                f"technical limit is {TRUE_PEAK_LIMIT_DBTP:.1f} dBTP."
            ),
        })
    if findings:
        status = "fail"
    elif abs(loudness_delta) > 1.0 or true_peak_dbtp > -3.0:
        status = "warning"
        findings.append({
            "rule_id": "LOUD-003",
            "severity": "warning",
            "message": (
                "The measured audio is within the configured limits but is "
                "close enough to a boundary to merit review."
            ),
        })
    else:
        status = "pass"
    return LoudnessResult(
        profile="ATSC A/85",
        integrated_lkfs=round(integrated_lkfs, 1),
        true_peak_dbtp=round(true_peak_dbtp, 1),
        target_lkfs=TARGET_LKFS,
        tolerance_lu=TOLERANCE_LU,
        true_peak_limit_dbtp=TRUE_PEAK_LIMIT_DBTP,
        status=status,
        findings=findings,
        legal_disclaimer=(
            "This is a technical loudness assessment, not a legal certification "
            "or a determination of compliance with SB 576 or any other law."
        ),
    )


def parse_ebur128_output(output: str) -> LoudnessResult:
    integrated = _INTEGRATED_PATTERN.findall(output)
    peaks = _PEAK_PATTERN.findall(output)
    if not integrated or not peaks:
        raise LoudnessAnalysisError(
            "The loudness analyzer did not return integrated loudness and "
            "true peak metrics."
        )
    return evaluate_atsc_a85(float(integrated[-1]), float(peaks[-1]))


def parse_loudnorm_output(output: str) -> LoudnessResult:
    for candidate in reversed(re.findall(r"\{.*?\}", output, re.DOTALL)):
        try:
            metrics = json.loads(candidate)
            integrated_lkfs = float(metrics["input_i"])
            true_peak_dbtp = float(metrics["input_tp"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
        return evaluate_atsc_a85(integrated_lkfs, true_peak_dbtp)
    raise LoudnessAnalysisError(
        "The loudness analyzer did not return integrated loudness and "
        "true peak metrics."
    )


def _ffmpeg_executable() -> str:
    configured = os.getenv("BTP_FFMPEG_PATH", "").strip()
    if configured:
        return configured
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise LoudnessAnalysisError("The loudness analyzer is not installed.") from exc
    return imageio_ffmpeg.get_ffmpeg_exe()


def analyze_hls_loudness(playlist_url: str, duration_minutes: int) -> dict:
    if duration_minutes not in ALLOWED_DURATIONS:
        raise LoudnessAnalysisError(
            "Monitoring period must be 5, 10, or 15 minutes."
        )
    command = [
        _ffmpeg_executable(),
        "-nostdin",
        "-hide_banner",
        "-nostats",
        "-loglevel",
        "info",
        "-threads",
        "1",
        "-i",
        playlist_url,
        "-t",
        str(duration_minutes * 60),
        "-vn",
        "-map",
        "0:a:0",
        "-filter:a",
        "loudnorm=I=-24:LRA=7:TP=-2:print_format=json",
        "-ar",
        "48000",
        "-f",
        "null",
        "-",
    ]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=(duration_minutes * 60) + 90,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LoudnessAnalysisError(
            "The loudness analysis could not be completed."
        ) from exc
    analyzer_output = completed.stderr or ""
    if completed.returncode != 0:
        details = analyzer_output.strip().splitlines()
        if details:
            detail = details[-1][:240]
        elif completed.returncode < 0:
            detail = (
                "The analyzer process was interrupted by signal "
                f"{-completed.returncode}."
            )
        else:
            detail = (
                "FFmpeg exited with code "
                f"{completed.returncode} without diagnostic output."
            )
        raise LoudnessAnalysisError(
            "The stream audio could not be analyzed: "
            f"{detail}"
        )
    return asdict(parse_loudnorm_output(analyzer_output))


class LoudnessJobStore:
    def __init__(self, analyzer: Callable[[str, int], dict] = analyze_hls_loudness):
        self.analyzer = analyzer
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="btp-loudness",
        )

    def start(
        self,
        *,
        organization_id: str,
        user_id: str,
        playlist_url: str,
        duration_minutes: int,
    ) -> dict:
        if duration_minutes not in ALLOWED_DURATIONS:
            raise LoudnessAnalysisError(
                "Monitoring period must be 5, 10, or 15 minutes."
            )
        self._cleanup()
        job_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        job = {
            "id": job_id,
            "organization_id": organization_id,
            "user_id": user_id,
            "status": "queued",
            "duration_minutes": duration_minutes,
            "created_at": now.isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
        }
        with self._lock:
            if any(
                existing["organization_id"] == organization_id
                and existing["status"] in {"queued", "running"}
                for existing in self._jobs.values()
            ):
                raise LoudnessAnalysisError(
                    "This organization already has a loudness analysis in progress."
                )
            queued_count = sum(
                existing["status"] in {"queued", "running"}
                for existing in self._jobs.values()
            )
            if queued_count >= 10:
                raise LoudnessAnalysisError(
                    "The loudness analyzer is at capacity. Please try again later."
                )
            self._jobs[job_id] = job
        self._executor.submit(self._run, job_id, playlist_url, duration_minutes)
        return self.public(job_id, organization_id)

    def _run(self, job_id: str, playlist_url: str, duration_minutes: int) -> None:
        with self._lock:
            self._jobs[job_id]["status"] = "running"
            self._jobs[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()
        try:
            result = self.analyzer(playlist_url, duration_minutes)
        except Exception as exc:
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "failed"
                job["error"] = str(exc)[:500]
                job["completed_at"] = datetime.now(timezone.utc).isoformat()
            return
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "completed"
            job["result"] = result
            job["completed_at"] = datetime.now(timezone.utc).isoformat()

    def public(self, job_id: str, organization_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job["organization_id"] != organization_id:
                raise KeyError("Loudness analysis not found.")
            return {
                key: value
                for key, value in job.items()
                if key not in {"organization_id", "user_id"}
            }

    def _cleanup(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        with self._lock:
            expired = [
                job_id for job_id, job in self._jobs.items()
                if datetime.fromisoformat(job["created_at"]) < cutoff
            ]
            for job_id in expired:
                self._jobs.pop(job_id, None)


loudness_jobs = LoudnessJobStore()
