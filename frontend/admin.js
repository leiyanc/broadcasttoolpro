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
const adminBackupStatus = document.querySelector("#admin-backup-status");
const adminBackupDetails = document.querySelector("#admin-backup-details");
const adminBackupMessage = document.querySelector("#admin-backup-message");
const runBackupButton = document.querySelector("#run-backup-button");
const suspendedAdminControlButton = document.querySelector(
  "#suspended-admin-button",
);
const adminTicketPanel = document.querySelector("#admin-ticket-panel");
const adminTicketTitle = document.querySelector("#admin-ticket-title");
const adminTicketMeta = document.querySelector("#admin-ticket-meta");
const adminTicketDetails = document.querySelector("#admin-ticket-details");
const adminTicketConversation = document.querySelector(
  "#admin-ticket-conversation",
);
const adminTicketNotes = document.querySelector("#admin-ticket-notes");
const adminCustomerReplyForm = document.querySelector(
  "#admin-customer-reply-form",
);
const adminInternalNoteForm = document.querySelector(
  "#admin-internal-note-form",
);
const adminTicketStatus = document.querySelector("#admin-ticket-status");
const adminTicketResolution = document.querySelector(
  "#admin-ticket-resolution",
);
const adminSaveTicketStatus = document.querySelector("#save-ticket-status");
const adminTicketActivity = document.querySelector("#admin-ticket-activity");
const adminTicketMessage = document.querySelector("#admin-ticket-message");
const adminCloseTicket = document.querySelector("#close-admin-ticket");
let adminCurrentTicketId = null;

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

function adminTicketItem(author, message, createdAt, visibility = "") {
  const item = document.createElement("article");
  const heading = document.createElement("div");
  const strong = document.createElement("strong");
  const small = document.createElement("small");
  const paragraph = document.createElement("p");
  strong.textContent = author || "System";
  small.textContent = `${visibility ? `${visibility} · ` : ""}${
    new Date(createdAt).toLocaleString()
  }`;
  paragraph.textContent = message;
  heading.append(strong, small);
  item.append(heading, paragraph);
  return item;
}

function renderBackupStatus(backup) {
  const latest = backup.latest_backup;
  adminBackupStatus.textContent = latest
    ? `Last verified backup: ${new Date(latest.created_at).toLocaleString()}`
    : "No verified backup has been created yet.";
  adminBackupDetails.replaceChildren();
  const drive = backup.google_drive || {};
  const driveUsage = Number(drive.drive_usage_bytes || 0);
  const driveTarget = Number(drive.target_usage_bytes || 0);
  const details = {
    Status: backup.status,
    Retention: `${backup.retention_days} days`,
    Schedule: `Every ${backup.automatic_interval_hours} hours`,
    Storage: drive.authorized
      ? "Encrypted Google Drive backup"
      : backup.external_storage_configured
        ? "External backup location configured"
        : "Local development location — configure external storage before launch",
    "Drive usage": drive.authorized && driveUsage
      ? `${(driveUsage / 1_000_000_000).toFixed(2)} GB of ${(driveTarget / 1_000_000_000).toFixed(0)} GB operating target`
      : drive.authorized
        ? "Connected — awaiting first upload"
        : "Not connected",
  };
  Object.entries(details).forEach(([label, value]) => {
    const item = document.createElement("div");
    const strong = document.createElement("strong");
    const small = document.createElement("small");
    strong.textContent = value;
    small.textContent = label;
    item.append(strong, small);
    adminBackupDetails.appendChild(item);
  });
}

