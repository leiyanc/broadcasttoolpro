import hashlib
import re
from pathlib import Path

from backend.main import (
    FRONTEND_DIR,
    application,
    email_policy,
    home,
    privacy_policy,
    security_and_data_handling,
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
    assert (FRONTEND_DIR / "security.html").is_file()


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
    assert "Manage channel operations with confidence." in html
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
    assert 'data-i18n-aria-label="landing.hero.title"' in landing_html
    assert 'data-i18n="landing.hero.title.line1"' in landing_html
    assert "broadcastToolPro.language" in javascript
    assert 'new Set(["en", "es"])' in javascript
    assert 'document.documentElement.lang = language' in javascript
    assert 'new CustomEvent("btp:languagechange"' in javascript
    assert "localStorage.setItem" in javascript
    assert "navigator.language" in javascript


def test_homepage_exposes_free_xmltv_validator_without_registration():
    html = (FRONTEND_DIR / "landing.html").read_text()
    javascript = (FRONTEND_DIR / "landing.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    assert 'id="public-xmltv-form"' in html
    assert 'id="public-xmltv-file" type="file" name="file" accept=".xml,application/xml,text/xml" />' in html
    assert 'accept=".xml,application/xml,text/xml" required' not in html
    assert 'id="public-validator-results"' in html
    assert "/api/public/xmltv/validate" in javascript
    assert "/api/public/xmltv/report/pdf" in javascript
    assert "btp-xmltv-validation-report.pdf" in javascript
    assert '"landing.validator.fileRequired"' in javascript
    assert "Start Free Trial" not in html
    assert 'href="#platform" data-i18n="landing.nav.platform"' not in html
    assert "Platform Product Map" not in html
    assert '"landing.validator.cta"' in translations



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
    assert "localizedFixMessage(fix)" in application_javascript
    assert '"generator.fix.duration"' in translations
    assert "Convertir las duraciones numéricas al formato HH:MM:SS." in translations
    assert "Normalizar los valores localizados de Sí/No." in translations
    assert "Combinar las filas de continuación en un solo programa." in translations
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
        "hls.loudnessDisclaimer",
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
        "auth.selfService",
        "auth.continueCheckout",
        "auth.accountApproved",
        "account.suspended",
    ):
        assert f'data-i18n="{key}"' in html
        assert f'"{key}"' in translations

    assert 'window.addEventListener("btp:languagechange"' in javascript
    assert "renderLocalizedIdentity" in javascript
    assert "localizedRole" in javascript
    assert 'organization.plan' in javascript
    assert 'organization?.status === "suspended"' in javascript
    assert 'entitlements.access?.type === "trial"' not in javascript


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
    assert Path(security_and_data_handling().path) == FRONTEND_DIR / "security.html"


def test_security_page_documents_verified_data_controls_bilingually():
    html = (FRONTEND_DIR / "security.html").read_text()
    css = (FRONTEND_DIR / "legal.css").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    assert 'data-language-select' in html
    assert 'data-i18n="security.title"' in html
    assert "security@broadcasttoolpro.com" in html
    assert "mailto:security@broadcasttoolpro.com" in html
    assert 'data-i18n="security.access.recovery"' in html
    assert 'data-i18n="security.backups.copy"' in html
    assert 'data-i18n="security.retention.copy"' in html
    assert 'data-i18n="security.providers.copy"' in html
    assert '"security.title": "Seguridad y gestión de datos"' in translations
    assert '"security.contact.title": "Consultas o divulgación responsable"' in translations
    assert ".security-facts" in css
    assert ".security-contact" in css
    assert "security@broadcasttoolpro.com" in (FRONTEND_DIR / "privacy.html").read_text()


def test_terms_explain_subscription_cancellation_and_refunds():
    terms = (FRONTEND_DIR / "terms.html").read_text()

    assert "cancellation takes effect at the end" in terms
    assert "Downgrades" in terms
    assert "prorated charge or" in terms
    assert "subscription payments are non-refundable" in terms
    assert "refund does not by itself" in terms


def test_public_landing_page_presents_the_platform():
    html = (FRONTEND_DIR / "landing.html").read_text()
    css = (FRONTEND_DIR / "landing.css").read_text()
    javascript = (FRONTEND_DIR / "landing.js").read_text()

    assert "Stop repairing" in html
    assert 'data-i18n="landing.hero.title.line2">XMLTV</span>' in html
    assert "by hand." in html
    assert html.count('data-i18n="landing.hero.title.line') == 3
    assert 'data-i18n="landing.hero.trust.aggregator"' in html
    assert "Validate XMLTV Free</a>" not in html
    assert "Explore the Platform</a>" not in html
    assert ".landing-hero h1 span" in css
    assert "white-space: nowrap;" in css
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
    assert 'href="#roadmap"' not in html
    assert "Media QC Engine" not in html
    assert "COMING SOON" not in html
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
    assert "/app?mode=trial" not in html
    assert "broadcastcontrol.io" not in html.lower()
    assert "Broadcast Control" not in html
    assert "Orion Media" not in html
    assert "It is not a fabricated product screenshot." not in html
    assert "--landing-black: #02060c" in css
    assert "@media (max-width: 760px)" in css
    assert "landing-menu-toggle" in javascript


def test_public_landing_page_has_bilingual_founder_profiles():
    html = (FRONTEND_DIR / "landing.html").read_text()
    css = (FRONTEND_DIR / "landing.css").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    assert 'id="about"' in html
    assert 'href="#about" data-i18n="landing.nav.about"' in html
    assert "Leiyan Cotayo" in html
    assert "Freddy Arias" in html
    assert "/static/assets/leiyan-cotayo-headshot.jpg" in html
    assert "/static/assets/freddy-arias-headshot.jpg" in html
    assert "https://www.linkedin.com/in/leiyan-cotayo-61b50820" in html
    assert "https://www.linkedin.com/in/freddyarias/" in html
    assert html.count('rel="noopener noreferrer"') >= 2
    assert (FRONTEND_DIR / "assets" / "leiyan-cotayo-headshot.jpg").is_file()
    assert (FRONTEND_DIR / "assets" / "freddy-arias-headshot.jpg").is_file()
    assert '"landing.about.kicker": "SOBRE NOSOTROS"' in translations
    assert '"landing.about.role": "Cofundador, Broadcast Tool Pro"' in translations
    assert '"landing.about.linkedin": "Ver perfil en LinkedIn"' in translations
    assert ".landing-founder-grid" in css
    assert ".landing-founder-linkedin" in css
    assert "aspect-ratio: 4 / 3" in css
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
    assert "/static/landing.css?v=20260827-3" in html


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
    assert "/api/hls/loudness/jobs" in hls_javascript


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

    assert '/static/hls-validator.js?v=20260902-3' in html
    assert '/static/i18n.js?v=20260902-3' in html

    assert 'href="#hls-validator"' in html
    assert 'id="monitor-hls-button"' in html
    assert 'id="analyze-hls-loudness-button"' not in html
    assert 'id="hls-loudness-panel"' in html
    assert 'id="stop-hls-monitor-button"' in html
    assert 'id="hls-monitor-trigger-body"' in html
    hls_form_start = html.index('id="hls-validator-form"')
    hls_form_end = html.index("</form>", hls_form_start)
    monitor_panel = html.index('id="hls-monitor-panel"')
    loudness_panel = html.index('id="hls-loudness-panel"')
    assert hls_form_start < hls_form_end < monitor_panel < loudness_panel
    assert 'id="download-hls-report-button"' in html
    report_button = html.split('id="download-hls-report-button"', 1)[0].rsplit(
        "<button", 1
    )[1]
    assert "is-hidden" not in report_button
    assert "disabled" in html.split('id="download-hls-report-button"', 1)[1].split(
        ">", 1
    )[0]
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
    assert "void startLoudnessAnalysis()" in javascript
    assert "void stopLoudnessAnalysis()" in javascript
    assert 'method: "DELETE"' in javascript
    assert 'hlsLoudnessState = "stopping"' in javascript
    assert 'payload.status === "completed" && payload.result' in javascript
    assert 'result.loudness_range_lu' in javascript
    assert 'if (latestLoudnessResult)' in javascript
    assert 'hlsLoudnessState === "stopping"' in javascript
    assert 'hlsLoudnessState === "stopped"' in javascript
    assert 'if (hlsLoudnessState === "stopped") return null;' in javascript
    assert "updateHlsReportAvailability" in javascript
    assert 'hlsMonitorState === "stopped"' in javascript
    assert "hlsReportButton.disabled = !reportReady" in javascript
    assert 'rule_id: "LOUDNESS-INCOMPLETE"' in javascript
    assert "/api/hls/report/pdf" in javascript
    assert "summarizeScteBreaks" in javascript
    assert "continuation_count" in javascript


def test_secure_account_interface_is_present():
    html = (FRONTEND_DIR / "index.html").read_text()

    assert 'id="bootstrap-form"' in html
    assert 'id="login-form"' in html
    assert 'id="trial-form"' not in html
    assert 'id="show-login-tab"' in html
    assert 'id="show-get-started-tab"' in html
    assert 'class="auth-tabs"' not in html
    assert 'data-i18n="auth.newToBtp"' in html
    assert 'data-i18n="auth.alreadyAccount"' in html
    assert 'name="remember_me"' in html
    assert "Start 7-Day Free Trial" not in html
    assert "Continue to Secure Checkout" in html
    assert 'id="platform-content"' in html
    assert 'id="account-button"' in html
    assert 'id="trial-reminder-preference"' not in html
    assert 'id="trial-expired"' not in html
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
    assert "/api/auth/email-preferences" not in auth_javascript
    assert '"trialing"' not in admin_javascript
    assert "/api/auth/signup" in auth_javascript
    assert "/api/auth/trial" not in auth_javascript
    assert 'requestedMode === "trial"' not in auth_javascript
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
    assert '["canceled", "cancelled"].includes(subscription.status)' in javascript
    assert 'billingText("billing.notScheduled", "Not scheduled")' in javascript
    assert '"billing.notScheduled": "No programada"' in translations
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


def test_public_contact_uses_an_internal_sales_form():
    html = (FRONTEND_DIR / "landing.html").read_text()
    javascript = (FRONTEND_DIR / "landing.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    assert 'id="landing-contact-form"' in html
    assert 'name="contact_name"' in html
    assert 'name="organization_name"' in html
    assert 'name="email"' in html
    assert 'name="message"' in html
    assert "mailto:" not in html
    assert 'fetch("/api/auth/sales-inquiries"' in javascript
    assert 'name="requested_plan"' not in html
    assert 'name="billing_cycle"' not in html
    assert '"landing.footer.sales": "Ventas"' in translations
    assert "landing.footer.support" not in html
    assert 'href="/security" data-i18n="landing.footer.security"' in html


def test_self_service_signup_only_requests_initial_channel_name():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "auth.js").read_text()
    signup = html.split('id="access-request-form"', 1)[1].split(
        "</form>", 1
    )[0]

    assert 'name="channel_name" required' in signup
    assert 'name="channel_code"' not in signup
    assert 'name="channel_timezone"' not in signup
    assert 'name="channel_language"' not in signup
    assert 'id="active-channel-select"' in html
    assert "/channels`" in javascript
    assert 'new CustomEvent("btp:channel"' in javascript
    assert "applyRegisteredChannel(window.BTPActiveChannel)" in (
        FRONTEND_DIR / "app.js"
    ).read_text()
    assert 'id="active-channel-language"' in html
    assert 'id="save-channel-language"' in html
    assert 'method: "PATCH"' in javascript


def test_missing_template_channel_warning_is_localized():
    javascript = (FRONTEND_DIR / "app.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    assert (
        '["VAL-011", "VAL-012", "VAL-013", "CHANNEL-LANGUAGE"]'
        ".includes(issue.rule_id)"
    ) in javascript
    assert '"generator.rule.VAL-011"' in translations
    assert "El canal es obligatorio." in translations
    assert "Array.isArray(detail)" in javascript
    assert 'rule_id: "REQUEST"' in javascript
    assert '"generator.channelSelectionRequired"' in translations
    assert "must exactly match the registered channel name" in translations
    assert "debe coincidir exactamente con el nombre del canal registrado" in translations
    assert 'actual: issue.actual_channel || ""' in javascript
    assert 'expected: issue.expected_channel || ""' in javascript
    assert "no coincide con el canal registrado" in translations
    assert '"generator.metricWarnings.one": "{count} Warning"' in translations
    assert '"generator.metricWarnings.one": "{count} Advertencia"' in translations
    assert "function metricText(" in javascript


def test_template_download_links_are_cache_busted():
    html = (FRONTEND_DIR / "index.html").read_text()

    assert html.count("/api/xmltv/template/excel?v=20260902-1") == 2
    assert html.count("/api/xmltv/template/csv?v=20260902-1") == 2
    for script in (
        "i18n.js",
        "auth.js",
        "app.js",
        "prelog-filter.js",
        "postlog-certification.js",
        "hls-validator.js",
    ):
        assert f"/static/{script}?v=20260902-3" in html


def test_billing_supports_reviewed_additional_channel_purchase():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "billing.js").read_text()

    assert 'id="billing-channel-form"' in html
    assert 'id="billing-channel-preview"' in html
    channel_form = html.split('id="billing-channel-form"', 1)[1].split(
        "</form>", 1
    )[0]
    assert 'name="name"' in channel_form
    assert 'name="channel_code"' not in channel_form
    assert 'name="timezone"' not in channel_form
    assert 'name="primary_language"' not in channel_form
    assert "/channels/preview`" in javascript
    assert "confirmChannelPurchase" in javascript
    assert "Stripe prorated amount" in javascript
    assert "channel.is_included" in javascript
    assert "activeChannels.length === 1" not in javascript


