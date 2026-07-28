const helpLauncher = document.querySelector("#help-launcher");
const helpPanel = document.querySelector("#help-panel");
const helpClose = document.querySelector("#help-close");
const helpTitle = document.querySelector("#help-title");
const helpContent = document.querySelector("#help-content");
const helpGuideSelect = document.querySelector("#help-guide-select");
const helpLanguageSelect = document.querySelector("#help-language-select");
const helpFooter = document.querySelector("#help-footer");
const helpSupportActions = document.querySelector("#help-support-actions");
const helpReportButton = document.querySelector("#help-report-button");
const helpRequestsButton = document.querySelector("#help-requests-button");
const helpSupportForm = document.querySelector("#help-support-form");
const helpSupportModule = document.querySelector("#help-support-module");
const helpSupportMessage = document.querySelector("#help-support-message");
const helpFormBack = document.querySelector("#help-form-back");
const helpRequests = document.querySelector("#help-requests");
const helpRequestsBack = document.querySelector("#help-requests-back");
const helpRequestsStatus = document.querySelector("#help-requests-status");
const helpRequestList = document.querySelector("#help-request-list");
const helpFormTitle = document.querySelector("#help-form-title");
const helpRequestsTitle = document.querySelector("#help-requests-title");
const helpCategoryLabel = document.querySelector("#help-category-label");
const helpPriorityLabel = document.querySelector("#help-priority-label");
const helpSummaryLabel = document.querySelector("#help-summary-label");
const helpDetailsLabel = document.querySelector("#help-details-label");
const helpErrorLabel = document.querySelector("#help-error-label");
const helpPrivacy = document.querySelector("#help-privacy");
const helpSubmitButton = document.querySelector("#help-submit-button");
const helpPreferenceKey = "broadcastToolPro.helpLanguage";

