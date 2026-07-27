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

if (hlsForm) {
  hlsForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!hlsForm.reportValidity()) return;

    hlsButton.disabled = true;
    hlsButton.textContent = "Validating…";

    const formData = new FormData();
    formData.append("playlist_url", hlsUrl.value.trim());

    try {
      const response = await fetch("/api/hls/validate", {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) {
        renderHlsRequestError(
          typeof payload.detail === "string"
            ? payload.detail
            : "The HLS validation request failed.",
        );
      } else {
        renderHlsResult(payload);
      }
    } catch {
      renderHlsRequestError("The HLS validation service is unavailable.");
    } finally {
      hlsButton.disabled = false;
      hlsButton.textContent = "Validate HLS";
    }
  });
}
