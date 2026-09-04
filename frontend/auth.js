const authGate = document.querySelector("#auth-gate");
const platformContent = document.querySelector("#platform-content");
const bootstrapForm = document.querySelector("#bootstrap-form");
const loginForm = document.querySelector("#login-form");
const accessRequestForm = document.querySelector("#access-request-form");
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
const accessRequestMessage = document.querySelector(
  "#access-request-message",
);
const accessRequestPlan = document.querySelector("#access-request-plan");
const accessRequestMonitoring = accessRequestForm?.querySelector(
  "[name='include_stream_monitoring']",
);
const accessRequestMonitoringNote = document.querySelector(
  "#access-request-monitoring-note",
);
const accessRequestTotal = document.querySelector("#access-request-total");
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
const showLoginTab = document.querySelector("#show-login-tab");
const showGetStartedTab = document.querySelector("#show-get-started-tab");
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
const authAdminControlPanel = document.querySelector("#admin-control-plane");
const suspendedPanel = document.querySelector("#organization-suspended");
const suspendedAdminButton = document.querySelector(
  "#suspended-admin-button",
);
let currentIdentity = null;
let currentEntitlements = null;
let currentChannel = null;
const activeChannelSelect = document.querySelector("#active-channel-select");
const activeChannelTimezone = document.querySelector("#active-channel-timezone");
const activeChannelName = document.querySelector("#active-channel-name");
const activeChannelDetails = document.querySelector("#active-channel-details");
const channelProfileSettings = document.querySelector("#channel-profile-settings");
const activeChannelLanguage = document.querySelector("#active-channel-language");
const activeChannelRatingSystem = document.querySelector(
  "#active-channel-rating-system",
);
const saveChannelLanguage = document.querySelector("#save-channel-language");
const channelLanguageStatus = document.querySelector("#channel-language-status");

if (activeChannelTimezone) {
  const generatorTimezone = document.querySelector(
    "#xmltv-form [name='channel_timezone']",
  );
  for (const group of generatorTimezone?.children || []) {
    activeChannelTimezone.append(group.cloneNode(true));
  }
}

function publishActiveChannel(channel) {
  currentChannel = channel || null;
  window.BTPActiveChannel = currentChannel;
  if (activeChannelName) {
    activeChannelName.textContent = channel?.name || "No registered channel";
  }
  if (activeChannelDetails) {
    activeChannelDetails.textContent = channel
      ? `${channel.channel_code || channel.slug} · ${channel.timezone} · ${String(channel.primary_language || "und").toUpperCase()}`
      : "";
  }
  if (activeChannelLanguage) {
    activeChannelLanguage.value = channel?.primary_language === "und"
      ? ""
      : channel?.primary_language || "";
  }
  if (activeChannelTimezone) {
    activeChannelTimezone.value = channel?.timezone || "UTC";
  }
  if (activeChannelRatingSystem) {
    activeChannelRatingSystem.value = channel?.rating_system || "";
  }
  const role = currentIdentity?.organizations?.[0]?.role;
  channelProfileSettings?.classList.toggle(
    "is-hidden",
    !channel || !["owner", "admin"].includes(role),
  );
  window.dispatchEvent(new CustomEvent("btp:channel", {
    detail: currentChannel,
  }));
}

