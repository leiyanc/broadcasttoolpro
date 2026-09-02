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

function applyRegisteredChannel(channel) {
  if (!channel) return;
  form.elements.channel_id.value = channel.id;
  form.elements.channel_name.value = channel.name;
  form.elements.channel_timezone.value = channel.timezone;
  form.elements.primary_language.value = channel.primary_language || "en";
}

window.addEventListener("btp:channel", (event) => {
  applyRegisteredChannel(event.detail);
});
applyRegisteredChannel(window.BTPActiveChannel);

function uiText(key, fallback, values = {}) {
  const template = window.BTPi18n?.t(key, fallback) ?? fallback;
  return Object.entries(values).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
    template,
  );
}

const FIX_MESSAGE_KEYS = {
  duration: "generator.fix.duration",
  boolean: "generator.fix.boolean",
  continuation: "generator.fix.continuation",
  duplicate: "generator.fix.duplicate",
  "Convert numeric durations to HH:MM:SS.": "generator.fix.duration",
  "Normalize localized Yes/No values.": "generator.fix.boolean",
  "Merge continuation rows into one programme.": "generator.fix.continuation",
  "Remove exact duplicate rows.": "generator.fix.duplicate",
};

function localizedFixMessage(fix) {
  const fallback = fix.message || uiText(
    "generator.correction",
    "Correction",
  );
  const key = FIX_MESSAGE_KEYS[fix.code] || FIX_MESSAGE_KEYS[fix.message];
  return key ? uiText(key, fallback) : fallback;
}

