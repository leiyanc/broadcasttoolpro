const prelogForm = document.querySelector("#prelog-filter-form");
const prelogFiles = document.querySelector("#prelog-files");
const prelogDropZone = document.querySelector("#prelog-drop-zone");
const prelogFileTitle = document.querySelector("#prelog-file-title");
const prelogFileSubtitle = document.querySelector("#prelog-file-subtitle");
const inspectPlaylistsButton = document.querySelector("#inspect-playlists-button");
const applyPrelogFiltersButton = document.querySelector(
  "#apply-prelog-filters-button",
);
const prelogFilterMode = document.querySelector("#prelog-filter-mode");
const prelogFilterValue = document.querySelector("#prelog-filter-value");
const prelogFilterSuggestions = document.querySelector(
  "#prelog-filter-suggestions",
);
const filterValueField = document.querySelector(".filter-value-field");
const prelogStartDate = document.querySelector("#prelog-start-date");
const prelogEndDate = document.querySelector("#prelog-end-date");
const playlistSummary = document.querySelector("#playlist-summary");
const playlistSummaryMetrics = document.querySelector(
  "#playlist-summary-metrics",
);
const playlistSummaryMessage = document.querySelector(
  "#playlist-summary-message",
);
const prelogResultPanel = document.querySelector("#prelog-result-panel");
const prelogResultIcon = document.querySelector("#prelog-result-icon");
const prelogResultTitle = document.querySelector("#prelog-result-title");
const prelogResultMessage = document.querySelector("#prelog-result-message");
const prelogResultMetrics = document.querySelector("#prelog-result-metrics");
const prelogPreviewBody = document.querySelector("#prelog-preview-body");
const prelogExportPanel = document.querySelector("#prelog-export-panel");
const prelogChannelName = document.querySelector("#prelog-channel-name");
const prelogReportLanguage = document.querySelector("#prelog-report-language");
const prelogAgency = document.querySelector("#prelog-agency");
const prelogLogo = document.querySelector("#prelog-logo");
const exportPrelogButton = document.querySelector("#export-prelog-button");
const prelogExportStatus = document.querySelector("#prelog-export-status");

let playlistsInspected = false;
let availableFilterOptions = null;
const PRELOG_FILTER_STORAGE_KEY = "broadcastToolPro.prelogFilters";
const PRELOG_FILTER_MODE_STORAGE_KEY = "broadcastToolPro.prelogFilterMode";

function storedFilterValues() {
  try {
    return JSON.parse(
      localStorage.getItem(PRELOG_FILTER_STORAGE_KEY) || "{}",
    );
  } catch {
    return {};
  }
}

function saveCurrentFilterValue() {
  const mode = prelogFilterMode.value;
  if (mode === "all") return;

  const values = storedFilterValues();
  values[mode] = prelogFilterValue.value;
  localStorage.setItem(
    PRELOG_FILTER_STORAGE_KEY,
    JSON.stringify(values),
  );
}

function restoreFilterValue() {
  const mode = prelogFilterMode.value;
  prelogFilterValue.value = (
    mode === "all" ? "" : storedFilterValues()[mode] || ""
  );
}

function appendFiles(data) {
  for (const file of prelogFiles.files) {
    data.append("playlist_files", file);
  }
}

function addMetric(container, text) {
  const metric = document.createElement("span");
  metric.textContent = text;
  container.appendChild(metric);
}

function updatePrelogFiles() {
  const files = [...prelogFiles.files];
  if (!files.length) return;

  const invalid = files.some(
    (file) => !file.name.toLowerCase().endsWith(".csv"),
  );
  prelogFiles.setCustomValidity(
    invalid ? "All playlist files must use the .csv extension." : "",
  );
  prelogDropZone.classList.toggle("is-invalid", invalid);
  prelogFileTitle.textContent = (
    files.length === 1 ? files[0].name : `${files.length} playlists selected`
  );
  const totalKilobytes = (
    files.reduce((total, file) => total + file.size, 0) / 1024
  );
  prelogFileSubtitle.textContent = `${totalKilobytes.toFixed(1)} KB total`;
  playlistsInspected = false;
  availableFilterOptions = null;
  applyPrelogFiltersButton.disabled = true;
  playlistSummary.classList.add("is-hidden");
  prelogResultPanel.classList.add("is-hidden");
  prelogExportPanel.classList.add("is-hidden");
}

