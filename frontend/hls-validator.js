const hlsForm = document.querySelector("#hls-validator-form");
const hlsUrl = document.querySelector("#hls-playlist-url");
const hlsButton = document.querySelector("#validate-hls-button");
const hlsPanel = document.querySelector("#hls-result-panel");
const hlsIcon = document.querySelector("#hls-result-icon");
const hlsTitle = document.querySelector("#hls-result-title");
const hlsMessage = document.querySelector("#hls-result-message");
const hlsMetrics = document.querySelector("#hls-result-metrics");
const hlsIssues = document.querySelector("#hls-issue-list");
const hlsVariantTable = document.querySelector("#hls-variant-table");
const hlsVariantBody = document.querySelector("#hls-variant-body");
const hlsTriggerTable = document.querySelector("#hls-trigger-table");
const hlsTriggerBody = document.querySelector("#hls-trigger-body");
const hlsMonitorDuration = document.querySelector("#hls-monitor-duration");
const hlsMonitorButton = document.querySelector("#monitor-hls-button");
const hlsStopButton = document.querySelector("#stop-hls-monitor-button");
const hlsMonitorPanel = document.querySelector("#hls-monitor-panel");
const hlsMonitorTitle = document.querySelector("#hls-monitor-title");
const hlsMonitorStatus = document.querySelector("#hls-monitor-status");
const hlsMonitorCountdown = document.querySelector("#hls-monitor-countdown");
const hlsMonitorTriggerBody = document.querySelector(
  "#hls-monitor-trigger-body",
);
const hlsReportButton = document.querySelector(
  "#download-hls-report-button",
);

let hlsMonitorTimer = null;
let hlsCountdownTimer = null;
let hlsMonitorEndsAt = null;
let hlsMonitorUrl = "";
let hlsPolls = 0;
let latestHlsResult = null;
let hlsMonitorStartedAt = null;
let hlsMonitorFailed = false;
const hlsSeenTriggers = new Set();
const hlsMonitorTriggers = [];
const hlsMonitorIssues = new Map();
let hlsInitialVariants = [];

function hlsMetric(label) {
  const metric = document.createElement("span");
  metric.textContent = label;
  hlsMetrics.appendChild(metric);
}

function hlsCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = value ?? "—";
  row.appendChild(cell);
}

function renderHlsResult(result) {
  latestHlsResult = result;
  hlsReportButton.classList.remove("is-hidden");
  hlsPanel.classList.remove("is-hidden", "is-error");
  hlsMetrics.replaceChildren();
  hlsIssues.replaceChildren();
  hlsVariantBody.replaceChildren();
  hlsTriggerBody.replaceChildren();
  hlsVariantTable.classList.add("is-hidden");
  hlsTriggerTable.classList.add("is-hidden");

  hlsPanel.classList.toggle("is-error", !result.valid);
  hlsIcon.textContent = result.valid ? "✓" : "!";
  hlsTitle.textContent = result.valid
    ? "HLS playlist is valid"
    : "HLS playlist needs attention";
  hlsMessage.textContent = result.playlist_type === "master"
    ? "Master playlist inspected successfully."
    : "Media playlist inspected successfully.";

  hlsMetric(result.playlist_type === "master"
    ? "Master Playlist"
    : "Media Playlist");
  hlsMetric(`${result.critical || 0} Critical`);
  hlsMetric(`${result.warnings || 0} Warnings`);
  hlsMetric(`${result.trigger_count || 0} Triggers`);
  hlsMetric(result.scte35_detected ? "SCTE-35 Detected" : "No SCTE-35");

  if (result.media) {
    hlsMetric(`${result.media.segments || 0} Segments`);
    hlsMetric(result.media.live ? "Live" : "VOD");
    if (result.media.target_duration != null) {
      hlsMetric(`${result.media.target_duration}s Target`);
    }
  }

  const issues = Array.isArray(result.issues) ? result.issues : [];
  issues.forEach((issue) => {
    const item = document.createElement("li");
    item.textContent = `${issue.rule_id}: ${issue.message}`;
    hlsIssues.appendChild(item);
  });

  const variants = Array.isArray(result.variants) ? result.variants : [];
  if (variants.length) {
    variants.forEach((variant) => {
      const row = document.createElement("tr");
      hlsCell(
        row,
        variant.bandwidth
          ? `${Math.round(variant.bandwidth / 1000)} kbps`
          : "—",
      );
      hlsCell(row, variant.resolution);
      hlsCell(row, variant.frame_rate);
      hlsCell(row, variant.codecs);
      hlsCell(row, variant.segments);
      hlsCell(row, variant.trigger_count || 0);
      hlsCell(row, variant.valid === false ? "Needs attention" : "Valid");
      hlsVariantBody.appendChild(row);
    });
    hlsVariantTable.classList.remove("is-hidden");
    hlsMetric(`${result.variant_count || variants.length} Variants`);
  }

  const triggers = result.media?.triggers
    || variants.flatMap((variant) => variant.triggers || []);
  if (triggers.length) {
    triggers.forEach((trigger) => {
      const row = document.createElement("tr");
      hlsCell(row, trigger.type);
      hlsCell(row, trigger.id);
      hlsCell(row, trigger.start_date);
      hlsCell(
        row,
        trigger.duration == null ? "—" : `${trigger.duration}s`,
      );
      hlsTriggerBody.appendChild(row);
    });
    hlsTriggerTable.classList.remove("is-hidden");
  }
}

