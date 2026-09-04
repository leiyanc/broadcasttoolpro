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
const helpRequestDetail = document.querySelector("#help-request-detail");
const helpRequestDetailTitle = document.querySelector(
  "#help-request-detail-title",
);
const helpRequestDetailBack = document.querySelector(
  "#help-request-detail-back",
);
const helpRequestDetailBody = document.querySelector(
  "#help-request-detail-body",
);
const helpRequestThread = document.querySelector("#help-request-thread");
const helpRequestReplyForm = document.querySelector(
  "#help-request-reply-form",
);
const helpReopenRequest = document.querySelector("#help-reopen-request");
const helpRequestDetailMessage = document.querySelector(
  "#help-request-detail-message",
);
const helpFormTitle = document.querySelector("#help-form-title");
const helpRequestsTitle = document.querySelector("#help-requests-title");
const helpCategoryLabel = document.querySelector("#help-category-label");
const helpPriorityLabel = document.querySelector("#help-priority-label");
const helpSummaryLabel = document.querySelector("#help-summary-label");
const helpDetailsLabel = document.querySelector("#help-details-label");
const helpErrorLabel = document.querySelector("#help-error-label");
const helpErrorField = document.querySelector("#help-error-field");
const helpCategory = document.querySelector("#help-category");
const helpTopicContact = document.querySelector("#help-topic-contact");
const helpRequestTypeField = document.querySelector(
  "#help-request-type-field",
);
const helpRequestTypeLabel = document.querySelector(
  "#help-request-type-label",
);
const helpRequestType = document.querySelector("#help-request-type");
const helpPrivacy = document.querySelector("#help-privacy");
const helpSubmitButton = document.querySelector("#help-submit-button");

function helpIsSpanish() {
  return helpLanguageSelect.value === "es";
}

function helpUiText(english, spanish) {
  return helpIsSpanish() ? spanish : english;
}

function helpUpdateTopicContact() {
  const contacts = {
    billing: ["Billing", "Facturación", "billing@broadcasttoolpro.com"],
    privacy: [
      "Security and privacy",
      "Seguridad y privacidad",
      "security@broadcasttoolpro.com",
    ],
  };
  const [english, spanish, email] = contacts[helpCategory.value] || [
    "Customer support",
    "Soporte al cliente",
    "support@broadcasttoolpro.com",
  ];
  helpTopicContact.textContent = `${helpUiText(english, spanish)}: ${email}`;
}

function helpStatusLabel(status) {
  const labels = helpIsSpanish()
    ? {
        open: "Abierta",
        in_progress: "En progreso",
        waiting_customer: "Esperando respuesta",
        resolved: "Resuelta",
        closed: "Cerrada",
      }
    : {
        open: "Open",
        in_progress: "In progress",
        waiting_customer: "Waiting for customer",
        resolved: "Resolved",
        closed: "Closed",
      };
  return labels[status] || status;
}

