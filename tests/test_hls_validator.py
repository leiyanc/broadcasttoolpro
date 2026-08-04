from backend.main import app
from backend.services.hls.validator import (
    HlsValidationError,
    _validate_public_url,
    inspect_mpegts_scte35,
    validate_hls,
)
from backend.api.hls import download_hls_report
from backend.services.hls.report import generate_hls_report
from backend.services.hls.report import _scte_summary, _timestamp_label


MASTER_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:6
#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,FRAME-RATE=29.97,CODECS="avc1.4d401e,mp4a.40.2"
360p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2400000,RESOLUTION=1280x720,CODECS="avc1.4d401f,mp4a.40.2"
720p/index.m3u8
"""

MEDIA_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:100
#EXTINF:6.0,
segment100.ts
#EXTINF:5.5,
segment101.ts
#EXT-X-ENDLIST
"""

SCTE35_PLAYLIST = """#EXTM3U
#EXT-X-TARGETDURATION:8
#EXT-X-PROGRAM-DATE-TIME:2026-07-27T12:00:00Z
#EXT-X-DATERANGE:ID="break-100",CLASS="com.apple.hls.scte35",START-DATE="2026-07-27T12:00:00Z",PLANNED-DURATION=30.0,SCTE35-OUT=0xFC30
#EXT-X-CUE-OUT:30
#EXTINF:8,
segment100.ts
#EXT-X-CUE-IN
#EXTINF:8,
segment101.ts
"""


def test_hls_report_timestamp_label_uses_utc():
    assert _timestamp_label("2026-07-27T12:30:45Z") == (
        "2026-07-27 12:30:45 UTC"
    )


def test_master_playlist_reports_variants():
    playlists = {
        "https://cdn.example.com/live/master.m3u8": MASTER_PLAYLIST,
        "https://cdn.example.com/live/360p/index.m3u8": MEDIA_PLAYLIST,
        "https://cdn.example.com/live/720p/index.m3u8": MEDIA_PLAYLIST,
    }
    result = validate_hls(
        "https://cdn.example.com/live/master.m3u8",
        fetcher=playlists.__getitem__,
    )

    assert result["valid"] is True
    assert result["playlist_type"] == "master"
    assert result["variant_count"] == 2
    assert result["variants"][0]["resolution"] == "640x360"
    assert result["variants"][0]["segments"] == 2
    assert result["variants"][0]["valid"] is True
    assert result["variants"][1]["bandwidth"] == 2_400_000


def test_media_playlist_reports_segments_and_duration():
    result = validate_hls(
        "https://cdn.example.com/live/index.m3u8",
        fetcher=lambda _: MEDIA_PLAYLIST,
    )

    assert result["valid"] is True
    assert result["playlist_type"] == "media"
    assert result["media"]["segments"] == 2
    assert result["media"]["total_duration"] == 11.5
    assert result["media"]["live"] is False


def test_media_playlist_reports_observed_segment_bandwidth():
    result = validate_hls(
        "https://cdn.example.com/live/index.m3u8",
        fetcher=lambda _: MEDIA_PLAYLIST,
        inspect_segments=True,
        segment_fetcher=lambda _: (b"", 1_100_000),
    )

    assert result["media"]["measured_bandwidth_kbps"] == 1600.0


def test_invalid_media_playlist_reports_blocking_issues():
    result = validate_hls(
        "https://cdn.example.com/live/index.m3u8",
        fetcher=lambda _: "#EXTM3U\n#EXTINF:8,\nsegment.ts\n",
    )

    assert result["valid"] is False
    assert any(
        issue["rule_id"] == "HLS-008"
        for issue in result["issues"]
    )


def test_scte35_and_legacy_cue_triggers_are_detected():
    result = validate_hls(
        "https://cdn.example.com/live/index.m3u8",
        fetcher=lambda _: SCTE35_PLAYLIST,
    )

    trigger_types = {
        trigger["type"]
        for trigger in result["media"]["triggers"]
    }
    assert result["valid"] is True
    assert result["scte35_detected"] is True
    assert result["trigger_count"] == 3
    assert {
        "SCTE-35 DATERANGE",
        "CUE-OUT",
        "CUE-IN",
    } <= trigger_types
    assert result["media"]["triggers"][0]["id"] == "break-100"
    assert result["media"]["triggers"][0]["duration"] == 30.0


