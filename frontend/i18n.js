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
