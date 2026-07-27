from backend.main import app
from backend.services.hls.validator import (
    HlsValidationError,
    _validate_public_url,
    validate_hls,
)


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