function updateHelpSupportFields() {
  const spanish = helpLanguageSelect.value === "es";
  const category = helpCategory.value;
  const isBilling = category === "billing";
  const isAccount = category === "account";
  const isPrivacy = category === "privacy";
  const showError = ["technical", "validation", "export"].includes(category);

  helpSupportModule.value = isPrivacy
    ? "Account & Privacy"
    : (helpGuides[helpCurrentGuide]?.en.title || "Platform");

  helpFormTitle.textContent = isBilling
    ? (spanish ? "Solicitud de facturación" : "Billing Request")
    : (isAccount
      ? (spanish ? "Solicitud de cuenta" : "Account Request")
      : (isPrivacy
        ? (spanish ? "Solicitud de privacidad y datos" : "Privacy & Data Request")
        : (spanish ? "Reportar un problema" : "Report a Problem")));
  helpDetailsLabel.textContent = isBilling || isAccount || isPrivacy
    ? (spanish ? "Detalles de la solicitud" : "Request details")
    : (spanish ? "¿Qué ocurrió?" : "What happened?");
  helpErrorField.classList.toggle("is-hidden", !showError);
  helpRequestTypeField.classList.toggle("is-hidden", !isPrivacy);
  helpRequestType.required = isPrivacy;
  helpRequestType.disabled = !isPrivacy;
  if (!showError) helpSupportForm.elements.error_message.value = "";
}

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
      summary: "Create a compliant XMLTV file from the Broadcast Tool Pro Excel or CSV schedule template.",
      steps: [
        "Download and complete the official schedule template.",
        "Select the registered channel and enter its name in the required Channel column on every programme row.",
        "Confirm the channel's time zone once in Channel Settings. Enter schedule times in the channel's local time; Broadcast Tool Pro uses the saved time zone automatically when exporting XMLTV.",
        "Confirm the channel's primary language in Channel Settings. Choose a major language or regional/script variant, such as Simplified or Traditional Chinese. Broadcast Tool Pro applies it automatically to the XMLTV.",
        "If the channel uses ratings, select its optional Rating System once in Channel Settings. Leave it as None when ratings are not used.",
        "Parental Rating is optional free text in the template. Enter the official value, such as TV-PG for VCHIP, then copy, paste, or drag repeated values across programme rows.",
        "Validate the schedule and review suggested safe corrections.",
        "Authorize corrections when appropriate, then generate XMLTV.",
        "Optionally create a Programming Grid from the same validated EPG.",
      ],
      tip: "Time Zone, Primary Language, and the optional Rating System come from Channel Settings. The schedule template does not need a time-zone column, and no US or regional rating system is assumed.",
    },
    es: {
      title: "Generador XMLTV",
      summary: "Crea un XMLTV compatible usando la plantilla Excel o CSV de Broadcast Tool Pro.",
      steps: [
        "Descarga y completa la plantilla oficial.",
        "Selecciona el canal registrado e ingresa su nombre en la columna obligatoria Channel de cada fila de programación.",
        "Confirma una sola vez la zona horaria del canal en Configuración del canal. Ingresa la programación en la hora local del canal; Broadcast Tool Pro utiliza automáticamente la zona guardada al exportar el XMLTV.",
        "Confirma el idioma principal del canal en Configuración del canal. Elige un idioma principal o una variante regional/de escritura, como chino simplificado o tradicional. Broadcast Tool Pro lo aplica automáticamente al XMLTV.",
        "Si el canal utiliza clasificaciones, selecciona una sola vez su Rating System opcional en Configuración del canal. Déjalo en Ninguno cuando no se utilicen clasificaciones.",
        "Parental Rating es texto libre opcional en la plantilla. Escribe el valor oficial, como TV-PG para VCHIP, y copia, pega o arrastra los valores repetidos entre las filas.",
        "Valida la programación y revisa las correcciones sugeridas.",
        "Autoriza las correcciones apropiadas y genera el XMLTV.",
        "Opcionalmente crea un Programming Grid desde el mismo EPG validado.",
      ],
      tip: "Zona horaria, Primary Language y el Rating System opcional provienen de Configuración del canal. La plantilla no necesita una columna de zona horaria y no se presume ningún sistema estadounidense ni regional.",
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
      summary: "Manage the organization subscription, licensed channels, renewal period, enabled services, and invoices.",
      steps: [
        "Confirm the active organization, plan, subscription status, and renewal date.",
        "Review the registered channels. Every plan includes one channel; additional channels use the rate shown for that plan.",
        "To add a channel, enter its name and review Stripe's prorated charge before confirming. Broadcast Tool Pro creates its internal identity automatically, and the channel joins the organization's existing billing cycle.",
        "To remove an additional channel, review the renewal adjustment and confirm removal at period end. The channel stays active until that date and no mid-cycle credit is issued.",
        "Cancel a scheduled removal before renewal if the organization decides to keep the channel.",
        "Use Payment History to retrieve issued invoices.",
      ],
      tip: "Only Owners and Admins can manage billing. The last active channel cannot be removed, and removed-channel reports and history remain retained under BTP policy.",
    },
    es: {
      title: "Facturación y suscripciones",
      summary: "Administra la suscripción, canales licenciados, renovación, servicios y facturas de la organización.",
      steps: [
        "Confirma la organización, el plan, el estado de la suscripción y la fecha de renovación.",
        "Revisa los canales registrados. Cada plan incluye un canal; los canales adicionales usan la tarifa indicada para ese plan.",
        "Para agregar un canal, registra su identidad y revisa el cargo prorrateado de Stripe antes de confirmar. El canal se integra al ciclo existente de la organización.",
        "Para retirar un canal adicional, revisa el ajuste y confirma el retiro al final del período. El canal sigue activo hasta esa fecha y no recibe crédito a mitad de ciclo.",
        "Cancela un retiro programado antes de la renovación si la organización decide conservar el canal.",
        "Utiliza el historial de pagos para recuperar facturas emitidas.",
      ],
      tip: "Solo Owners y Admins administran la facturación. No puede retirarse el último canal activo, y el historial y los reportes del canal retirado se conservan según la política de BTP.",
    },
  },
  privacy: {
    section: null,
    en: {
      title: "Privacy & Data Requests",
      summary: "Request access, correction, export, deletion, or clarification about retention of eligible account information.",
      steps: [
        "Choose Report a Problem from this guide.",
        "Select the privacy request type that matches the action you need.",
        "Describe the affected account or organization information without including passwords or confidential source files.",
        "Follow the request from My Support Requests while the administrator verifies ownership and scope.",
      ],
      tip: "Deletion applies only to eligible data and requires identity, authorization, retention, and legal review.",
    },
    es: {
      title: "Privacidad y solicitudes de datos",
      summary: "Solicita acceso, corrección, exportación, eliminación o información sobre la retención de datos elegibles de la cuenta.",
      steps: [
        "Selecciona Reportar un problema desde esta guía.",
        "Elige el tipo de solicitud de privacidad correspondiente.",
        "Describe los datos de cuenta u organización afectados sin incluir contraseñas ni archivos confidenciales.",
        "Sigue la solicitud desde Mis solicitudes mientras se verifican la identidad y el alcance.",
      ],
      tip: "La eliminación solo aplica a datos elegibles y requiere revisar identidad, autorización, retención y obligaciones legales.",
    },
  },
};

