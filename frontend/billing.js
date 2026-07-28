const billingOpenButton = document.querySelector("#open-billing-button");
const billingCloseButton = document.querySelector("#close-billing-button");
const billingPanel = document.querySelector("#billing-panel");
const billingMessage = document.querySelector("#billing-message");
const billingSummary = document.querySelector("#billing-summary");
const billingEntitlements = document.querySelector(
  "#billing-entitlements",
);
const billingPricingGrid = document.querySelector("#billing-pricing-grid");
const billingPricingAddons = document.querySelector(
  "#billing-pricing-addons",
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

function pricingButton(plan, currentPlan) {
  const button = document.createElement("button");
  const isCurrent = plan.name === currentPlan;
  button.className = (
    `button ${isCurrent ? "button-secondary" : "button-primary"}`
  );
  button.type = "button";
  button.textContent = isCurrent ? "Current Plan" : "Request Plan Change";
  button.disabled = isCurrent;
  if (!isCurrent) {
    button.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("btp:open-support", {
        detail: {
          category: "billing",
          summary: `Plan change request: ${plan.name}`,
          details: (
            `Please review changing our subscription to ${plan.name} `
            + `at ${billingMoney(plan.monthly_cents, "USD")}/month.`
          ),
        },
      }));
    });
  }
  return button;
}

function renderPricing(pricing) {
  billingPricingGrid.replaceChildren();
  (pricing.available_plans || []).forEach((plan) => {
    const card = document.createElement("article");
    card.className = "pricing-card";
    if (plan.featured) card.classList.add("is-featured");
    if (plan.name === pricing.display_name) card.classList.add("is-current");

    const eyebrow = document.createElement("small");
    eyebrow.textContent = plan.featured ? "Most Popular" : "Plan";
    const title = document.createElement("h4");
    title.textContent = plan.name;
    const price = document.createElement("p");
    price.className = "pricing-price";
    price.textContent = (
      `${plan.starting_at ? "From " : ""}`
      + `${billingMoney(plan.monthly_cents, "USD")}`
    );
    const period = document.createElement("span");
    period.textContent = "/month";
    price.appendChild(period);
    const description = document.createElement("p");
    description.className = "pricing-description";
    description.textContent = plan.description;
    const features = document.createElement("ul");
    plan.features.forEach((feature) => {
      const item = document.createElement("li");
      item.textContent = feature;
      features.appendChild(item);
    });
    card.append(
      eyebrow,
      title,
      price,
      description,
      features,
      pricingButton(plan, pricing.display_name),
    );
    billingPricingGrid.appendChild(card);
  });

  billingPricingAddons.replaceChildren();
  (pricing.available_addons || []).forEach((addon) => {
    const card = document.createElement("div");
    const copy = document.createElement("div");
    const label = document.createElement("small");
    label.textContent = "Optional Add-on";
    const title = document.createElement("strong");
    title.textContent = addon.name;
    const description = document.createElement("p");
    description.textContent = addon.description;
    copy.append(label, title, description);
    const price = document.createElement("strong");
    price.className = "pricing-addon-price";
    price.textContent = (
      `+${billingMoney(addon.monthly_cents, "USD")}/month`
    );
    const actions = document.createElement("div");
    actions.className = "pricing-addon-actions";
    const button = document.createElement("button");
    const isIncluded = pricing.display_name === "Enterprise";
    const isActive = (pricing.addons || []).some(
      (item) => item.code === addon.code,
    );
    button.className = (
      `button ${isIncluded || isActive
        ? "button-secondary"
        : "button-primary"}`
    );
    button.type = "button";
    button.textContent = isIncluded
      ? "Included"
      : (isActive ? "Active Add-on" : "Request Add-on");
    button.disabled = isIncluded || isActive;
    if (!button.disabled) {
      button.addEventListener("click", () => {
        window.dispatchEvent(new CustomEvent("btp:open-support", {
          detail: {
            category: "billing",
            summary: `Add-on request: ${addon.name}`,
            details: (
              `Please review adding ${addon.name} to our subscription `
              + `at ${billingMoney(addon.monthly_cents, "USD")}/month.`
            ),
          },
        }));
      });
    }
    actions.append(price, button);
    card.append(copy, actions);
    billingPricingAddons.appendChild(card);
  });
}

function renderBilling(payload) {
  const subscription = payload.subscription;
  const pricing = payload.pricing;
  billingSummary.replaceChildren(
    billingCard(
      "Plan",
      pricing.display_name,
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
      `${billingMoney(
        pricing.billing_total_cents,
        pricing.currency,
      )}/${pricing.billing_period}`,
    ),
  );
  renderPricing(pricing);

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
        billingCard(
          "Included",
          module.name,
          subscription.plan === "enterprise"
            ? "Enterprise plan"
            : `${pricing.base.name} plan`,
        ),
      );
    });
  addons
    .filter((addon) => addon.enabled)
    .forEach((addon) => {
      const enterprise = subscription.plan === "enterprise";
      const addonPricing = (pricing.addons || []).find(
        (item) => item.code === addon.code,
      );
      billingEntitlements.appendChild(
        billingCard(
          enterprise ? "Included" : "Add-on",
          addon.name,
          enterprise
            ? "Enterprise plan"
            : `${billingMoney(
                addonPricing?.monthly_cents,
                pricing.currency,
              )}/month`,
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