const helpGuides = {
  getting_started: {
    section: null,
    en: {
      title: "Getting Started",
      summary: "Choose a workflow, prepare the required source file, review the results, and download the final deliverable.",
      steps: [
        "Select the module that matches the job you need to complete.",
        "Use the supplied template when a module provides one.",
        "Review validation findings before authorizing corrections or exports.",
        "Keep downloaded reports with the related source files for auditability.",
      ],
      tip: "Your plan and add-ons determine which modules are available.",
    },
    es: {
      title: "Primeros pasos",
      summary: "Selecciona un flujo, prepara el archivo requerido, revisa los resultados y descarga el entregable final.",
      steps: [
        "Selecciona el módulo correspondiente al trabajo que necesitas realizar.",
        "Utiliza la plantilla provista cuando el módulo incluya una.",
        "Revisa los resultados antes de autorizar correcciones o exportaciones.",
        "Conserva los reportes descargados junto con sus archivos originales.",
      ],
      tip: "Tu plan y complementos determinan qué módulos están disponibles.",
    },
  },
  generator: {
    section: "generator",
    en: {
      title: "XMLTV Generator",
      summary: "Create a compliant XMLTV feed from the Broadcast Tool Pro Excel or CSV schedule template.",
      steps: [
        "Download and complete the official schedule template.",
        "Select the channel settings and upload the completed file.",
        "Validate the schedule and review suggested safe corrections.",
        "Authorize corrections when appropriate, then generate XMLTV.",
        "Optionally create a Programming Grid from the same validated EPG.",
      ],
      tip: "Do not rename the Programming sheet or template headers.",
    },
    es: {
      title: "Generador XMLTV",
      summary: "Crea un XMLTV compatible usando la plantilla Excel o CSV de Broadcast Tool Pro.",
      steps: [
        "Descarga y completa la plantilla oficial.",
        "Selecciona la configuración del canal y sube el archivo.",
        "Valida la programación y revisa las correcciones sugeridas.",
        "Autoriza las correcciones apropiadas y genera el XMLTV.",
        "Opcionalmente crea un Programming Grid desde el mismo EPG validado.",
      ],
      tip: "No cambies el nombre de la hoja Programming ni sus encabezados.",
    },
  },
  validator: {
    section: "validator",
    en: {
      title: "XMLTV Validator",
      summary: "Inspect an existing XMLTV file and produce a detailed validation report.",
      steps: [
        "Upload the XMLTV file you received or generated.",
        "Run validation and review critical findings, errors, and warnings.",
        "Inspect the affected line, element, and recommended action.",
        "Download the report in the required format.",
      ],
      tip: "A valid result confirms the checks performed; it does not guarantee acceptance by every distributor.",
    },
    es: {
      title: "Validador XMLTV",
      summary: "Inspecciona un XMLTV existente y genera un reporte detallado.",
      steps: [
        "Sube el archivo XMLTV recibido o generado.",
        "Ejecuta la validación y revisa errores críticos y advertencias.",
        "Revisa la línea, elemento y acción recomendada.",
        "Descarga el reporte en el formato necesario.",
      ],
      tip: "Un resultado válido confirma estas pruebas, pero no garantiza aceptación por todos los distribuidores.",
    },
  },
  repair: {
    section: "repair",
    en: {
      title: "XMLTV Repair",
      summary: "Preview safe XMLTV corrections before creating a repaired copy.",
      steps: [
        "Upload the XMLTV file that needs correction.",
        "Review every proposed repair before authorization.",
        "Authorize only the corrections you want applied.",
        "Download the repaired XMLTV and validate it again.",
      ],
      tip: "The original uploaded file is never overwritten.",
    },
    es: {
      title: "Reparación XMLTV",
      summary: "Previsualiza correcciones seguras antes de crear una copia reparada.",
      steps: [
        "Sube el XMLTV que necesita corrección.",
        "Revisa cada reparación propuesta antes de autorizarla.",
        "Autoriza solamente las correcciones que deseas aplicar.",
        "Descarga el XMLTV reparado y valídalo nuevamente.",
      ],
      tip: "El archivo original nunca se sobrescribe.",
    },
  },
  prelog: {
    section: "prelog",
    en: {
      title: "Pre Logs",
      summary: "Find selected assets in one or more future playlists and export their scheduled airings.",
      steps: [
        "Upload all playlists covering the requested broadcast dates.",
        "Select a prefix, exact ID, or text filter.",
        "Confirm the playlist time zone and broadcast-day range.",
        "Review every selected occurrence before export.",
        "Add optional client details and logo, then download the report.",
      ],
      tip: "The playlist filename is not used to identify its contents.",
    },
    es: {
      title: "Pre Logs",
      summary: "Localiza elementos en playlists futuras y exporta sus emisiones programadas.",
      steps: [
        "Sube todos los playlists correspondientes a las fechas solicitadas.",
        "Selecciona prefijo, ID exacto o filtro de texto.",
        "Confirma la zona horaria y el rango de días de emisión.",
        "Revisa todas las ocurrencias antes de exportar.",
        "Agrega datos opcionales y el logo, y descarga el reporte.",
      ],
      tip: "El nombre del playlist no se utiliza para identificar su contenido.",
    },
  },
  postlog: {
    section: "postlog",
    en: {
      title: "Post Logs",
      summary: "Certify the actual airings of a selected asset using one or more As-Run logs.",
      steps: [
        "Upload all As-Run files covering the certification period.",
        "Filter the exact asset, prefix, or text requested by the client.",
        "Confirm the dates, time zone, and detected occurrences.",
        "Generate one independent certification per selected asset.",
        "Add optional client details and download Excel or PDF.",
      ],
      tip: "Post Logs certify observed airings; they do not compare against an original media order.",
    },
    es: {
      title: "Post Logs",
      summary: "Certifica las emisiones reales de un elemento utilizando archivos As-Run.",
      steps: [
        "Sube todos los As-Run correspondientes al período.",
        "Filtra el elemento exacto, prefijo o texto solicitado.",
        "Confirma fechas, zona horaria y emisiones detectadas.",
        "Genera una certificación independiente por cada elemento.",
        "Agrega datos opcionales y descarga Excel o PDF.",
      ],
      tip: "Post Logs certifica emisiones observadas; no compara una orden de pauta original.",
    },
  },
  hls_validator: {
    section: "hls-validator",
    en: {
      title: "HLS Validator",
      summary: "Inspect an HLS playlist instantly or monitor it for 5, 10, or 15 minutes.",
      steps: [
        "Enter a publicly reachable HLS playlist URL.",
        "Use Validate HLS for playlist structure and current variants.",
        "Use Monitor Stream when SCTE-35 and bandwidth behavior must be observed.",
        "Wait until monitoring finishes before downloading the complete PDF.",
      ],
      tip: "A cue must occur during the selected monitoring window to appear in the report.",
    },
    es: {
      title: "Validador HLS",
      summary: "Inspecciona un playlist HLS o monitorea el stream durante 5, 10 o 15 minutos.",
      steps: [
        "Ingresa un URL HLS accesible públicamente.",
        "Usa Validate HLS para revisar estructura y variantes actuales.",
        "Usa Monitor Stream para observar SCTE-35 y comportamiento del bandwidth.",
        "Espera que termine el monitoreo antes de descargar el PDF completo.",
      ],
      tip: "El cue debe ocurrir durante el período monitoreado para aparecer en el reporte.",
    },
  },
  report_history: {
    section: "report-history",
    en: {
      title: "Report History",
      summary: "Retrieve previously generated Pre Log and Post Log deliverables.",
      steps: [
        "Refresh history to load the latest generated reports.",
        "Locate the report using its client, channel, date range, and type.",
        "Download the archived deliverable.",
      ],
      tip: "History is an operational archive and should follow the retention policy of your plan.",
    },
    es: {
      title: "Historial de reportes",
      summary: "Recupera reportes Pre Log y Post Log generados anteriormente.",
      steps: [
        "Actualiza el historial para cargar los reportes más recientes.",
        "Localiza el reporte por cliente, canal, fechas y tipo.",
        "Descarga el entregable archivado.",
      ],
      tip: "El historial es un archivo operativo sujeto a la retención de tu plan.",
    },
  },
  billing: {
    section: "billing-panel",
    en: {
      title: "Billing & Subscriptions",
      summary: "Review the organization plan, subscription status, enabled services, renewal period, and invoices.",
      steps: [
        "Confirm the active organization and plan.",
        "Review the subscription status and renewal date.",
        "Verify the plan services and enabled add-ons.",
        "Use Payment History to retrieve issued invoices.",
      ],
      tip: "Only organization Owners and Admins can access billing information.",
    },
    es: {
      title: "Facturación y suscripciones",
      summary: "Revisa el plan, estado, servicios, renovación y facturas de la organización.",
      steps: [
        "Confirma la organización y el plan activos.",
        "Revisa el estado de la suscripción y la renovación.",
        "Verifica servicios incluidos y complementos habilitados.",
        "Utiliza Payment History para recuperar facturas emitidas.",
      ],
      tip: "Solo Owners y Admins pueden acceder a la información de facturación.",
    },
  },
};

