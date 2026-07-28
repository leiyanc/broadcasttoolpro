const validatorForm = document.querySelector("#validator-form");
const xmltvFileInput = document.querySelector("#xmltv-file");
const validatorDropZone = document.querySelector("#validator-drop-zone");
const validatorFileTitle = document.querySelector("#validator-file-title");
const validatorFileSubtitle = document.querySelector("#validator-file-subtitle");
const validateXmltvButton = document.querySelector("#validate-xmltv-button");
const validatorResultPanel = document.querySelector("#validator-result-panel");
const validatorResultIcon = document.querySelector("#validator-result-icon");
const validatorResultTitle = document.querySelector("#validator-result-title");
const validatorResultMessage = document.querySelector("#validator-result-message");
const validatorResultMetrics = document.querySelector("#validator-result-metrics");
const validatorIssueList = document.querySelector("#validator-issue-list");
const validatorResultActions = document.querySelector("#validator-result-actions");
const downloadValidatorReport = document.querySelector("#download-validator-report");
const downloadValidatorHtmlReport = document.querySelector(
  "#download-validator-html-report",
);
let latestValidatorReport = null;

function updateValidatorFileLabel() {
  const file = xmltvFileInput.files[0];
  if (!file) return;

  const isXml = file.name.toLowerCase().endsWith(".xml");
  xmltvFileInput.setCustomValidity(
    isXml ? "" : "Choose a file with the .xml extension.",
  );
  validatorFileTitle.textContent = file.name;
  validatorFileSubtitle.textContent = isXml
    ? `${(file.size / 1024).toFixed(1)} KB — ready to validate`
    : "Only .xml files are supported.";
  validatorDropZone.classList.toggle("is-invalid", !isXml);
}

function addValidatorMetric(text) {
  const metric = document.createElement("span");
  metric.textContent = text;
  validatorResultMetrics.appendChild(metric);
}

function addValidatorIssue(issue) {
  const item = document.createElement("li");
  const row = issue.row ? ` (line ${issue.row})` : "";
  item.textContent = (
    `${issue.rule_id || "XMLTV"}: ${issue.message || "Unknown issue"}${row}`
  );
  validatorIssueList.appendChild(item);
}

