import hashlib
import re
from pathlib import Path

from backend.main import (
    FRONTEND_DIR,
    application,
    email_policy,
    home,
    privacy_policy,
    terms_of_service,
)


def test_frontend_files_exist():
    assert (FRONTEND_DIR / "landing.html").is_file()
    assert (FRONTEND_DIR / "landing.css").is_file()
    assert (FRONTEND_DIR / "landing.js").is_file()
    assert (FRONTEND_DIR / "i18n.js").is_file()
    assert (FRONTEND_DIR / "index.html").is_file()
    assert (FRONTEND_DIR / "styles.css").is_file()
    assert (FRONTEND_DIR / "app.js").is_file()
    assert (FRONTEND_DIR / "theme.js").is_file()
    assert (FRONTEND_DIR / "legal.css").is_file()
    assert (FRONTEND_DIR / "privacy.html").is_file()
    assert (FRONTEND_DIR / "terms.html").is_file()
    assert (FRONTEND_DIR / "email-policy.html").is_file()


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


def test_public_and_authenticated_interfaces_share_language_preference():
    app_html = (FRONTEND_DIR / "index.html").read_text()
    landing_html = (FRONTEND_DIR / "landing.html").read_text()
    javascript = (FRONTEND_DIR / "i18n.js").read_text()

    assert "/static/i18n.js" in app_html
    assert "/static/i18n.js" in landing_html
    assert app_html.count("data-language-select") >= 1
    assert landing_html.count("data-language-select") >= 1
    assert 'data-i18n="auth.signIn"' in app_html
    assert 'data-i18n="home.title"' in app_html
    assert 'data-i18n="landing.hero.title"' in landing_html
    assert "broadcastToolPro.language" in javascript
    assert 'new Set(["en", "es"])' in javascript
    assert 'document.documentElement.lang = language' in javascript
    assert 'new CustomEvent("btp:languagechange"' in javascript
    assert "localStorage.setItem" in javascript
    assert "navigator.language" in javascript


def test_xmltv_generator_and_programming_grid_are_localized_independently():
    html = (FRONTEND_DIR / "index.html").read_text()
    application_javascript = (FRONTEND_DIR / "app.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    for key in [
        "generator.title",
        "generator.channelName",
        "generator.validate",
        "generator.generate",
        "preview.title",
        "preview.broadcastDate",
        "grid.title",
        "grid.download",
    ]:
        assert f'data-i18n="{key}"' in html
        assert f'"{key}"' in translations

    assert 'data-i18n-placeholder="preview.searchPlaceholder"' in html
    assert 'window.addEventListener("btp:languagechange"' in application_javascript
    assert 'uiText("generator.validating"' in application_javascript
    assert '"preview.summary"' in application_javascript
    assert '"grid.download"' in application_javascript

    # Export language remains an explicit workflow setting and is not coupled
    # to the global interface preference.
    assert 'id="prelog-report-language"' in html
    assert 'id="postlog-report-language"' in html
    assert 'id="hls-report-language"' in html
    assert 'id="hls-channel-name"' in html
    assert 'id="hls-client-name"' in html
    assert 'id="hls-test-reference"' in html
    assert 'id="hls-operator-name"' in html
    assert 'id="hls-monitoring-purpose"' in html
    assert 'id="hls-expected-cue-at"' in html
    assert 'id="hls-expected-break-duration"' in html
    assert 'id="hls-report-timezone"' in html


def test_xmltv_validator_and_repair_localize_ui_without_mutating_exports():
    html = (FRONTEND_DIR / "index.html").read_text()
    validator = (FRONTEND_DIR / "xmltv-validator.js").read_text()
    repair = (FRONTEND_DIR / "xmltv-repair.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    for key in (
        "validator.title",
        "validator.validate",
        "validator.downloadReport",
        "repair.title",
        "repair.analyze",
        "repair.download",
    ):
        assert f'data-i18n="{key}"' in html
        assert f'"{key}"' in translations

    assert 'window.addEventListener("btp:languagechange"' in validator
    assert 'window.addEventListener("btp:languagechange"' in repair
    assert 'validator.rule.XMLTV-003' in translations
    assert 'repair.rule.REPAIR-005' in translations

    # Canonical XML and exported report formats remain untouched by the
    # global interface preference.
    assert 'application/pdf' in validator
    assert 'application/json' in validator
    assert 'text/html;charset=utf-8' in validator
    assert 'link.download = match?.[1] || "xmltv-repaired.xml"' in repair


