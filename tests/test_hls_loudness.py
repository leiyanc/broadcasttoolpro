import subprocess
import threading
import time

import pytest
import backend.services.hls.loudness as loudness_module

from backend.services.hls.loudness import (
    LoudnessAnalysisError,
    LoudnessAnalysisCancelled,
    LoudnessJobStore,
    _ffmpeg_executable,
    analyze_hls_loudness,
    evaluate_atsc_a85,
    parse_ebur128_output,
    parse_loudnorm_output,
)


def test_atsc_a85_passes_centered_program_audio():
    result = evaluate_atsc_a85(-24.0, -4.0)

    assert result.status == "pass"
    assert result.integrated_lkfs == -24.0
    assert result.true_peak_dbtp == -4.0
    assert result.findings == []


def test_atsc_a85_warns_near_configured_boundary():
    result = evaluate_atsc_a85(-22.5, -2.5)

    assert result.status == "warning"
    assert result.findings[0]["rule_id"] == "LOUD-003"


def test_atsc_a85_fails_outside_loudness_and_peak_limits():
    result = evaluate_atsc_a85(-18.0, -0.5)

    assert result.status == "fail"
    assert {finding["rule_id"] for finding in result.findings} == {
        "LOUD-001",
        "LOUD-002",
    }


def test_parser_uses_final_ebur128_summary():
    output = """
      I:         -70.0 LUFS
      Peak:      -30.0 dBFS
    Summary:
      I:         -23.8 LUFS
      Peak:       -4.1 dBFS
    """

    result = parse_ebur128_output(output)

    assert result.integrated_lkfs == -23.8
    assert result.true_peak_dbtp == -4.1


def test_parser_uses_latest_live_ebur128_measurement():
    output = """
    [Parsed_ebur128_0] t: 9.9 TARGET:-23 LUFS M:-23.0 S:-23.2 I:-23.1 LUFS LRA:1.5 LU FTPK:-15.0 -14.0 dBFS TPK:-13.7 -13.6 dBFS
    [Parsed_ebur128_0] t: 10.0 TARGET:-23 LUFS M:-22.9 S:-23.1 I:-23.0 LUFS LRA:1.6 LU FTPK:-14.9 -14.2 dBFS TPK:-13.7 -13.6 dBFS
    """

    result = parse_ebur128_output(output)

    assert result.integrated_lkfs == -23.0
    assert result.true_peak_dbtp == -13.6
    assert result.loudness_range_lu == 1.6
    assert result.measured_seconds == 10.0


def test_parser_rejects_incomplete_analyzer_output():
    with pytest.raises(LoudnessAnalysisError):
        parse_ebur128_output("No audio summary")


def test_loudnorm_parser_uses_measured_input_metrics():
    output = '''
    {
        "input_i": "-24.07",
        "input_tp": "-14.52",
        "input_lra": "2.10"
    }
    '''

    result = parse_loudnorm_output(output)

    assert result.integrated_lkfs == -24.1
    assert result.true_peak_dbtp == -14.5


def test_loudnorm_parser_rejects_missing_metrics():
    with pytest.raises(LoudnessAnalysisError):
        parse_loudnorm_output('{"output_i": "-24.0"}')


def test_ffmpeg_executable_prefers_configured_path(monkeypatch):
    monkeypatch.setenv("BTP_FFMPEG_PATH", "/usr/bin/ffmpeg")
    monkeypatch.setattr("backend.services.hls.loudness.shutil.which", lambda _: None)

    assert _ffmpeg_executable() == "/usr/bin/ffmpeg"


def test_ffmpeg_executable_uses_system_binary_before_packaged_one(monkeypatch):
    monkeypatch.delenv("BTP_FFMPEG_PATH", raising=False)
    monkeypatch.setattr(
        "backend.services.hls.loudness.shutil.which",
        lambda _: "/usr/local/bin/ffmpeg",
    )

    assert _ffmpeg_executable() == "/usr/local/bin/ffmpeg"


