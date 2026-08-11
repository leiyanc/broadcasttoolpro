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
const adminSecurityBody = document.querySelector("#admin-security-body");
const adminSecurityTable = document.querySelector("#admin-security-table");
const adminSecurityStatus = document.querySelector("#admin-security-status");
const adminAccessBody = document.querySelector("#admin-access-body");
const adminAccessTable = document.querySelector("#admin-access-table");
const adminAccessStatus = document.querySelector("#admin-access-status");
const adminAccessMessage = document.querySelector("#admin-access-message");
const adminEmailMetrics = document.querySelector("#admin-email-metrics");
const adminEmailMessage = document.querySelector("#admin-email-message");
const adminEmailAttemptStatus = document.querySelector(
  "#admin-email-attempt-status",
);
const adminEmailAttemptTable = document.querySelector(
  "#admin-email-attempt-table",
);
const adminEmailAttemptBody = document.querySelector(
  "#admin-email-attempt-body",
);
const adminSuppressionStatus = document.querySelector(
  "#admin-suppression-status",
);
const adminSuppressionTable = document.querySelector(
  "#admin-suppression-table",
);
const adminSuppressionBody = document.querySelector(
  "#admin-suppression-body",
);
const adminEmailEventStatus = document.querySelector(
  "#admin-email-event-status",
);
const adminEmailEventTable = document.querySelector(
  "#admin-email-event-table",
);
const adminEmailEventBody = document.querySelector(
  "#admin-email-event-body",
);
const refreshEmailHealthButton = document.querySelector(
  "#refresh-email-health",
);
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

function adminDate(value) {
  return value ? new Date(value).toLocaleDateString() : "—";
}

