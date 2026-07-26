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
    repair_javascript = (
        FRONTEND_DIR / "xmltv-repair.js"
    ).read_text()
    prelog_javascript = (
        FRONTEND_DIR / "prelog-filter.js"
    ).read_text()

    assert "/api/xmltv/import" in javascript
    assert "/api/xmltv/generate" in javascript
    assert "/api/xmltv/validate" in validator_javascript
    assert "/api/xmltv/repair/preview" in repair_javascript
    assert "/api/xmltv/repair" in repair_javascript
    assert "/api/prelogs/options" in prelog_javascript
    assert "/api/prelogs/filter" in prelog_javascript
    assert "/api/prelogs/export" in prelog_javascript


def test_validator_frontend_is_available():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (
        FRONTEND_DIR / "xmltv-validator.js"
    ).read_text()

    assert (FRONTEND_DIR / "xmltv-validator.js").is_file()
    assert 'id="validator-form"' in html
    assert 'name="xmltv_file"' in html
    assert 'href="#validator"' in html
    assert 'id="download-validator-report"' in html
    assert 'id="download-validator-html-report"' in html
    assert 'class="download-menu"' in html
    assert "Download Report" in html
    assert "validation-report.json" in javascript
    assert "validation-report.html" in javascript
    assert "escapeHtml" in javascript


def test_repair_frontend_is_available():
    html = (FRONTEND_DIR / "index.html").read_text()

    assert (FRONTEND_DIR / "xmltv-repair.js").is_file()
    assert 'id="repair-form"' in html
    assert 'id="accept-repairs"' in html
    assert 'href="#repair"' in html


def test_prelog_filter_builder_is_available():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "prelog-filter.js").read_text()

    assert (FRONTEND_DIR / "prelog-filter.js").is_file()
    assert 'id="prelog-filter-form"' in html
    assert 'value="prefix"' in html
    assert 'value="exact"' in html
    assert 'value="contains"' in html
    assert 'name="start_date"' in html
    assert 'name="end_date"' in html
    assert 'name="broadcast_day_start"' in html
    assert 'name="source_timezone"' in html
    assert "Auto Detect from Playlist" in html
    assert "broadcastToolPro.prelogFilters" in javascript
    assert "broadcastToolPro.prelogFilterMode" in javascript
    assert 'id="prelog-export-panel"' in html
    assert 'id="prelog-logo"' in html
    assert 'id="prelog-product"' in html
    assert ".jpg,.jpeg" in html
    assert 'id="export-prelog-button"' in html
    assert "<th>Date</th>" in html
    assert "<th>Time</th>" in html


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
