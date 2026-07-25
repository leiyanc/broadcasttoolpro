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
  const validation = result.validation;
  const issues = validation.issues || [];
  const suggestedFixes = result.suggested_fixes || 0;
  const fixSummary = result.fix_summary || [];
  const success = result.success;

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
          `${result.programmes_imported} programmes are valid. Review and ` +
          `authorize ${suggestedFixes} suggested corrections.`
        )
      : `${result.programmes_imported} programmes were imported successfully.`
    : "Correct the blocking issues before generating XMLTV.";
  resultMetrics.innerHTML = [
    `<span>Score ${validation.score}/100</span>`,
    `<span>${validation.critical} Critical</span>`,
    `<span>${validation.errors} Errors</span>`,
    `<span>${validation.warnings} Warnings</span>`,
    `<span>${suggestedFixes} Suggested fixes</span>`,
  ].join("");
  const issueItems = issues
    .slice(0, 8)
    .map(
      (issue) =>
        `<li>${issue.rule_id}: ${issue.message}${issue.row ? ` (row ${issue.row})` : ""}</li>`,
    );
  const fixItems = fixSummary.map(
    (fix) => `<li>Suggested: ${fix.count} × ${fix.message}</li>`,
  );
  issueList.innerHTML = [...issueItems, ...fixItems].join("");

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
    const result = await response.json();
    showResult(result);
    return result.success;
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
      const validation = error.detail || {
        score: 0,
        critical: 1,
        errors: 0,
        warnings: 0,
        issues: [{ rule_id: "GENERATION", message: "XMLTV generation failed." }],
      };
      showResult({
        success: false,
        programmes_imported: 0,
        validation,
        suggested_fixes: validation.suggested_fixes || 0,
      });
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
    resultMetrics.innerHTML = "";
    issueList.innerHTML = "";
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