def test_traffic_modules_localize_ui_without_changing_report_language():
    html = (FRONTEND_DIR / "index.html").read_text()
    prelog = (FRONTEND_DIR / "prelog-filter.js").read_text()
    postlog = (FRONTEND_DIR / "postlog-certification.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    for key in (
        "prelog.title",
        "prelog.inspect",
        "postlog.title",
        "postlog.find",
        "traffic.filterType",
        "traffic.reportLanguage",
    ):
        assert f'data-i18n="{key}"' in html
        assert f'"{key}"' in translations

    assert 'window.addEventListener("btp:languagechange"' in prelog
    assert 'window.addEventListener("btp:languagechange"' in postlog
    assert 'data.append("report_language", prelogReportLanguage.value)' in prelog
    assert '"report_language",' in postlog
    assert 'document.querySelector("#postlog-report-language").value' in postlog


def test_hls_workflows_localize_ui_without_changing_report_language():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "hls-validator.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    for key in (
        "hls.title",
        "hls.validate",
        "hls.monitor",
        "hls.downloadReport",
        "hls.bandwidth",
        "hls.scteTrack",
    ):
        assert f'data-i18n="{key}"' in html
        assert f'"{key}"' in translations

    assert 'window.addEventListener("btp:languagechange"' in javascript
    assert '"hls.monitoring"' in javascript
    assert '"hls.inspectionSummary"' in javascript
    assert 'report_language: hlsReportLanguage.value' in javascript
    assert 'id="hls-report-language"' in html
    assert 'value="en" data-i18n="language.english"' in html
    assert 'value="es" data-i18n="language.spanish"' in html


def test_help_center_shares_global_language_without_mutating_tickets():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "help.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    for key in (
        "help.launcher",
        "help.center",
        "help.allGuides",
    ):
        assert f'data-i18n="{key}"' in html
        assert f'"{key}"' in translations

    assert "broadcastToolPro.helpLanguage" not in javascript
    assert "window.BTPi18n.setLanguage" in javascript
    assert 'window.addEventListener("btp:languagechange"' in javascript
    assert "helpStatusLabel" in javascript
    assert 'request.id' in javascript


def test_billing_localizes_presentation_without_mutating_commercial_data():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "billing.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    for key in (
        "billing.title",
        "billing.pricingTitle",
        "billing.servicesTitle",
        "billing.invoices",
    ):
        assert f'data-i18n="{key}"' in html
        assert f'"{key}"' in translations

    assert "latestBillingPayload" in javascript
    assert 'window.addEventListener("btp:languagechange"' in javascript
    assert "billingPlanDescription" in javascript
    assert "billingFeature" in javascript
    assert "/api/billing/organizations/" in javascript


def test_account_access_workflows_localize_without_mutating_identity_data():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "auth.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    for key in (
        "auth.recovery",
        "auth.requestReceived",
        "auth.trialEyebrow",
        "auth.accountApproved",
        "account.trialReminders",
        "account.suspended",
    ):
        assert f'data-i18n="{key}"' in html
        assert f'"{key}"' in translations

    assert 'window.addEventListener("btp:languagechange"' in javascript
    assert "renderLocalizedIdentity" in javascript
    assert "localizedRole" in javascript
    assert 'organization.plan' in javascript
    assert 'organization?.status === "suspended"' in javascript
    assert 'entitlements.access?.type === "trial"' in javascript


def test_report_history_localizes_without_mutating_archived_files():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "report-history.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    for key in ("history.title", "history.refresh", "history.download"):
        assert f'"{key}"' in translations
    assert 'data-i18n="history.title"' in html
    assert 'data-i18n="history.format"' in html
    assert 'window.addEventListener("btp:languagechange"' in javascript
    assert "renderReportHistory(latestReports)" in javascript
    assert 'download.setAttribute("download", report.filename)' in javascript
    assert "report.output_format.toUpperCase()" in javascript


def test_home_returns_frontend():
    landing_response = home()
    application_response = application()

    assert Path(landing_response.path) == FRONTEND_DIR / "landing.html"
    assert Path(application_response.path) == FRONTEND_DIR / "index.html"


def test_public_policy_routes_return_their_pages():
    assert Path(privacy_policy().path) == FRONTEND_DIR / "privacy.html"
    assert Path(terms_of_service().path) == FRONTEND_DIR / "terms.html"
    assert Path(email_policy().path) == FRONTEND_DIR / "email-policy.html"


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
    assert "OUR CLIENTS" in html
    assert "/static/assets/tarima-logo-white-v2.png" in html
    assert "/static/assets/tarima-logo-white.png" not in html
    assert "/static/assets/comercio-logo-white.png" in html
    tarima_logo = FRONTEND_DIR / "assets" / "tarima-logo-white-v2.png"
    assert hashlib.sha256(tarima_logo.read_bytes()).hexdigest() == (
        "7c7548599eda46dcb581ff12211002d6496220aa1ba5df63eda8d8710b53e0e0"
    )
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
    assert 'href="/privacy"' in html
    assert 'href="/terms"' in html
    assert 'href="/email-policy"' in html


