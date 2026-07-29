from pathlib import Path

from backend.main import FRONTEND_DIR, application, home


def test_frontend_files_exist():
    assert (FRONTEND_DIR / "landing.html").is_file()
    assert (FRONTEND_DIR / "landing.css").is_file()
    assert (FRONTEND_DIR / "landing.js").is_file()
    assert (FRONTEND_DIR / "index.html").is_file()
    assert (FRONTEND_DIR / "styles.css").is_file()
    assert (FRONTEND_DIR / "app.js").is_file()
    assert (FRONTEND_DIR / "theme.js").is_file()


def test_frontend_supports_persistent_light_and_dark_modes():
    html = (FRONTEND_DIR / "index.html").read_text()
    css = (FRONTEND_DIR / "styles.css").read_text()
    javascript = (FRONTEND_DIR / "theme.js").read_text()

    assert 'id="theme-toggle"' in html
    assert "/static/theme.js" in html
    assert '[data-theme="dark"]' in css
    assert "broadcastToolPro.theme" in javascript
    assert "localStorage.setItem" in javascript
    assert 'class="operations-home"' in html
    assert 'class="operations-rail"' in html
    assert 'class="module-launcher"' in html
    assert html.count('class="module-icon"') == 6
    assert html.count('<svg viewBox="0 0 24 24">') == 6
    assert "Control every broadcast workflow." in html
    assert "Create XMLTV File" in html
    assert "Validate XMLTV File" in html
    assert "Repair XMLTV File" in html
    assert "XMLTV Feed" not in html
    assert "--signal: #16c9d4" in css
    assert ".preview-table tbody tr:nth-child(even) td" in css
    assert "drop-shadow(0 4px 12px rgba(32, 214, 223, 0.16))" in css
    assert "background: #0c2a26" not in css
    assert (
        FRONTEND_DIR / "assets" / "broadcast-tool-pro-logo.png"
    ).is_file()


def test_home_returns_frontend():
    landing_response = home()
    application_response = application()

    assert Path(landing_response.path) == FRONTEND_DIR / "landing.html"
    assert Path(application_response.path) == FRONTEND_DIR / "index.html"


def test_public_landing_page_presents_the_platform():
    html = (FRONTEND_DIR / "landing.html").read_text()
    css = (FRONTEND_DIR / "landing.css").read_text()
    javascript = (FRONTEND_DIR / "landing.js").read_text()

    assert "Every broadcast workflow. One operating layer." in html
    assert "PROGRAMMING SUITE" in html
    assert "TRAFFIC OPERATIONS" in html
    assert "STREAMING QC" in html
    assert "XMLTV Generator" in html
    assert "Pre-Logs" in html
    assert "Post-Logs" in html
    assert "HLS Validator" in html
    assert ">39<" in html
    assert ">99<" in html
    assert ">199<" in html
    assert "+$59" in html
    assert "Media QC Engine" in html
    assert "COMING SOON" in html
    assert "/app?mode=signin" in html
    assert "/app?mode=create" in html
    assert "/app?mode=trial" in html
    assert "broadcastcontrol.io" not in html.lower()
    assert "Broadcast Control" not in html
    assert "Orion Media" not in html
    assert "It is not a fabricated product screenshot." in html
    assert "--landing-black: #02060c" in css
    assert "@media (max-width: 760px)" in css
    assert "landing-menu-toggle" in javascript


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
    postlog_javascript = (
        FRONTEND_DIR / "postlog-certification.js"
    ).read_text()
    hls_javascript = (
        FRONTEND_DIR / "hls-validator.js"
    ).read_text()

    assert "/api/xmltv/import" in javascript
    assert "/api/xmltv/generate" in javascript
    assert "/api/xmltv/programming-grid" in javascript
    assert "/api/xmltv/validate" in validator_javascript
    assert "/api/xmltv/validate/report/pdf" in validator_javascript
    assert "/api/xmltv/repair/preview" in repair_javascript
    assert "/api/xmltv/repair" in repair_javascript
    assert "/api/prelogs/options" in prelog_javascript
    assert "/api/prelogs/filter" in prelog_javascript
    assert "/api/prelogs/export" in prelog_javascript
    assert "/api/postlogs/options" in postlog_javascript
    assert "/api/postlogs/filter" in postlog_javascript
    assert "/api/postlogs/export" in postlog_javascript
    assert "/api/hls/validate" in hls_javascript


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
    assert 'id="download-validator-pdf-report"' in html
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


def test_hls_stream_monitor_has_bounded_periods():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "hls-validator.js").read_text()

    assert 'href="#hls-validator"' in html
    assert 'id="monitor-hls-button"' in html
    assert 'id="stop-hls-monitor-button"' in html
    assert 'id="hls-monitor-trigger-body"' in html
    assert 'id="download-hls-report-button"' in html
    assert 'id="hls-report-language"' in html
    assert '<option value="en">English</option>' in html
    assert '<option value="es">Español</option>' in html
    assert '<option value="5">5 minutes</option>' in html
    assert '<option value="10">10 minutes</option>' in html
    assert '<option value="15">15 minutes</option>' in html
    assert "pollHlsMonitor" in javascript
    assert "hlsSeenTriggers" in javascript
    assert "/api/hls/report/pdf" in javascript