function subscriptionTiming(subscription) {
  if (!subscription) return "—";
  if (subscription.provider === "stripe_pending") {
    return "Begins after Stripe Checkout";
  }
  if (subscription.access_state === "payment_grace") {
    return `Grace ends ${adminDate(subscription.grace_period_ends_at)}`;
  }
  if (subscription.access_state === "payment_suspended") {
    return `Suspended after ${adminDate(subscription.grace_period_ends_at)}`;
  }
  if (subscription.provider === "complimentary") {
    return `Access ends ${adminDate(
      subscription.waiver_expires_at || subscription.current_period_end,
    )}`;
  }
  if (subscription.provider === "stripe") {
    return subscription.cancel_at_period_end
      ? `Access ends ${adminDate(subscription.current_period_end)}`
      : `Renews ${adminDate(subscription.current_period_end)} ↻`;
  }
  return adminDate(subscription.current_period_end);
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

function renderSecurityEvents(events) {
  adminSecurityBody.replaceChildren();
  adminSecurityStatus.textContent = events.length
    ? `${events.length} recent security events.`
    : "No security events recorded.";
  adminSecurityTable.classList.toggle("is-hidden", events.length === 0);
  events.forEach((event) => {
    const row = document.createElement("tr");
    adminCell(row, new Date(event.created_at).toLocaleString());
    adminCell(row, event.event_type.replaceAll("_", " "));
    adminCell(row, event.email || "System");
    adminCell(row, event.success ? "Successful" : "Rejected");
    adminCell(row, event.details || "—");
    adminSecurityBody.appendChild(row);
  });
}

function renderEmailHealth(health) {
  adminEmailMetrics.replaceChildren();
  const outbox = health.outbox || {};
  const events = health.events || {};
  const metrics = {
    Provider: health.provider === "amazon_ses"
      ? "Amazon SES enabled"
      : "Sending disabled",
    "SNS Events": health.sns_configured
      ? "Configured"
      : "Awaiting public endpoint",
    Queued: outbox.queued || 0,
    Sent: outbox.sent || 0,
    Failed: outbox.failed || 0,
    "Permanent Bounces": events.permanent_bounce || 0,
    Complaints: events.complaint || 0,
    Suppressed: health.suppressions.length,
  };
  Object.entries(metrics).forEach(([label, value]) => {
    const item = document.createElement("div");
    const strong = document.createElement("strong");
    const small = document.createElement("small");
    strong.textContent = value;
    small.textContent = label;
    item.append(strong, small);
    adminEmailMetrics.appendChild(item);
  });

  const attempts = health.recent_attempts || [];
  adminEmailAttemptBody.replaceChildren();
  adminEmailAttemptStatus.textContent = attempts.length
    ? `${attempts.length} recent delivery attempt(s).`
    : "No delivery attempts recorded.";
  adminEmailAttemptTable.classList.toggle("is-hidden", attempts.length === 0);
  attempts.forEach((attempt) => {
    const row = document.createElement("tr");
    adminCell(row, new Date(attempt.created_at).toLocaleString());
    adminCell(row, attempt.recipient_email);
    adminCell(row, attempt.subject);
    adminCell(
      row,
      `${attempt.status.replaceAll("_", " ")} · ${attempt.attempts} attempt(s)`,
    );
    adminCell(row, attempt.last_error || "—");
    const actionCell = adminCell(row, "");
    if (["queued", "failed"].includes(attempt.status)) {
      const retryButton = document.createElement("button");
      retryButton.className = "button button-secondary admin-save";
      retryButton.type = "button";
      retryButton.textContent = "Retry";
      retryButton.addEventListener("click", async () => {
        if (!window.confirm(
          `Retry delivery to ${attempt.recipient_email}? Confirm the address `
          + "is authorized to receive email before continuing.",
        )) {
          return;
        }
        retryButton.disabled = true;
        adminEmailMessage.textContent = "Queueing delivery retry…";
        adminEmailMessage.classList.remove("is-error", "is-success");
        try {
          const result = await adminRequest(
            `/api/admin/email-outbox/${encodeURIComponent(attempt.id)}/retry`,
            { method: "POST" },
          );
          adminEmailMessage.textContent = result.detail;
          adminEmailMessage.classList.add("is-success");
          await loadEmailHealth();
        } catch (error) {
          adminEmailMessage.textContent = error.message;
          adminEmailMessage.classList.add("is-error");
          retryButton.disabled = false;
        }
      });
      actionCell.replaceChildren(retryButton);
    } else {
      actionCell.textContent = "—";
    }
    adminEmailAttemptBody.appendChild(row);
  });

  adminSuppressionBody.replaceChildren();
  adminSuppressionStatus.textContent = health.suppressions.length
    ? `${health.suppressions.length} suppressed recipient(s).`
    : "No suppressed recipients.";
  adminSuppressionTable.classList.toggle(
    "is-hidden",
    health.suppressions.length === 0,
  );
  health.suppressions.forEach((suppression) => {
    const row = document.createElement("tr");
    adminCell(row, suppression.recipient_email);
    adminCell(row, suppression.reason.replaceAll("_", " "));
    adminCell(row, suppression.source);
    adminCell(row, new Date(suppression.updated_at).toLocaleString());
    const actionCell = adminCell(row, "");
    const removeButton = document.createElement("button");
    removeButton.className = "button button-secondary admin-save";
    removeButton.type = "button";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", async () => {
      if (!window.confirm(
        `Remove email suppression for ${suppression.recipient_email}? `
        + "Only continue after verifying the address and recipient intent.",
      )) {
        return;
      }
      removeButton.disabled = true;
      adminEmailMessage.textContent = "Removing suppression…";
      adminEmailMessage.classList.remove("is-error", "is-success");
      try {
        const result = await adminRequest(
          `/api/admin/email-suppressions/${
            encodeURIComponent(suppression.recipient_email)
          }`,
          { method: "DELETE" },
        );
        adminEmailMessage.textContent = result.message;
        adminEmailMessage.classList.add("is-success");
        await loadEmailHealth();
      } catch (error) {
        adminEmailMessage.textContent = error.message;
        adminEmailMessage.classList.add("is-error");
        removeButton.disabled = false;
      }
    });
    actionCell.replaceChildren(removeButton);
    adminSuppressionBody.appendChild(row);
  });

  adminEmailEventBody.replaceChildren();
  adminEmailEventStatus.textContent = health.recent_events.length
    ? `${health.recent_events.length} recent email event(s).`
    : "No delivery events recorded.";
  adminEmailEventTable.classList.toggle(
    "is-hidden",
    health.recent_events.length === 0,
  );
  health.recent_events.forEach((event) => {
    const row = document.createElement("tr");
    adminCell(row, new Date(event.occurred_at).toLocaleString());
    adminCell(row, event.event_type.replaceAll("_", " "));
    adminCell(row, event.recipient_email || "Not disclosed");
    adminCell(row, event.provider.replaceAll("_", " "));
    adminCell(row, event.provider_message_id || "—");
    adminEmailEventBody.appendChild(row);
  });
}

async function loadEmailHealth() {
  const health = await adminRequest("/api/admin/email-health");
  renderEmailHealth(health);
}