function updateFilterControls(options = null) {
  const mode = prelogFilterMode.value;
  const needsValue = mode !== "all";
  filterValueField.classList.toggle("is-hidden", !needsValue);
  prelogFilterValue.required = needsValue;
  prelogFilterSuggestions.replaceChildren();

  if (!options || !needsValue) return;

  const suggestions = mode === "prefix"
    ? options.prefixes
        .map((item) => item.prefix)
        .filter((value) => value !== "(no prefix)")
    : options.assets.map((item) => item.asset_id);

  for (const value of suggestions) {
    const option = document.createElement("option");
    option.value = value;
    prelogFilterSuggestions.appendChild(option);
  }
}

function showPrelogError(message) {
  prelogResultPanel.classList.remove("is-hidden");
  prelogResultPanel.classList.add("is-error");
  prelogResultIcon.textContent = "!";
  prelogResultTitle.textContent = "Playlist needs attention";
  prelogResultMessage.textContent = message;
  prelogResultMetrics.replaceChildren();
  prelogPreviewBody.replaceChildren();
}

prelogFiles.addEventListener("change", updatePrelogFiles);
prelogFilterMode.addEventListener("change", () => {
  localStorage.setItem(
    PRELOG_FILTER_MODE_STORAGE_KEY,
    prelogFilterMode.value,
  );
  restoreFilterValue();
  updateFilterControls(availableFilterOptions);
});
prelogFilterValue.addEventListener("input", saveCurrentFilterValue);

for (const eventName of ["dragenter", "dragover"]) {
  prelogDropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    prelogDropZone.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  prelogDropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    prelogDropZone.classList.remove("is-dragging");
  });
}

prelogDropZone.addEventListener("drop", (event) => {
  if (!event.dataTransfer.files.length) return;
  const transfer = new DataTransfer();
  for (const file of event.dataTransfer.files) {
    transfer.items.add(file);
  }
  prelogFiles.files = transfer.files;
  updatePrelogFiles();
});

inspectPlaylistsButton.addEventListener("click", async () => {
  if (!prelogFiles.reportValidity()) return;

  const data = new FormData();
  appendFiles(data);
  data.append(
    "source_timezone",
    prelogForm.elements.source_timezone.value,
  );
  inspectPlaylistsButton.disabled = true;
  inspectPlaylistsButton.textContent = "Inspecting…";

  try {
    const response = await fetch("/api/prelogs/options", {
      method: "POST",
      body: data,
    });
    const result = await response.json();

    if (!response.ok) {
      showPrelogError(result.detail || "The playlists could not be inspected.");
      return;
    }

    playlistsInspected = true;
    availableFilterOptions = result;
    prelogChannelName.value = result.channels[0] || "";
    applyPrelogFiltersButton.disabled = false;
    playlistSummary.classList.remove("is-hidden");
    playlistSummaryMetrics.replaceChildren();
    addMetric(playlistSummaryMetrics, `${result.files_processed} Files`);
    addMetric(playlistSummaryMetrics, `${result.events_received} Events`);
    addMetric(playlistSummaryMetrics, `${result.assets.length} Unique assets`);
    addMetric(playlistSummaryMetrics, `${result.channels.length} Channels`);
    addMetric(
      playlistSummaryMetrics,
      result.source_timezone || "Time zone not detected",
    );
    playlistSummaryMessage.textContent = (
      `${result.channels.join(", ") || "Unknown channel"} · ` +
      `Broadcast days ${result.start_date || "Unknown"} to ` +
      `${result.end_date || "Unknown"} · 06:00–05:59`
    );
    prelogStartDate.value = result.start_date || "";
    prelogEndDate.value = result.end_date || "";
    updateFilterControls(result);
  } catch {
    showPrelogError("The server could not inspect the playlists.");
  } finally {
    inspectPlaylistsButton.disabled = false;
    inspectPlaylistsButton.textContent = "Inspect Playlists";
  }
});

prelogForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!playlistsInspected || !prelogForm.reportValidity()) return;

  const data = new FormData();
  appendFiles(data);
  for (const field of [
    "filter_mode",
    "filter_value",
    "start_date",
    "end_date",
    "broadcast_day_start",
    "source_timezone",
  ]) {
    const value = prelogForm.elements[field].value;
    if (value) data.append(field, value);
  }

  applyPrelogFiltersButton.disabled = true;
  applyPrelogFiltersButton.textContent = "Filtering…";

  try {
    const response = await fetch("/api/prelogs/filter", {
      method: "POST",
      body: data,
    });
    const result = await response.json();

    if (!response.ok) {
      showPrelogError(result.detail || "The filters could not be applied.");
      return;
    }

    prelogResultPanel.classList.remove("is-hidden", "is-error");
    prelogResultIcon.textContent = "✓";
    prelogResultTitle.textContent = "Selection ready";
    prelogResultMessage.textContent = result.matching_events
      ? "Review the scheduled occurrences selected for this Pre Log."
      : "No events match the selected filters.";
    prelogResultMetrics.replaceChildren();
    addMetric(prelogResultMetrics, `${result.files_processed} Files`);
    addMetric(prelogResultMetrics, `${result.matching_events} Matches`);
    addMetric(prelogResultMetrics, `${result.unique_assets} Unique assets`);
    prelogPreviewBody.replaceChildren();

    for (const match of result.matches) {
      const row = document.createElement("tr");
      for (const value of [
        match.channel_name || "—",
        match.asset_id,
        new Date(match.air_datetime).toLocaleString(),
        match.duration || "—",
      ]) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      }
      prelogPreviewBody.appendChild(row);
    }

    prelogExportPanel.classList.toggle(
      "is-hidden",
      result.matching_events === 0,
    );
    prelogExportStatus.textContent = "";

    prelogResultPanel.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
  } catch {
    showPrelogError("The server could not apply the filters.");
  } finally {
    applyPrelogFiltersButton.disabled = false;
    applyPrelogFiltersButton.textContent = "Apply Filters";
  }
});

exportPrelogButton.addEventListener("click", async () => {
  if (!prelogChannelName.reportValidity()) return;

  const data = new FormData();
  appendFiles(data);
  for (const field of [
    "filter_mode",
    "filter_value",
    "start_date",
    "end_date",
    "broadcast_day_start",
    "source_timezone",
  ]) {
    const value = prelogForm.elements[field].value;
    if (value) data.append(field, value);
  }
  data.append("channel_name", prelogChannelName.value);
  data.append("report_language", prelogReportLanguage.value);
  if (prelogAgency.value.trim()) {
    data.append("agency", prelogAgency.value.trim());
  }
  if (prelogLogo.files[0]) {
    data.append("logo_file", prelogLogo.files[0]);
  }

  exportPrelogButton.disabled = true;
  exportPrelogButton.textContent = "Generating…";
  prelogExportStatus.classList.remove("is-error");
  prelogExportStatus.textContent = "Preparing your Excel Pre Log…";

  try {
    const response = await fetch("/api/prelogs/export", {
      method: "POST",
      body: data,
    });

    if (!response.ok) {
      const result = await response.json();
      prelogExportStatus.classList.add("is-error");
      prelogExportStatus.textContent = (
        result.detail || "The Pre Log could not be generated."
      );
      return;
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const filenameMatch = disposition.match(/filename="([^"]+)"/);
    const filename = filenameMatch?.[1] || "prelog.xlsx";
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    prelogExportStatus.textContent = `${filename} downloaded successfully.`;
  } catch {
    prelogExportStatus.classList.add("is-error");
    prelogExportStatus.textContent = (
      "The server could not generate the Pre Log."
    );
  } finally {
    exportPrelogButton.disabled = false;
    exportPrelogButton.textContent = "Download Excel Pre Log";
  }
});

const savedFilterMode = localStorage.getItem(
  PRELOG_FILTER_MODE_STORAGE_KEY,
);
if (["all", "prefix", "exact", "contains"].includes(savedFilterMode)) {
  prelogFilterMode.value = savedFilterMode;
}
restoreFilterValue();
updateFilterControls();
