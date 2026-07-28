const billingOpenButton = document.querySelector("#open-billing-button");
const billingCloseButton = document.querySelector("#close-billing-button");
const billingPanel = document.querySelector("#billing-panel");
const billingMessage = document.querySelector("#billing-message");
const billingSummary = document.querySelector("#billing-summary");
const billingEntitlements = document.querySelector(
  "#billing-entitlements",
);
const billingInvoiceStatus = document.querySelector(
  "#billing-invoice-status",
);
const billingInvoiceTable = document.querySelector(
  "#billing-invoice-table",
);
const billingInvoiceBody = document.querySelector("#billing-invoice-body");
let billingOrganization = null;

function billingDate(value) {
  if (!value) return "Not scheduled";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function billingMoney(cents, currency) {
  if (cents === null || cents === undefined) return "Pricing pending";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currency || "USD",
  }).format(cents / 100);
}

function billingCard(label, value, detail = "") {
  const card = document.createElement("div");
  const small = document.createElement("small");
  const strong = document.createElement("strong");
  small.textContent = label;
  strong.textContent = value;
  card.append(small, strong);
  if (detail) {
    const paragraph = document.createElement("p");
    paragraph.textContent = detail;
    card.appendChild(paragraph);
  }
  return card;
}

function renderBilling(payload) {
  const subscription = payload.subscription;
  billingSummary.replaceChildren(
    billingCard(
      "Plan",
      subscription.plan[0].toUpperCase() + subscription.plan.slice(1),
      subscription.organization_name,
    ),
    billingCard(
      "Subscription",
      subscription.status.replace("_", " "),
      `${subscription.billing_cycle} billing`,
    ),
    billingCard(
      subscription.cancel_at_period_end ? "Access Until" : "Renews",
      billingDate(subscription.current_period_end),
      billingMoney(subscription.amount_cents, subscription.currency),
    ),
  );

  const modules = Object.values(payload.entitlements.modules || {});
  const addons = payload.entitlements.addons || [];
  billingEntitlements.replaceChildren();
  modules
    .filter((module) => (
      module.enabled
      && module.available !== false
      && module.source === "professional"
    ))
    .forEach((module) => {
      billingEntitlements.appendChild(
        billingCard("Included", module.name, "Professional plan"),
      );
    });
  addons
    .filter((addon) => addon.enabled)
    .forEach((addon) => {
      const enterprise = subscription.plan === "enterprise";
      billingEntitlements.appendChild(
        billingCard(
          enterprise ? "Included" : "Add-on",
          addon.name,
          enterprise ? "Enterprise plan" : "Enabled",
        ),
      );
    });

  const invoices = payload.invoices || [];
  billingInvoiceBody.replaceChildren();
  billingInvoiceTable.classList.toggle("is-hidden", !invoices.length);
  billingInvoiceStatus.textContent = invoices.length
    ? `${invoices.length} invoice(s).`
    : "No invoices have been issued.";
  invoices.forEach((invoice) => {
    const row = document.createElement("tr");
    [
      invoice.id,
      billingDate(invoice.invoice_date),
      invoice.status,
      billingMoney(invoice.amount_due_cents, invoice.currency),
    ].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.appendChild(cell);
    });
    billingInvoiceBody.appendChild(row);
  });
}

async function loadBilling() {
  if (!billingOrganization) return;
  billingMessage.textContent = "Loading subscription…";
  billingMessage.classList.remove("is-error");
  try {
    const payload = await authRequest(
      `/api/billing/organizations/${billingOrganization.id}`,
    );
    renderBilling(payload);
    billingMessage.textContent = "";
  } catch (error) {
    billingMessage.textContent = error.message;
    billingMessage.classList.add("is-error");
  }
}

window.addEventListener("btp:identity", (event) => {
  const organization = event.detail?.organizations?.[0];
  billingOrganization = organization || null;
  const allowed = ["owner", "admin"].includes(organization?.role);
  billingOpenButton.classList.toggle("is-hidden", !allowed);
  if (!allowed) billingPanel.classList.add("is-hidden");
});

billingOpenButton.addEventListener("click", () => {
  billingPanel.classList.remove("is-hidden");
  accountPanel.classList.add("is-hidden");
  platformContent.classList.add("is-hidden");
  loadBilling();
});

billingCloseButton.addEventListener("click", () => {
  billingPanel.classList.add("is-hidden");
  applyOrganizationAccess(currentIdentity);
});
