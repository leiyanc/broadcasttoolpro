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
const hlsReportLanguage = document.querySelector("#hls-report-language");
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
let hlsMonitorStoppedAt = null;
let hlsMonitorFailed = false;
let hlsMonitorState = "idle";
const hlsSeenTriggers = new Set();
const hlsMonitorTriggers = [];
const hlsMonitorIssues = new Map();
let hlsInitialVariants = [];
const hlsBandwidthSamples = [];

function hlsText(key, fallback, values = {}) {
  let text = window.BTPi18n?.t(key, fallback) ?? fallback;
  Object.entries(values).forEach(([name, value]) => {
    text = text.replaceAll(`{${name}}`, String(value));
  });
  return text;
}

function renderHlsMonitorSummary(mode = "unique") {
  const summary = summarizeScteBreaks(hlsMonitorTriggers);
  hlsMonitorStatus.textContent = mode === "breaks"
    ? hlsText("hls.inspectionSummary", (
      "{inspections} inspections · {breaks} ad breaks · "
      + "{seconds}s planned · {continuations} continuation markers"
    ), {
      inspections: hlsPolls,
      breaks: summary.break_count,
      seconds: summary.total_planned_duration,
      continuations: summary.continuation_count,
    })
    : hlsText("hls.uniqueSummary", (
      "{inspections} inspections · {triggers} unique triggers"
    ), {
      inspections: hlsPolls,
      triggers: hlsSeenTriggers.size,
    });
}

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
    ? hlsText("hls.valid", "HLS playlist is valid")
    : hlsText("hls.attention", "HLS playlist needs attention");
  hlsMessage.textContent = result.playlist_type === "master"
    ? hlsText("hls.masterInspected", "Master playlist inspected successfully.")
    : hlsText("hls.mediaInspected", "Media playlist inspected successfully.");

  hlsMetric(result.playlist_type === "master"
    ? hlsText("hls.masterPlaylist", "Master Playlist")
    : hlsText("hls.mediaPlaylist", "Media Playlist"));
  hlsMetric(hlsText("hls.critical", "{count} Critical", {
    count: result.critical || 0,
  }));
  hlsMetric(hlsText("hls.warnings", "{count} Warnings", {
    count: result.warnings || 0,
  }));
  if (result.scte35_detected) {
    hlsMetric(hlsText("hls.trackPresent", "SCTE-35 Track Present"));
  } else if (result.scte35_track_detected) {
    hlsMetric(hlsText("hls.trackPresent", "SCTE-35 Track Present"));
  } else {
    hlsMetric(hlsText("hls.noScte", "No SCTE-35"));
  }

  if (result.media) {
    hlsMetric(hlsText("hls.segmentsCount", "{count} Segments", {
      count: result.media.segments || 0,
    }));
    hlsMetric(result.media.live ? hlsText("hls.live", "Live") : "VOD");
    if (result.media.target_duration != null) {
      hlsMetric(hlsText("hls.target", "{seconds}s Target", {
        seconds: result.media.target_duration,
      }));
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
      hlsCell(
        row,
        variant.scte35_track_detected
          ? hlsText("hls.presentPid", "Present (PID {pids})", {
            pids: (variant.scte35_pids || []).join(", "),
          })
          : hlsText("hls.notDetected", "Not detected"),
      );
      hlsCell(
        row,
        variant.valid === false
          ? hlsText("hls.needsAttention", "Needs attention")
          : hlsText("hls.validStatus", "Valid"),
      );
      hlsVariantBody.appendChild(row);
    });
    hlsVariantTable.classList.remove("is-hidden");
    hlsMetric(hlsText("hls.variants", "{count} Variants", {
      count: result.variant_count || variants.length,
    }));
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
  hlsMessage.textContent = hlsText(
    "hls.inspectFailed",
    "The playlist could not be inspected.",
  );
}

