const postlogForm = document.querySelector("#postlog-form");
const postlogFiles = document.querySelector("#postlog-files");
const postlogFileTitle = document.querySelector("#postlog-file-title");
const postlogFileSubtitle = document.querySelector("#postlog-file-subtitle");
const inspectPostlogsButton = document.querySelector("#inspect-postlogs-button");
const filterPostlogsButton = document.querySelector("#filter-postlogs-button");
const postlogMode = document.querySelector("#postlog-filter-mode");
const postlogValue = document.querySelector("#postlog-filter-value");
const postlogValueField = document.querySelector("#postlog-filter-value-field");
const postlogSuggestions = document.querySelector(
  "#postlog-filter-suggestions",
);
const postlogSummary = document.querySelector("#postlog-summary");
const postlogSummaryMetrics = document.querySelector(
  "#postlog-summary-metrics",
);
const postlogSummaryMessage = document.querySelector(
  "#postlog-summary-message",
);
const postlogResult = document.querySelector("#postlog-result-panel");
const postlogResultMessage = document.querySelector(
  "#postlog-result-message",
);
const postlogResultMetrics = document.querySelector(
  "#postlog-result-metrics",
);
const postlogPreview = document.querySelector("#postlog-preview-body");
const postlogExportPanel = document.querySelector("#postlog-export-panel");
const postlogChannelName = document.querySelector("#postlog-channel-name");
const exportPostlogButton = document.querySelector("#export-postlog-button");
const postlogExportStatus = document.querySelector("#postlog-export-status");

let postlogsInspected = false;
const POSTLOG_FILTERS_KEY = "broadcastToolPro.postlogFilters";

function postlogStoredFilters() {
  try {
    return JSON.parse(localStorage.getItem(POSTLOG_FILTERS_KEY) || "{}");
  } catch {
    return {};
  }
}

function appendPostlogFiles(data) {
  for (const file of postlogFiles.files) {
    data.append("as_run_files", file);
  }
}

function appendPostlogFilters(data) {
  for (const name of [
    "filter_mode",
    "filter_value",
    "start_date",
    "end_date",
    "broadcast_day_start",
    "source_timezone",
  ]) {
    const value = postlogForm.elements[name].value;
    if (value) data.append(name, value);
  }
}

function postlogMetric(container, text) {
  const item = document.createElement("span");
  item.textContent = text;
  container.appendChild(item);
}

function updatePostlogMode() {
  const needsValue = postlogMode.value !== "all";
  postlogValueField.classList.toggle("is-hidden", !needsValue);
  postlogValue.required = needsValue;
  postlogValue.value = (
    needsValue ? postlogStoredFilters()[postlogMode.value] || "" : ""
  );
}

postlogFiles.addEventListener("change", () => {
  const files = [...postlogFiles.files];
  if (!files.length) return;
  postlogFileTitle.textContent = (
    files.length === 1 ? files[0].name : `${files.length} As-Run files selected`
  );
  postlogFileSubtitle.textContent = `${(
    files.reduce((total, file) => total + file.size, 0) / 1024
  ).toFixed(1)} KB total`;
  postlogsInspected = false;
  filterPostlogsButton.disabled = true;
  postlogSummary.classList.add("is-hidden");
  postlogResult.classList.add("is-hidden");
  postlogExportPanel.classList.add("is-hidden");
});

postlogMode.addEventListener("change", updatePostlogMode);
postlogValue.addEventListener("input", () => {
  const values = postlogStoredFilters();
  values[postlogMode.value] = postlogValue.value;
  localStorage.setItem(POSTLOG_FILTERS_KEY, JSON.stringify(values));
});