def test_analyzer_uses_resource_bounded_ffmpeg_options(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return type("Completed", (), {
            "returncode": 0,
            "stderr": "Summary:\n I: -24.0 LUFS\n LRA: 1.2 LU\n Peak: -4.0 dBFS",
        })()

    monkeypatch.setattr(
        "backend.services.hls.loudness._ffmpeg_executable",
        lambda: "ffmpeg",
    )
    monkeypatch.setattr(
        "backend.services.hls.loudness.subprocess.run",
        fake_run,
    )

    result = analyze_hls_loudness("https://example.com/live.m3u8", 5)

    assert result["integrated_lkfs"] == -24.0
    assert "-re" not in captured["command"]
    assert captured["command"][captured["command"].index("-threads") + 1] == "1"
    assert captured["command"][captured["command"].index("-map") + 1] == "0:a:0"
    assert "ebur128=peak=true" in captured["command"]
    assert captured["kwargs"]["stdout"] is subprocess.DEVNULL


def test_analyzer_reports_signal_when_ffmpeg_is_interrupted(monkeypatch):
    monkeypatch.setattr(
        "backend.services.hls.loudness._ffmpeg_executable",
        lambda: "ffmpeg",
    )
    monkeypatch.setattr(
        "backend.services.hls.loudness.subprocess.run",
        lambda *_args, **_kwargs: type("Completed", (), {
            "returncode": -9,
            "stderr": "",
        })(),
    )

    with pytest.raises(LoudnessAnalysisError, match="signal 9"):
        analyze_hls_loudness("https://example.com/live.m3u8", 5)


def test_analyzer_terminates_ffmpeg_when_cancelled(monkeypatch):
    cancel_event = threading.Event()
    cancel_event.set()

    class FakeProcess:
        returncode = -15
        signal_sent = None

        def send_signal(self, sent_signal):
            self.signal_sent = sent_signal

        def kill(self):
            raise AssertionError("Terminate should stop the fake process.")

        def communicate(self, timeout=None):
            return "", ""

    process = FakeProcess()
    monkeypatch.setattr(
        "backend.services.hls.loudness._ffmpeg_executable",
        lambda: "ffmpeg",
    )
    monkeypatch.setattr(
        "backend.services.hls.loudness.subprocess.Popen",
        lambda *_args, **_kwargs: process,
    )

    with pytest.raises(LoudnessAnalysisCancelled):
        analyze_hls_loudness(
            "https://example.com/live.m3u8",
            5,
            cancel_event=cancel_event,
        )

    assert process.signal_sent is not None


def test_analyzer_preserves_partial_metrics_when_stopped(monkeypatch):
    cancel_event = threading.Event()
    cancel_event.set()

    class FakeProcess:
        returncode = 255

        def send_signal(self, _sent_signal):
            return None

        def kill(self):
            raise AssertionError("Graceful stop should preserve the summary.")

        def communicate(self, timeout=None):
            return "", (
                "[Parsed_ebur128_0] t: 8.0 TARGET:-23 LUFS M:-24.0 "
                "S:-23.9 I:-23.9 LUFS LRA:2.3 LU FTPK:-5.0 -4.8 dBFS "
                "TPK:-4.5 -4.7 dBFS"
            )

    monkeypatch.setattr(
        "backend.services.hls.loudness._ffmpeg_executable",
        lambda: "ffmpeg",
    )
    monkeypatch.setattr(
        "backend.services.hls.loudness.subprocess.Popen",
        lambda *_args, **_kwargs: FakeProcess(),
    )

    result = analyze_hls_loudness(
        "https://example.com/live.m3u8",
        5,
        cancel_event=cancel_event,
    )

    assert result["partial"] is True
    assert result["integrated_lkfs"] == -23.9
    assert result["true_peak_dbtp"] == -4.5
    assert result["loudness_range_lu"] == 2.3
    assert result["measured_seconds"] >= 0


def test_job_store_scopes_results_to_organization():
    store = LoudnessJobStore(
        analyzer=lambda _url, _duration: {
            "status": "pass",
            "integrated_lkfs": -24.0,
        }
    )
    created = store.start(
        organization_id="org-a",
        user_id="user-a",
        playlist_url="https://example.com/live.m3u8",
        duration_minutes=5,
    )

    for _ in range(100):
        result = store.public(created["id"], "org-a")
        if result["status"] == "completed":
            break
        time.sleep(0.01)

    assert result["result"]["integrated_lkfs"] == -24.0
    with pytest.raises(KeyError):
        store.public(created["id"], "org-b")


def test_job_store_rejects_unsupported_duration():
    store = LoudnessJobStore()

    with pytest.raises(LoudnessAnalysisError):
        store.start(
            organization_id="org-a",
            user_id="user-a",
            playlist_url="https://example.com/live.m3u8",
            duration_minutes=20,
        )


def test_job_store_allows_only_one_active_job_per_organization():
    def delayed_analyzer(_url, _duration):
        time.sleep(0.1)
        return {"status": "pass"}

    store = LoudnessJobStore(analyzer=delayed_analyzer)
    store.start(
        organization_id="org-a",
        user_id="user-a",
        playlist_url="https://example.com/live.m3u8",
        duration_minutes=5,
    )

    with pytest.raises(LoudnessAnalysisError):
        store.start(
            organization_id="org-a",
            user_id="user-b",
            playlist_url="https://example.com/other.m3u8",
            duration_minutes=5,
        )


def test_job_store_cancellation_remains_terminal():
    release = threading.Event()

    def delayed_analyzer(_url, _duration):
        release.wait(0.5)
        return {"status": "pass"}

    store = LoudnessJobStore(analyzer=delayed_analyzer)
    created = store.start(
        organization_id="org-a",
        user_id="user-a",
        playlist_url="https://example.com/live.m3u8",
        duration_minutes=5,
    )

    cancelled = store.cancel(created["id"], "org-a")
    assert cancelled["status"] == "cancelled"
    release.set()
    time.sleep(0.05)
    assert store.public(created["id"], "org-a")["status"] == "cancelled"


def test_job_store_keeps_partial_result_from_real_analyzer(monkeypatch):
    def partial_analyzer(_url, _duration, cancel_event=None):
        assert cancel_event is not None
        cancel_event.wait(1)
        return {
            "status": "pass",
            "integrated_lkfs": -24.0,
            "partial": True,
        }

    monkeypatch.setattr(
        loudness_module,
        "analyze_hls_loudness",
        partial_analyzer,
    )
    store = LoudnessJobStore(analyzer=partial_analyzer)
    created = store.start(
        organization_id="org-a",
        user_id="user-a",
        playlist_url="https://example.com/live.m3u8",
        duration_minutes=5,
    )

    for _ in range(100):
        if store.public(created["id"], "org-a")["status"] == "running":
            break
        time.sleep(0.01)
    stopped = store.cancel(created["id"], "org-a")

    assert stopped["status"] == "completed"
    assert stopped["result"]["partial"] is True
    assert stopped["result"]["integrated_lkfs"] == -24.0
