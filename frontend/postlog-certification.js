const postlogForm = document.querySelector("#postlog-form");
const postlogFiles = document.querySelector("#postlog-files");
const postlogDropZone = document.querySelector("#postlog-drop-zone");
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
const postlogClientName = document.querySelector("#postlog-client-name");
const postlogChannelName = document.querySelector("#postlog-channel-name");
const exportPostlogButton = document.querySelector("#export-postlog-button");
const postlogExportStatus = document.querySelector("#postlog-export-status");
const postlogProfileSelect = document.querySelector(
  "#postlog-profile-select",
);
const postlogProfileName = document.querySelector("#postlog-profile-name");
const savePostlogProfile = document.querySelector("#save-postlog-profile");
const deletePostlogProfile = document.querySelector(
  "#delete-postlog-profile",
);
const postlogProfileStatus = document.querySelector(
  "#postlog-profile-status",
);

let postlogsInspected = false;
let postlogDragDepth = 0;
const POSTLOG_FILTERS_KEY = "broadcastToolPro.postlogFilters";
const PROFILE_DATABASE = "BroadcastToolPro";
const PROFILE_STORE = "postlogProfiles";

function postlogText(key, fallback, values = {}) {
  let text = window.BTPi18n?.t(key, fallback) || fallback;
  for (const [name, value] of Object.entries(values)) {
    text = text.replaceAll(`{${name}}`, value);
  }
  return text;
}

function openProfileDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(PROFILE_DATABASE, 1);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(PROFILE_STORE)) {
        database.createObjectStore(PROFILE_STORE, { keyPath: "name" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function profileTransaction(mode, operation) {
  const database = await openProfileDatabase();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(PROFILE_STORE, mode);
    const request = operation(transaction.objectStore(PROFILE_STORE));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    transaction.oncomplete = () => database.close();
  });
}

async function profileByName(name) {
  return profileTransaction("readonly", (store) => store.get(name));
}

async function refreshProfileList(selectedName = "") {
  const profiles = await profileTransaction(
    "readonly",
    (store) => store.getAll(),
  );
  profiles.sort((left, right) => left.name.localeCompare(right.name));
  postlogProfileSelect.replaceChildren();
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = postlogText("postlog.chooseProfile", "Choose a saved profile");
  postlogProfileSelect.appendChild(empty);
  for (const profile of profiles) {
    const option = document.createElement("option");
    option.value = profile.name;
    option.textContent = profile.name;
    postlogProfileSelect.appendChild(option);
  }
  postlogProfileSelect.value = selectedName;
  deletePostlogProfile.disabled = !selectedName;
}

async function applyProfile(profile) {
  postlogProfileName.value = profile.name;
  postlogClientName.value = profile.clientName || "";
  postlogChannelName.value = profile.channelName || "";
  document.querySelector("#postlog-report-language").value = (
    profile.reportLanguage || "en"
  );
  document.querySelector("#postlog-output-format").value = (
    profile.outputFormat || "xlsx"
  );
  document.querySelector("#postlog-product").value = profile.product || "";
  document.querySelector("#postlog-agency").value = profile.agency || "";
  postlogForm.elements.source_timezone.value = (
    profile.sourceTimezone || "America/New_York"
  );
  postlogMode.value = profile.filterMode || "all";
  updatePostlogMode();
  postlogValue.value = profile.filterValue || "";

  const logoInput = document.querySelector("#postlog-logo");
  if (profile.logo?.blob) {
    const transfer = new DataTransfer();
    transfer.items.add(new File(
      [profile.logo.blob],
      profile.logo.name,
      { type: profile.logo.type },
    ));
    logoInput.files = transfer.files;
  } else {
    logoInput.value = "";
  }
}

async function saveCurrentProfile() {
  const name = postlogProfileName.value.trim();
  if (!name) {
    throw new Error(postlogText("postlog.profileRequired", "Enter a Profile Name first."));
  }
  const existing = await profileByName(name);
  const logoFile = document.querySelector("#postlog-logo").files[0];
  const profile = {
    name,
    clientName: postlogClientName.value.trim(),
    channelName: postlogChannelName.value.trim(),
    reportLanguage: document.querySelector(
      "#postlog-report-language",
    ).value,
    outputFormat: document.querySelector("#postlog-output-format").value,
    product: document.querySelector("#postlog-product").value.trim(),
    agency: document.querySelector("#postlog-agency").value.trim(),
    sourceTimezone: postlogForm.elements.source_timezone.value,
    filterMode: postlogMode.value,
    filterValue: postlogValue.value.trim(),
    logo: logoFile
      ? {
          name: logoFile.name,
          type: logoFile.type,
          blob: logoFile,
        }
      : existing?.logo || null,
    updatedAt: new Date().toISOString(),
  };
  await profileTransaction("readwrite", (store) => store.put(profile));
  await refreshProfileList(name);
}

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

function handlePostlogFilesChanged() {
  const files = [...postlogFiles.files];
  if (!files.length) return;
  postlogFileTitle.textContent = (
    files.length === 1 ? files[0].name : postlogText("postlog.filesSelected", `${files.length} As-Run files selected`, { count: files.length })
  );
  postlogFileSubtitle.textContent = postlogText("traffic.kbTotal", `${(
    files.reduce((total, file) => total + file.size, 0) / 1024
  ).toFixed(1)} KB total`, { size: (files.reduce((total, file) => total + file.size, 0) / 1024).toFixed(1) });
  postlogsInspected = false;
  filterPostlogsButton.disabled = true;
  postlogSummary.classList.add("is-hidden");
  postlogResult.classList.add("is-hidden");
  postlogExportPanel.classList.add("is-hidden");
}

postlogFiles.addEventListener("change", handlePostlogFilesChanged);

if (postlogDropZone) {
  postlogDropZone.addEventListener("dragenter", (event) => {
    event.preventDefault();
    postlogDragDepth += 1;
    postlogDropZone.classList.add("is-dragging");
  });
  postlogDropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  });
  postlogDropZone.addEventListener("dragleave", (event) => {
    event.preventDefault();
    postlogDragDepth = Math.max(0, postlogDragDepth - 1);
    if (!postlogDragDepth) {
      postlogDropZone.classList.remove("is-dragging");
    }
  });
  postlogDropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    postlogDragDepth = 0;
    postlogDropZone.classList.remove("is-dragging");
    const supported = new Set(["csv", "xlsx", "json", "txt", "xml"]);
    const files = [...event.dataTransfer.files].filter((file) => {
      const extension = file.name.split(".").pop()?.toLowerCase();
      return supported.has(extension);
    });
    if (!files.length) {
      postlogFileTitle.textContent = postlogText("postlog.unsupported", "Unsupported As-Run file");
      postlogFileSubtitle.textContent = postlogText("postlog.supported", "Use CSV, XLSX, JSON, TXT, or XML.");
      return;
    }
    const transfer = new DataTransfer();
    files.forEach((file) => transfer.items.add(file));
    postlogFiles.files = transfer.files;
    handlePostlogFilesChanged();
  });
}

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
  inspectPostlogsButton.textContent = postlogText("postlog.inspecting", "Inspecting…");

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
      `${result.channels.join(", ") || postlogText("traffic.unknownChannel", "Unknown channel")} · ` +
      `${result.start_date || postlogText("traffic.unknown", "Unknown")} to ${result.end_date || postlogText("traffic.unknown", "Unknown")}`
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
      error.message || postlogText("postlog.inspectError", "The As-Run files could not be inspected.")
    );
  } finally {
    inspectPostlogsButton.disabled = false;
    inspectPostlogsButton.textContent = postlogText("postlog.inspect", "Inspect As-Run");
  }
});

postlogForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!postlogsInspected || !postlogForm.reportValidity()) return;
  const data = new FormData();
  appendPostlogFiles(data);
  appendPostlogFilters(data);
  filterPostlogsButton.disabled = true;
  filterPostlogsButton.textContent = postlogText("postlog.finding", "Finding…");

  try {
    const response = await fetch("/api/postlogs/filter", {
      method: "POST",
      body: data,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail);

    postlogResult.classList.remove("is-hidden");
    postlogResultMessage.textContent = result.matching_events
      ? postlogText("postlog.reviewSelection", "These actual airings will be included in the certification.")
      : postlogText("postlog.noMatches", "No actual airings match the selected filters.");
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
      error.message || postlogText("postlog.filterError", "The actual airings could not be filtered.")
    );
  } finally {
    filterPostlogsButton.disabled = false;
    filterPostlogsButton.textContent = postlogText("postlog.find", "Find Actual Airings");
  }
});

exportPostlogButton.addEventListener("click", async () => {
  if (!postlogChannelName.reportValidity()) return;
  const data = new FormData();
  appendPostlogFiles(data);
  appendPostlogFilters(data);
  if (postlogClientName.value.trim()) {
    data.append("client_name", postlogClientName.value.trim());
  }
  data.append("channel_id", window.BTPActiveChannel?.id || "");
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
  exportPostlogButton.textContent = postlogText("traffic.generating", "Generating…");
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
    postlogExportStatus.textContent = postlogText("traffic.downloadSuccess", `${filename} downloaded successfully.`, { filename });
    window.dispatchEvent(new CustomEvent("report-generated"));
  } catch (error) {
    postlogExportStatus.classList.add("is-error");
    postlogExportStatus.textContent = (
      error.message || postlogText("postlog.generateError", "The certification could not be generated.")
    );
  } finally {
    exportPostlogButton.disabled = false;
    exportPostlogButton.textContent = postlogText("postlog.download", "Download Certifications");
  }
});

postlogProfileSelect.addEventListener("change", async () => {
  const name = postlogProfileSelect.value;
  deletePostlogProfile.disabled = !name;
  if (!name) return;
  try {
    const profile = await profileByName(name);
    if (profile) {
      await applyProfile(profile);
      postlogProfileStatus.classList.remove("is-error");
      postlogProfileStatus.textContent = `${name} loaded.`;
    }
  } catch {
    postlogProfileStatus.classList.add("is-error");
    postlogProfileStatus.textContent = "The profile could not be loaded.";
  }
});

savePostlogProfile.addEventListener("click", async () => {
  savePostlogProfile.disabled = true;
  try {
    await saveCurrentProfile();
    postlogProfileStatus.classList.remove("is-error");
    postlogProfileStatus.textContent = (
      `${postlogProfileName.value.trim()} saved successfully.`
    );
  } catch (error) {
    postlogProfileStatus.classList.add("is-error");
    postlogProfileStatus.textContent = (
      error.message || "The profile could not be saved."
    );
  } finally {
    savePostlogProfile.disabled = false;
  }
});

deletePostlogProfile.addEventListener("click", async () => {
  const name = postlogProfileSelect.value;
  if (!name) return;
  try {
    await profileTransaction(
      "readwrite",
      (store) => store.delete(name),
    );
    postlogProfileName.value = "";
    await refreshProfileList();
    postlogProfileStatus.classList.remove("is-error");
    postlogProfileStatus.textContent = `${name} deleted.`;
  } catch {
    postlogProfileStatus.classList.add("is-error");
    postlogProfileStatus.textContent = "The profile could not be deleted.";
  }
});

updatePostlogMode();
refreshProfileList().catch(() => {
  postlogProfileStatus.classList.add("is-error");
  postlogProfileStatus.textContent = "Saved profiles are unavailable.";
});

window.addEventListener("btp:languagechange", () => {
  window.BTPi18n?.apply(document.querySelector("#postlog"));
  refreshProfileList(postlogProfileSelect.value).catch(() => {});
  if (postlogFiles.files.length) handlePostlogFilesChanged();
});

window.addEventListener("btp:channel", (event) => {
  postlogChannelName.value = event.detail?.name || "";
});

window.addEventListener("btp:identity", (event) => {
  postlogClientName.value = event.detail?.organizations?.[0]?.name || "";
});
