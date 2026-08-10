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
let latestBillingPayload = null;
let billingPaymentsAvailable = false;

function billingText(key, fallback, values = {}) {
  let text = window.BTPi18n?.t(key, fallback) ?? fallback;
  Object.entries(values).forEach(([name, value]) => {
    text = text.replaceAll(`{${name}}`, String(value));
  });
  return text;
}

function billingLocale() {
  return window.BTPi18n?.getLanguage?.() === "es" ? "es" : "en";
}

const billingFeatureKeys = {
  "Everything in Programming Suite": "billing.feature.everythingProgramming",
  "Everything in Professional": "billing.feature.everythingProfessional",
  "Branded Excel and PDF reports": "billing.feature.brandedReports",
  "Multi-format playlist and As-Run imports": "billing.feature.multiFormat",
  "Stream Monitoring included": "billing.feature.monitoringIncluded",
  "Higher channel and user limits": "billing.feature.higherLimits",
  "Advanced auditability": "billing.feature.auditability",
  "Priority onboarding and support": "billing.feature.prioritySupport",
  "Media QC: loudness, captions, black frames, and freeze frames": (
    "billing.feature.mediaQc"
  ),
};

function billingFeature(label) {
  const key = billingFeatureKeys[label];
  return key ? billingText(key, label) : label;
}

function billingPlanDescription(plan) {
  const keys = {
    programming_suite: "billing.plan.programming",
    professional: "billing.plan.professional",
    enterprise: "billing.plan.enterprise",
  };
  return billingText(keys[plan.code], plan.description);
}

function billingStatus(status) {
  const normalized = String(status || "").replaceAll("_", " ");
  const translations = billingLocale() === "es"
    ? {
        active: "Activa",
        canceled: "Cancelada",
        cancelled: "Cancelada",
        pending: "Pendiente",
        paid: "Pagada",
        open: "Abierta",
        monthly: "mensual",
        annual: "anual",
      }
    : {};
  return translations[normalized.toLowerCase()] || normalized;
}