async function requestHlsValidation(playlistUrl) {
  const formData = new FormData();
  formData.append("playlist_url", playlistUrl);
  formData.append("inspect_segments", "true");
  const response = await fetch("/api/hls/validate", {
    method: "POST",
    body: formData,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(
      typeof payload.detail === "string"
        ? payload.detail
        : hlsText(
          "hls.validationFailed",
          "The HLS validation request failed.",
        ),
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

function summarizeScteBreaks(triggers) {
  const dateRangeBreaks = triggers.filter((trigger) => (
    trigger.type === "SCTE-35 DATERANGE"
    && trigger.ad_trigger !== false
  ));
  const cueOutBreaks = triggers.filter(
    (trigger) => trigger.type === "CUE-OUT",
  );
  const breaks = dateRangeBreaks.length ? dateRangeBreaks : cueOutBreaks;
  const knownDurations = breaks
    .map((trigger) => Number(trigger.duration))
    .filter((duration) => Number.isFinite(duration) && duration > 0);
  return {
    break_count: Math.max(dateRangeBreaks.length, cueOutBreaks.length),
    continuation_count: triggers.filter(
      (trigger) => trigger.type === "CUE-OUT-CONT",
    ).length,
    durations_reported: knownDurations.length,
    total_planned_duration: knownDurations.reduce(
      (total, duration) => total + duration,
      0,
    ),
  };
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
  renderHlsMonitorSummary("breaks");
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

function collectBandwidthSample(result) {
  const measured = result.media?.measured_bandwidth_kbps
    ?? result.variants?.[0]?.measured_bandwidth_kbps;
  if (!Number.isFinite(Number(measured))) return;
  hlsBandwidthSamples.push({
    detected_at: new Date().toISOString(),
    bandwidth_kbps: Number(measured),
  });
}

function stopHlsMonitoring(completed = false) {
  window.clearTimeout(hlsMonitorTimer);
  window.clearInterval(hlsCountdownTimer);
  hlsMonitorTimer = null;
  hlsCountdownTimer = null;
  hlsMonitorState = completed ? "complete" : "stopped";
  hlsMonitorButton.disabled = false;
  hlsMonitorButton.textContent = hlsText("hls.monitor", "Monitor Stream");
  hlsStopButton.classList.add("is-hidden");
  hlsMonitorTitle.textContent = completed
    ? hlsText("hls.monitorComplete", "Monitoring complete")
    : hlsText("hls.monitorStopped", "Monitoring stopped");
  renderHlsMonitorSummary();
  hlsMonitorCountdown.textContent = "00:00";
  if (hlsMonitorStartedAt) {
    hlsMonitorStoppedAt = new Date();
  }
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
    collectBandwidthSample(result);

    if (result.playlist_type === "master" && result.variants?.length) {
      hlsInitialVariants = result.variants;
      hlsMonitorUrl = result.variants[0].url;
    }
    const targetDuration = result.media?.target_duration
      || result.variants?.[0]?.target_duration
      || 6;
    renderHlsMonitorSummary();
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

    stopHlsMonitoring();
    hlsMonitorPanel.classList.add("is-hidden");
    hlsStopButton.classList.add("is-hidden");
    hlsButton.disabled = true;
    hlsButton.textContent = hlsText("hls.validating", "Validating…");
    hlsMonitorStartedAt = null;
    hlsMonitorStoppedAt = null;
    hlsMonitorFailed = false;
    hlsMonitorTriggers.length = 0;
    hlsMonitorIssues.clear();
    hlsInitialVariants = [];
    hlsBandwidthSamples.length = 0;

    try {
      renderHlsResult(await requestHlsValidation(hlsUrl.value.trim()));
    } catch (error) {
      renderHlsRequestError(error.message);
    } finally {
      hlsButton.disabled = false;
      hlsButton.textContent = hlsText("hls.validate", "Validate HLS");
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
    hlsBandwidthSamples.length = 0;
    hlsMonitorTriggerBody.replaceChildren();
    hlsPolls = 0;
    hlsMonitorFailed = false;
    hlsMonitorState = "monitoring";
    hlsMonitorStartedAt = new Date();
    hlsMonitorStoppedAt = null;
    hlsMonitorUrl = hlsUrl.value.trim();
    hlsMonitorEndsAt = (
      Date.now() + Number(hlsMonitorDuration.value) * 60 * 1000
    );
    hlsMonitorPanel.classList.remove("is-hidden");
    hlsStopButton.classList.remove("is-hidden");
    hlsMonitorButton.disabled = true;
    hlsMonitorButton.textContent = hlsText(
      "hls.monitoringButton",
      "Monitoring…",
    );
    hlsMonitorTitle.textContent = hlsText(
      "hls.monitoring",
      "Monitoring stream…",
    );
    hlsMonitorStatus.textContent = hlsText(
      "hls.starting",
      "Starting first inspection…",
    );
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
    monitoring_started_at: hlsMonitorStartedAt?.toISOString() || null,
    monitoring_ended_at: (
      hlsMonitorStoppedAt || (hlsMonitorStartedAt ? new Date() : null)
    )?.toISOString() || null,
    inspections: hlsPolls || 1,
    generated_at: new Date().toISOString(),
    report_language: hlsReportLanguage.value,
    scte35_detected: (
      result.scte35_detected
      || triggers.some((trigger) => (
        trigger.type?.includes("SCTE")
        || trigger.type?.startsWith("CUE-")
      ))
    ),
    scte35_track_detected: Boolean(result.scte35_track_detected),
    trigger_count: triggers.length,
    scte35_summary: summarizeScteBreaks(triggers),
    variants: hlsInitialVariants.length
      ? hlsInitialVariants
      : (result.variants || []),
    triggers,
    bandwidth_samples: hlsBandwidthSamples,
    issues,
  };
}

async function downloadHlsPdfReport() {
  hlsReportButton.disabled = true;
  hlsReportButton.textContent = hlsText(
    "hls.preparingPdf",
    "Preparing PDF…",
  );
  try {
    const response = await fetch("/api/hls/report/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(hlsReportPayload()),
    });
    if (!response.ok) {
      throw new Error(hlsText(
        "hls.pdfFailed",
        "The PDF report could not be created.",
      ));
    }
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
    hlsReportButton.textContent = hlsText(
      "hls.downloadReport",
      "Download PDF Report",
    );
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

window.addEventListener("btp:languagechange", () => {
  if (!hlsButton.disabled) {
    hlsButton.textContent = hlsText("hls.validate", "Validate HLS");
  }
  if (!hlsMonitorButton.disabled) {
    hlsMonitorButton.textContent = hlsText("hls.monitor", "Monitor Stream");
  }
  if (!hlsReportButton.disabled) {
    hlsReportButton.textContent = hlsText(
      "hls.downloadReport",
      "Download PDF Report",
    );
  }
  hlsStopButton.textContent = hlsText("hls.stop", "Stop Monitoring");
  if (latestHlsResult && !hlsPanel.classList.contains("is-hidden")) {
    renderHlsResult(latestHlsResult);
  }
  if (hlsMonitorState === "monitoring") {
    hlsMonitorButton.textContent = hlsText(
      "hls.monitoringButton",
      "Monitoring…",
    );
    hlsMonitorTitle.textContent = hlsText(
      "hls.monitoring",
      "Monitoring stream…",
    );
    renderHlsMonitorSummary();
  } else if (hlsMonitorState === "complete") {
    hlsMonitorTitle.textContent = hlsText(
      "hls.monitorComplete",
      "Monitoring complete",
    );
    renderHlsMonitorSummary();
  } else if (hlsMonitorState === "stopped") {
    hlsMonitorTitle.textContent = hlsText(
      "hls.monitorStopped",
      "Monitoring stopped",
    );
    renderHlsMonitorSummary();
  }
});
