import subprocess
import time

import pytest

from backend.services.hls.loudness import (
    LoudnessAnalysisError,
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
            "stderr": '{"input_i": "-24.0", "input_tp": "-4.0"}',
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
    assert "loudnorm=I=-24:LRA=7:TP=-2:print_format=json" in captured["command"]
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
