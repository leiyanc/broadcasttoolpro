const authGate = document.querySelector("#auth-gate");
const platformContent = document.querySelector("#platform-content");
const bootstrapForm = document.querySelector("#bootstrap-form");
const loginForm = document.querySelector("#login-form");
const trialForm = document.querySelector("#trial-form");
const accessRequestForm = document.querySelector("#access-request-form");
const accessRequestSuccess = document.querySelector(
  "#access-request-success",
);
const accessRequestSuccessTitle = document.querySelector(
  "#access-request-success-title",
);
const accessRequestReference = document.querySelector(
  "#access-request-reference",
);
const accountActivationForm = document.querySelector(
  "#account-activation-form",
);
const passwordResetRequestForm = document.querySelector(
  "#password-reset-request-form",
);
const passwordResetConfirmForm = document.querySelector(
  "#password-reset-confirm-form",
);
const bootstrapMessage = document.querySelector("#bootstrap-message");
const loginMessage = document.querySelector("#login-message");
const trialMessage = document.querySelector("#trial-message");
const accessRequestMessage = document.querySelector(
  "#access-request-message",
);
const accountActivationMessage = document.querySelector(
  "#account-activation-message",
);
const passwordResetRequestMessage = document.querySelector(
  "#password-reset-request-message",
);
const passwordResetConfirmMessage = document.querySelector(
  "#password-reset-confirm-message",
);
const showPasswordReset = document.querySelector("#show-password-reset");
const showFreeTrialLink = document.querySelector("#show-free-trial-link");
const showLoginTab = document.querySelector("#show-login-tab");
const showTrialTab = document.querySelector("#show-trial-tab");
const showFreeTrialTab = document.querySelector("#show-free-trial-tab");
const accountButton = document.querySelector("#account-button");
const accountAvatar = document.querySelector("#account-avatar");
const accountName = document.querySelector("#account-name");
const accountRole = document.querySelector("#account-role");
const accountPanel = document.querySelector("#account-panel");
const accountPanelName = document.querySelector("#account-panel-name");
const accountPanelEmail = document.querySelector("#account-panel-email");
const accountPanelOrganization = document.querySelector(
  "#account-panel-organization",
);
const logoutButton = document.querySelector("#logout-button");
const openAdminButton = document.querySelector("#open-admin-button");
const suspendedPanel = document.querySelector("#organization-suspended");
const trialExpiredPanel = document.querySelector("#trial-expired");
const suspendedAdminButton = document.querySelector(
  "#suspended-admin-button",
);
let currentIdentity = null;
let currentEntitlements = null;

const moduleSurfaces = {
  xmltv_generator: ['a[href="#generator"]', "#generator"],
  xmltv_validator: ['a[href="#validator"]', "#validator"],
  xmltv_repair: ['a[href="#repair"]', "#repair"],
  prelogs: ['a[href="#prelog"]', "#prelog"],
  postlogs: ['a[href="#postlog"]', "#postlog"],
  hls_validator: ['a[href="#hls-validator"]', "#hls-validator"],
};

function applyOrganizationAccess(identity) {
  const organization = identity?.organizations?.[0];
  const suspended = organization?.status === "suspended";
  const controlPlane = document.querySelector("#admin-control-plane");
  const controlPlaneOpen = !controlPlane?.classList.contains("is-hidden");
  suspendedPanel.classList.toggle(
    "is-hidden",
    !suspended || controlPlaneOpen,
  );
  suspendedAdminButton.classList.toggle(
    "is-hidden",
    !suspended || !identity?.user?.is_superuser,
  );
  if (!controlPlaneOpen) {
    platformContent.classList.toggle("is-hidden", suspended);
  }
}

function setModuleAvailability(element, enabled) {
  if (!element) return;
  element.classList.toggle("is-hidden", !enabled);
}

