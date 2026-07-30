const form = document.querySelector("#xmltv-form");
const fileInput = document.querySelector("#schedule-file");
const dropZone = document.querySelector("#drop-zone");
const fileTitle = document.querySelector("#file-title");
const fileSubtitle = document.querySelector("#file-subtitle");
const validateButton = document.querySelector("#validate-button");
const generateButton = document.querySelector("#generate-button");
const resultPanel = document.querySelector("#result-panel");
const resultIcon = document.querySelector("#result-icon");
const resultTitle = document.querySelector("#result-title");
const resultMessage = document.querySelector("#result-message");
const resultMetrics = document.querySelector("#result-metrics");
const issueList = document.querySelector("#issue-list");
const xmltvTemplateGuidance = document.querySelector(
  "#xmltv-template-guidance",
);
const authorizationPanel = document.querySelector("#authorization-panel");
const authorizationMessage = document.querySelector("#authorization-message");
const acceptAutoFixes = document.querySelector("#accept-auto-fixes");
const epgPreview = document.querySelector("#epg-preview");
const epgPreviewSummary = document.querySelector("#epg-preview-summary");
const epgPreviewDate = document.querySelector("#epg-preview-date");
const epgPreviewSearch = document.querySelector("#epg-preview-search");
const epgPreviewStats = document.querySelector("#epg-preview-stats");
const epgPreviewBody = document.querySelector("#epg-preview-body");
const epgPreviewStatus = document.querySelector("#epg-preview-status");
const programmingGridButton = document.querySelector(
  "#programming-grid-button",
);
const programmingGridStatus = document.querySelector(
  "#programming-grid-status",
);
const programmingGridLogo = document.querySelector(
  "#programming-grid-logo",
);

let latestSchedule = [];

const fallbackValidation = (message, ruleId = "REQUEST") => ({
  score: 0,
  critical: 1,
  errors: 0,
  warnings: 0,
  issues: [{ rule_id: ruleId, message }],
});

function normalizeResult(payload, responseOk = true) {
  const body = payload && typeof payload === "object" ? payload : {};
  const detail = body.detail;

  if (body.validation && typeof body.validation === "object") {
    return body;
  }

  if (detail && typeof detail === "object") {
    return {
      success: false,
      programmes_imported: 0,
      suggested_fixes: detail.suggested_fixes || 0,
      validation: detail,
    };
  }

  const message = typeof detail === "string"
    ? detail
    : responseOk
      ? "The server returned an incomplete validation response."
      : "The server could not process the schedule.";

  return {
    success: false,
    programmes_imported: 0,
    validation: fallbackValidation(message),
  };
}

function appendListItem(text) {
  const item = document.createElement("li");
  item.textContent = text;
  issueList.appendChild(item);
}

function updateFileLabel() {
  const file = fileInput.files[0];
  if (!file) return;
  fileTitle.textContent = file.name;
  fileSubtitle.textContent = `${(file.size / 1024).toFixed(1)} KB — ready to validate`;
  latestSchedule = [];
  epgPreview.classList.add("is-hidden");
  programmingGridStatus.textContent = "";
}

