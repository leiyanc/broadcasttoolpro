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
const authorizationPanel = document.querySelector("#authorization-panel");
const authorizationMessage = document.querySelector("#authorization-message");
const acceptAutoFixes = document.querySelector("#accept-auto-fixes");

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
