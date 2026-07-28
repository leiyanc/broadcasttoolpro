const adminOpenButton = document.querySelector("#open-admin-button");
const closeAdminButton = document.querySelector("#close-admin-button");
const refreshAdminButton = document.querySelector("#refresh-admin-button");
const adminControlPlane = document.querySelector("#admin-control-plane");
const adminMetrics = document.querySelector("#admin-metrics");
const adminOrganizationsBody = document.querySelector(
  "#admin-organizations-body",
);
const adminIncidentsBody = document.querySelector("#admin-incidents-body");
const adminIncidentsTable = document.querySelector("#admin-incidents-table");
const adminIncidentsStatus = document.querySelector("#admin-incidents-status");
const adminMessage = document.querySelector("#admin-message");

async function adminRequest(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "The admin request failed.");
  }
  return payload;
}

function adminCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = value;
  row.appendChild(cell);
  return cell;
}

function adminSelect(options, selected) {
  const select = document.createElement("select");
  options.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value[0].toUpperCase() + value.slice(1);
    option.selected = value === selected;
    select.appendChild(option);
  });
  return select;
}

function addonToggle(enabled, label) {
  const control = document.createElement("label");
  control.className = "admin-toggle";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = enabled;
  const text = document.createElement("span");
  text.textContent = label;
  control.append(input, text);
  return { control, input };
}

async function saveOrganization(context) {
  const { organization, plan, status, traffic, monitoring, button } = context;
  button.disabled = true;
  adminMessage.textContent = "";
  adminMessage.classList.remove("is-error");
  try {
    await adminRequest(`/api/admin/organizations/${organization.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        plan: plan.value,
        status: status.value,
      }),
    });
    await Promise.all([
      adminRequest(
        `/api/admin/organizations/${organization.id}`
        + "/addons/traffic_operations",
        {
          method: "PUT",
          body: JSON.stringify({ enabled: traffic.checked }),
        },
      ),
      adminRequest(
        `/api/admin/organizations/${organization.id}`
        + "/addons/stream_monitoring",
        {
          method: "PUT",
          body: JSON.stringify({ enabled: monitoring.checked }),
        },
      ),
    ]);
    adminMessage.textContent = `${organization.name} was updated.`;
  } catch (error) {
    adminMessage.textContent = error.message;
    adminMessage.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
}

function renderOrganizations(organizations) {
  adminOrganizationsBody.replaceChildren();
  organizations.forEach((organization) => {
    const row = document.createElement("tr");
    adminCell(row, organization.name);
    const planCell = adminCell(row, "");
    const plan = adminSelect(
      ["professional", "enterprise"],
      organization.plan,
    );
    planCell.replaceChildren(plan);
    const statusCell = adminCell(row, "");
    const status = adminSelect(
      ["active", "suspended"],
      organization.status,
    );
    statusCell.replaceChildren(status);
    adminCell(row, organization.member_count);
    adminCell(row, organization.channel_count);
    const trafficCell = adminCell(row, "");
    const traffic = addonToggle(
      organization.entitlements.addons.find(
        (addon) => addon.code === "traffic_operations",
      )?.enabled,
      "Enabled",
    );
    trafficCell.replaceChildren(traffic.control);
    const monitoringCell = adminCell(row, "");
    const monitoring = addonToggle(
      organization.entitlements.addons.find(
        (addon) => addon.code === "stream_monitoring",
      )?.enabled,
      "Enabled",
    );
    monitoringCell.replaceChildren(monitoring.control);
    const actionCell = adminCell(row, "");
    const button = document.createElement("button");
    button.className = "button button-secondary admin-save";
    button.type = "button";
    button.textContent = "Save";
    button.addEventListener("click", () => saveOrganization({
      organization,
      plan,
      status,
      traffic: traffic.input,
      monitoring: monitoring.input,
      button,
    }));
    actionCell.replaceChildren(button);
    adminOrganizationsBody.appendChild(row);
  });
}

function renderIncidents(incidents) {
  adminIncidentsBody.replaceChildren();
  adminIncidentsTable.classList.toggle("is-hidden", !incidents.length);
  adminIncidentsStatus.textContent = incidents.length
    ? `${incidents.length} recent incident(s).`
    : "No incidents recorded.";
  incidents.forEach((incident) => {
    const row = document.createElement("tr");
    adminCell(row, incident.id);
    adminCell(row, incident.organization_name || "Platform");
    adminCell(row, incident.module);
    adminCell(row, incident.severity);
    adminCell(row, incident.status);
    adminCell(row, new Date(incident.created_at).toLocaleString());
    adminIncidentsBody.appendChild(row);
  });
}

async function loadControlPlane() {
  adminMessage.textContent = "";
  try {
    const [overview, organizations, incidents] = await Promise.all([
      adminRequest("/api/admin/overview"),
      adminRequest("/api/admin/organizations"),
      adminRequest("/api/admin/incidents"),
    ]);
    adminMetrics.replaceChildren();
    Object.entries({
      Organizations: overview.organizations,
      "Active Customers": overview.active_organizations,
      Users: overview.users,
      Channels: overview.channels,
      "Open Incidents": overview.open_incidents,
    }).forEach(([label, value]) => {
      const metric = document.createElement("div");
      const strong = document.createElement("strong");
      const small = document.createElement("small");
      strong.textContent = value;
      small.textContent = label;
      metric.append(strong, small);
      adminMetrics.appendChild(metric);
    });
    renderOrganizations(organizations.organizations);
    renderIncidents(incidents.incidents);
  } catch (error) {
    adminMessage.textContent = error.message;
    adminMessage.classList.add("is-error");
  }
}

adminOpenButton.addEventListener("click", () => {
  adminControlPlane.classList.remove("is-hidden");
  accountPanel.classList.add("is-hidden");
  platformContent.classList.add("is-hidden");
  loadControlPlane();
});

closeAdminButton.addEventListener("click", () => {
  adminControlPlane.classList.add("is-hidden");
  platformContent.classList.remove("is-hidden");
});

refreshAdminButton.addEventListener("click", loadControlPlane);