async function refreshOrganizationEntitlements() {
  try {
    currentIdentity = await authRequest("/api/auth/me");
    const organization = currentIdentity.organizations?.[0];
    if (!organization) return;
    accountPanelOrganization.textContent =
      `${organization.name} · ${organization.plan}`;
    applyOrganizationAccess(currentIdentity);
    const entitlements = await authRequest(
      `/api/platform/organizations/${organization.id}/entitlements`,
    );
    const modules = entitlements.modules || {};
    currentEntitlements = entitlements;
    document.body.dataset.accessType = entitlements.access?.type || "paid";
    const trialExpired = (
      entitlements.access?.type === "trial"
      && !entitlements.access?.active
    );
    trialExpiredPanel.classList.toggle("is-hidden", !trialExpired);
    if (trialExpired) {
      platformContent.classList.add("is-hidden");
    }
    for (const [moduleCode, selectors] of Object.entries(moduleSurfaces)) {
      for (const selector of selectors) {
        document.querySelectorAll(selector).forEach((element) => {
          setModuleAvailability(element, Boolean(modules[moduleCode]?.enabled));
        });
      }
    }
    document.querySelectorAll(".paid-download-option").forEach((element) => {
      element.classList.toggle(
        "is-hidden",
        entitlements.access?.type === "trial",
      );
    });
    const prelogFormat = document.querySelector("#prelog-output-format");
    const prelogExcel = prelogFormat?.querySelector('option[value="xlsx"]');
    if (prelogExcel) {
      prelogExcel.disabled = entitlements.access?.type === "trial";
      if (entitlements.access?.type === "trial") {
        prelogFormat.value = "pdf";
      }
    }
    const monitorEnabled = Boolean(modules.hls_monitor?.enabled);
    setModuleAvailability(
      document.querySelector("#monitor-hls-button"),
      monitorEnabled,
    );
    document.querySelector("#hls-monitor-duration")
      ?.closest("label")
      ?.classList.toggle("is-hidden", !monitorEnabled);
    window.dispatchEvent(new CustomEvent("btp:entitlements", {
      detail: entitlements,
    }));
  } catch {
    // Keep core modules available if entitlement refresh is interrupted.
  }
}

async function authRequest(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const payload = response.status === 204
    ? {}
    : await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "The request could not be completed.");
  }
  return payload;
}