async function openAdminTicket(incidentId) {
  adminCurrentTicketId = incidentId;
  adminTicketPanel.classList.remove("is-hidden");
  adminTicketMessage.textContent = "Loading ticket…";
  adminTicketMessage.classList.remove("is-error");
  try {
    const payload = await adminRequest(
      `/api/admin/incidents/${incidentId}`,
    );
    const incident = payload.incident;
    adminTicketTitle.textContent = `${incident.id} · ${incident.summary}`;
    adminTicketMeta.textContent =
      `${incident.organization_name || "Platform"} · ${
        incident.reporter_name || "System"
      } · ${incident.reporter_email || ""}`;
    adminTicketDetails.replaceChildren(
      adminTicketItem(
        "Customer report",
        incident.details || "No details provided.",
        incident.created_at,
        incident.module,
      ),
    );
    if (incident.error_message) {
      adminTicketDetails.appendChild(
        adminTicketItem(
          "Exact error message",
          incident.error_message,
          incident.created_at,
        ),
      );
    }
    adminTicketConversation.replaceChildren();
    adminTicketNotes.replaceChildren();
    payload.messages.forEach((message) => {
      const target = message.visibility === "internal"
        ? adminTicketNotes
        : adminTicketConversation;
      target.appendChild(adminTicketItem(
        message.author_name,
        message.message,
        message.created_at,
        message.visibility,
      ));
    });
    if (!adminTicketConversation.children.length) {
      adminTicketConversation.textContent = "No customer messages yet.";
    }
    if (!adminTicketNotes.children.length) {
      adminTicketNotes.textContent = "No internal notes yet.";
    }
    adminTicketStatus.value = incident.status;
    adminTicketResolution.value = incident.resolution || "";
    adminTicketActivity.replaceChildren();
    payload.activity.forEach((activity) => {
      adminTicketActivity.appendChild(adminTicketItem(
        activity.actor_name || "System",
        `${activity.event_type.replaceAll("_", " ")}${
          activity.details ? `: ${activity.details}` : ""
        }`,
        activity.created_at,
      ));
    });
    adminTicketMessage.textContent = "";
    adminTicketPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    adminTicketMessage.textContent = error.message;
    adminTicketMessage.classList.add("is-error");
  }
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
  const {
    organization,
    plan,
    status,
    subscriptionStatus,
    billingCycle,
    traffic,
    monitoring,
    button,
    rowStatus,
  } = context;
  button.disabled = true;
  button.textContent = "Saving…";
  rowStatus.textContent = "Saving changes…";
  rowStatus.classList.remove("is-error", "is-success");
  adminMessage.textContent = "";
  adminMessage.classList.remove("is-error", "is-success");
  try {
    await adminRequest(`/api/admin/organizations/${organization.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        plan: plan.value,
        status: status.value,
      }),
    });
    await adminRequest(
      `/api/admin/organizations/${organization.id}/subscription`,
      {
        method: "PATCH",
        body: JSON.stringify({
          status: subscriptionStatus.value,
          billing_cycle: billingCycle.value,
        }),
      },
    );
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
    adminMessage.classList.add("is-success");
    rowStatus.textContent = "Saved";
    rowStatus.classList.add("is-success");
    await refreshOrganizationEntitlements();
  } catch (error) {
    adminMessage.textContent = error.message;
    adminMessage.classList.add("is-error");
    rowStatus.textContent = error.message;
    rowStatus.classList.add("is-error");
  } finally {
    button.disabled = false;
    button.textContent = "Save";
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
    const subscriptionStatusCell = adminCell(row, "");
    const subscriptionStatus = adminSelect(
      ["trialing", "active", "past_due", "canceled"],
      organization.subscription.status,
    );
    subscriptionStatusCell.replaceChildren(subscriptionStatus);
    const billingCycleCell = adminCell(row, "");
    const billingCycle = adminSelect(
      ["monthly", "annual"],
      organization.subscription.billing_cycle,
    );
    billingCycleCell.replaceChildren(billingCycle);
    adminCell(row, organization.member_count);
    adminCell(row, organization.channel_count);
    const trafficCell = adminCell(row, "");
    const traffic = addonToggle(
      organization.entitlements.addons.find(
        (addon) => addon.code === "traffic_operations",
      )?.enabled,
      "Enabled",
    );
    const enterprise = organization.plan === "enterprise";
    traffic.input.disabled = enterprise;
    traffic.control.querySelector("span").textContent = enterprise
      ? "Included"
      : (traffic.input.checked ? "Enabled" : "Disabled");
    trafficCell.replaceChildren(traffic.control);
    const monitoringCell = adminCell(row, "");
    const monitoring = addonToggle(
      organization.entitlements.addons.find(
        (addon) => addon.code === "stream_monitoring",
      )?.enabled,
      "Enabled",
    );
    monitoring.input.disabled = enterprise;
    monitoring.control.querySelector("span").textContent = enterprise
      ? "Included"
      : (monitoring.input.checked ? "Enabled" : "Disabled");
    monitoringCell.replaceChildren(monitoring.control);
    const actionCell = adminCell(row, "");
    const button = document.createElement("button");
    button.className = "button button-secondary admin-save";
    button.type = "button";
    button.textContent = "Save";
    const rowStatus = document.createElement("small");
    rowStatus.className = "admin-row-status";
    const markDirty = () => {
      rowStatus.textContent = "Unsaved changes";
      rowStatus.classList.remove("is-error", "is-success");
    };
    [
      plan,
      status,
      subscriptionStatus,
      billingCycle,
      traffic.input,
      monitoring.input,
    ].forEach((control) => {
      control.addEventListener("change", () => {
        if (control === plan) {
          const included = plan.value === "enterprise";
          for (const addon of [traffic, monitoring]) {
            addon.input.disabled = included;
            if (included) addon.input.checked = true;
            addon.control.querySelector("span").textContent = included
              ? "Included"
              : (addon.input.checked ? "Enabled" : "Disabled");
          }
        } else if (control.type === "checkbox") {
          control.closest("label").querySelector("span").textContent =
            control.checked ? "Enabled" : "Disabled";
        }
        markDirty();
      });
    });
    button.addEventListener("click", () => saveOrganization({
      organization,
      plan,
      status,
      subscriptionStatus,
      billingCycle,
      traffic: traffic.input,
      monitoring: monitoring.input,
      button,
      rowStatus,
    }));
    actionCell.replaceChildren(button, rowStatus);
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
    adminCell(
      row,
      incident.reporter_name
        ? `${incident.reporter_name} · ${incident.reporter_email}`
        : "System",
    );
    adminCell(row, incident.module);
    adminCell(row, incident.category || "—");
    adminCell(row, incident.priority || "—");
    adminCell(row, incident.severity);
    adminCell(row, incident.status);
    adminCell(row, incident.summary);
    adminCell(row, new Date(incident.created_at).toLocaleString());
    const openCell = adminCell(row, "");
    const openButton = document.createElement("button");
    openButton.className = "button button-secondary admin-save";
    openButton.type = "button";
    openButton.textContent = "Open Ticket";
    openButton.addEventListener("click", () => {
      openAdminTicket(incident.id);
    });
    openCell.replaceChildren(openButton);
    adminIncidentsBody.appendChild(row);
  });
}

async function submitAdminTicketMessage(form, visibility) {
  if (!adminCurrentTicketId) return;
  const button = form.querySelector("button[type='submit']");
  const message = new FormData(form).get("message");
  button.disabled = true;
  adminTicketMessage.textContent = "";
  try {
    await adminRequest(
      `/api/admin/incidents/${adminCurrentTicketId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ visibility, message }),
      },
    );
    form.reset();
    await openAdminTicket(adminCurrentTicketId);
    adminTicketMessage.textContent = visibility === "internal"
      ? "Internal note saved."
      : "Reply sent to the customer.";
  } catch (error) {
    adminTicketMessage.textContent = error.message;
    adminTicketMessage.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
}

adminCustomerReplyForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitAdminTicketMessage(adminCustomerReplyForm, "customer");
});

adminInternalNoteForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitAdminTicketMessage(adminInternalNoteForm, "internal");
});

adminSaveTicketStatus.addEventListener("click", async () => {
  if (!adminCurrentTicketId) return;
  adminSaveTicketStatus.disabled = true;
  adminTicketMessage.textContent = "";
  adminTicketMessage.classList.remove("is-error");
  try {
    await adminRequest(
      `/api/admin/incidents/${adminCurrentTicketId}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          status: adminTicketStatus.value,
          resolution: adminTicketResolution.value || null,
        }),
      },
    );
    await Promise.all([
      openAdminTicket(adminCurrentTicketId),
      loadControlPlane(),
    ]);
    adminTicketMessage.textContent = "Ticket status updated.";
  } catch (error) {
    adminTicketMessage.textContent = error.message;
    adminTicketMessage.classList.add("is-error");
  } finally {
    adminSaveTicketStatus.disabled = false;
  }
});

adminCloseTicket.addEventListener("click", () => {
  adminTicketPanel.classList.add("is-hidden");
  adminCurrentTicketId = null;
});

async function loadControlPlane() {
  adminMessage.textContent = "";
  try {
    const [overview, organizations, incidents, backups] = await Promise.all([
      adminRequest("/api/admin/overview"),
      adminRequest("/api/admin/organizations"),
      adminRequest("/api/admin/incidents"),
      adminRequest("/api/admin/backups"),
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
    renderBackupStatus(backups);
  } catch (error) {
    adminMessage.textContent = error.message;
    adminMessage.classList.add("is-error");
  }
}

runBackupButton.addEventListener("click", async () => {
  runBackupButton.disabled = true;
  adminBackupMessage.textContent = "Creating and verifying backup…";
  adminBackupMessage.classList.remove("is-error", "is-success");
  try {
    const result = await adminRequest("/api/admin/backups", {
      method: "POST",
    });
    renderBackupStatus(result.status);
    adminBackupMessage.textContent = "Verified backup completed.";
    adminBackupMessage.classList.add("is-success");
  } catch (error) {
    adminBackupMessage.textContent = error.message;
    adminBackupMessage.classList.add("is-error");
  } finally {
    runBackupButton.disabled = false;
  }
});

adminOpenButton.addEventListener("click", () => {
  adminControlPlane.classList.remove("is-hidden");
  accountPanel.classList.add("is-hidden");
  platformContent.classList.add("is-hidden");
  suspendedPanel.classList.add("is-hidden");
  loadControlPlane();
});

closeAdminButton.addEventListener("click", () => {
  adminControlPlane.classList.add("is-hidden");
  applyOrganizationAccess(currentIdentity);
});

refreshAdminButton.addEventListener("click", loadControlPlane);
suspendedAdminControlButton.addEventListener("click", () => {
  adminControlPlane.classList.remove("is-hidden");
  suspendedPanel.classList.add("is-hidden");
  platformContent.classList.add("is-hidden");
  loadControlPlane();
});
