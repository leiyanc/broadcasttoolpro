const authGate = document.querySelector("#auth-gate");
const platformContent = document.querySelector("#platform-content");
const bootstrapForm = document.querySelector("#bootstrap-form");
const loginForm = document.querySelector("#login-form");
const bootstrapMessage = document.querySelector("#bootstrap-message");
const loginMessage = document.querySelector("#login-message");
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
const suspendedAdminButton = document.querySelector(
  "#suspended-admin-button",
);
let currentIdentity = null;

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
    const trafficEnabled = Boolean(
      modules.prelogs?.enabled && modules.postlogs?.enabled,
    );
    setModuleAvailability(
      document.querySelector('a[href="#prelog"]'),
      trafficEnabled,
    );
    setModuleAvailability(
      document.querySelector('a[href="#postlog"]'),
      trafficEnabled,
    );
    setModuleAvailability(
      document.querySelector("#prelog"),
      trafficEnabled,
    );
    setModuleAvailability(
      document.querySelector("#postlog"),
      trafficEnabled,
    );
    const monitorEnabled = Boolean(modules.hls_monitor?.enabled);
    setModuleAvailability(
      document.querySelector("#monitor-hls-button"),
      monitorEnabled,
    );
    document.querySelector("#hls-monitor-duration")
      ?.closest("label")
      ?.classList.toggle("is-hidden", !monitorEnabled);
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

function showAuthentication(bootstrapRequired) {
  authGate.classList.remove("is-hidden");
  platformContent.classList.add("is-hidden");
  accountButton.classList.add("is-hidden");
  accountPanel.classList.add("is-hidden");
  suspendedPanel.classList.add("is-hidden");
  bootstrapForm.classList.toggle("is-hidden", !bootstrapRequired);
  loginForm.classList.toggle("is-hidden", bootstrapRequired);
}

function showPlatform(identity) {
  currentIdentity = identity;
  const user = identity.user;
  const organization = identity.organizations?.[0];
  authGate.classList.add("is-hidden");
  bootstrapForm.classList.add("is-hidden");
  loginForm.classList.add("is-hidden");
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
  refreshOrganizationEntitlements();
}

async function initializeAuthentication() {
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

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitAuthentication(loginForm, "/api/auth/login", loginMessage);
});

accountButton.addEventListener("click", () => {
  accountPanel.classList.toggle("is-hidden");
});

logoutButton.addEventListener("click", async () => {
  await authRequest("/api/auth/logout", { method: "POST" });
  const status = await authRequest("/api/auth/status");
  showAuthentication(status.bootstrap_required);
});

initializeAuthentication();