function renderHlsRequestError(message) {
  renderHlsResult({
    valid: false,
    playlist_type: "unknown",
    critical: 1,
    warnings: 0,
    issues: [{
      rule_id: "REQUEST",
      message,
    }],
  });
  hlsMessage.textContent = "The playlist could not be inspected.";
}

async function requestHlsValidation(playlistUrl) {
  const formData = new FormData();
  formData.append("playlist_url", playlistUrl);
  const response = await fetch("/api/hls/validate", {
    method: "POST",
    body: formData,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(
      typeof payload.detail === "string"
        ? payload.detail
        : "The HLS validation request failed.",
    );
  }
  return payload;
}

function hlsTriggerKey(trigger) {
  return JSON.stringify([
    trigger.type,
    trigger.id,
    trigger.start_date,
    trigger.duration,
    trigger.payload,
  ]);
}

function addMonitoredTriggers(result) {
  const variants = Array.isArray(result.variants) ? result.variants : [];
  const triggers = result.media?.triggers
    || variants.flatMap((variant) => variant.triggers || []);
  let added = 0;

  triggers.forEach((trigger) => {
    const key = hlsTriggerKey(trigger);
    if (hlsSeenTriggers.has(key)) return;
    hlsSeenTriggers.add(key);
    added += 1;
    hlsMonitorTriggers.push({
      ...trigger,
      detected_at: new Date().toISOString(),
      source_url: result.url,
    });

    const row = document.createElement("tr");
    hlsCell(row, new Date().toLocaleTimeString());
    hlsCell(row, trigger.type);
    hlsCell(row, trigger.id);
    hlsCell(
      row,
      trigger.duration == null ? "—" : `${trigger.duration}s`,
    );
    hlsMonitorTriggerBody.prepend(row);
  });
  return added;
}

function collectMonitorIssues(result) {
  const issues = Array.isArray(result.issues) ? result.issues : [];
  issues.forEach((issue) => {
    const key = JSON.stringify([
      issue.rule_id,
      issue.severity,
      issue.message,
    ]);
    hlsMonitorIssues.set(key, issue);
  });
  if (!result.valid) hlsMonitorFailed = true;
}

function stopHlsMonitoring(completed = false) {
  window.clearTimeout(hlsMonitorTimer);
  window.clearInterval(hlsCountdownTimer);
  hlsMonitorTimer = null;
  hlsCountdownTimer = null;
  hlsMonitorButton.disabled = false;
  hlsMonitorButton.textContent = "Monitor Stream";
  hlsStopButton.classList.add("is-hidden");
  hlsMonitorTitle.textContent = completed
    ? "Monitoring complete"
    : "Monitoring stopped";
  hlsMonitorStatus.textContent = (
    `${hlsPolls} inspections · ${hlsSeenTriggers.size} unique triggers`
  );
  hlsMonitorCountdown.textContent = "00:00";
}

function updateHlsCountdown() {
  const remaining = Math.max(0, hlsMonitorEndsAt - Date.now());
  const seconds = Math.ceil(remaining / 1000);
  const minutes = Math.floor(seconds / 60);
  hlsMonitorCountdown.textContent = (
    `${String(minutes).padStart(2, "0")}:`
    + `${String(seconds % 60).padStart(2, "0")}`
  );
  if (remaining <= 0 && hlsMonitorTimer) {
    stopHlsMonitoring(true);
  }
}

async function pollHlsMonitor() {
  if (!hlsMonitorTimer || Date.now() >= hlsMonitorEndsAt) {
    stopHlsMonitoring(true);
    return;
  }

  try {
    const result = await requestHlsValidation(hlsMonitorUrl);
    latestHlsResult = result;
    hlsReportButton.classList.remove("is-hidden");
    hlsPolls += 1;
    addMonitoredTriggers(result);
    collectMonitorIssues(result);

    if (result.playlist_type === "master" && result.variants?.length) {
      hlsInitialVariants = result.variants;
      hlsMonitorUrl = result.variants[0].url;
    }
    const targetDuration = result.media?.target_duration
      || result.variants?.[0]?.target_duration
      || 6;
    hlsMonitorStatus.textContent = (
      `${hlsPolls} inspections · ${hlsSeenTriggers.size} unique triggers`
    );
    hlsMonitorTimer = window.setTimeout(
      pollHlsMonitor,
      Math.max(2, targetDuration) * 1000,
    );
  } catch (error) {
    hlsMonitorStatus.textContent = error.message;
    hlsMonitorFailed = true;
    hlsMonitorIssues.set(error.message, {
      severity: "critical",
      rule_id: "REQUEST",
      message: error.message,
      recommendation: (
        "Verify stream availability, authorization, DNS, and origin health."
      ),
    });
    hlsMonitorTimer = window.setTimeout(pollHlsMonitor, 6000);
  }
}

if (hlsForm) {
  hlsForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!hlsForm.reportValidity()) return;

    hlsButton.disabled = true;
    hlsButton.textContent = "Validating…";
    hlsMonitorStartedAt = null;
    hlsMonitorFailed = false;
    hlsMonitorTriggers.length = 0;
    hlsMonitorIssues.clear();
    hlsInitialVariants = [];

    try {
      renderHlsResult(await requestHlsValidation(hlsUrl.value.trim()));
    } catch (error) {
      renderHlsRequestError(error.message);
    } finally {
      hlsButton.disabled = false;
      hlsButton.textContent = "Validate HLS";
    }
  });
}