function formPayload(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function selectAuthenticationMode(mode) {
  const trial = mode === "trial";
  const accessRequest = mode === "create" || mode === "request";
  const activation = mode === "activate";
  const resetRequest = mode === "forgot";
  const resetConfirm = mode === "reset";
  loginForm.classList.toggle(
    "is-hidden",
    trial || accessRequest || activation || resetRequest || resetConfirm,
  );
  trialForm.classList.toggle(
    "is-hidden", !trial,
  );
  accessRequestForm.classList.toggle("is-hidden", !accessRequest);
  accessRequestSuccess.classList.add("is-hidden");
  accountActivationForm.classList.toggle("is-hidden", !activation);
  passwordResetRequestForm.classList.toggle("is-hidden", !resetRequest);
  passwordResetConfirmForm.classList.toggle("is-hidden", !resetConfirm);
  showLoginTab.classList.toggle(
    "is-active",
    !trial
      && !accessRequest
      && !activation
      && !resetRequest
      && !resetConfirm,
  );
  showTrialTab.classList.toggle("is-active", accessRequest);
  showFreeTrialTab.classList.toggle("is-active", trial);
  showLoginTab.setAttribute(
    "aria-selected",
    String(
      !trial
        && !accessRequest
        && !activation
        && !resetRequest
        && !resetConfirm,
    ),
  );
  showTrialTab.setAttribute(
    "aria-selected",
    String(accessRequest),
  );
  showFreeTrialTab.setAttribute("aria-selected", String(trial));
}

function requestedAuthenticationMode() {
  const mode = new URLSearchParams(window.location.search).get("mode");
  return [
    "trial",
    "create",
    "request",
    "activate",
    "forgot",
    "reset",
  ].includes(mode)
    ? mode
    : "signin";
}

function showAuthentication(bootstrapRequired) {
  authGate.classList.remove("is-hidden");
  platformContent.classList.add("is-hidden");
  accountButton.classList.add("is-hidden");
  accountPanel.classList.add("is-hidden");
  suspendedPanel.classList.add("is-hidden");
  trialExpiredPanel.classList.add("is-hidden");
  window.dispatchEvent(new CustomEvent("btp:identity", {
    detail: null,
  }));
  bootstrapForm.classList.toggle("is-hidden", !bootstrapRequired);
  document.querySelector(".auth-access-panel").classList.toggle(
    "is-hidden",
    bootstrapRequired,
  );
  if (!bootstrapRequired) {
    selectAuthenticationMode(requestedAuthenticationMode());
  }
}

function showPlatform(identity) {
  currentIdentity = identity;
  const user = identity.user;
  const organization = identity.organizations?.[0];
  authGate.classList.add("is-hidden");
  bootstrapForm.classList.add("is-hidden");
  loginForm.classList.add("is-hidden");
  trialForm.classList.add("is-hidden");
  accessRequestForm.classList.add("is-hidden");
  accountActivationForm.classList.add("is-hidden");
  passwordResetRequestForm.classList.add("is-hidden");
  passwordResetConfirmForm.classList.add("is-hidden");
  platformContent.classList.remove("is-hidden");
  accountButton.classList.remove("is-hidden");
  accountAvatar.textContent = user.display_name.slice(0, 1).toUpperCase();
  accountName.textContent = user.display_name;
  accountRole.textContent = organization?.role || "Member";
  openAdminButton.classList.toggle("is-hidden", !user.is_superuser);
  accountPanelName.textContent = user.display_name;
  accountPanelEmail.textContent = user.email;
  accountPanelOrganization.textContent = organization
    ? `${organization.name} · ${organization.plan}`
    : "No organization assigned";
  applyOrganizationAccess(identity);
  window.dispatchEvent(new CustomEvent("btp:identity", {
    detail: identity,
  }));
  refreshOrganizationEntitlements();
}

async function initializeAuthentication() {
  const requestedMode = requestedAuthenticationMode();
  if (
    requestedMode === "trial"
    || requestedMode === "create"
    || requestedMode === "request"
    || requestedMode === "activate"
    || requestedMode === "forgot"
    || requestedMode === "reset"
  ) {
    showAuthentication(false);
    selectAuthenticationMode(requestedMode);
    return;
  }
  try {
    showPlatform(await authRequest("/api/auth/me"));
  } catch {
    try {
      const status = await authRequest("/api/auth/status");
      showAuthentication(status.bootstrap_required);
    } catch {
      showAuthentication(false);
      loginMessage.textContent = "The authentication service is unavailable.";
      loginMessage.classList.add("is-error");
    }
  }
}

async function submitAuthentication(form, endpoint, message) {
  const button = form.querySelector("button[type='submit']");
  message.textContent = "";
  message.classList.remove("is-error");
  button.disabled = true;
  try {
    const identity = await authRequest(endpoint, {
      method: "POST",
      body: JSON.stringify(formPayload(form)),
    });
    form.reset();
    showPlatform(identity);
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
}

bootstrapForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitAuthentication(
    bootstrapForm,
    "/api/auth/bootstrap",
    bootstrapMessage,
  );
});

trialForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitAuthentication(
    trialForm,
    "/api/auth/trial",
    trialMessage,
  );
});

accessRequestForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = accessRequestForm.querySelector("button[type='submit']");
  button.disabled = true;
  accessRequestMessage.classList.remove("is-error");
  try {
    const payload = formPayload(accessRequestForm);
    const result = await authRequest("/api/auth/access-requests", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    accessRequestForm.reset();
    accessRequestMessage.textContent = "";
    accessRequestSuccessTitle.textContent =
      `Thank you, ${payload.contact_name}.`;
    accessRequestReference.textContent = result.request_id;
    accessRequestForm.classList.add("is-hidden");
    accessRequestSuccess.classList.remove("is-hidden");
  } catch (error) {
    accessRequestMessage.textContent = error.message;
    accessRequestMessage.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
});

accountActivationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = accountActivationForm.querySelector(
    "button[type='submit']",
  );
  button.disabled = true;
  accountActivationMessage.classList.remove("is-error");
  try {
    const token = new URLSearchParams(window.location.search).get("token");
    const identity = await authRequest("/api/auth/activate-account", {
      method: "POST",
      body: JSON.stringify({
        token,
        password: new FormData(accountActivationForm).get("password"),
      }),
    });
    accountActivationForm.reset();
    history.replaceState(null, "", "/app");
    showPlatform(identity);
  } catch (error) {
    accountActivationMessage.textContent = error.message;
    accountActivationMessage.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
});

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitAuthentication(loginForm, "/api/auth/login", loginMessage);
});

passwordResetRequestForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = passwordResetRequestForm.querySelector(
    "button[type='submit']",
  );
  button.disabled = true;
  passwordResetRequestMessage.classList.remove("is-error");
  try {
    const result = await authRequest("/api/auth/password-reset/request", {
      method: "POST",
      body: JSON.stringify(formPayload(passwordResetRequestForm)),
    });
    passwordResetRequestForm.reset();
    passwordResetRequestMessage.textContent = result.message;
  } catch (error) {
    passwordResetRequestMessage.textContent = error.message;
    passwordResetRequestMessage.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
});

passwordResetConfirmForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = passwordResetConfirmForm.querySelector(
    "button[type='submit']",
  );
  button.disabled = true;
  passwordResetConfirmMessage.classList.remove("is-error");
  try {
    const token = new URLSearchParams(window.location.search).get("token");
    const result = await authRequest("/api/auth/password-reset/confirm", {
      method: "POST",
      body: JSON.stringify({
        token,
        password: new FormData(passwordResetConfirmForm).get("password"),
      }),
    });
    passwordResetConfirmForm.reset();
    passwordResetConfirmMessage.textContent = result.message;
    window.setTimeout(() => {
      history.replaceState(null, "", "/app?mode=signin");
      selectAuthenticationMode("signin");
    }, 1200);
  } catch (error) {
    passwordResetConfirmMessage.textContent = error.message;
    passwordResetConfirmMessage.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
});

showPasswordReset.addEventListener("click", () => {
  history.replaceState(null, "", "/app?mode=forgot");
  selectAuthenticationMode("forgot");
});

document.querySelectorAll("[data-return-to-login]").forEach((button) => {
  button.addEventListener("click", () => {
    history.replaceState(null, "", "/app?mode=signin");
    selectAuthenticationMode("signin");
  });
});

showLoginTab.addEventListener("click", () => {
  history.replaceState(null, "", "/app?mode=signin");
  selectAuthenticationMode("signin");
});

showTrialTab.addEventListener("click", () => {
  history.replaceState(null, "", "/app?mode=create");
  selectAuthenticationMode("create");
});

function openFreeTrial() {
  history.replaceState(null, "", "/app?mode=trial");
  selectAuthenticationMode("trial");
}

showFreeTrialTab.addEventListener("click", openFreeTrial);
showFreeTrialLink.addEventListener("click", openFreeTrial);

accountButton.addEventListener("click", () => {
  accountPanel.classList.toggle("is-hidden");
});

logoutButton.addEventListener("click", async () => {
  await authRequest("/api/auth/logout", { method: "POST" });
  const status = await authRequest("/api/auth/status");
  showAuthentication(status.bootstrap_required);
});

initializeAuthentication();