function renderAccessRequests(requests) {
  adminAccessBody.replaceChildren();
  const pending = requests.filter((request) => request.status === "pending");
  adminAccessStatus.textContent = requests.length
    ? `${pending.length} pending · ${requests.length} total requests.`
    : "No access requests received.";
  adminAccessTable.classList.toggle("is-hidden", requests.length === 0);
  requests.forEach((request) => {
    const row = document.createElement("tr");
    adminCell(row, request.id);
    adminCell(row, request.organization_name);
    adminCell(
      row,
      `${request.contact_name}\n${request.email}${
        request.existing_account ? "\nExisting account" : ""
      }`,
    );
    adminCell(row, new Date(request.created_at).toLocaleString());
    adminCell(row, request.status);
    const requestedPlan = request.requested_plan || "professional";
    const requestedPrice = {
      programming_suite: 39,
      professional: 99,
      enterprise: 199,
    }[requestedPlan];
    const requestedTotal = requestedPrice
      + (request.include_stream_monitoring ? 59 : 0);
    adminCell(
      row,
      `${requestedPlan.replaceAll("_", " ")}\n${
        request.include_stream_monitoring
          ? "Stream Monitoring add-on\n"
          : ""
      }$${requestedTotal}/month`,
    );
    if (request.status !== "pending") {
      adminCell(
        row,
        request.assigned_plan
          ? `${request.assigned_plan.replaceAll("_", " ")}${
            request.assigned_stream_monitoring
              ? " + Stream Monitoring"
              : ""
          }`
          : "—",
      );
      const subscription = request.subscription;
      const paymentLabel = !subscription
        ? "—"
        : subscription.provider === "stripe_pending"
          ? "Awaiting Stripe payment"
          : subscription.provider === "complimentary"
            ? "Complimentary access"
            : subscription.access_state === "payment_grace"
              ? `Past due · ${subscription.payment_grace_hours || 72}-hour grace`
              : subscription.access_state === "payment_suspended"
                ? "Payment suspended"
            : subscription.provider === "stripe"
              ? "Active via Stripe"
              : subscription.status;
      adminCell(row, paymentLabel);
      adminCell(row, subscriptionTiming(subscription));
      adminCell(row, subscription?.waiver_reason || "—");
      adminCell(
        row,
        request.status === "rejected" ? "Rejected" : "Completed",
      );
      adminAccessBody.appendChild(row);
      return;
    }
    const planCell = document.createElement("td");
    const plan = document.createElement("input");
    plan.type = "hidden";
    plan.value = requestedPlan;
    const approvedPlan = document.createElement("strong");
    approvedPlan.textContent = requestedPlan.replaceAll("_", " ");
    const monitoringLabel = document.createElement("label");
    monitoringLabel.className = "admin-inline-checkbox";
    const monitoring = document.createElement("input");
    monitoring.type = "checkbox";
    monitoring.checked = (
      requestedPlan === "professional"
      && request.include_stream_monitoring
    );
    const monitoringText = document.createElement("span");
    monitoringText.textContent = "Stream Monitoring";
    monitoringLabel.append(monitoring, monitoringText);
    monitoring.disabled = true;
    planCell.append(approvedPlan, plan, monitoringLabel);
    row.appendChild(planCell);
    const paymentCell = document.createElement("td");
    const payment = adminSelect(
      ["Stripe checkout required", "Complimentary access"],
      "Stripe checkout required",
    );
    payment.setAttribute("aria-label", `Payment approval for ${request.id}`);
    paymentCell.appendChild(payment);
    row.appendChild(paymentCell);
    const expirationCell = document.createElement("td");
    const expiration = document.createElement("input");
    expiration.type = "date";
    expiration.disabled = true;
    const defaultExpiration = new Date();
    defaultExpiration.setDate(defaultExpiration.getDate() + 30);
    expiration.value = defaultExpiration.toISOString().slice(0, 10);
    expirationCell.appendChild(expiration);
    const recurringNote = document.createElement("small");
    recurringNote.className = "admin-row-status";
    recurringNote.textContent = "Renews automatically after payment ↻";
    expirationCell.appendChild(recurringNote);
    row.appendChild(expirationCell);
    const reasonCell = document.createElement("td");
    const reason = document.createElement("input");
    reason.type = "text";
    reason.maxLength = 500;
    reason.placeholder = "Required if waived";
    reason.disabled = true;
    reasonCell.appendChild(reason);
    row.appendChild(reasonCell);
    payment.addEventListener("change", () => {
      const complimentary = payment.value === "Complimentary access";
      expiration.disabled = !complimentary;
      expiration.classList.toggle("is-hidden", !complimentary);
      recurringNote.classList.toggle("is-hidden", complimentary);
      reason.disabled = !complimentary;
    });
    expiration.classList.add("is-hidden");
    const actionCell = document.createElement("td");
    const actionGroup = document.createElement("div");
    actionGroup.className = "admin-action-group";
    const action = adminSelect(["approve", "reject"], "approve");
    action.setAttribute("aria-label", `Action for ${request.id}`);
    const apply = document.createElement("button");
    apply.className = "button button-small button-primary";
    apply.type = "button";
    apply.textContent = "Apply";
    action.addEventListener("change", () => {
      apply.classList.toggle(
        "button-danger",
        action.value === "reject",
      );
    });
    apply.addEventListener("click", async () => {
      if (
        action.value === "reject"
        && !window.confirm(
          `Reject access request ${request.id}?`,
        )
      ) {
        return;
      }
      apply.disabled = true;
      action.disabled = true;
      if (action.value === "approve") {
        adminAccessMessage.textContent = "Creating customer account…";
        adminAccessMessage.classList.remove("is-error");
        try {
          const complimentary = payment.value === "Complimentary access";
          if (complimentary && !reason.value.trim()) {
            throw new Error(
              "Enter an internal reason for complimentary access.",
            );
          }
          const result = await adminRequest(
            `/api/admin/access-requests/${request.id}/approve`,
            {
              method: "POST",
              body: JSON.stringify({
                plan: plan.value,
                include_stream_monitoring: (
                  plan.value === "professional"
                  && monitoring.checked
                ),
                payment_method: complimentary ? "complimentary" : "stripe",
                access_expires_at: complimentary
                  ? `${expiration.value}T23:59:59Z`
                  : null,
                waiver_reason: complimentary
                  ? reason.value.trim()
                  : null,
              }),
            },
          );
          adminAccessMessage.textContent = (
            `${result.message} Activation link: ${result.activation_url}`
          );
          await loadControlPlane();
        } catch (error) {
          adminAccessMessage.textContent = error.message;
          adminAccessMessage.classList.add("is-error");
          apply.disabled = false;
          action.disabled = false;
        }
      } else {
        try {
          await adminRequest(
            `/api/admin/access-requests/${request.id}/reject`,
            { method: "POST" },
          );
          await loadControlPlane();
        } catch (error) {
          adminAccessMessage.textContent = error.message;
          adminAccessMessage.classList.add("is-error");
          apply.disabled = false;
          action.disabled = false;
        }
      }
    });
    actionGroup.append(action, apply);
    actionCell.appendChild(actionGroup);
    row.appendChild(actionCell);
    adminAccessBody.appendChild(row);
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
    if (incident.request_type) {
      adminTicketDetails.appendChild(
        adminTicketItem(
          "Privacy request type",
          incident.request_type.replaceAll("_", " "),
          incident.created_at,
        ),
      );
    }
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
    accessEnd,
    endAccess,
    lifecycleNote,
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
    const subscriptionUpdate = {
      status: subscriptionStatus.disabled ? null : subscriptionStatus.value,
      billing_cycle: billingCycle.disabled ? null : billingCycle.value,
      current_period_end: !accessEnd.disabled && accessEnd.value
        ? `${accessEnd.value}T23:59:59Z`
        : null,
      cancel_at_period_end: endAccess.disabled
        ? null
        : endAccess.checked,
      lifecycle_note: lifecycleNote.value.trim() || null,
    };
    const hasSubscriptionChange = [
      subscriptionUpdate.status,
      subscriptionUpdate.billing_cycle,
      subscriptionUpdate.current_period_end,
      subscriptionUpdate.cancel_at_period_end,
    ].some((value) => value !== null);
    if (hasSubscriptionChange) {
      await adminRequest(
        `/api/admin/organizations/${organization.id}/subscription`,
        {
          method: "PATCH",
          body: JSON.stringify(subscriptionUpdate),
        },
      );
    }
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
    adminCell(
      row,
      organization.owner_email
        ? `${organization.owner_name || "Account owner"}\n${
          organization.owner_email
        }`
        : "No owner assigned",
    );
    const planCell = adminCell(row, "");
    const plan = adminSelect(
      ["professional", "enterprise"],
      organization.plan,
    );
    planCell.replaceChildren(plan);
    const stripeManaged = ["stripe", "stripe_pending"].includes(
      organization.subscription.provider,
    );
    plan.disabled = stripeManaged;
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
    subscriptionStatus.disabled = stripeManaged;
    adminCell(
      row,
      organization.entitlements.access.active ? "Enabled" : "Blocked",
    );
    const billingCycleCell = adminCell(row, "");
    const billingCycle = adminSelect(
      ["monthly", "annual"],
      organization.subscription.billing_cycle,
    );
    billingCycleCell.replaceChildren(billingCycle);
    billingCycle.disabled = stripeManaged;
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
    const paymentLabel = organization.subscription.payment_waived
      ? "Complimentary"
      : organization.subscription.access_state === "awaiting_payment"
        ? "Awaiting payment"
        : organization.subscription.access_state === "payment_grace"
          ? "Past due · grace"
          : organization.subscription.access_state === "payment_suspended"
            ? "Suspended"
            : organization.subscription.provider === "stripe"
              ? "Stripe active"
              : organization.subscription.status;
    adminCell(row, paymentLabel);
    const accessEndCell = adminCell(row, "");
    const accessEnd = document.createElement("input");
    accessEnd.type = "date";
    accessEnd.value = organization.subscription.current_period_end
      ? organization.subscription.current_period_end.slice(0, 10)
      : "";
    const accessTiming = document.createElement("small");
    accessTiming.className = "admin-row-status";
    accessTiming.textContent = subscriptionTiming(organization.subscription);
    const fixedAccess = organization.subscription.provider === "complimentary";
    accessEnd.disabled = !fixedAccess;
    accessEnd.classList.toggle("is-hidden", !fixedAccess);
    accessEndCell.replaceChildren(accessTiming, accessEnd);
    const endAccessCell = adminCell(row, "");
    const endAccess = addonToggle(
      organization.subscription.cancel_at_period_end,
      organization.subscription.cancel_at_period_end
        ? "Ends on date"
        : "No scheduled end",
    );
    endAccess.input.disabled = stripeManaged || fixedAccess;
    if (stripeManaged) {
      endAccess.control.querySelector("span").textContent = "Managed by Stripe";
    } else if (fixedAccess) {
      endAccess.control.querySelector("span").textContent = "Fixed end date";
    }
    endAccessCell.replaceChildren(endAccess.control);
    const lifecycleNoteCell = adminCell(row, "");
    const lifecycleNote = document.createElement("input");
    lifecycleNote.type = "text";
    lifecycleNote.maxLength = 500;
    lifecycleNote.placeholder = "Reason for this change";
    const latestLifecycleEvent = document.createElement("small");
    latestLifecycleEvent.className = "admin-row-status";
    const latestEvent = organization.subscription_events?.[0];
    latestLifecycleEvent.textContent = latestEvent
      ? `${latestEvent.actor_name || "System"}: ${latestEvent.details}`
      : "No lifecycle changes recorded";
    lifecycleNoteCell.replaceChildren(lifecycleNote, latestLifecycleEvent);
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
      accessEnd,
      endAccess.input,
      lifecycleNote,
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
        } else if (control === endAccess.input) {
          endAccess.control.querySelector("span").textContent =
            control.checked ? "Ends on date" : "No scheduled end";
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
      accessEnd,
      endAccess: endAccess.input,
      lifecycleNote,
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
    const [
      overview,
      organizations,
      incidents,
      backups,
      security,
      accessRequests,
      emailHealth,
    ] = await Promise.all([
      adminRequest("/api/admin/overview"),
      adminRequest("/api/admin/organizations"),
      adminRequest("/api/admin/incidents"),
      adminRequest("/api/admin/backups"),
      adminRequest("/api/admin/security-events"),
      adminRequest("/api/admin/access-requests"),
      adminRequest("/api/admin/email-health"),
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
    renderSecurityEvents(security.events);
    renderAccessRequests(accessRequests.requests);
    renderEmailHealth(emailHealth);
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
refreshEmailHealthButton.addEventListener("click", async () => {
  refreshEmailHealthButton.disabled = true;
  adminEmailMessage.textContent = "Refreshing email health…";
  adminEmailMessage.classList.remove("is-error", "is-success");
  try {
    await loadEmailHealth();
    adminEmailMessage.textContent = "Email health refreshed.";
    adminEmailMessage.classList.add("is-success");
  } catch (error) {
    adminEmailMessage.textContent = error.message;
    adminEmailMessage.classList.add("is-error");
  } finally {
    refreshEmailHealthButton.disabled = false;
  }
});
suspendedAdminControlButton.addEventListener("click", () => {
  adminControlPlane.classList.remove("is-hidden");
  suspendedPanel.classList.add("is-hidden");
  platformContent.classList.add("is-hidden");
  loadControlPlane();
});