def test_billing_supports_channel_removal_at_period_end():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "billing.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    assert 'id="billing-channel-list"' in html
    assert 'id="billing-channel-removal"' in html
    assert "/removal/preview`" in javascript
    assert "/removal/cancel`" in javascript
    assert "renderBillingChannels(payload.channels || [])" in javascript
    assert '"billing.removeAtPeriodEnd"' in translations


def test_customer_help_routes_topics_to_the_right_mailbox():
    html = (FRONTEND_DIR / "index.html").read_text()
    javascript = (FRONTEND_DIR / "help.js").read_text()

    assert 'id="help-topic-contact"' in html
    assert "support@broadcasttoolpro.com" in javascript
    assert "billing@broadcasttoolpro.com" in javascript
    assert "security@broadcasttoolpro.com" in javascript


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
    ):
        assert f'name="{field_name}"' in html
    for removed_field in (
        "primary_language",
        "original_language",
        "rating_system",
    ):
        assert f'name="{removed_field}"' not in html
    assert "VCHIP — US Television" not in html


def test_help_explains_global_xmltv_metadata():
    help_javascript = (FRONTEND_DIR / "help.js").read_text()

    assert "no US or regional rating system is assumed" in help_javascript
    assert "no se presume ningún sistema estadounidense" in help_javascript
    assert "Channel Settings" in help_javascript
    assert "Configuración del canal" in help_javascript


def test_xmltv_generator_offers_us_latam_and_fixed_timezones():
    html = (FRONTEND_DIR / "index.html").read_text()

    for timezone_name in (
        "America/New_York",
        "America/Phoenix",
        "America/Puerto_Rico",
        "America/Mexico_City",
        "America/Guatemala",
        "America/Santo_Domingo",
        "America/Bogota",
        "America/Santiago",
        "America/Argentina/Buenos_Aires",
        "America/Sao_Paulo",
        "Etc/GMT+5",
    ):
        assert f'value="{timezone_name}"' in html

    assert "UTC−05:00 — EST (fixed, no DST)" in html
    assert "Eastern Time — New York (UTC−05/UTC−04)" in html


def test_xmltv_authorization_is_presented_as_review_not_error():
    javascript = (FRONTEND_DIR / "app.js").read_text()
    translations = (FRONTEND_DIR / "i18n.js").read_text()

    assert 'issue.rule_id === "AUTH-001"' in javascript
    assert '"generator.readyAuthorization", "Ready for authorization"' in javascript
    assert 'resultPanel.classList.toggle("is-error", !readyForReview)' in javascript
    assert '"generator.readyAuthorization": "Lista para autorización"' in translations


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