def test_public_landing_page_has_complete_bilingual_copy():
    html = (FRONTEND_DIR / "landing.html").read_text()
    css = (FRONTEND_DIR / "landing.css").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()
    landing_keys = set(re.findall(r'data-i18n="(landing\.[^"]+)"', html))

    assert len(landing_keys) >= 100
    for key in landing_keys:
        assert translations.count(f'"{key}"') >= 2, key

    assert '"landing.products.traffic.title": "Convierte playlists y datos As-Run en evidencia."' in translations
    assert '"landing.products.streaming.title": "Inspecciona la entrega antes de que se convierta en un incidente."' in translations
    assert '"landing.footer.copyright": "© 2026 Broadcast Tool Pro. Todos los derechos reservados."' in translations
    assert ".landing-kicker > span:first-child" in css
    assert ".landing-kicker span {" not in css
    assert '"landing.clients.kicker": "NUESTROS CLIENTES"' in translations
    assert "landing.clients.title" not in translations
    assert "landing.clients.copy" not in translations
    assert "/static/landing.css?v=20260817-6" in html


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

    assert '/static/hls-validator.js?v=20260817-1' in html
    assert '/static/i18n.js?v=20260818-1' in html

    assert 'href="#hls-validator"' in html
    assert 'id="monitor-hls-button"' in html
    assert 'id="stop-hls-monitor-button"' in html
    assert 'id="hls-monitor-trigger-body"' in html
    assert 'id="download-hls-report-button"' in html
    assert 'id="hls-report-language"' in html
    assert 'value="en" data-i18n="language.english"' in html
    assert 'value="es" data-i18n="language.spanish"' in html
    assert 'value="5" data-i18n="hls.minutes5"' in html
    assert 'value="10" data-i18n="hls.minutes10"' in html
    assert 'value="15" data-i18n="hls.minutes15"' in html
    assert "pollHlsMonitor" in javascript
    assert "hlsSeenTriggers" in javascript
    assert "hlsInspectedSegments" in javascript
    assert '"inspected_segment_urls"' in javascript
    assert "/api/hls/report/pdf" in javascript
    assert "summarizeScteBreaks" in javascript
    assert "continuation_count" in javascript


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
    assert 'id="trial-reminder-preference"' in html
    assert 'id="account-preference-message"' in html
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
    help_javascript = (FRONTEND_DIR / "help.js").read_text()
    assert "refreshOrganizationEntitlements" in auth_javascript
    assert "applyOrganizationAccess" in auth_javascript
    assert "/api/auth/email-preferences" in auth_javascript
    assert "/api/auth/trial" in auth_javascript
    assert 'requestedMode === "trial"' in auth_javascript
    assert "moduleSurfaces" in auth_javascript
    assert "Unsaved changes" in admin_javascript
    assert "Saving changes" in admin_javascript
    assert "Payment Setup" in html
    assert "Stripe checkout required" in admin_javascript
    assert "Complimentary access" in admin_javascript
    assert "payment_method" in admin_javascript
    assert "Awaiting Stripe payment" in admin_javascript
    assert "Ends on date" in admin_javascript
    assert "lifecycle_note" in admin_javascript
    assert "hasSubscriptionChange" in admin_javascript
    assert 'awaitingPayment' in admin_javascript
    assert "subscription_events" in admin_javascript
    assert "pending_plan_code" in admin_javascript
    assert "No pending plan change" in admin_javascript
    assert "/api/admin/incidents/" in admin_javascript
    assert "openAdminTicket" in admin_javascript
    assert 'id="admin-ticket-panel"' in html
    assert 'id="admin-customer-reply-form"' in html
    assert 'id="admin-internal-note-form"' in html
    assert 'id="admin-ticket-resolution"' in html
    assert 'id="admin-backup-status"' in html
    assert 'id="run-backup-button"' in html
    assert 'id="check-drive-button"' in html
    assert 'id="upload-backup-button"' in html
    assert "/api/admin/backups" in admin_javascript
    assert "/api/admin/backups/google-drive/check" in admin_javascript
    assert "/api/admin/backups/google-drive/upload-latest" in admin_javascript
    assert 'id="admin-email-metrics"' in html
    assert '<option value="privacy">Privacy or data request</option>' in html
    assert 'id="help-request-type"' in html
    assert '"Account & Privacy"' in help_javascript
    assert 'title: "Privacy & Data Requests"' in help_javascript
    assert 'helpCurrentGuide === "privacy"' in help_javascript
    assert 'id="admin-email-attempt-body"' in html
    assert 'id="admin-email-detail"' in html
    assert "View Details" in admin_javascript
    assert 'id="admin-suppression-body"' in html
    assert 'id="admin-email-event-body"' in html
    assert "/api/admin/email-health" in admin_javascript
    assert "/api/admin/email-outbox/" in admin_javascript
    assert "/api/admin/email-suppressions/" in admin_javascript