inspectPostlogsButton.addEventListener("click", async () => {
  if (!postlogFiles.reportValidity()) return;
  const data = new FormData();
  appendPostlogFiles(data);
  data.append(
    "source_timezone",
    postlogForm.elements.source_timezone.value,
  );
  inspectPostlogsButton.disabled = true;
  inspectPostlogsButton.textContent = "Inspecting…";

  try {
    const response = await fetch("/api/postlogs/options", {
      method: "POST",
      body: data,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail);

    postlogsInspected = true;
    filterPostlogsButton.disabled = false;
    postlogSummary.classList.remove("is-hidden");
    postlogSummaryMetrics.replaceChildren();
    postlogMetric(postlogSummaryMetrics, `${result.files_processed} Files`);
    postlogMetric(postlogSummaryMetrics, `${result.events_received} Events`);
    postlogMetric(postlogSummaryMetrics, `${result.assets.length} Assets`);
    postlogSummaryMessage.textContent = (
      `${result.channels.join(", ") || "Unknown channel"} · ` +
      `${result.start_date || "Unknown"} to ${result.end_date || "Unknown"}`
    );
    postlogForm.elements.start_date.value = result.start_date || "";
    postlogForm.elements.end_date.value = result.end_date || "";
    postlogChannelName.value = result.channels[0] || "";
    postlogSuggestions.replaceChildren();
    const suggestions = postlogMode.value === "prefix"
      ? result.prefixes.map((item) => item.prefix)
      : result.assets.map((item) => item.asset_id);
    for (const value of suggestions) {
      const option = document.createElement("option");
      option.value = value;
      postlogSuggestions.appendChild(option);
    }
  } catch (error) {
    postlogSummary.classList.remove("is-hidden");
    postlogSummaryMessage.textContent = (
      error.message || "The As-Run files could not be inspected."
    );
  } finally {
    inspectPostlogsButton.disabled = false;
    inspectPostlogsButton.textContent = "Inspect As-Run";
  }
});

postlogForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!postlogsInspected || !postlogForm.reportValidity()) return;
  const data = new FormData();
  appendPostlogFiles(data);
  appendPostlogFilters(data);
  filterPostlogsButton.disabled = true;
  filterPostlogsButton.textContent = "Finding…";

  try {
    const response = await fetch("/api/postlogs/filter", {
      method: "POST",
      body: data,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail);

    postlogResult.classList.remove("is-hidden");
    postlogResultMessage.textContent = result.matching_events
      ? "These actual airings will be included in the certification."
      : "No actual airings match the selected filters.";
    postlogResultMetrics.replaceChildren();
    postlogMetric(postlogResultMetrics, `${result.matching_events} Airings`);
    postlogMetric(postlogResultMetrics, `${result.unique_assets} Assets`);
    postlogPreview.replaceChildren();
    for (const match of result.matches) {
      const row = document.createElement("tr");
      const airing = new Date(match.air_datetime);
      for (const value of [
        match.channel_name || "—",
        match.asset_id,
        airing.toLocaleDateString(),
        airing.toLocaleTimeString(),
        match.duration || "—",
      ]) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      }
      postlogPreview.appendChild(row);
    }
    postlogExportPanel.classList.toggle(
      "is-hidden",
      result.matching_events === 0,
    );
  } catch (error) {
    postlogResult.classList.remove("is-hidden");
    postlogResultMessage.textContent = (
      error.message || "The actual airings could not be filtered."
    );
  } finally {
    filterPostlogsButton.disabled = false;
    filterPostlogsButton.textContent = "Find Actual Airings";
  }
});

exportPostlogButton.addEventListener("click", async () => {
  if (!postlogChannelName.reportValidity()) return;
  const data = new FormData();
  appendPostlogFiles(data);
  appendPostlogFilters(data);
  data.append("channel_name", postlogChannelName.value);
  data.append(
    "report_language",
    document.querySelector("#postlog-report-language").value,
  );
  data.append(
    "output_format",
    document.querySelector("#postlog-output-format").value,
  );
  for (const [name, selector] of [
    ["product", "#postlog-product"],
    ["agency", "#postlog-agency"],
  ]) {
    const value = document.querySelector(selector).value.trim();
    if (value) data.append(name, value);
  }
  const logo = document.querySelector("#postlog-logo").files[0];
  if (logo) data.append("logo_file", logo);

  exportPostlogButton.disabled = true;
  exportPostlogButton.textContent = "Generating…";
  try {
    const response = await fetch("/api/postlogs/export", {
      method: "POST",
      body: data,
    });
    if (!response.ok) {
      const result = await response.json();
      throw new Error(result.detail);
    }
    const blob = await response.blob();
    const header = response.headers.get("Content-Disposition") || "";
    const filename = header.match(/filename="([^"]+)"/)?.[1]
      || "postlog-certification.xlsx";
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
    postlogExportStatus.textContent = `${filename} downloaded successfully.`;
  } catch (error) {
    postlogExportStatus.classList.add("is-error");
    postlogExportStatus.textContent = (
      error.message || "The certification could not be generated."
    );
  } finally {
    exportPostlogButton.disabled = false;
    exportPostlogButton.textContent = "Download Certifications";
  }
});

updatePostlogMode();