let helpCurrentGuide = "getting_started";
let helpSupportAvailable = false;
let helpCurrentRequestId = null;

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
  helpRequestTypeLabel.textContent = spanish
    ? "Tipo de solicitud"
    : "Request Type";
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
        privacy: "Privacidad o solicitud de datos",
        other: "Otro",
      }
    : {
        technical: "Technical issue",
        validation: "Validation result",
        export: "Export or report",
        billing: "Billing",
        account: "Account access",
        privacy: "Privacy or data request",
        other: "Other",
      };
  const priorityLabels = spanish
    ? { low: "Baja", normal: "Normal", high: "Alta", urgent: "Urgente" }
    : { low: "Low", normal: "Normal", high: "High", urgent: "Urgent" };
  const requestTypeLabels = spanish
    ? {
        access: "Acceder a mis datos",
        correction: "Corregir mis datos",
        export: "Exportar mis datos",
        deletion: "Eliminar datos elegibles",
        retention: "Consulta sobre retención",
      }
    : {
        access: "Access my data",
        correction: "Correct my data",
        export: "Export my data",
        deletion: "Delete eligible data",
        retention: "Retention question",
      };
  document.querySelectorAll("#help-category option").forEach((option) => {
    option.textContent = categoryLabels[option.value];
  });
  document.querySelectorAll("#help-priority option").forEach((option) => {
    option.textContent = priorityLabels[option.value];
  });
  document.querySelectorAll("#help-request-type option").forEach((option) => {
    option.textContent = requestTypeLabels[option.value];
  });
  helpUpdateTopicContact();
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
  helpFooter.textContent = guideKey === "privacy"
    ? (language === "es"
      ? "Las solicitudes se revisan antes de exportar o eliminar información."
      : "Requests are reviewed before any information is exported or deleted.")
    : (language === "es"
      ? "¿Necesitas más ayuda? Contacta al administrador e incluye el módulo y el mensaje de error exacto."
      : "Need more assistance? Contact your platform administrator and include the module name and the exact error message.");
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