let helpCurrentGuide = "getting_started";
let helpSupportAvailable = false;

function helpTranslateSupportUi(language) {
  const spanish = language === "es";
  helpReportButton.textContent = spanish
    ? "Reportar un problema"
    : "Report a Problem";
  helpRequestsButton.textContent = spanish
    ? "Mis solicitudes"
    : "My Support Requests";
  helpFormTitle.textContent = helpReportButton.textContent;
  helpRequestsTitle.textContent = helpRequestsButton.textContent;
  helpFormBack.textContent = spanish ? "Volver" : "Back";
  helpRequestsBack.textContent = spanish ? "Volver" : "Back";
  helpCategoryLabel.textContent = spanish ? "Categoría" : "Category";
  helpPriorityLabel.textContent = spanish ? "Prioridad" : "Priority";
  helpSummaryLabel.textContent = spanish
    ? "Descripción breve"
    : "Short description";
  helpDetailsLabel.textContent = spanish
    ? "¿Qué ocurrió?"
    : "What happened?";
  helpErrorLabel.textContent = spanish
    ? "Mensaje de error exacto (Opcional)"
    : "Exact error message (Optional)";
  helpPrivacy.textContent = spanish
    ? "Los archivos operativos y datos originales no se adjuntan automáticamente."
    : "Operational files and source data are not attached automatically.";
  helpSubmitButton.textContent = spanish
    ? "Enviar solicitud"
    : "Submit Request";
  const categoryLabels = spanish
    ? {
        technical: "Problema técnico",
        validation: "Resultado de validación",
        export: "Exportación o reporte",
        billing: "Facturación",
        account: "Acceso a la cuenta",
        other: "Otro",
      }
    : {
        technical: "Technical issue",
        validation: "Validation result",
        export: "Export or report",
        billing: "Billing",
        account: "Account access",
        other: "Other",
      };
  const priorityLabels = spanish
    ? { low: "Baja", normal: "Normal", high: "Alta", urgent: "Urgente" }
    : { low: "Low", normal: "Normal", high: "High", urgent: "Urgent" };
  document.querySelectorAll("#help-category option").forEach((option) => {
    option.textContent = categoryLabels[option.value];
  });
  document.querySelectorAll("#help-priority option").forEach((option) => {
    option.textContent = priorityLabels[option.value];
  });
}