function localizedIssueMessage(issue) {
  const fallback = issue.message || uiText(
    "generator.unknownIssue",
    "Unknown issue",
  );
  return ["VAL-011", "VAL-012"].includes(issue.rule_id)
    ? uiText(`generator.rule.${issue.rule_id}`, fallback, {
      actual: issue.actual_channel || "",
      expected: issue.expected_channel || "",
    })
    : fallback;
}

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

  if (Array.isArray(detail)) {
    const issues = detail.map((item) => {
      const location = Array.isArray(item?.loc)
        ? item.loc.filter((part) => part !== "body").join(" → ")
        : "Request";
      return {
        rule_id: "REQUEST",
        severity: "critical",
        field: location,
        message: `${location}: ${item?.msg || "Invalid value."}`,
      };
    });
    return {
      success: false,
      programmes_imported: 0,
      suggested_fixes: 0,
      validation: {
        score: 0,
        critical: issues.length || 1,
        errors: 0,
        warnings: 0,
        issues: issues.length
          ? issues
          : fallbackValidation("Invalid request.").issues,
      },
    };
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
      ? uiText(
          "generator.serverIncomplete",
          "The server returned an incomplete validation response.",
        )
      : uiText(
          "generator.serverProcessError",
          "The server could not process the schedule.",
        );

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
  fileSubtitle.textContent = uiText(
    "generator.fileReady",
    "{size} KB — ready to validate",
    { size: (file.size / 1024).toFixed(1) },
  );
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
    programme.live ? uiText("preview.live", "Live") : "",
    programme.new ? uiText("preview.new", "New") : "",
    programme.premiere ? uiText("preview.premiere", "Premiere") : "",
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
    addPreviewCell(
      row,
      programme.duration || uiText("preview.calculated", "Calculated"),
    );
    addPreviewCell(row, programme.program_title, "programme-title");
    addPreviewCell(row, programmeEpisode(programme));
    addPreviewCell(row, programme.genre);
    addPreviewCell(row, programme.parental_rating);
    addPreviewCell(row, programmeFlags(programme));
    epgPreviewBody.appendChild(row);
  }

  epgPreviewStats.replaceChildren();
  for (const value of [
    uiText("preview.metricProgrammes", "{count} Programmes", {
      count: filtered.length,
    }),
    uiText("preview.metricDates", "{count} Dates", {
      count: new Set(filtered.map((item) => item.air_date)).size,
    }),
    uiText("preview.metricGenres", "{count} Genres", {
      count: new Set(filtered.map((item) => item.genre).filter(Boolean)).size,
    }),
  ]) {
    const metric = document.createElement("span");
    metric.textContent = value;
    epgPreviewStats.appendChild(metric);
  }
  epgPreviewStatus.textContent = filtered.length > visible.length
    ? uiText(
        "preview.showingFirst",
        "Showing the first {visible} of {total} programmes.",
        { visible: visible.length, total: filtered.length },
      )
    : filtered.length
      ? uiText("preview.shown", "{count} programme(s) shown.", {
          count: filtered.length,
        })
      : uiText(
          "preview.noMatches",
          "No programmes match the selected preview filters.",
        );
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
  allDates.textContent = uiText("preview.allDates", "All dates");
  epgPreviewDate.appendChild(allDates);
  for (const date of dates) {
    const option = document.createElement("option");
    option.value = date;
    option.textContent = date;
    epgPreviewDate.appendChild(option);
  }
  epgPreviewSearch.value = "";
  epgPreviewSummary.textContent = uiText(
    "preview.summary",
    "Previewing {count} programmes in {timezone}.",
    {
      count: latestSchedule.length,
      timezone: form.elements.channel_timezone.options[
        form.elements.channel_timezone.selectedIndex
      ].text,
    },
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

  if (!form.elements.channel_id.value) {
    showResult({
      success: false,
      programmes_imported: 0,
      validation: fallbackValidation(uiText(
        "generator.channelSelectionRequired",
        "This account has no active registered channel. Register or activate a channel before validating. The Channel value in the Excel file must exactly match the registered channel name.",
      ), "CHANNEL"),
    });
    return null;
  }

  data.append("schedule_file", file);
  data.append(
    "channel_timezone",
    form.elements.channel_timezone.value,
  );
  data.append("channel_id", form.elements.channel_id.value);

  if (includeProfile) {
    for (const field of [
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
  const authorizationOnly = suggestedFixes > 0
    && issues.length > 0
    && issues.every((issue) => issue.rule_id === "AUTH-001")
    && (validation.errors || 0) === 0
    && (validation.warnings || 0) === 0;
  const readyForReview = success || authorizationOnly;

  resultPanel.classList.remove("is-hidden");
  xmltvTemplateGuidance?.classList.toggle("is-hidden", readyForReview);
  resultPanel.classList.toggle("is-error", !readyForReview);
  resultIcon.textContent = authorizationOnly ? "i" : success ? "✓" : "!";
  resultTitle.textContent = authorizationOnly
    ? uiText("generator.readyAuthorization", "Ready for authorization")
    : success
    ? suggestedFixes
      ? uiText("generator.readyReview", "Schedule ready for review")
      : uiText("generator.readyGenerate", "Schedule ready to generate")
    : uiText("generator.needsAttention", "Schedule needs attention");
  resultMessage.textContent = authorizationOnly
    ? uiText(
        "generator.authorizationPending",
        "The schedule is valid. Authorize {fixes} safe corrections to generate XMLTV.",
        { fixes: suggestedFixes },
      )
    : success
    ? suggestedFixes
      ? (
          uiText(
            "generator.validReview",
            "{count} programmes are valid. Review and authorize {fixes} suggested corrections.",
            {
              count: normalized.programmes_imported || 0,
              fixes: suggestedFixes,
            },
          )
        )
      : uiText(
          "generator.importSuccess",
          "{count} programmes were imported successfully.",
          { count: normalized.programmes_imported || 0 },
        )
    : uiText(
        "generator.correctBlocking",
        "Correct the blocking issues before generating XMLTV.",
      );
  resultMetrics.replaceChildren();
  for (const text of [
    uiText("generator.metricScore", "Score {score}/100", {
      score: validation.score ?? 0,
    }),
    uiText("generator.metricCritical", "{count} Critical", {
      count: validation.critical ?? 0,
    }),
    uiText("generator.metricErrors", "{count} Errors", {
      count: validation.errors ?? 0,
    }),
    uiText("generator.metricWarnings", "{count} Warnings", {
      count: validation.warnings ?? 0,
    }),
    uiText("generator.metricFixes", "{count} Suggested fixes", {
      count: suggestedFixes,
    }),
  ]) {
    const metric = document.createElement("span");
    metric.textContent = text;
    resultMetrics.appendChild(metric);
  }

  issueList.replaceChildren();
  for (const issue of issues.slice(0, 8)) {
    const row = issue.row
      ? ` (${uiText("generator.issueRow", "row {row}", { row: issue.row })})`
      : "";
    appendListItem(
      `${issue.rule_id || "VALIDATION"}: ${localizedIssueMessage(issue)}${row}`,
    );
  }
  for (const fix of fixSummary) {
    appendListItem(uiText(
      "generator.suggested",
      "Suggested: {count} × {message}",
      {
        count: fix.count || 0,
        message: localizedFixMessage(fix),
      },
    ));
  }

  authorizationPanel.classList.toggle("is-hidden", suggestedFixes === 0);
  authorizationMessage.textContent = suggestedFixes
    ? uiText(
        "generator.applyFixes",
        "Apply {count} safe corrections only to the generated XMLTV.",
        { count: suggestedFixes },
      )
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
  validateButton.textContent = uiText("generator.validating", "Validating…");

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
          message: uiText(
            "generator.serverProcessError",
            "The server could not process the schedule.",
          ),
        }],
      },
    });
    return false;
  } finally {
    validateButton.disabled = false;
    validateButton.textContent = uiText("generator.validate", "Validate Schedule");
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
      uiText(
        "grid.validateFirst",
        "Validate the EPG before creating the Programming Grid.",
      )
    );
    return;
  }

  const data = buildFormData();
  if (!data) return;
  data.append(
    "accept_auto_fixes",
    acceptAutoFixes.checked ? "true" : "false",
  );
  if (programmingGridLogo.files[0]) {
    data.append("channel_logo", programmingGridLogo.files[0]);
  }

  programmingGridButton.disabled = true;
  programmingGridButton.textContent = uiText("generator.creatingPdf", "Creating PDF…");
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
        uiText("grid.createError", "The Programming Grid could not be created.")
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
      uiText(
        "generator.downloadSuccess",
        "{filename} was downloaded successfully.",
        { filename: link.download },
      )
    );
  } catch {
    programmingGridStatus.textContent = (
      uiText(
        "grid.serverError",
        "The server could not create the Programming Grid.",
      )
    );
  } finally {
    programmingGridButton.disabled = false;
    programmingGridButton.textContent = uiText(
      "grid.download",
      "Download Programming Grid",
    );
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  const data = buildFormData(true);
  if (!data) return;

  generateButton.disabled = true;
  generateButton.textContent = uiText("generator.generating", "Generating…");

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
    resultTitle.textContent = uiText("generator.generated", "XMLTV generated");
    resultMessage.textContent = uiText(
      "generator.downloadSuccess",
      "{filename} was downloaded successfully.",
      { filename: link.download },
    );
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
          message: uiText(
            "generator.serverGenerateError",
            "The server could not generate the XMLTV file.",
          ),
        }],
      },
    });
  } finally {
    generateButton.disabled = false;
    generateButton.textContent = uiText("generator.generate", "Generate XMLTV");
  }
});

window.addEventListener("btp:languagechange", () => {
  validateButton.textContent = uiText("generator.validate", "Validate Schedule");
  generateButton.textContent = uiText("generator.generate", "Generate XMLTV");
  programmingGridButton.textContent = uiText(
    "grid.download",
    "Download Programming Grid",
  );
  if (fileInput.files[0]) updateFileLabel();
  if (latestSchedule.length) showEpgPreview(latestSchedule);
});