def _ts_packet(pid: int, payload: bytes) -> bytes:
    header = bytes([
        0x47,
        0x40 | ((pid >> 8) & 0x1F),
        pid & 0xFF,
        0x10,
    ])
    return (header + b"\x00" + payload).ljust(188, b"\xFF")


def test_mpegts_scte35_track_and_cue_are_detected():
    pat = bytes.fromhex(
        "00b00d0001c100000001e1e000000000"
    )
    pmt = bytes.fromhex(
        "02b01a0001c10000e1e1f000"
        "1be1e1f000"
        "86e1e3f003520100"
        "00000000"
    )
    cue = bytes.fromhex("fc301100000000000000000000000000")
    content = (
        _ts_packet(0, pat)
        + _ts_packet(480, pmt)
        + _ts_packet(483, cue)
    )

    result = inspect_mpegts_scte35(content)

    assert result["mpegts"] is True
    assert result["track_detected"] is True
    assert result["pids"] == [483]
    assert result["triggers"][0]["type"] == "SCTE-35 MPEG-TS"


def test_non_playlist_resource_is_rejected():
    result = validate_hls(
        "https://cdn.example.com/not-hls",
        fetcher=lambda _: "<html>Not HLS</html>",
    )

    assert result["valid"] is False
    assert result["issues"][0]["rule_id"] == "HLS-001"


def test_local_network_urls_are_blocked():
    try:
        _validate_public_url("http://127.0.0.1/private.m3u8")
    except HlsValidationError as exc:
        assert "not allowed" in str(exc)
    else:
        raise AssertionError("Expected the local network URL to be blocked.")


def test_hls_router_is_registered():
    paths = set(app.openapi()["paths"])

    assert "/api/hls/validate" in paths
    assert "/api/hls/report/pdf" in paths


def sample_report() -> dict:
    return {
        "valid": False,
        "url": "https://cdn.example.com/live/master.m3u8",
        "playlist_type": "master",
        "monitoring_minutes": 5,
        "inspections": 50,
        "generated_at": "2026-07-27T16:00:00Z",
        "report_language": "en",
        "scte35_detected": True,
        "trigger_count": 1,
        "bandwidth_samples": [
            {
                "detected_at": "2026-07-27T15:55:00Z",
                "bandwidth_kbps": 2380,
            },
            {
                "detected_at": "2026-07-27T16:00:00Z",
                "bandwidth_kbps": 2510,
            },
        ],
        "variants": [{
            "bandwidth": 2_400_000,
            "resolution": "1280x720",
            "frame_rate": "29.97",
            "codecs": "avc1.4d401f,mp4a.40.2",
            "segments": 6,
            "trigger_count": 1,
            "valid": True,
        }],
        "triggers": [{
            "detected_at": "2026-07-27T15:59:30Z",
            "type": "SCTE-35 DATERANGE",
            "id": "break-100",
            "start_date": "2026-07-27T16:00:00Z",
            "duration": 30,
            "source_url": "https://cdn.example.com/live/720p.m3u8",
        }],
        "issues": [{
            "severity": "warning",
            "rule_id": "HLS-012",
            "message": "An unmatched CUE-IN marker was detected.",
        }],
    }


def test_scte_summary_does_not_count_continuations_or_duplicate_signaling():
    summary = _scte_summary({"triggers": [
        {
            "type": "SCTE-35 DATERANGE",
            "id": "break-100",
            "duration": 30,
            "ad_trigger": True,
        },
        {"type": "CUE-OUT", "duration": 30},
        {"type": "CUE-OUT-CONT", "duration": 8},
        {"type": "CUE-OUT-CONT", "duration": 16},
        {"type": "CUE-IN", "duration": None},
    ]})

    assert summary["break_count"] == 1
    assert summary["total_planned_duration"] == 30
    assert summary["continuation_count"] == 2


def test_hls_pdf_report_is_branded_and_downloadable():
    content = generate_hls_report(sample_report())
    response = download_hls_report(sample_report())

    assert content.startswith(b"%PDF")
    assert len(content) > 3_000
    assert response.media_type == "application/pdf"
    assert "broadcast-tool-pro-hls-report.pdf" in response.headers[
        "content-disposition"
    ]


def test_hls_pdf_report_supports_spanish():
    report = sample_report()
    report["report_language"] = "es"

    content = generate_hls_report(report)
    english_content = generate_hls_report(sample_report())

    assert content.startswith(b"%PDF")
    assert len(content) > 3_000
    assert content != english_content
