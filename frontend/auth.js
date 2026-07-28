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
  bootstrapForm.classList.toggle("is-hidden", !bootstrapRequired);
  loginForm.classList.toggle("is-hidden", bootstrapRequired);
}

function showPlatform(identity) {
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
  accountPanelName.textContent = user.display_name;
  accountPanelEmail.textContent = user.email;
  accountPanelOrganization.textContent = organization
    ? `${organization.name} · ${organization.plan}`
    : "No organization assigned";
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