def test_billing_and_subscription_interface_is_present():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "billing.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()
    assert (
        "const monitoringApproved = isApprovedPlan\n"
        "          ? Boolean(approvedCheckout.include_stream_monitoring)\n"
        "          : false;"
    ) in javascript

    assert (FRONTEND_DIR / "billing.js").is_file()
    assert 'id="open-billing-button"' in html
    assert 'id="billing-panel"' in html
    assert 'id="billing-summary"' in html
    assert 'id="billing-entitlements"' in html
    assert 'id="billing-pricing-grid"' in html
    assert 'id="billing-pricing-addons"' in html
    assert 'id="billing-invoice-body"' in html
    assert 'id="billing-provider-note"' in html
    assert 'id="billing-monitoring-choice-input"' in html
    assert "Keep Stream Monitoring for +$59.00/month" in html
    assert '.billing-monitoring-choice input[type="checkbox"]' in (
        FRONTEND_DIR / "styles.css"
    ).read_text()
    assert "renderSubscriptionChangePreview" in javascript
    assert '"billing.providerConnectedNote"' in javascript
    assert (
        "Payments and saved payment methods are securely managed by Stripe."
        in translations
    )
    assert (
        "Stripe administra de forma segura los pagos y los métodos de pago "
        "guardados."
        in translations
    )
    assert "Cancel Scheduled Change" in javascript
    assert "cancelScheduledSubscriptionChange" in javascript
    assert 'billingMonitoringChoiceInput.addEventListener("change"' in javascript
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
    assert 'href = "mailto:billing@broadcasttoolpro.com"' in javascript


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
    assert "window.BTPi18n.setLanguage" in javascript
    assert 'window.addEventListener("btp:languagechange"' in javascript
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
    assert "mailto:support@broadcasttoolpro.com" in html


def test_public_contact_addresses_are_visible():
    html = (FRONTEND_DIR / "landing.html").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    assert "mailto:hello@broadcasttoolpro.com" in html
    assert "mailto:support@broadcasttoolpro.com" in html
    assert "mailto:security@broadcasttoolpro.com" in html
    assert '"landing.footer.sales": "Ventas"' in translations
    assert '"landing.footer.support": "Soporte"' in translations


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
    assert 'data-i18n="traffic.date">Date</th>' in html
    assert 'data-i18n="traffic.time">Time</th>' in html


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


def test_access_request_collects_requested_plan_and_addon():
    html = (FRONTEND_DIR / "index.html").read_text()
    auth_javascript = (FRONTEND_DIR / "auth.js").read_text()
    admin_javascript = (FRONTEND_DIR / "admin.js").read_text()

    assert 'name="requested_plan"' in html
    assert 'value="programming_suite"' in html
    assert 'value="professional"' in html
    assert 'value="enterprise"' in html
    assert 'name="include_stream_monitoring"' in html
    assert 'name="billing_cycle"' in html
    assert "updateAccessRequestPricing" in auth_javascript
    assert "requestedPlan.replaceAll" in admin_javascript


def test_frontend_does_not_render_server_messages_as_html():
    javascript = (FRONTEND_DIR / "app.js").read_text()

    assert "issueList.innerHTML" not in javascript
    assert "resultMetrics.innerHTML" not in javascript
    assert "textContent = text" in javascript


def test_customer_session_clears_global_administrative_state():
    auth = (FRONTEND_DIR / "auth.js").read_text()
    admin = (FRONTEND_DIR / "admin.js").read_text()
    history = (FRONTEND_DIR / "report-history.js").read_text()

    assert "function resetAdministrativeSurface" in auth
    assert "resetAdministrativeSurface();" in auth
    assert "resetAdministrativeSurface(identity);" in auth
    assert 'document.querySelector("#admin-access-body")?.replaceChildren()' in auth
    assert 'document.querySelector("#admin-email-event-body")?.replaceChildren()' in auth
    assert 'fetch("/api/auth/me"' in admin
    assert "if (!identity?.user?.is_superuser)" in admin
    assert "function clearReportHistory" in history
    assert 'window.addEventListener("btp:identity"' in history