helpLanguageSelect.value = window.BTPi18n?.getLanguage?.() || "en";
helpCategory.addEventListener("change", helpUpdateTopicContact);
helpLauncher.addEventListener("click", () => {
  if (helpPanel.classList.contains("is-hidden")) helpOpen();
  else helpDismiss();
});
window.addEventListener("btp:open-support", (event) => {
  helpOpen();
  helpCurrentGuide = "billing";
  helpRenderGuide("billing");
  helpReportButton.click();
  const detail = event.detail || {};
  helpCategory.value = detail.category || "billing";
  updateHelpSupportFields();
  helpSupportForm.elements.summary.value = detail.summary || "";
  helpSupportForm.elements.details.value = detail.details || "";
});
helpClose.addEventListener("click", helpDismiss);
helpGuideSelect.addEventListener("change", () => {
  helpRenderGuide(helpGuideSelect.value);
});
helpLanguageSelect.addEventListener("change", () => {
  if (window.BTPi18n?.setLanguage) {
    window.BTPi18n.setLanguage(helpLanguageSelect.value);
  } else {
    helpRenderGuide();
  }
});
window.addEventListener("btp:languagechange", (event) => {
  helpLanguageSelect.value = event.detail?.language || "en";
  Object.entries(helpGuides).forEach(([key, guide]) => {
    const option = helpGuideSelect.querySelector(`option[value="${key}"]`);
    if (option) option.textContent = guide[helpLanguageSelect.value]?.title
      || guide.en.title;
  });
  helpRenderGuide();
});
helpCategory.addEventListener("change", updateHelpSupportFields);

helpReportButton.addEventListener("click", () => {
  helpContent.classList.add("is-hidden");
  helpSupportActions.classList.add("is-hidden");
  helpRequests.classList.add("is-hidden");
  helpControlsVisible(false);
  helpSupportForm.classList.remove("is-hidden");
  helpSupportModule.value = helpGuides[helpCurrentGuide]?.en.title
    || "Platform";
  if (helpCurrentGuide === "privacy") {
    helpCategory.value = "privacy";
  } else if (helpCategory.value === "privacy") {
    helpCategory.value = "technical";
  }
  helpSupportMessage.textContent = "";
  helpSupportMessage.classList.remove("is-error");
  updateHelpSupportFields();
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
    updateHelpSupportFields();
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
  helpRequestsStatus.textContent = helpUiText(
    "Loading requests…",
    "Cargando solicitudes…",
  );
  helpRequestList.replaceChildren();
  helpRequestDetail.classList.add("is-hidden");
  helpRequestList.classList.remove("is-hidden");
  try {
    const payload = await authRequest("/api/support/requests");
    const requests = payload.requests || [];
    helpRequestsStatus.textContent = requests.length
      ? helpUiText(
        `${requests.length} support request(s).`,
        `${requests.length} solicitud(es) de soporte.`,
      )
      : helpUiText(
        "No support requests have been submitted.",
        "No se han enviado solicitudes de soporte.",
      );
    requests.forEach((request) => {
      const card = document.createElement("article");
      const heading = document.createElement("div");
      const title = document.createElement("strong");
      const status = document.createElement("span");
      const detail = document.createElement("p");
      title.textContent = request.summary;
      status.textContent = helpStatusLabel(request.status);
      detail.textContent = `${request.id} · ${request.module} · ${
        new Date(request.created_at).toLocaleDateString()
      }`;
      heading.append(title, status);
      card.append(heading, detail);
      card.tabIndex = 0;
      card.setAttribute("role", "button");
      card.setAttribute("aria-label", helpUiText(
        `Open ${request.id}`,
        `Abrir ${request.id}`,
      ));
      card.addEventListener("click", () => {
        helpOpenRequest(request.id);
      });
      card.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          helpOpenRequest(request.id);
        }
      });
      helpRequestList.appendChild(card);
    });
  } catch (error) {
    helpRequestsStatus.textContent = error.message;
  }
}

