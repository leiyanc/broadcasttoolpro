const landingMenuToggle = document.querySelector("#landing-menu-toggle");
const landingNav = document.querySelector("#landing-nav");
const landingContactForm = document.querySelector("#landing-contact-form");
const landingContactStatus = document.querySelector("#landing-contact-status");
const publicXmltvForm = document.querySelector("#public-xmltv-form");
const publicXmltvInput = document.querySelector("#public-xmltv-file");
const publicXmltvStatus = document.querySelector("#public-xmltv-status");
const publicXmltvResults = document.querySelector("#public-validator-results");
const publicXmltvFilename = document.querySelector("#public-xmltv-filename");
const publicXmltvDropzone = document.querySelector("#xmltv-dropzone");
let publicXmltvFile = null;

const landingText = (key, fallback) => window.BTPi18n?.t(key, fallback) || fallback;

function setPublicXmltvFile(file) {
  publicXmltvFile = file || null;
  publicXmltvFilename.textContent = file?.name || landingText("landing.validator.limit", "XML · Maximum 10 MB");
}

publicXmltvInput?.addEventListener("change", () => setPublicXmltvFile(publicXmltvInput.files?.[0]));
["dragenter", "dragover"].forEach((name) => publicXmltvDropzone?.addEventListener(name, (event) => {
  event.preventDefault();
  publicXmltvDropzone.classList.add("is-dragging");
}));
["dragleave", "drop"].forEach((name) => publicXmltvDropzone?.addEventListener(name, (event) => {
  event.preventDefault();
  publicXmltvDropzone.classList.remove("is-dragging");
}));
publicXmltvDropzone?.addEventListener("drop", (event) => {
  const file = event.dataTransfer?.files?.[0];
  if (file) setPublicXmltvFile(file);
});

function renderLayerIssues(result) {
  const groups = [
    [landingText("landing.validator.format", "XMLTV FORMAT"), result.xmltv?.issues || []],
    [landingText("landing.validator.operations", "OPERATIONAL READINESS"), result.operational?.issues || []],
    [landingText("landing.validator.profile", "BTP DELIVERY PROFILE"), result.btp_profile?.issues || []],
  ];
  const container = document.querySelector("#public-validator-issues");
  container.replaceChildren();
  groups.forEach(([label, issues]) => {
    if (!issues.length) return;
    const section = document.createElement("section");
    const heading = document.createElement("h3");
    heading.textContent = `${label} · ${issues.length}`;
    section.append(heading);
    const list = document.createElement("ul");
    issues.slice(0, 100).forEach((issue) => {
      const item = document.createElement("li");
      const line = issue.row ? ` · ${landingText("landing.validator.line", "Line")} ${issue.row}` : "";
      item.textContent = `${issue.rule_id}${line}: ${issue.message}`;
      list.append(item);
    });
    section.append(list);
    container.append(section);
  });
}

function renderPublicXmltvResult(result) {
  document.querySelector("#public-validator-summary").textContent = `${result.filename} · ${result.channels} ${landingText("landing.validator.channels", "channels")} · ${result.programmes} ${landingText("landing.validator.programmes", "programmes")}`;
  document.querySelector("#validator-format-status").textContent = result.valid ? landingText("landing.validator.passed", "Passed") : landingText("landing.validator.attention", "Needs attention");
  document.querySelector("#validator-format-counts").textContent = `${result.xmltv.critical} critical · ${result.xmltv.errors} errors`;
  document.querySelector("#validator-operations-status").textContent = result.operational_ready ? landingText("landing.validator.ready", "Ready") : landingText("landing.validator.review", "Review recommended");
  document.querySelector("#validator-operations-counts").textContent = `${result.operational.errors} errors · ${result.operational.warnings} warnings`;
  document.querySelector("#validator-profile-score").textContent = `${result.btp_profile.score}/100`;
  document.querySelector("#validator-profile-counts").textContent = `${result.btp_profile.recommendations} ${landingText("landing.validator.recommendations", "recommendations")}`;
  renderLayerIssues(result);
  publicXmltvResults.hidden = false;
  publicXmltvResults.scrollIntoView({ behavior: "smooth", block: "start" });
}

publicXmltvForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = publicXmltvFile || publicXmltvInput.files?.[0];
  if (!file) {
    publicXmltvStatus.textContent = landingText(
      "landing.validator.fileRequired",
      "Choose or drop an XMLTV file first.",
    );
    publicXmltvStatus.classList.add("is-error");
    return;
  }
  const button = publicXmltvForm.querySelector("button[type='submit']");
  button.disabled = true;
  publicXmltvStatus.classList.remove("is-error");
  publicXmltvStatus.textContent = landingText("landing.validator.validating", "Validating…");
  try {
    const body = new FormData();
    body.append("file", file);
    const response = await fetch("/api/public/xmltv/validate", { method: "POST", body });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "The XMLTV file could not be validated.");
    renderPublicXmltvResult(result);
    publicXmltvStatus.textContent = landingText("landing.validator.complete", "Validation complete.");
  } catch (error) {
    publicXmltvStatus.textContent = error.message;
    publicXmltvStatus.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#download-public-xmltv-report")?.addEventListener("click", async (event) => {
  if (!publicXmltvFile) return;
  const button = event.currentTarget;
  button.disabled = true;
  try {
    const body = new FormData();
    body.append("file", publicXmltvFile);
    body.append("language", document.documentElement.lang === "es" ? "es" : "en");
    const response = await fetch("/api/public/xmltv/report/pdf", { method: "POST", body });
    if (!response.ok) throw new Error("The report could not be generated.");
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = "btp-xmltv-validation-report.pdf";
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    publicXmltvStatus.textContent = error.message;
    publicXmltvStatus.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
});

landingMenuToggle.addEventListener("click", () => {
  const open = landingNav.classList.toggle("is-open");
  landingMenuToggle.setAttribute("aria-expanded", String(open));
  landingMenuToggle.setAttribute(
    "aria-label",
    open ? "Close navigation" : "Open navigation",
  );
});

landingNav.addEventListener("click", (event) => {
  if (!event.target.closest("a")) return;
  landingNav.classList.remove("is-open");
  landingMenuToggle.setAttribute("aria-expanded", "false");
  landingMenuToggle.setAttribute("aria-label", "Open navigation");
});

landingContactForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = landingContactForm.querySelector("button[type='submit']");
  const payload = Object.fromEntries(new FormData(landingContactForm));
  button.disabled = true;
  landingContactStatus.classList.remove("is-error");
  landingContactStatus.textContent = window.BTPi18n?.t(
    "landing.contact.sending",
    "Sending…",
  ) || "Sending…";
  try {
    const response = await fetch("/api/auth/sales-inquiries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.detail || "The request could not be sent.");
    }
    landingContactForm.reset();
    landingContactStatus.textContent = window.BTPi18n?.t(
      "landing.contact.sent",
      "Thank you. Our team will contact you shortly.",
    ) || "Thank you. Our team will contact you shortly.";
  } catch (error) {
    landingContactStatus.textContent = error.message;
    landingContactStatus.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
});