def test_secure_account_interface_is_present():
    html = (FRONTEND_DIR / "index.html").read_text()

    assert 'id="bootstrap-form"' in html
    assert 'id="login-form"' in html
    assert 'id="trial-form"' in html
    assert 'id="show-login-tab"' in html
    assert 'id="show-trial-tab"' in html
    assert 'name="remember_me"' in html
    assert "Start 7-Day Free Trial" in html
    assert 'id="platform-content"' in html
    assert 'id="account-button"' in html
    assert "/static/auth.js" in html
    assert "/static/admin.js" in html
    assert "/static/billing.js" in html
    assert 'id="admin-control-plane"' in html
    assert 'id="open-admin-button"' in html
    assert 'id="organization-suspended"' in html
    assert 'id="suspended-admin-button"' in html
    assert html.count(
        '/static/assets/broadcast-tool-pro-logo.png'
    ) >= 2
    auth_javascript = (FRONTEND_DIR / "auth.js").read_text()
    admin_javascript = (FRONTEND_DIR / "admin.js").read_text()
    assert "refreshOrganizationEntitlements" in auth_javascript
    assert "applyOrganizationAccess" in auth_javascript
    assert "/api/auth/trial" in auth_javascript
    assert 'requestedMode === "trial"' in auth_javascript
    assert "moduleSurfaces" in auth_javascript
    assert "Unsaved changes" in admin_javascript
    assert "Saving changes" in admin_javascript
    assert "/api/admin/incidents/" in admin_javascript
    assert "openAdminTicket" in admin_javascript
    assert 'id="admin-ticket-panel"' in html
    assert 'id="admin-customer-reply-form"' in html
    assert 'id="admin-internal-note-form"' in html
    assert 'id="admin-ticket-resolution"' in html
    assert 'id="admin-backup-status"' in html
    assert 'id="run-backup-button"' in html
    assert "/api/admin/backups" in admin_javascript


def test_billing_and_subscription_interface_is_present():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "billing.js").read_text()

    assert (FRONTEND_DIR / "billing.js").is_file()
    assert 'id="open-billing-button"' in html
    assert 'id="billing-panel"' in html
    assert 'id="billing-summary"' in html
    assert 'id="billing-entitlements"' in html
    assert 'id="billing-pricing-grid"' in html
    assert 'id="billing-pricing-addons"' in html
    assert 'id="billing-invoice-body"' in html
    assert "/api/billing/organizations/" in javascript
    assert '["owner", "admin"]' in javascript
    assert 'module.source === "professional"' in javascript
    assert "module.available !== false" in javascript
    assert "pricing.display_name" in javascript
    assert "pricing.billing_total_cents" in javascript
    assert "Request Plan Change" in javascript
    assert "Request Add-on" in javascript
    assert "Active Add-on" in javascript
    assert "pricing-feature-status" in javascript


def test_contextual_help_center_is_present():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "help.js").read_text()

    assert (FRONTEND_DIR / "help.js").is_file()
    assert "/static/help.js" in html
    assert 'id="help-launcher"' in html
    assert 'id="help-panel"' in html
    assert 'id="help-guide-select"' in html
    assert 'id="help-language-select"' in html
    assert "helpGuideForViewport" in javascript
    assert "broadcastToolPro.helpLanguage" in javascript
    assert "XMLTV Generator" in javascript
    assert "Post Logs" in javascript
    assert "HLS Validator" in javascript
    assert 'id="help-report-button"' in html
    assert 'id="help-requests-button"' in html
    assert 'id="help-support-form"' in html
    assert 'id="help-error-field"' in html
    assert "/api/support/requests" in javascript
    assert "Ticket:" in javascript
    assert 'id="help-request-detail"' in html
    assert 'id="help-request-reply-form"' in html
    assert 'id="help-reopen-request"' in html
    assert "helpOpenRequest" in javascript
    assert "updateHelpSupportFields" in javascript


def test_epg_preview_is_available_after_schedule_validation():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "app.js").read_text()

    assert 'id="epg-preview"' in html
    assert 'id="epg-preview-date"' in html
    assert 'id="epg-preview-search"' in html
    assert 'id="epg-preview-body"' in html
    assert "showEpgPreview" in javascript
    assert "normalized.programmes" in javascript
    assert "textContent" in javascript
    assert 'id="programming-grid-button"' in html
    assert 'id="programming-grid-status"' in html
    assert 'id="programming-grid-logo"' in html
    assert ".png,.jpg,.jpeg" in html
    assert "Download Programming Grid" in html


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
    assert "scopedStorageKey" in javascript
    assert 'window.addEventListener("btp:identity"' in javascript
    assert 'id="prelog-export-panel"' in html
    assert 'id="prelog-logo"' in html
    assert 'id="prelog-product"' in html
    assert 'id="prelog-output-format"' in html
    assert ".jpg,.jpeg" in html
    assert 'id="export-prelog-button"' in html
    assert "<th>Date</th>" in html
    assert "<th>Time</th>" in html


def test_postlog_certification_is_available():
    html = (FRONTEND_DIR / "index.html").read_text()

    assert (FRONTEND_DIR / "postlog-certification.js").is_file()
    assert 'href="#postlog"' in html
    assert 'id="postlog-form"' in html
    assert 'name="as_run_files"' in html
    assert 'id="postlog-export-panel"' in html
    assert 'id="postlog-output-format"' in html
    assert 'id="postlog-profile-select"' in html
    assert 'id="save-postlog-profile"' in html
    assert 'id="delete-postlog-profile"' in html
    assert "Certify Actual Airings" in html
    assert "indexedDB.open" in (
        FRONTEND_DIR / "postlog-certification.js"
    ).read_text()
    for extension in (".csv", ".xlsx", ".json", ".txt", ".xml"):
        assert extension in html


def test_report_history_is_available():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "report-history.js").read_text()

    assert 'id="report-history"' in html
    assert 'id="prelog-client-name"' in html
    assert 'id="postlog-client-name"' in html
    assert "/api/history" in javascript
    assert "textContent" in javascript
    assert "innerHTML" not in javascript


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
