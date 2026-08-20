import json

from tools import release_readiness


def _deployment_fetch(health):
    def fetch(_base_url, path):
        if path == "/health":
            return 200, json.dumps(health).encode(), "application/json"
        return 200, b"Terms of Service Privacy Policy Transactional Email Policy", "text/html"

    return fetch


def test_local_backup_warning_passes_when_remote_backup_is_healthy(monkeypatch):
    monkeypatch.setattr(
        release_readiness,
        "_fetch",
        _deployment_fetch(
            {
                "status": "healthy",
                "backup": "warning",
                "remote_backup": "healthy",
                "email_delivery": "enabled",
                "temporary_storage": "healthy",
            }
        ),
    )

    results = release_readiness.check_deployment("https://example.com")

    assert results[0].passed is True
    assert "healthy remote backup" in results[0].detail


def test_local_backup_warning_fails_without_healthy_remote_backup(monkeypatch):
    monkeypatch.setattr(
        release_readiness,
        "_fetch",
        _deployment_fetch(
            {
                "status": "healthy",
                "backup": "warning",
                "remote_backup": "error",
                "email_delivery": "enabled",
                "temporary_storage": "healthy",
            }
        ),
    )

    results = release_readiness.check_deployment("https://example.com")

    assert results[0].passed is False
    assert "remote_backup='error'" in results[0].detail