function countLabel(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function downloadReportBlob(content, type, filename) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function buildHtmlReport(report, brandLogo) {
  const validation = report.validation;
  const issues = Array.isArray(validation.issues) ? validation.issues : [];
  const status = report.valid ? "Valid XMLTV" : "XMLTV Needs Attention";
  const issueRows = issues.length
    ? issues.map((issue) => `
        <tr>
          <td>${escapeHtml(issue.severity)}</td>
          <td>${escapeHtml(issue.rule_id)}</td>
          <td>${escapeHtml(issue.row || "—")}</td>
          <td>${escapeHtml(issue.field || "—")}</td>
          <td>${escapeHtml(issue.message)}</td>
        </tr>
      `).join("")
    : '<tr><td colspan="5">No issues found.</td></tr>';

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XMLTV Validation Report</title>
    <style>
      body { margin: 0; color: #172033; background: #f6f8fb; font: 15px Arial, sans-serif; }
      main { width: min(920px, calc(100% - 40px)); margin: 40px auto; }
      header, section { padding: 28px; background: white; border: 1px solid #dbe3ee; border-radius: 16px; }
      section { margin-top: 20px; }
      h1, h2 { margin-top: 0; color: #102a43; }
      .status { color: ${report.valid ? "#087f5b" : "#b42318"}; font-weight: 700; }
      .metrics { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
      .metric { padding: 9px 12px; background: #f6f8fb; border-radius: 8px; font-weight: 700; }
      table { width: 100%; border-collapse: collapse; }
      th, td { padding: 11px; border-bottom: 1px solid #dbe3ee; text-align: left; vertical-align: top; }
      th { color: #40526a; font-size: 12px; text-transform: uppercase; }
      .meta { color: #64748b; }
      .brand-logo { display: block; width: 320px; max-width: 75%; height: auto; margin-bottom: 24px; }
      @media print { body { background: white; } main { width: 100%; margin: 0; } }
    </style>
  </head>
  <body>
    <main>
      <header>
        <img class="brand-logo" src="${brandLogo}" alt="Broadcast Tool Pro">
        <h1>XMLTV Validation Report</h1>
        <p class="status">${escapeHtml(status)}</p>
        <p class="meta">
          File: ${escapeHtml(report.filename || "Unknown")}<br>
          Generated: ${escapeHtml(report.generated_at)}
        </p>
        <div class="metrics">
          <span class="metric">Score ${escapeHtml(validation.score ?? 0)}/100</span>
          <span class="metric">${escapeHtml(validation.critical ?? 0)} Critical</span>
          <span class="metric">${escapeHtml(validation.errors ?? 0)} Errors</span>
          <span class="metric">${escapeHtml(validation.warnings ?? 0)} Warnings</span>
          <span class="metric">${escapeHtml(report.channels ?? 0)} Channels</span>
          <span class="metric">${escapeHtml(report.programmes ?? 0)} Programmes</span>
        </div>
      </header>
      <section>
        <h2>Validation Issues</h2>
        <table>
          <thead>
            <tr><th>Severity</th><th>Rule</th><th>Line</th><th>Field</th><th>Message</th></tr>
          </thead>
          <tbody>${issueRows}</tbody>
        </table>
      </section>
    </main>
  </body>
</html>`;
}

function normalizeValidatorResponse(payload, responseOk) {
  if (payload && typeof payload === "object" && payload.validation) {
    return payload;
  }

  const detail = payload && typeof payload.detail === "string"
    ? payload.detail
    : "The server could not validate the XMLTV file.";

  return {
    valid: false,
    well_formed: false,
    channels: 0,
    programmes: 0,
    validation: {
      score: 0,
      critical: 1,
      errors: 0,
      warnings: 0,
      issues: [{
        rule_id: responseOk ? "XMLTV" : "REQUEST",
        message: detail,
      }],
    },
  };
}

function showValidatorResult(result) {
  const validation = result.validation;
  const issues = Array.isArray(validation.issues) ? validation.issues : [];

  validatorResultPanel.classList.remove("is-hidden");
  validatorResultPanel.classList.toggle("is-error", !result.valid);
  validatorResultIcon.textContent = result.valid ? "✓" : "!";
  validatorResultTitle.textContent = result.valid
    ? "XMLTV is valid"
    : "XMLTV needs attention";
  validatorResultMessage.textContent = result.valid
    ? (
        `${countLabel(result.channels, "channel")} and ` +
        `${countLabel(result.programmes, "programme")} ` +
        "passed validation."
      )
    : "Review the reported issues before delivering this XMLTV file.";

  validatorResultMetrics.replaceChildren();
  addValidatorMetric(`Score ${validation.score ?? 0}/100`);
  addValidatorMetric(`${validation.critical ?? 0} Critical`);
  addValidatorMetric(`${validation.errors ?? 0} Errors`);
  addValidatorMetric(`${validation.warnings ?? 0} Warnings`);
  addValidatorMetric(countLabel(result.channels ?? 0, "Channel"));
  addValidatorMetric(countLabel(result.programmes ?? 0, "Programme"));

  validatorIssueList.replaceChildren();
  for (const issue of issues.slice(0, 20)) {
    addValidatorIssue(issue);
  }

  latestValidatorReport = {
    generated_at: new Date().toISOString(),
    filename: xmltvFileInput.files[0]?.name || null,
    ...result,
  };
  validatorResultActions.classList.remove("is-hidden");

  validatorResultPanel.scrollIntoView({
    behavior: "smooth",
    block: "nearest",
  });
}

xmltvFileInput.addEventListener("change", () => {
  latestValidatorReport = null;
  validatorResultActions.classList.add("is-hidden");
});
xmltvFileInput.addEventListener("change", updateValidatorFileLabel);

downloadValidatorReport.addEventListener("click", () => {
  if (!latestValidatorReport) return;

  const sourceName = latestValidatorReport.filename || "xmltv";
  const reportName = sourceName.replace(/\.xml$/i, "");
  downloadReportBlob(
    JSON.stringify(latestValidatorReport, null, 2),
    "application/json",
    `${reportName}-validation-report.json`,
  );
  downloadValidatorReport.closest("details").removeAttribute("open");
});

downloadValidatorHtmlReport.addEventListener("click", async () => {
  if (!latestValidatorReport) return;

  const sourceName = latestValidatorReport.filename || "xmltv";
  const reportName = sourceName.replace(/\.xml$/i, "");
  const logoResponse = await fetch(
    "/static/assets/broadcast-tool-pro-logo.png",
  );
  const logoBlob = await logoResponse.blob();
  const brandLogo = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(logoBlob);
  });
  downloadReportBlob(
    buildHtmlReport(latestValidatorReport, brandLogo),
    "text/html;charset=utf-8",
    `${reportName}-validation-report.html`,
  );
  downloadValidatorHtmlReport.closest("details").removeAttribute("open");
});

for (const eventName of ["dragenter", "dragover"]) {
  validatorDropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    validatorDropZone.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  validatorDropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    validatorDropZone.classList.remove("is-dragging");
  });
}

validatorDropZone.addEventListener("drop", (event) => {
  const [file] = event.dataTransfer.files;
  if (!file) return;

  const transfer = new DataTransfer();
  transfer.items.add(file);
  xmltvFileInput.files = transfer.files;
  updateValidatorFileLabel();
});

validatorForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validatorForm.reportValidity()) return;

  const data = new FormData();
  data.append("xmltv_file", xmltvFileInput.files[0]);
  validateXmltvButton.disabled = true;
  validateXmltvButton.textContent = "Validating…";

  try {
    const response = await fetch("/api/xmltv/validate", {
      method: "POST",
      body: data,
    });
    const payload = await response.json();
    showValidatorResult(
      normalizeValidatorResponse(payload, response.ok),
    );
  } catch {
    showValidatorResult(
      normalizeValidatorResponse(null, false),
    );
  } finally {
    validateXmltvButton.disabled = false;
    validateXmltvButton.textContent = "Validate XMLTV";
  }
});