function helpThreadMessage(author, message, createdAt) {
  const item = document.createElement("article");
  const heading = document.createElement("div");
  const strong = document.createElement("strong");
  const small = document.createElement("small");
  const paragraph = document.createElement("p");
  strong.textContent = author || helpUiText("Support", "Soporte");
  small.textContent = new Date(createdAt).toLocaleString();
  paragraph.textContent = message;
  heading.append(strong, small);
  item.append(heading, paragraph);
  return item;
}

async function helpOpenRequest(incidentId) {
  helpCurrentRequestId = incidentId;
  helpRequestList.classList.add("is-hidden");
  helpRequestDetail.classList.remove("is-hidden");
  helpRequestDetailMessage.textContent = helpUiText(
    "Loading request…",
    "Cargando solicitud…",
  );
  try {
    const payload = await authRequest(
      `/api/support/requests/${incidentId}`,
    );
    const incident = payload.incident;
    helpRequestDetailTitle.textContent =
      `${incident.id} · ${incident.summary}`;
    helpRequestDetailBody.replaceChildren(
      helpThreadMessage(
        helpUiText("Original request", "Solicitud original"),
        incident.details,
        incident.created_at,
      ),
    );
    if (incident.error_message) {
      helpRequestDetailBody.appendChild(
        helpThreadMessage(
          helpUiText("Exact error message", "Mensaje de error exacto"),
          incident.error_message,
          incident.created_at,
        ),
      );
    }
    if (incident.resolution) {
      helpRequestDetailBody.appendChild(
        helpThreadMessage(
          helpUiText("Resolution", "Resolución"),
          incident.resolution,
          incident.resolved_at,
        ),
      );
    }
    helpRequestThread.replaceChildren();
    payload.messages.forEach((message) => {
      helpRequestThread.appendChild(helpThreadMessage(
        message.author_name,
        message.message,
        message.created_at,
      ));
    });
    if (!payload.messages.length) {
      helpRequestThread.textContent = helpUiText(
        "No replies yet.",
        "Aún no hay respuestas.",
      );
    }
    helpReopenRequest.classList.toggle(
      "is-hidden",
      incident.status !== "resolved",
    );
    helpRequestReplyForm.classList.toggle(
      "is-hidden",
      incident.status === "resolved",
    );
    helpRequestDetailMessage.textContent =
      helpUiText(
        `Status: ${helpStatusLabel(incident.status)}`,
        `Estado: ${helpStatusLabel(incident.status)}`,
      );
  } catch (error) {
    helpRequestDetailMessage.textContent = error.message;
    helpRequestDetailMessage.classList.add("is-error");
  }
}

helpRequestDetailBack.addEventListener("click", helpLoadRequests);

helpRequestReplyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!helpCurrentRequestId) return;
  const button = helpRequestReplyForm.querySelector(
    "button[type='submit']",
  );
  const message = new FormData(helpRequestReplyForm).get("message");
  button.disabled = true;
  try {
    await authRequest(
      `/api/support/requests/${helpCurrentRequestId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ message }),
      },
    );
    helpRequestReplyForm.reset();
    await helpOpenRequest(helpCurrentRequestId);
  } catch (error) {
    helpRequestDetailMessage.textContent = error.message;
    helpRequestDetailMessage.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
});

helpReopenRequest.addEventListener("click", async () => {
  if (!helpCurrentRequestId) return;
  helpReopenRequest.disabled = true;
  try {
    await authRequest(
      `/api/support/requests/${helpCurrentRequestId}/reopen`,
      { method: "POST" },
    );
    await helpOpenRequest(helpCurrentRequestId);
  } catch (error) {
    helpRequestDetailMessage.textContent = error.message;
    helpRequestDetailMessage.classList.add("is-error");
  } finally {
    helpReopenRequest.disabled = false;
  }
});

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