if (hlsMonitorButton) {
  hlsMonitorButton.addEventListener("click", () => {
    if (!hlsForm.reportValidity()) return;

    stopHlsMonitoring();
    hlsSeenTriggers.clear();
    hlsMonitorTriggers.length = 0;
    hlsMonitorIssues.clear();
    hlsMonitorTriggerBody.replaceChildren();
    hlsPolls = 0;
    hlsMonitorFailed = false;
    hlsMonitorStartedAt = new Date();
    hlsMonitorUrl = hlsUrl.value.trim();
    hlsMonitorEndsAt = (
      Date.now() + Number(hlsMonitorDuration.value) * 60 * 1000
    );
    hlsMonitorPanel.classList.remove("is-hidden");
    hlsStopButton.classList.remove("is-hidden");
    hlsMonitorButton.disabled = true;
    hlsMonitorButton.textContent = "Monitoring…";
    hlsMonitorTitle.textContent = "Monitoring stream…";
    hlsMonitorStatus.textContent = "Starting first inspection…";
    hlsMonitorTimer = window.setTimeout(pollHlsMonitor, 0);
    hlsCountdownTimer = window.setInterval(updateHlsCountdown, 1000);
    updateHlsCountdown();
  });
}

function hlsReportPayload() {
  const result = latestHlsResult || {};
  const monitoringMinutes = hlsMonitorStartedAt
    ? Number(hlsMonitorDuration.value)
    : 0;
  const instantTriggers = result.media?.triggers
    || (result.variants || []).flatMap((variant) => variant.triggers || []);
  const triggers = hlsMonitorTriggers.length
    ? hlsMonitorTriggers
    : instantTriggers.map((trigger) => ({
        ...trigger,
        detected_at: new Date().toISOString(),
        source_url: result.url,
      }));
  const issues = hlsMonitorIssues.size
    ? [...hlsMonitorIssues.values()]
    : (result.issues || []);

  return {
    valid: Boolean(result.valid) && !hlsMonitorFailed,
    url: hlsUrl.value.trim(),
    playlist_type: result.playlist_type || "unknown",
    monitoring_minutes: monitoringMinutes,
    inspections: hlsPolls || 1,
    generated_at: new Date().toISOString(),
    scte35_detected: (
      result.scte35_detected
      || triggers.some((trigger) => (
        trigger.type?.includes("SCTE")
        || trigger.type?.startsWith("CUE-")
      ))
    ),
    trigger_count: triggers.length,
    variants: hlsInitialVariants.length
      ? hlsInitialVariants
      : (result.variants || []),
    triggers,
    issues,
  };
}

async function downloadHlsPdfReport() {
  hlsReportButton.disabled = true;
  hlsReportButton.textContent = "Preparing PDF…";
  try {
    const response = await fetch("/api/hls/report/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(hlsReportPayload()),
    });
    if (!response.ok) throw new Error("The PDF report could not be created.");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "broadcast-tool-pro-hls-report.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    hlsMonitorStatus.textContent = error.message;
  } finally {
    hlsReportButton.disabled = false;
    hlsReportButton.textContent = "Download PDF Report";
  }
}

if (hlsReportButton) {
  hlsReportButton.addEventListener("click", downloadHlsPdfReport);
}

if (hlsStopButton) {
  hlsStopButton.addEventListener("click", () => {
    stopHlsMonitoring();
  });
}
