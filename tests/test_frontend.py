from pathlib import Path

from backend.main import FRONTEND_DIR, home


def test_frontend_files_exist():
    assert (FRONTEND_DIR / "index.html").is_file()
    assert (FRONTEND_DIR / "styles.css").is_file()
    assert (FRONTEND_DIR / "app.js").is_file()


def test_home_returns_frontend():
    response = home()

    assert Path(response.path) == FRONTEND_DIR / "index.html"


def test_frontend_uses_xmltv_endpoints():
    javascript = (FRONTEND_DIR / "app.js").read_text()
    validator_javascript = (
        FRONTEND_DIR / "xmltv-validator.js"
    ).read_text()

    assert "/api/xmltv/import" in javascript
    assert "/api/xmltv/generate" in javascript
    assert "/api/xmltv/validate" in validator_javascript


def test_validator_frontend_is_available():
    html = (FRONTEND_DIR / "index.html").read_text()

    assert (FRONTEND_DIR / "xmltv-validator.js").is_file()
    assert 'id="validator-form"' in html
    assert 'name="xmltv_file"' in html
    assert 'href="#validator"' in html


def test_frontend_preserves_backend_field_names():
    html = (FRONTEND_DIR / "index.html").read_text()

    for field_name in (
        "schedule_file",
        "channel_timezone",
        "channel_id",
        "channel_name",
        "primary_language",
        "original_language",
        "rating_system",
    ):
        assert f'name="{field_name}"' in html


def test_frontend_does_not_render_server_messages_as_html():
    javascript = (FRONTEND_DIR / "app.js").read_text()

    assert "issueList.innerHTML" not in javascript
    assert "resultMetrics.innerHTML" not in javascript
    assert "textContent = text" in javascript