function helpShowGuideView() {
  helpSupportForm.classList.add("is-hidden");
  helpRequests.classList.add("is-hidden");
  helpContent.classList.remove("is-hidden");
  helpControlsVisible(true);
  helpSupportActions.classList.toggle("is-hidden", !helpSupportAvailable);
}

function helpControlsVisible(visible) {
  document.querySelector(".help-controls")
    .classList.toggle("is-hidden", !visible);
}

function helpRenderGuide(guideKey = helpCurrentGuide) {
  const guide = helpGuides[guideKey] || helpGuides.getting_started;
  const language = helpLanguageSelect.value;
  const content = guide[language] || guide.en;
  helpCurrentGuide = guideKey;
  helpGuideSelect.value = guideKey;
  helpTitle.textContent = content.title;
  helpFooter.textContent = language === "es"
    ? "¿Necesitas más ayuda? Contacta al administrador e incluye el módulo y el mensaje de error exacto."
    : "Need more assistance? Contact your platform administrator and include the module name and the exact error message.";
  helpTranslateSupportUi(language);
  const summary = document.createElement("p");
  summary.className = "help-summary";
  summary.textContent = content.summary;
  const list = document.createElement("ol");
  content.steps.forEach((step) => {
    const item = document.createElement("li");
    item.textContent = step;
    list.appendChild(item);
  });
  const tip = document.createElement("p");
  tip.className = "help-tip";
  tip.textContent = `${language === "es" ? "Importante" : "Important"}: ${content.tip}`;
  helpContent.replaceChildren(summary, list, tip);
  helpShowGuideView();
}

function helpGuideForViewport() {
  if (!billingPanel.classList.contains("is-hidden")) return "billing";
  let best = null;
  let bestDistance = Number.POSITIVE_INFINITY;
  Object.entries(helpGuides).forEach(([key, guide]) => {
    if (!guide.section) return;
    const section = document.getElementById(guide.section);
    if (!section || section.classList.contains("is-hidden")) return;
    const rectangle = section.getBoundingClientRect();
    const distance = Math.abs(rectangle.top - 120);
    if (rectangle.bottom > 80 && distance < bestDistance) {
      best = key;
      bestDistance = distance;
    }
  });
  return best || "getting_started";
}