function billingDate(value) {
  if (!value) return billingText("billing.notScheduled", "Not scheduled");
  return new Date(value).toLocaleDateString(billingLocale(), {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function billingMoney(cents, currency) {
  if (cents === null || cents === undefined) {
    return billingText("billing.pricingPending", "Pricing pending");
  }
  return new Intl.NumberFormat(billingLocale(), {
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

async function startCheckout(planCode, includeStreamMonitoring = false) {
  if (!billingOrganization) return;
  billingMessage.textContent = billingText(
    "billing.redirecting",
    "Opening secure Stripe Checkout…",
  );
  billingMessage.classList.remove("is-error");
  try {
    const result = await authRequest(
      `/api/billing/organizations/${billingOrganization.id}/checkout`,
      {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          plan_code: planCode,
          include_stream_monitoring: includeStreamMonitoring,
        }),
      },
    );
    window.location.assign(result.checkout_url);
  } catch (error) {
    billingMessage.textContent = error.message;
    billingMessage.classList.add("is-error");
  }
}

function pricingButton(plan, currentPlan) {
  const button = document.createElement("button");
  const isCurrent = plan.name === currentPlan;
  const isStripeCurrent = (
    isCurrent
    && latestBillingPayload?.subscription?.provider === "stripe"
    && ["active", "trialing"].includes(
      latestBillingPayload?.subscription?.status,
    )
  );
  const canSubscribeCurrent = (
    isCurrent && billingPaymentsAvailable && !isStripeCurrent
  );
  button.className = (
    `button ${isCurrent ? "button-secondary" : "button-primary"}`
  );
  button.type = "button";
  button.textContent = (isCurrent && !canSubscribeCurrent)
    ? billingText("billing.currentPlan", "Current Plan")
    : (billingPaymentsAvailable
      ? (isCurrent
        ? billingText("billing.subscribe", "Subscribe")
        : billingText("billing.choosePlan", "Choose Plan"))
      : billingText("billing.requestPlan", "Request Plan Change"));
  button.disabled = isCurrent && !canSubscribeCurrent;
  if (!button.disabled) {
    button.addEventListener("click", () => {
      if (billingPaymentsAvailable) {
        startCheckout(plan.code);
        return;
      }
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
    eyebrow.textContent = plan.featured
      ? billingText("billing.mostPopular", "Most Popular")
      : billingText("billing.plan", "Plan");
    const title = document.createElement("h4");
    title.textContent = plan.name;
    const price = document.createElement("p");
    price.className = "pricing-price";
    price.textContent = (
      `${plan.starting_at ? billingText("billing.from", "From ") : ""}`
      + `${billingMoney(plan.monthly_cents, "USD")}`
    );
    const period = document.createElement("span");
    period.textContent = billingText("billing.perMonth", "/month");
    price.appendChild(period);
    const description = document.createElement("p");
    description.className = "pricing-description";
    description.textContent = billingPlanDescription(plan);
    const features = document.createElement("ul");
    plan.features.forEach((feature) => {
      const item = document.createElement("li");
      const label = typeof feature === "string" ? feature : feature.label;
      item.append(document.createTextNode(billingFeature(label)));
      if (typeof feature !== "string" && feature.status) {
        const status = document.createElement("span");
        status.className = "pricing-feature-status";
        status.textContent = feature.status === "Coming Soon"
          ? billingText("billing.comingSoon", "Coming Soon")
          : feature.status;
        item.appendChild(status);
      }
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
    label.textContent = billingText("billing.optionalAddon", "Optional Add-on");
    const title = document.createElement("strong");
    title.textContent = addon.name;
    const description = document.createElement("p");
    description.textContent = addon.code === "stream_monitoring"
      ? billingText("billing.addon.stream", addon.description)
      : addon.description;
    copy.append(label, title, description);
    const price = document.createElement("strong");
    price.className = "pricing-addon-price";
    price.textContent = (
      `+${billingMoney(addon.monthly_cents, "USD")}`
      + billingText("billing.perMonth", "/month")
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
      ? billingText("billing.included", "Included")
      : (isActive
        ? billingText("billing.activeAddon", "Active Add-on")
        : billingText("billing.requestAddon", "Request Add-on"));
    button.disabled = isIncluded || isActive;
    if (!button.disabled) {
      button.addEventListener("click", () => {
        if (billingPaymentsAvailable && pricing.display_name === "Professional") {
          startCheckout("professional", true);
          return;
        }
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
  latestBillingPayload = payload;
  billingPaymentsAvailable = Boolean(payload.payments_available);
  const subscription = payload.subscription;
  const pricing = payload.pricing;
  const complimentary = subscription.payment_waived;
  billingSummary.replaceChildren(
    billingCard(
      billingText("billing.plan", "Plan"),
      pricing.display_name,
      subscription.organization_name,
    ),
    billingCard(
      billingText("billing.subscription", "Subscription"),
      complimentary
        ? billingText("billing.complimentary", "Complimentary access")
        : billingStatus(subscription.status),
      complimentary
        ? billingText(
          "billing.paymentWaived",
          "Payment waived by Broadcast Tool Pro",
        )
        : billingText("billing.billingCycle", "{cycle} billing", {
          cycle: billingStatus(subscription.billing_cycle),
        }),
    ),
    billingCard(
      complimentary || subscription.cancel_at_period_end
        ? billingText("billing.accessUntil", "Access Until")
        : billingText("billing.renews", "Renews"),
      billingDate(
        subscription.waiver_expires_at
        || subscription.current_period_end,
      ),
      complimentary
        ? billingText("billing.noPayment", "No payment due")
        : `${billingMoney(
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
          billingText("billing.included", "Included"),
          module.name,
          subscription.plan === "enterprise"
            ? billingText("billing.enterprisePlan", "Enterprise plan")
            : billingText("billing.namedPlan", "{plan} plan", {
              plan: pricing.base.name,
            }),
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
          enterprise
            ? billingText("billing.included", "Included")
            : billingText("billing.addon", "Add-on"),
          addon.name,
          enterprise
            ? billingText("billing.enterprisePlan", "Enterprise plan")
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
    ? billingText("billing.invoiceCount", "{count} invoice(s).", {
      count: invoices.length,
    })
    : billingText("billing.noInvoices", "No invoices have been issued.");
  invoices.forEach((invoice) => {
    const row = document.createElement("tr");
    [
      invoice.id,
      billingDate(invoice.invoice_date),
      billingStatus(invoice.status),
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
  billingMessage.textContent = billingText(
    "billing.loading",
    "Loading subscription…",
  );
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

window.addEventListener("btp:languagechange", () => {
  if (latestBillingPayload) renderBilling(latestBillingPayload);
});
