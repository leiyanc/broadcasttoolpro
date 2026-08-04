const repairForm = document.querySelector("#repair-form");
const repairFileInput = document.querySelector("#repair-xmltv-file");
const repairDropZone = document.querySelector("#repair-drop-zone");
const repairFileTitle = document.querySelector("#repair-file-title");
const repairFileSubtitle = document.querySelector("#repair-file-subtitle");
const previewRepairsButton = document.querySelector("#preview-repairs-button");
const downloadRepairedButton = document.querySelector("#download-repaired-button");
const repairAuthorizationPanel = document.querySelector(
  "#repair-authorization-panel",
);
const acceptRepairs = document.querySelector("#accept-repairs");
const repairAuthorizationMessage = document.querySelector(
  "#repair-authorization-message",
);
const repairResultPanel = document.querySelector("#repair-result-panel");
const repairResultIcon = document.querySelector("#repair-result-icon");
const repairResultTitle = document.querySelector("#repair-result-title");
const repairResultMessage = document.querySelector("#repair-result-message");
const repairResultMetrics = document.querySelector("#repair-result-metrics");
const repairChangeList = document.querySelector("#repair-change-list");

let repairPreviewComplete = false;
let latestRepairPreview = null;

function repairText(key, fallback, values = {}) {
  const template = window.BTPi18n?.t(key, fallback) || fallback;
  return Object.entries(values).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, value),
    template,
  );
}

function localizeRepairChange(change) {
  if (window.BTPi18n?.getLanguage() !== "es") {
    return change.message || repairText("repair.unknownChange", "Unknown repair");
  }
  return repairText(
    `repair.rule.${change.rule_id}`,
    change.message || repairText("repair.unknownChange", "Unknown repair"),
  );
}

function resetRepairState() {
  repairPreviewComplete = false;
  acceptRepairs.checked = false;
  downloadRepairedButton.disabled = true;
  repairAuthorizationPanel.classList.add("is-hidden");
  repairResultPanel.classList.add("is-hidden");
}

function updateRepairFileLabel(reset = true) {
  const file = repairFileInput.files[0];
  if (!file) return;

  const isXml = file.name.toLowerCase().endsWith(".xml");
  repairFileInput.setCustomValidity(
    isXml ? "" : repairText("repair.chooseXml", "Choose a file with the .xml extension."),
  );
  repairFileTitle.textContent = file.name;
  repairFileSubtitle.textContent = isXml
    ? repairText("repair.fileReady", "{size} KB — ready to analyze", {
        size: (file.size / 1024).toFixed(1),
      })
    : repairText("repair.onlyXml", "Only .xml files are supported.");
  repairDropZone.classList.toggle("is-invalid", !isXml);
  if (reset) resetRepairState();
}

function repairFormData(includeAuthorization = false) {
  const file = repairFileInput.files[0];
  if (!file) {
    repairFileInput.reportValidity();
    return null;
  }

  const data = new FormData();
  data.append("xmltv_file", file);
  if (includeAuthorization) {
    data.append("accept_repairs", acceptRepairs.checked ? "true" : "false");
  }
  return data;
}

function addRepairMetric(text) {
  const metric = document.createElement("span");
  metric.textContent = text;
  repairResultMetrics.appendChild(metric);
}

function showRepairError(message) {
  repairResultPanel.classList.remove("is-hidden");
  repairResultPanel.classList.add("is-error");
  repairResultIcon.textContent = "!";
  repairResultTitle.textContent = repairText("repair.unsafe", "XMLTV cannot be repaired safely");
  repairResultMessage.textContent = message;
  repairResultMetrics.replaceChildren();
  repairChangeList.replaceChildren();
}