saveChannelLanguage?.addEventListener("click", async () => {
  if (!currentChannel) return;
  const value = activeChannelLanguage.value.trim();
  const timezone = activeChannelTimezone?.value.trim();
  const ratingSystem = activeChannelRatingSystem?.value.trim() || null;
  if (!value) {
    channelLanguageStatus.textContent = authText(
      "channel.languageInvalid",
      "Select the channel's primary language.",
    );
    return;
  }
  if (!timezone) {
    channelLanguageStatus.textContent = authText(
      "channel.timezoneInvalid",
      "Select the channel's time zone.",
    );
    return;
  }
  saveChannelLanguage.disabled = true;
  channelLanguageStatus.textContent = "";
  try {
    const updated = await authRequest(
      `/api/platform/channels/${currentChannel.id}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          timezone,
          primary_language: value,
          rating_system: ratingSystem,
        }),
      },
    );
    publishActiveChannel(updated);
    channelLanguageStatus.textContent = authText(
      "channel.profileSaved",
      "Channel settings saved.",
    );
  } catch (error) {
    channelLanguageStatus.textContent = error.message;
  } finally {
    saveChannelLanguage.disabled = false;
  }
});

async function loadOrganizationChannels(organization) {
  if (!organization || !activeChannelSelect) return;
  const result = await authRequest(
    `/api/platform/organizations/${organization.id}/channels`,
  );
  const channels = (result.channels || []).filter((channel) => channel.active);
  activeChannelSelect.replaceChildren();
  for (const channel of channels) {
    const option = document.createElement("option");
    option.value = channel.id;
    option.textContent = channel.name;
    activeChannelSelect.appendChild(option);
  }
  const storageKey = `btp.active-channel.${organization.id}`;
  const storedId = localStorage.getItem(storageKey);
  const selected = channels.find((channel) => channel.id === storedId)
    || channels[0]
    || null;
  if (selected) activeChannelSelect.value = selected.id;
  publishActiveChannel(selected);
  activeChannelSelect.onchange = () => {
    const channel = channels.find(
      (candidate) => candidate.id === activeChannelSelect.value,
    ) || null;
    if (channel) localStorage.setItem(storageKey, channel.id);
    publishActiveChannel(channel);
  };
}

function updateAccessRequestPricing() {
  const plan = accessRequestPlan.value;
  const planPrices = {
    programming_suite: 39,
    professional: 99,
    enterprise: 199,
  };
  const professional = plan === "professional";
  accessRequestMonitoring.disabled = !professional;
  if (!professional) accessRequestMonitoring.checked = false;
  accessRequestMonitoringNote.textContent = plan === "enterprise"
    ? authText(
      "auth.streamAddonIncluded",
      "Stream Monitoring is included with Enterprise.",
    )
    : authText(
      "auth.streamAddonAvailable",
      "Available as a $59/month add-on with Professional.",
    );
  const total = planPrices[plan]
    + (accessRequestMonitoring.checked ? 59 : 0);
  accessRequestTotal.textContent = authText(
    "auth.estimatedTotal",
    `Estimated monthly total: $${total.toFixed(2)}`,
    { total: total.toFixed(2) },
  );
}

accessRequestPlan.addEventListener("change", updateAccessRequestPricing);
accessRequestMonitoring.addEventListener("change", updateAccessRequestPricing);
updateAccessRequestPricing();
const signupPlan = new URLSearchParams(window.location.search).get("plan");
if (["programming_suite", "professional", "enterprise"].includes(signupPlan)) {
  accessRequestPlan.value = signupPlan;
  updateAccessRequestPricing();
}

function resetAdministrativeSurface(identity = null) {
  const isSuperuser = Boolean(identity?.user?.is_superuser);
  openAdminButton.classList.toggle("is-hidden", !isSuperuser);
  suspendedAdminButton.classList.toggle("is-hidden", !isSuperuser);
  authAdminControlPanel?.classList.add("is-hidden");

  if (isSuperuser) return;

  document.querySelector("#admin-metrics")?.replaceChildren();
  document.querySelector("#admin-security-body")?.replaceChildren();
  document.querySelector("#admin-email-attempt-body")?.replaceChildren();
  document.querySelector("#admin-suppression-body")?.replaceChildren();
  document.querySelector("#admin-email-event-body")?.replaceChildren();
  document.querySelector("#admin-access-body")?.replaceChildren();
  document.querySelector("#admin-organizations-body")?.replaceChildren();
  document.querySelector("#admin-incidents-body")?.replaceChildren();
  document.querySelector("#admin-ticket-panel")?.classList.add("is-hidden");
}

function authText(key, fallback, values = {}) {
  let translated = window.BTPi18n?.t(key, fallback) || fallback;
  for (const [name, value] of Object.entries(values)) {
    translated = translated.replaceAll(`{${name}}`, String(value));
  }
  return translated;
}

function localizedRole(role) {
  const normalized = String(role || "member").toLowerCase();
  return authText(`auth.role.${normalized}`, role || authText("auth.member", "Member"));
}

function renderLocalizedIdentity() {
  if (currentIdentity?.user) {
    const organization = currentIdentity.organizations?.[0];
    accountRole.textContent = localizedRole(organization?.role);
    accountPanelOrganization.textContent = organization
      ? `${organization.name} · ${organization.plan}`
      : authText("account.none", "No organization assigned");
  }
}

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
    const productAccessActive = Boolean(entitlements.access?.active);
    document.querySelector("#report-history")?.classList.toggle(
      "is-hidden",
      !productAccessActive
        || !(modules.prelogs?.enabled || modules.postlogs?.enabled),
    );
    for (const [moduleCode, selectors] of Object.entries(moduleSurfaces)) {
      for (const selector of selectors) {
        document.querySelectorAll(selector).forEach((element) => {
          setModuleAvailability(
            element,
            productAccessActive && Boolean(modules[moduleCode]?.enabled),
          );
        });
      }
    }
    document.querySelectorAll(".paid-download-option").forEach((element) => {
      element.classList.remove("is-hidden");
    });
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
    throw new Error(
      payload.detail || authText("auth.requestFailed", "The request could not be completed."),
    );
  }
  return payload;
}

function formPayload(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function selectAuthenticationMode(mode) {
  const accessRequest = mode === "create" || mode === "request";
  const activation = mode === "activate";
  const resetRequest = mode === "forgot";
  const resetConfirm = mode === "reset";
  loginForm.classList.toggle(
    "is-hidden",
    accessRequest || activation || resetRequest || resetConfirm,
  );
  accessRequestForm.classList.toggle("is-hidden", !accessRequest);
  accountActivationForm.classList.toggle("is-hidden", !activation);
  passwordResetRequestForm.classList.toggle("is-hidden", !resetRequest);
  passwordResetConfirmForm.classList.toggle("is-hidden", !resetConfirm);
}

function requestedAuthenticationMode() {
  const mode = new URLSearchParams(window.location.search).get("mode");
  return [
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
  currentIdentity = null;
  currentEntitlements = null;
  publishActiveChannel(null);
  resetAdministrativeSurface();
  authGate.classList.remove("is-hidden");
  platformContent.classList.add("is-hidden");
  accountButton.classList.add("is-hidden");
  accountPanel.classList.add("is-hidden");
  suspendedPanel.classList.add("is-hidden");
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
  resetAdministrativeSurface(identity);
  authGate.classList.add("is-hidden");
  bootstrapForm.classList.add("is-hidden");
  loginForm.classList.add("is-hidden");
  accessRequestForm.classList.add("is-hidden");
  accountActivationForm.classList.add("is-hidden");
  passwordResetRequestForm.classList.add("is-hidden");
  passwordResetConfirmForm.classList.add("is-hidden");
  platformContent.classList.remove("is-hidden");
  accountButton.classList.remove("is-hidden");
  accountAvatar.textContent = user.display_name.slice(0, 1).toUpperCase();
  accountName.textContent = user.display_name;
  accountRole.textContent = localizedRole(organization?.role);
  accountPanelName.textContent = user.display_name;
  accountPanelEmail.textContent = user.email;
  accountPanelOrganization.textContent = organization
    ? `${organization.name} · ${organization.plan}`
    : authText("account.none", "No organization assigned");
  applyOrganizationAccess(identity);
  window.dispatchEvent(new CustomEvent("btp:identity", {
    detail: identity,
  }));
  loadOrganizationChannels(organization).catch(() => publishActiveChannel(null));
  refreshOrganizationEntitlements();
}

async function initializeAuthentication() {
  const requestedMode = requestedAuthenticationMode();
  if (
    requestedMode === "create"
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
      loginMessage.textContent = authText(
        "auth.serviceUnavailable",
        "The authentication service is unavailable.",
      );
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

accessRequestForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = accessRequestForm.querySelector("button[type='submit']");
  button.disabled = true;
  accessRequestMessage.classList.remove("is-error");
  try {
    const payload = formPayload(accessRequestForm);
    payload.include_stream_monitoring = accessRequestMonitoring.checked;
    const identity = await authRequest("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    try {
      const organization = identity.organizations[0];
      const checkout = await authRequest(
        `/api/billing/organizations/${organization.id}/checkout`,
        {
          method: "POST",
          body: JSON.stringify(identity.checkout),
        },
      );
      window.location.assign(checkout.checkout_url);
    } catch (checkoutError) {
      history.replaceState(null, "", "/app");
      showPlatform(identity);
      document.querySelector("#open-billing-button")?.click();
      const billingMessage = document.querySelector("#billing-message");
      if (billingMessage) {
        billingMessage.textContent = authText(
          "auth.checkoutRetry",
          "Your account was created. Select your plan in Billing to retry secure Checkout.",
        );
        billingMessage.classList.add("is-error");
      }
    }
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

showGetStartedTab.addEventListener("click", () => {
  history.replaceState(null, "", "/app?mode=create");
  selectAuthenticationMode("create");
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

window.addEventListener("btp:languagechange", renderLocalizedIdentity);
window.addEventListener("btp:languagechange", updateAccessRequestPricing);