function helpOpen() {
  helpPanel.classList.remove("is-hidden");
  helpLauncher.setAttribute("aria-expanded", "true");
  helpRenderGuide(helpGuideForViewport());
}

function helpDismiss() {
  helpPanel.classList.add("is-hidden");
  helpLauncher.setAttribute("aria-expanded", "false");
}

Object.entries(helpGuides).forEach(([key, guide]) => {
  const option = document.createElement("option");
  option.value = key;
  option.textContent = guide.en.title;
  helpGuideSelect.appendChild(option);
});

helpLanguageSelect.value =
  localStorage.getItem(helpPreferenceKey) || "en";
helpLauncher.addEventListener("click", () => {
  if (helpPanel.classList.contains("is-hidden")) helpOpen();
  else helpDismiss();
});
helpClose.addEventListener("click", helpDismiss);
helpGuideSelect.addEventListener("change", () => {
  helpRenderGuide(helpGuideSelect.value);
});
helpLanguageSelect.addEventListener("change", () => {
  localStorage.setItem(helpPreferenceKey, helpLanguageSelect.value);
  helpRenderGuide();
});

helpReportButton.addEventListener("click", () => {
  helpContent.classList.add("is-hidden");
  helpSupportActions.classList.add("is-hidden");
  helpRequests.classList.add("is-hidden");
  helpControlsVisible(false);
  helpSupportForm.classList.remove("is-hidden");
  helpSupportModule.value = helpGuides[helpCurrentGuide]?.en.title
    || "Platform";
  helpSupportMessage.textContent = "";
  helpSupportMessage.classList.remove("is-error");
});

helpFormBack.addEventListener("click", helpShowGuideView);
helpRequestsBack.addEventListener("click", helpShowGuideView);

helpSupportForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = helpSupportForm.querySelector("button[type='submit']");
  const payload = Object.fromEntries(new FormData(helpSupportForm).entries());
  helpSupportMessage.textContent = "";
  helpSupportMessage.classList.remove("is-error");
  button.disabled = true;
  try {
    const result = await authRequest("/api/support/requests", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    helpSupportForm.reset();
    helpSupportModule.value = helpGuides[helpCurrentGuide]?.en.title
      || "Platform";
    helpSupportMessage.textContent =
      `${result.message} Ticket: ${result.id}`;
  } catch (error) {
    helpSupportMessage.textContent = error.message;
    helpSupportMessage.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
});

async function helpLoadRequests() {
  helpContent.classList.add("is-hidden");
  helpSupportActions.classList.add("is-hidden");
  helpSupportForm.classList.add("is-hidden");
  helpControlsVisible(false);
  helpRequests.classList.remove("is-hidden");
  helpRequestsStatus.textContent = "Loading requests…";
  helpRequestList.replaceChildren();
  try {
    const payload = await authRequest("/api/support/requests");
    const requests = payload.requests || [];
    helpRequestsStatus.textContent = requests.length
      ? `${requests.length} support request(s).`
      : "No support requests have been submitted.";
    requests.forEach((request) => {
      const card = document.createElement("article");
      const heading = document.createElement("div");
      const title = document.createElement("strong");
      const status = document.createElement("span");
      const detail = document.createElement("p");
      title.textContent = request.summary;
      status.textContent = request.status;
      detail.textContent = `${request.id} · ${request.module} · ${
        new Date(request.created_at).toLocaleDateString()
      }`;
      heading.append(title, status);
      card.append(heading, detail);
      helpRequestList.appendChild(card);
    });
  } catch (error) {
    helpRequestsStatus.textContent = error.message;
  }
}

helpRequestsButton.addEventListener("click", helpLoadRequests);
window.addEventListener("btp:identity", (event) => {
  helpSupportAvailable = Boolean(event.detail?.user);
  helpSupportActions.classList.toggle(
    "is-hidden",
    !helpSupportAvailable || helpContent.classList.contains("is-hidden"),
  );
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") helpDismiss();
});