function showRepairPreview(result) {
  latestRepairPreview = result;
  const changes = Array.isArray(result.changes) ? result.changes : [];
  const validation = result.validation?.validation || {};

  repairResultPanel.classList.remove("is-hidden", "is-error");
  repairResultIcon.textContent = "✓";
  repairResultTitle.textContent = changes.length
    ? repairText("repair.ready", "Repairs ready for review")
    : repairText("repair.noneRequired", "No safe repairs are required");
  repairResultMessage.textContent = changes.length
    ? repairText("repair.found", "{count} safe corrections were identified. Review and authorize them before downloading.", { count: changes.length })
    : repairText("repair.noAutomatic", "The file does not contain issues that can be repaired automatically.");

  repairResultMetrics.replaceChildren();
  addRepairMetric(repairText("repair.metricSuggested", "{count} Suggested repairs", { count: changes.length }));
  addRepairMetric(repairText("repair.metricScore", "Result score {score}/100", { score: validation.score ?? 0 }));
  addRepairMetric(repairText("repair.metricCritical", "{count} Remaining critical", { count: validation.critical ?? 0 }));
  addRepairMetric(repairText("repair.metricWarnings", "{count} Remaining warnings", { count: validation.warnings ?? 0 }));

  repairChangeList.replaceChildren();
  for (const change of changes.slice(0, 20)) {
    const item = document.createElement("li");
    const line = change.line
      ? ` (${repairText("repair.line", "line {line}", { line: change.line })})`
      : "";
    item.textContent = (
      `${change.rule_id}: ${localizeRepairChange(change)}${line}`
    );
    repairChangeList.appendChild(item);
  }

  repairPreviewComplete = true;
  repairAuthorizationPanel.classList.toggle("is-hidden", changes.length === 0);
  repairAuthorizationMessage.textContent = (
    repairText("repair.applyCount", "Apply {count} reviewed corrections to the downloaded XMLTV.", { count: changes.length })
  );
  downloadRepairedButton.disabled = true;
  repairResultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

repairFileInput.addEventListener("change", updateRepairFileLabel);

acceptRepairs.addEventListener("change", () => {
  downloadRepairedButton.disabled = !(
    repairPreviewComplete && acceptRepairs.checked
  );
});

for (const eventName of ["dragenter", "dragover"]) {
  repairDropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    repairDropZone.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  repairDropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    repairDropZone.classList.remove("is-dragging");
  });
}

repairDropZone.addEventListener("drop", (event) => {
  const [file] = event.dataTransfer.files;
  if (!file) return;

  const transfer = new DataTransfer();
  transfer.items.add(file);
  repairFileInput.files = transfer.files;
  updateRepairFileLabel();
});

previewRepairsButton.addEventListener("click", async () => {
  const data = repairFormData();
  if (!data || !repairForm.reportValidity()) return;

  previewRepairsButton.disabled = true;
  previewRepairsButton.textContent = repairText("repair.analyzing", "Analyzing…");

  try {
    const response = await fetch("/api/xmltv/repair/preview", {
      method: "POST",
      body: data,
    });
    const result = await response.json();

    if (!response.ok) {
      showRepairError(
        typeof result.detail === "string"
          ? result.detail
          : repairText("repair.analyzeError", "The XMLTV file could not be analyzed."),
      );
      return;
    }

    showRepairPreview(result);
  } catch {
    showRepairError(repairText("repair.serverAnalyzeError", "The server could not analyze the XMLTV file."));
  } finally {
    previewRepairsButton.disabled = false;
    previewRepairsButton.textContent = repairText("repair.analyze", "Analyze Repairs");
  }
});

repairForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!repairPreviewComplete || !acceptRepairs.checked) return;

  const data = repairFormData(true);
  if (!data) return;

  downloadRepairedButton.disabled = true;
  downloadRepairedButton.textContent = repairText("repair.repairing", "Repairing…");

  try {
    const response = await fetch("/api/xmltv/repair", {
      method: "POST",
      body: data,
    });

    if (!response.ok) {
      const result = await response.json();
      showRepairError(
        typeof result.detail === "string"
          ? result.detail
          : result.detail?.message || repairText("repair.failed", "XMLTV repair failed."),
      );
      return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const disposition = response.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    link.href = url;
    link.download = match?.[1] || "xmltv-repaired.xml";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    repairResultTitle.textContent = repairText("repair.repaired", "XMLTV repaired");
    repairResultMessage.textContent = repairText("repair.downloadSuccess", "{filename} was downloaded successfully.", { filename: link.download });
  } catch {
    showRepairError(repairText("repair.serverRepairError", "The server could not repair the XMLTV file."));
  } finally {
    downloadRepairedButton.disabled = false;
    downloadRepairedButton.textContent = repairText("repair.download", "Download Repaired XMLTV");
  }
});

window.addEventListener("btp:languagechange", () => {
  previewRepairsButton.textContent = repairText("repair.analyze", "Analyze Repairs");
  downloadRepairedButton.textContent = repairText("repair.download", "Download Repaired XMLTV");
  if (repairFileInput.files[0]) updateRepairFileLabel(false);
  if (latestRepairPreview) showRepairPreview(latestRepairPreview);
});
