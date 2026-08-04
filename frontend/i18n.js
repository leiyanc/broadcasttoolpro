(() => {
  const STORAGE_KEY = "broadcastToolPro.language";
  const SUPPORTED = new Set(["en", "es"]);
  const dictionaries = {
    en: {
      "language.label": "Language",
      "header.status": "All Systems Operational",
      "landing.nav.platform": "Platform",
      "landing.nav.products": "Products",
      "landing.nav.operations": "Operations",
      "landing.nav.pricing": "Pricing",
      "landing.nav.roadmap": "Roadmap",
      "landing.signIn": "Sign In",
      "landing.requestAccess": "Request Access",
      "landing.hero.title": "Every broadcast workflow. One operating layer.",
      "landing.hero.copy": "Automate programming, traffic, XMLTV, stream validation, monitoring, and reporting without stitching together spreadsheets and scripts.",
      "landing.hero.explore": "Explore the Platform",
      "landing.hero.trial": "Start Free Trial",
      "landing.products.title": "Built around the work broadcasters actually do.",
      "landing.products.copy": "Specialized tools share one secure workspace, one operating model, and one consistent path from source file to final deliverable.",
      "auth.welcome": "Welcome to Broadcast Tool Pro.",
      "auth.welcomeCopy": "Sign in to access your organization's channels, workflows, reports, and settings.",
      "auth.signIn": "Sign In",
      "auth.requestAccess": "Request Access",
      "auth.freeTrial": "Free Trial",
      "auth.accountLogin": "ACCOUNT LOGIN",
      "auth.signInCopy": "Use the account assigned to your organization.",
      "auth.email": "Email Address",
      "auth.password": "Password",
      "auth.remember": "Remember me",
      "auth.rememberCopy": "Keep this account signed in for 30 days.",
      "auth.forgot": "Forgot your password?",
      "auth.paidAccess": "PAID ACCOUNT ACCESS",
      "auth.requestCopy": "Tell us who you are. We will review your workflow and assign a Professional or Enterprise account separately from the free trial.",
      "auth.organization": "Organization Name",
      "auth.name": "Your Name",
      "auth.goal": "What would you like to accomplish? (Optional)",
      "auth.goalPlaceholder": "Channels, workflows, formats, or operational needs",
      "auth.submitRequest": "Submit Access Request",
      "auth.tryTrial": "Prefer to evaluate first? Start a 7-Day Free Trial",
      "home.desk": "OPERATIONS DESK",
      "home.programming": "Programming",
      "home.traffic": "Traffic",
      "home.streaming": "Streaming QC",
      "home.reports": "Reports",
      "home.title": "Control every broadcast workflow.",
      "home.copy": "One accountable workspace for programming, traffic, validation, monitoring, and operational reporting.",
      "home.secure": "Secure workspace",
      "home.roles": "Role-based access",
      "home.audit": "Audit-ready exports",
      "module.generator.copy": "Create compliant XMLTV files",
      "module.validator.copy": "Inspect syntax and schedule integrity",
      "module.repair.copy": "Apply controlled, traceable corrections",
      "module.prelog.copy": "Select and document planned airings",
      "module.postlog.copy": "Certify broadcast occurrences",
      "module.hls.copy": "Validate stream delivery and signals",
      "common.english": "English",
      "common.spanish": "Spanish",
      "generator.eyebrow": "XMLTV GENERATOR",
      "generator.title": "Create XMLTV File",
      "generator.template.download": "Download Template",
      "generator.template.excelCopy": "Recommended · Includes instructions and examples",
      "generator.template.csvCopy": "Headers only",
      "generator.channelName": "Channel Name",
      "generator.channelId": "Channel ID",
      "generator.timezone": "Channel Time Zone",
      "generator.primaryLanguage": "Primary Language",
      "generator.originalLanguage": "Original Language",
      "generator.ratingSystem": "Rating System",
      "generator.timestampFormat": "Timestamp Format",
      "generator.timestampIso": "ISO 8601 — Broad Compatibility",
      "generator.timestampCompact": "XMLTV Compact",
      "generator.dropTitle": "Drop your schedule here",
      "generator.dropCopy": "or click to choose an .xlsx or .csv file",
      "generator.authorize": "Authorize Suggested Corrections",
      "generator.authorizeCopy": "Allow Broadcast Tool Pro to apply safe corrections before generating the XMLTV file.",
      "generator.validate": "Validate Schedule",
      "generator.generate": "Generate XMLTV",
      "generator.resultReady": "Schedule Ready",
      "generator.guidanceTitle": "Need a compatible schedule?",
      "generator.guidanceCopy": "Start with the official Broadcast Tool Pro template to avoid column, sheet, date, and formatting errors.",
      "generator.guidanceExcel": "Download Excel Template",
      "generator.guidanceCsv": "Download CSV Template",
      "preview.eyebrow": "EPG PREVIEW",
      "preview.title": "Schedule Timeline",
      "preview.broadcastDate": "Broadcast Date",
      "preview.allDates": "All dates",
      "preview.search": "Search",
      "preview.searchPlaceholder": "Title, episode, genre…",
      "preview.date": "Date",
      "preview.start": "Start",
      "preview.end": "End",
      "preview.duration": "Duration",
      "preview.programme": "Programme",
      "preview.episode": "Episode",
      "preview.genre": "Genre",
      "preview.rating": "Rating",
      "preview.flags": "Flags",
      "grid.eyebrow": "OPTIONAL PDF EXPORT",
      "grid.title": "Programming Grid",
      "grid.copy": "Create one visual schedule page per week from this validated EPG. The PDF is generated only when requested.",
      "grid.logo": "Channel Logo (Optional PNG or JPG)",
      "grid.download": "Download Programming Grid",
      "generator.fileReady": "{size} KB — ready to validate",
      "generator.validating": "Validating…",
      "generator.generating": "Generating…",
      "generator.creatingPdf": "Creating PDF…",
      "generator.serverIncomplete": "The server returned an incomplete validation response.",
      "generator.serverProcessError": "The server could not process the schedule.",
      "generator.serverGenerateError": "The server could not generate the XMLTV file.",
      "generator.readyReview": "Schedule ready for review",
      "generator.readyGenerate": "Schedule ready to generate",
      "generator.needsAttention": "Schedule needs attention",
      "generator.validReview": "{count} programmes are valid. Review and authorize {fixes} suggested corrections.",
      "generator.importSuccess": "{count} programmes were imported successfully.",
      "generator.correctBlocking": "Correct the blocking issues before generating XMLTV.",
      "generator.metricScore": "Score {score}/100",
      "generator.metricCritical": "{count} Critical",
      "generator.metricErrors": "{count} Errors",
      "generator.metricWarnings": "{count} Warnings",
      "generator.metricFixes": "{count} Suggested fixes",
      "generator.issueRow": "row {row}",
      "generator.unknownIssue": "Unknown issue",
      "generator.suggested": "Suggested: {count} × {message}",
      "generator.correction": "Correction",
      "generator.applyFixes": "Apply {count} safe corrections only to the generated XMLTV.",
      "generator.generated": "XMLTV generated",
      "generator.downloadSuccess": "{filename} was downloaded successfully.",
      "preview.calculated": "Calculated",
      "preview.live": "Live",
      "preview.new": "New",
      "preview.premiere": "Premiere",
      "preview.metricProgrammes": "{count} Programmes",
      "preview.metricDates": "{count} Dates",
      "preview.metricGenres": "{count} Genres",
      "preview.showingFirst": "Showing the first {visible} of {total} programmes.",
      "preview.shown": "{count} programme(s) shown.",
      "preview.noMatches": "No programmes match the selected preview filters.",
      "preview.summary": "Previewing {count} programmes in {timezone}.",
      "grid.validateFirst": "Validate the EPG before creating the Programming Grid.",
      "grid.createError": "The Programming Grid could not be created.",
      "grid.serverError": "The server could not create the Programming Grid.",
    },
    es: {
      "language.label": "Idioma",
      "header.status": "Todos los sistemas operativos",
      "landing.nav.platform": "Plataforma",
      "landing.nav.products": "Productos",
      "landing.nav.operations": "Operaciones",
      "landing.nav.pricing": "Precios",
      "landing.nav.roadmap": "Hoja de ruta",
      "landing.signIn": "Iniciar sesión",
      "landing.requestAccess": "Solicitar acceso",
      "landing.hero.title": "Todos los flujos de broadcast. Una sola plataforma.",
      "landing.hero.copy": "Automatiza programación, tráfico, XMLTV, validación de streams, monitoreo y reportes sin depender de hojas de cálculo y scripts desconectados.",
      "landing.hero.explore": "Explorar la plataforma",
      "landing.hero.trial": "Comenzar prueba gratis",
      "landing.products.title": "Diseñado para el trabajo real de los broadcasters.",
      "landing.products.copy": "Herramientas especializadas comparten un espacio seguro, un mismo modelo operativo y un proceso consistente desde el archivo fuente hasta la entrega final.",
      "auth.welcome": "Bienvenido a Broadcast Tool Pro.",
      "auth.welcomeCopy": "Inicia sesión para acceder a los canales, flujos, reportes y ajustes de tu organización.",
      "auth.signIn": "Iniciar sesión",
      "auth.requestAccess": "Solicitar acceso",
      "auth.freeTrial": "Prueba gratis",
      "auth.accountLogin": "ACCESO A LA CUENTA",
      "auth.signInCopy": "Usa la cuenta asignada a tu organización.",
      "auth.email": "Correo electrónico",
      "auth.password": "Contraseña",
      "auth.remember": "Recordarme",
      "auth.rememberCopy": "Mantener esta cuenta conectada durante 30 días.",
      "auth.forgot": "¿Olvidaste tu contraseña?",
      "auth.paidAccess": "ACCESO A CUENTA DE PAGO",
      "auth.requestCopy": "Cuéntanos quién eres. Revisaremos tu flujo de trabajo y asignaremos una cuenta Professional o Enterprise separada de la prueba gratis.",
      "auth.organization": "Nombre de la organización",
      "auth.name": "Tu nombre",
      "auth.goal": "¿Qué deseas lograr? (Opcional)",
      "auth.goalPlaceholder": "Canales, flujos, formatos o necesidades operativas",
      "auth.submitRequest": "Enviar solicitud de acceso",
      "auth.tryTrial": "¿Prefieres evaluar primero? Comienza una prueba gratis de 7 días",
      "home.desk": "CENTRO DE OPERACIONES",
      "home.programming": "Programación",
      "home.traffic": "Tráfico",
      "home.streaming": "Control de streaming",
      "home.reports": "Reportes",
      "home.title": "Controla todos los flujos de broadcast.",
      "home.copy": "Un espacio centralizado para programación, tráfico, validación, monitoreo y reportes operativos.",
      "home.secure": "Espacio seguro",
      "home.roles": "Acceso por roles",
      "home.audit": "Exportaciones auditables",
      "module.generator.copy": "Crea archivos XMLTV compatibles",
      "module.validator.copy": "Inspecciona la sintaxis y la integridad de la programación",
      "module.repair.copy": "Aplica correcciones controladas y trazables",
      "module.prelog.copy": "Selecciona y documenta emisiones planificadas",
      "module.postlog.copy": "Certifica emisiones reales",
      "module.hls.copy": "Valida la distribución y las señales del stream",
      "common.english": "Inglés",
      "common.spanish": "Español",
      "generator.eyebrow": "GENERADOR XMLTV",
      "generator.title": "Crear archivo XMLTV",
      "generator.template.download": "Descargar plantilla",
      "generator.template.excelCopy": "Recomendada · Incluye instrucciones y ejemplos",
      "generator.template.csvCopy": "Solo encabezados",
      "generator.channelName": "Nombre del canal",
      "generator.channelId": "ID del canal",
      "generator.timezone": "Zona horaria del canal",
      "generator.primaryLanguage": "Idioma principal",
      "generator.originalLanguage": "Idioma original",
      "generator.ratingSystem": "Sistema de clasificación",
      "generator.timestampFormat": "Formato de fecha y hora",
      "generator.timestampIso": "ISO 8601 — Amplia compatibilidad",
      "generator.timestampCompact": "XMLTV compacto",
      "generator.dropTitle": "Arrastra tu programación aquí",
      "generator.dropCopy": "o haz clic para elegir un archivo .xlsx o .csv",
      "generator.authorize": "Autorizar correcciones sugeridas",
      "generator.authorizeCopy": "Permite que Broadcast Tool Pro aplique correcciones seguras antes de generar el archivo XMLTV.",
      "generator.validate": "Validar programación",
      "generator.generate": "Generar XMLTV",
      "generator.resultReady": "Programación lista",
      "generator.guidanceTitle": "¿Necesitas una programación compatible?",
      "generator.guidanceCopy": "Usa la plantilla oficial de Broadcast Tool Pro para evitar errores de columnas, hojas, fechas y formato.",
      "generator.guidanceExcel": "Descargar plantilla Excel",
      "generator.guidanceCsv": "Descargar plantilla CSV",
      "preview.eyebrow": "VISTA PREVIA DEL EPG",
      "preview.title": "Línea de tiempo de programación",
      "preview.broadcastDate": "Fecha de emisión",
      "preview.allDates": "Todas las fechas",
      "preview.search": "Buscar",
      "preview.searchPlaceholder": "Título, episodio, género…",
      "preview.date": "Fecha",
      "preview.start": "Inicio",
      "preview.end": "Fin",
      "preview.duration": "Duración",
      "preview.programme": "Programa",
      "preview.episode": "Episodio",
      "preview.genre": "Género",
      "preview.rating": "Clasificación",
      "preview.flags": "Indicadores",
      "grid.eyebrow": "EXPORTACIÓN PDF OPCIONAL",
      "grid.title": "Parrilla de programación",
      "grid.copy": "Crea una página visual de programación por semana desde este EPG validado. El PDF se genera únicamente cuando lo solicitas.",
      "grid.logo": "Logo del canal (PNG o JPG opcional)",
      "grid.download": "Descargar parrilla de programación",
      "generator.fileReady": "{size} KB — listo para validar",
      "generator.validating": "Validando…",
      "generator.generating": "Generando…",
      "generator.creatingPdf": "Creando PDF…",
      "generator.serverIncomplete": "El servidor devolvió una respuesta de validación incompleta.",
      "generator.serverProcessError": "El servidor no pudo procesar la programación.",
      "generator.serverGenerateError": "El servidor no pudo generar el archivo XMLTV.",
      "generator.readyReview": "Programación lista para revisión",
      "generator.readyGenerate": "Programación lista para generar",
      "generator.needsAttention": "La programación requiere atención",
      "generator.validReview": "{count} programas son válidos. Revisa y autoriza {fixes} correcciones sugeridas.",
      "generator.importSuccess": "Se importaron correctamente {count} programas.",
      "generator.correctBlocking": "Corrige los problemas bloqueantes antes de generar el XMLTV.",
      "generator.metricScore": "Puntuación {score}/100",
      "generator.metricCritical": "{count} Críticos",
      "generator.metricErrors": "{count} Errores",
      "generator.metricWarnings": "{count} Advertencias",
      "generator.metricFixes": "{count} Correcciones sugeridas",
      "generator.issueRow": "fila {row}",
      "generator.unknownIssue": "Problema desconocido",
      "generator.suggested": "Sugerido: {count} × {message}",
      "generator.correction": "Corrección",
      "generator.applyFixes": "Aplicar {count} correcciones seguras únicamente al XMLTV generado.",
      "generator.generated": "XMLTV generado",
      "generator.downloadSuccess": "{filename} se descargó correctamente.",
      "preview.calculated": "Calculada",
      "preview.live": "En vivo",
      "preview.new": "Nuevo",
      "preview.premiere": "Estreno",
      "preview.metricProgrammes": "{count} Programas",
      "preview.metricDates": "{count} Fechas",
      "preview.metricGenres": "{count} Géneros",
      "preview.showingFirst": "Mostrando los primeros {visible} de {total} programas.",
      "preview.shown": "{count} programa(s) mostrados.",
      "preview.noMatches": "Ningún programa coincide con los filtros de vista previa.",
      "preview.summary": "Vista previa de {count} programas en {timezone}.",
      "grid.validateFirst": "Valida el EPG antes de crear la parrilla de programación.",
      "grid.createError": "No se pudo crear la parrilla de programación.",
      "grid.serverError": "El servidor no pudo crear la parrilla de programación.",
    },
  };
  let language = "en";

  function normalize(value) {
    return SUPPORTED.has(String(value || "").toLowerCase())
      ? String(value).toLowerCase()
      : "en";
  }

  function detectLanguage() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return normalize(saved);
    return navigator.language?.toLowerCase().startsWith("es") ? "es" : "en";
  }

  function translateElement(element) {
    const key = element.dataset.i18n;
    const value = dictionaries[language][key] ?? dictionaries.en[key];
    if (value != null) element.textContent = value;
  }

  function translateAttribute(element, attribute, key) {
    const value = dictionaries[language][key] ?? dictionaries.en[key];
    if (value != null) element.setAttribute(attribute, value);
  }

  function apply(root = document) {
    document.documentElement.lang = language;
    root.querySelectorAll("[data-i18n]").forEach(translateElement);
    root.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
      translateAttribute(element, "placeholder", element.dataset.i18nPlaceholder);
    });
    root.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
      translateAttribute(element, "aria-label", element.dataset.i18nAriaLabel);
    });
    document.querySelectorAll("[data-language-select]").forEach((select) => {
      select.value = language;
    });
  }

  function register(locale, messages) {
    const normalized = normalize(locale);
    Object.assign(dictionaries[normalized], messages);
    apply();
  }

  function setLanguage(locale) {
    language = normalize(locale);
    localStorage.setItem(STORAGE_KEY, language);
    apply();
    window.dispatchEvent(new CustomEvent("btp:languagechange", {
      detail: { language },
    }));
  }

  function t(key, fallback = key) {
    return dictionaries[language][key] ?? dictionaries.en[key] ?? fallback;
  }

  language = detectLanguage();
  window.BTPi18n = {
    apply,
    getLanguage: () => language,
    register,
    setLanguage,
    t,
  };

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-language-select]").forEach((select) => {
      select.addEventListener("change", () => setLanguage(select.value));
    });
    apply();
  });
})();