function formatPreviewTime(isoValue, timezoneName) {
  if (!isoValue) return "—";
  try {
    return new Intl.DateTimeFormat("en-US", {
      timeZone: timezoneName,
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(isoValue));
  } catch {
    return "—";
  }
}

function programmeEpisode(programme) {
  const parts = [];
  if (programme.season_number != null) {
    parts.push(`S${programme.season_number}`);
  }
  if (programme.episode_number != null) {
    parts.push(`E${programme.episode_number}`);
  }
  const number = parts.join(" ");
  return [number, programme.original_episode_title]
    .filter(Boolean)
    .join(" — ") || "—";
}

function programmeFlags(programme) {
  return [
    programme.live ? "Live" : "",
    programme.new ? "New" : "",
    programme.premiere ? "Premiere" : "",
  ].filter(Boolean).join(", ") || "—";
}

function addPreviewCell(row, value, className = "") {
  const cell = document.createElement("td");
  cell.textContent = value ?? "—";
  if (className) cell.className = className;
  row.appendChild(cell);
}

function renderEpgPreview() {
  const selectedDate = epgPreviewDate.value;
  const query = epgPreviewSearch.value.trim().toLowerCase();
  const filtered = latestSchedule.filter((programme) => {
    if (selectedDate && programme.air_date !== selectedDate) return false;
    if (!query) return true;
    return [
      programme.program_title,
      programme.original_episode_title,
      programme.genre,
      programme.program_description,
    ].some((value) => String(value || "").toLowerCase().includes(query));
  });
  const visible = filtered.slice(0, 300);

  epgPreviewBody.replaceChildren();
  for (const programme of visible) {
    const row = document.createElement("tr");
    addPreviewCell(row, programme.air_date, "preview-date");
    addPreviewCell(
      row,
      formatPreviewTime(
        programme.start_utc,
        form.elements.channel_timezone.value,
      ),
      "preview-time",
    );
    addPreviewCell(
      row,
      formatPreviewTime(
        programme.stop_utc,
        form.elements.channel_timezone.value,
      ),
      "preview-time",
    );
    addPreviewCell(row, programme.duration || "Calculated");
    addPreviewCell(row, programme.program_title, "programme-title");
    addPreviewCell(row, programmeEpisode(programme));
    addPreviewCell(row, programme.genre);
    addPreviewCell(row, programme.parental_rating);
    addPreviewCell(row, programmeFlags(programme));
    epgPreviewBody.appendChild(row);
  }

  epgPreviewStats.replaceChildren();
  for (const value of [
    `${filtered.length} Programmes`,
    `${new Set(filtered.map((item) => item.air_date)).size} Dates`,
    `${new Set(filtered.map((item) => item.genre).filter(Boolean)).size} Genres`,
  ]) {
    const metric = document.createElement("span");
    metric.textContent = value;
    epgPreviewStats.appendChild(metric);
  }
  epgPreviewStatus.textContent = filtered.length > visible.length
    ? `Showing the first ${visible.length} of ${filtered.length} programmes.`
    : filtered.length
      ? `${filtered.length} programme${filtered.length === 1 ? "" : "s"} shown.`
      : "No programmes match the selected preview filters.";
}

function showEpgPreview(programmes) {
  latestSchedule = Array.isArray(programmes) ? programmes : [];
  if (!latestSchedule.length) {
    epgPreview.classList.add("is-hidden");
    return;
  }

  const dates = [...new Set(
    latestSchedule.map((programme) => programme.air_date).filter(Boolean),
  )].sort();
  epgPreviewDate.replaceChildren();
  const allDates = document.createElement("option");
  allDates.value = "";
  allDates.textContent = "All dates";
  epgPreviewDate.appendChild(allDates);
  for (const date of dates) {
    const option = document.createElement("option");
    option.value = date;
    option.textContent = date;
    epgPreviewDate.appendChild(option);
  }
  epgPreviewSearch.value = "";
  epgPreviewSummary.textContent = (
    `Previewing ${latestSchedule.length} programmes in ` +
    `${form.elements.channel_timezone.options[
      form.elements.channel_timezone.selectedIndex
    ].text}.`
  );
  epgPreview.classList.remove("is-hidden");
  renderEpgPreview();
}

function buildFormData(includeProfile = false) {
  const data = new FormData();
  const file = fileInput.files[0];

  if (!file) {
    fileInput.reportValidity();
    return null;
  }

  data.append("schedule_file", file);
  data.append(
    "channel_timezone",
    form.elements.channel_timezone.value,
  );

  if (includeProfile) {
    for (const field of [
      "channel_id",
      "channel_name",
      "primary_language",
      "original_language",
      "rating_system",
      "timestamp_format",
    ]) {
      data.append(field, form.elements[field].value);
    }
    data.append(
      "accept_auto_fixes",
      acceptAutoFixes.checked ? "true" : "false",
    );
  }

  return data;
}

function showResult(result) {
  const normalized = normalizeResult(result);
  const validation = normalized.validation;
  const issues = Array.isArray(validation.issues) ? validation.issues : [];
  const suggestedFixes = normalized.suggested_fixes || 0;
  const fixSummary = Array.isArray(normalized.fix_summary)
    ? normalized.fix_summary
    : [];
  const success = Boolean(normalized.success);

  resultPanel.classList.remove("is-hidden");
  xmltvTemplateGuidance?.classList.toggle("is-hidden", success);
  resultPanel.classList.toggle("is-error", !success);
  resultIcon.textContent = success ? "✓" : "!";
  resultTitle.textContent = success
    ? suggestedFixes
      ? "Schedule ready for review"
      : "Schedule ready to generate"
    : "Schedule needs attention";
  resultMessage.textContent = success
    ? suggestedFixes
      ? (
          `${normalized.programmes_imported || 0} programmes are valid. Review and ` +
          `authorize ${suggestedFixes} suggested corrections.`
        )
      : `${normalized.programmes_imported || 0} programmes were imported successfully.`
    : "Correct the blocking issues before generating XMLTV.";
  resultMetrics.replaceChildren();
  for (const text of [
    `Score ${validation.score ?? 0}/100`,
    `${validation.critical ?? 0} Critical`,
    `${validation.errors ?? 0} Errors`,
    `${validation.warnings ?? 0} Warnings`,
    `${suggestedFixes} Suggested fixes`,
  ]) {
    const metric = document.createElement("span");
    metric.textContent = text;
    resultMetrics.appendChild(metric);
  }

  issueList.replaceChildren();
  for (const issue of issues.slice(0, 8)) {
    const row = issue.row ? ` (row ${issue.row})` : "";
    appendListItem(`${issue.rule_id || "VALIDATION"}: ${issue.message || "Unknown issue"}${row}`);
  }
  for (const fix of fixSummary) {
    appendListItem(`Suggested: ${fix.count || 0} × ${fix.message || "Correction"}`);
  }

  authorizationPanel.classList.toggle("is-hidden", suggestedFixes === 0);
  authorizationMessage.textContent = suggestedFixes
    ? `Apply ${suggestedFixes} safe corrections only to the generated XMLTV.`
    : "";
  if (suggestedFixes === 0) {
    acceptAutoFixes.checked = false;
  }
  showEpgPreview(success ? normalized.programmes : []);
  resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function validateSchedule() {
  const data = buildFormData();
  if (!data) return false;

  validateButton.disabled = true;
  validateButton.textContent = "Validating…";

  try {
    const response = await fetch("/api/xmltv/import", {
      method: "POST",
      body: data,
    });
    const payload = await response.json();
    const result = normalizeResult(payload, response.ok);
    showResult(result);
    return response.ok && result.success;
  } catch {
    showResult({
      success: false,
      programmes_imported: 0,
      validation: {
        score: 0,
        critical: 1,
        errors: 0,
        warnings: 0,
        issues: [{
          rule_id: "CONNECTION",
          message: "The server could not process the schedule.",
        }],
      },
    });
    return false;
  } finally {
    validateButton.disabled = false;
    validateButton.textContent = "Validate Schedule";
  }
}

fileInput.addEventListener("change", updateFileLabel);

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  });
}

dropZone.addEventListener("drop", (event) => {
  const [file] = event.dataTransfer.files;
  if (!file) return;

  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  updateFileLabel();
});

validateButton.addEventListener("click", validateSchedule);
epgPreviewDate.addEventListener("change", renderEpgPreview);
epgPreviewSearch.addEventListener("input", renderEpgPreview);
form.elements.channel_timezone.addEventListener("change", () => {
  if (latestSchedule.length) showEpgPreview(latestSchedule);
});

programmingGridButton.addEventListener("click", async () => {
  if (!latestSchedule.length) {
    programmingGridStatus.textContent = (
      "Validate the EPG before creating the Programming Grid."
    );
    return;
  }

  const data = buildFormData();
  if (!data) return;
  data.append("channel_name", form.elements.channel_name.value);
  data.append(
    "accept_auto_fixes",
    acceptAutoFixes.checked ? "true" : "false",
  );
  if (programmingGridLogo.files[0]) {
    data.append("channel_logo", programmingGridLogo.files[0]);
  }

  programmingGridButton.disabled = true;
  programmingGridButton.textContent = "Creating PDF…";
  programmingGridStatus.textContent = "";

  try {
    const response = await fetch("/api/xmltv/programming-grid", {
      method: "POST",
      body: data,
    });
    if (!response.ok) {
      const error = await response.json();
      showResult(normalizeResult(error, false));
      programmingGridStatus.textContent = (
        "The Programming Grid could not be created."
      );
      return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const disposition = response.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    link.href = url;
    link.download = match?.[1] || "programming-grid.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    programmingGridStatus.textContent = (
      `${link.download} downloaded successfully.`
    );
  } catch {
    programmingGridStatus.textContent = (
      "The server could not create the Programming Grid."
    );
  } finally {
    programmingGridButton.disabled = false;
    programmingGridButton.textContent = "Download Programming Grid";
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  const data = buildFormData(true);
  if (!data) return;

  generateButton.disabled = true;
  generateButton.textContent = "Generating…";

  try {
    const response = await fetch("/api/xmltv/generate", {
      method: "POST",
      body: data,
    });

    if (!response.ok) {
      const error = await response.json();
      showResult(normalizeResult(error, false));
      return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const disposition = response.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    link.href = url;
    link.download = match?.[1] || "broadcast-tool-pro-xmltv.xml";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    resultPanel.classList.remove("is-hidden", "is-error");
    resultIcon.textContent = "✓";
    resultTitle.textContent = "XMLTV generated";
    resultMessage.textContent = `${link.download} was downloaded successfully.`;
    resultMetrics.replaceChildren();
    issueList.replaceChildren();
  } catch {
    showResult({
      success: false,
      programmes_imported: 0,
      validation: {
        score: 0,
        critical: 1,
        errors: 0,
        warnings: 0,
        issues: [{
          rule_id: "CONNECTION",
          message: "The server could not generate the XMLTV file.",
        }],
      },
    });
  } finally {
    generateButton.disabled = false;
    generateButton.textContent = "Generate XMLTV";
  }
});
