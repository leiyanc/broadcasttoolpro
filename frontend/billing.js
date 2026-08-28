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
const billingProviderNote = document.querySelector("#billing-provider-note");
const billingSubscriptionActions = document.querySelector(
  "#billing-subscription-actions",
);
const billingConfirmation = document.querySelector("#billing-confirmation");
const billingChangeSummary = document.querySelector("#billing-change-summary");
const billingChangeNotice = document.querySelector("#billing-change-notice");
const billingChangeBack = document.querySelector("#billing-change-back");
const billingChangeConfirm = document.querySelector("#billing-change-confirm");
const billingMonitoringChoice = document.querySelector(
  "#billing-monitoring-choice",
);
const billingMonitoringChoiceInput = document.querySelector(
  "#billing-monitoring-choice-input",
);
let billingOrganization = null;
let latestBillingPayload = null;
let billingPaymentsAvailable = false;
let pendingBillingChange = null;

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
  "Media Loudness Compliance included": "billing.feature.mediaQc",
  "Higher channel and user limits": "billing.feature.higherLimits",
  "Advanced auditability": "billing.feature.auditability",
  "Priority onboarding and support": "billing.feature.prioritySupport",
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

function billingDateTime(value) {
  if (!value) return billingText("billing.notScheduled", "Not scheduled");
  return new Date(value).toLocaleString(billingLocale(), {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
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

function changeSummaryRow(label, value) {
  const row = document.createElement("div");
  const name = document.createElement("span");
  const amount = document.createElement("strong");
  name.textContent = label;
  amount.textContent = value;
  row.append(name, amount);
  return row;
}

function closeBillingConfirmation() {
  pendingBillingChange = null;
  billingConfirmation.classList.add("is-hidden");
}

function renderSubscriptionChangePreview(planCode, includeStreamMonitoring, preview) {
  pendingBillingChange = {planCode, includeStreamMonitoring, preview};
  const planName = {
    programming_suite: "Programming Suite",
    professional: "Professional",
    enterprise: "Enterprise",
  }[planCode];
  const canChooseMonitoring = ["programming_suite", "professional"].includes(
    planCode,
  );
  billingMonitoringChoice.classList.toggle("is-hidden", !canChooseMonitoring);
  billingMonitoringChoiceInput.checked = preview.include_stream_monitoring;
  billingChangeSummary.replaceChildren(
    changeSummaryRow("New plan", planName),
    changeSummaryRow(
      "Stream Monitoring",
      preview.include_stream_monitoring
        ? "Added — $59.00/month"
        : (planCode === "enterprise" ? "Included" : "Not included"),
    ),
    changeSummaryRow(
      "Due now",
      billingMoney(preview.amount_due_now_cents, preview.currency),
    ),
    changeSummaryRow(
      "New monthly total",
      billingMoney(preview.recurring_monthly_cents, preview.currency),
    ),
    changeSummaryRow(
      "Effective",
      preview.effective === "immediately"
        ? "Immediately"
        : billingDate(preview.effective_at),
    ),
  );
  billingChangeNotice.textContent = preview.effective === "immediately"
    ? "The amount due now includes Stripe's prorated charge and credit for the current billing period. Your plan updates after payment succeeds."
    : "No charge is due today. Your current plan remains active through the end of this billing period, then the new monthly total begins.";
}

async function requestSubscriptionChange(planCode, includeStreamMonitoring) {
  billingMessage.textContent = "Calculating your exact cost summary…";
  billingMessage.classList.remove("is-error");
  try {
    const preview = await authRequest(
      `/api/billing/organizations/${billingOrganization.id}/change/preview`,
      {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          plan_code: planCode,
          include_stream_monitoring: includeStreamMonitoring,
        }),
      },
    );
    renderSubscriptionChangePreview(
      planCode, includeStreamMonitoring, preview,
    );
    billingConfirmation.classList.remove("is-hidden");
    billingMessage.textContent = "";
    return true;
  } catch (error) {
    billingMessage.textContent = error.message;
    billingMessage.classList.add("is-error");
    return false;
  }
}

async function confirmSubscriptionChange() {
  if (!pendingBillingChange) return;
  billingChangeConfirm.disabled = true;
  billingChangeBack.disabled = true;
  try {
    const result = await authRequest(
      `/api/billing/organizations/${billingOrganization.id}/change`,
      {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          plan_code: pendingBillingChange.planCode,
          include_stream_monitoring: pendingBillingChange.includeStreamMonitoring,
        }),
      },
    );
    closeBillingConfirmation();
    await loadBilling();
    billingMessage.textContent = result.effective === "immediately"
      ? "Your subscription was updated immediately."
      : result.effective === "pending_payment"
        ? "Payment must complete before your current plan changes."
        : `Your subscription change is scheduled for ${billingDate(result.change_at)}.`;
  } catch (error) {
    billingChangeNotice.textContent = error.message;
    billingChangeNotice.classList.add("is-error");
  } finally {
    billingChangeConfirm.disabled = false;
    billingChangeBack.disabled = false;
  }
}

async function setCancellation(cancel) {
  const action = cancel ? "cancel" : "resume";
  if (!window.confirm(
    cancel
      ? "Cancel at the end of the current billing period? Access will remain active until then."
      : "Resume automatic renewal for this subscription?",
  )) return;
  billingMessage.textContent = `${action === "cancel" ? "Scheduling cancellation" : "Resuming renewal"}…`;
  billingMessage.classList.remove("is-error");
  try {
    await authRequest(
      `/api/billing/organizations/${billingOrganization.id}/cancellation?cancel=${cancel}`,
      {method: "POST"},
    );
    await loadBilling();
    billingMessage.textContent = cancel
      ? "Cancellation scheduled. Access remains active through the current period."
      : "Automatic renewal resumed.";
  } catch (error) {
    billingMessage.textContent = error.message;
    billingMessage.classList.add("is-error");
  }
}

async function cancelScheduledSubscriptionChange() {
  if (!window.confirm(
    "Cancel the scheduled plan change and keep your current subscription?",
  )) return;
  billingMessage.textContent = "Canceling the scheduled change…";
  billingMessage.classList.remove("is-error");
  try {
    await authRequest(
      `/api/billing/organizations/${billingOrganization.id}/change/cancel`,
      {method: "POST"},
    );
    await loadBilling();
    billingMessage.textContent = "Scheduled change canceled. Your current plan remains active.";
  } catch (error) {
    billingMessage.textContent = error.message;
    billingMessage.classList.add("is-error");
  }
}

function pricingButton(plan, currentPlan) {
  const button = document.createElement("button");
  const isCurrent = plan.name === currentPlan;
  const approvedCheckout = latestBillingPayload?.approved_checkout;
  const isApprovedPlan = approvedCheckout?.plan_code === plan.code;
  const lockedToApprovedPlan = Boolean(approvedCheckout?.plan_code);
  const isStripeCurrent = (
    isCurrent
    && latestBillingPayload?.subscription?.provider === "stripe"
    && latestBillingPayload?.subscription?.status !== "canceled"
  );
  const canCancelScheduledChange = Boolean(
    isStripeCurrent
    && latestBillingPayload?.subscription?.pending_plan_code,
  );
  const paymentProblem = isStripeCurrent && [
    "payment_grace", "payment_suspended",
  ].includes(latestBillingPayload?.subscription?.access_state);
  const payableInvoice = (latestBillingPayload?.invoices || []).find(
    (invoice) => invoice.hosted_invoice_url
      && !["paid", "void"].includes(invoice.status),
  );
  const canSubscribeCurrent = (
    isCurrent && billingPaymentsAvailable && !isStripeCurrent
  );
  const awaitingPayment = (
    latestBillingPayload?.subscription?.provider === "stripe_pending"
    && latestBillingPayload?.subscription?.status === "past_due"
  );
  button.className = (
    `button ${isCurrent ? "button-secondary" : "button-primary"}`
  );
  button.type = "button";
  button.textContent = (lockedToApprovedPlan && !isApprovedPlan)
    ? billingText("billing.notSelected", "Not Selected")
    : (isApprovedPlan
      ? billingText("billing.completeSubscription", "Complete Subscription")
      : (isCurrent && !canSubscribeCurrent)
    ? (paymentProblem
      ? billingText("billing.updatePayment", "Update Payment")
      : (canCancelScheduledChange
        ? "Cancel Scheduled Change"
        : billingText("billing.currentPlan", "Current Plan")))
    : (billingPaymentsAvailable
      ? (isCurrent
        ? (awaitingPayment
          ? billingText("billing.completeSubscription", "Complete Subscription")
          : billingText("billing.subscribe", "Subscribe"))
        : billingText("billing.choosePlan", "Choose Plan"))
      : billingText("billing.requestPlan", "Request Plan Change")));
  button.disabled = (lockedToApprovedPlan && !isApprovedPlan)
    || (isCurrent && !canSubscribeCurrent && !paymentProblem
      && !isApprovedPlan && !canCancelScheduledChange)
    || (paymentProblem && !payableInvoice)
    || (awaitingPayment && !isCurrent);
  if (!button.disabled) {
    button.addEventListener("click", () => {
      if (canCancelScheduledChange) {
        cancelScheduledSubscriptionChange();
        return;
      }
      if (paymentProblem && payableInvoice) {
        window.location.assign(payableInvoice.hosted_invoice_url);
        return;
      }
      if (billingPaymentsAvailable) {
        const monitoringApproved = isApprovedPlan
          ? Boolean(approvedCheckout.include_stream_monitoring)
          : false;
        if (latestBillingPayload?.subscription?.provider === "stripe") {
          requestSubscriptionChange(plan.code, monitoringApproved);
        } else {
          startCheckout(plan.code, monitoringApproved);
        }
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
    if (isActive) button.title = "Active Add-on — remove at period end";
    button.textContent = isIncluded
      ? billingText("billing.included", "Included")
      : (isActive
        ? "Remove Add-on"
        : (billingPaymentsAvailable
          ? "Add Stream Monitoring"
          : billingText("billing.requestAddon", "Request Add-on")));
    button.disabled = isIncluded;
    if (!button.disabled) {
      button.addEventListener("click", () => {
        if (billingPaymentsAvailable) {
          const planCode = latestBillingPayload.subscription.plan === "starter"
            ? "programming_suite"
            : latestBillingPayload.subscription.plan;
          if (latestBillingPayload.subscription.provider === "stripe") {
            requestSubscriptionChange(planCode, !isActive);
          } else {
            startCheckout(planCode, true);
          }
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
  if (billingProviderNote) {
    const providerKey = billingPaymentsAvailable
      ? "billing.providerConnectedNote"
      : "billing.providerNote";
    const providerFallback = billingPaymentsAvailable
      ? (
          "Payments and saved payment methods are securely managed by Stripe. "
          + "Broadcast Tool Pro does not store card details."
        )
      : (
          "Online payment management will become available when the payment "
          + "provider is connected. No payment method is stored by Broadcast "
          + "Tool Pro at this stage."
        );
    billingProviderNote.dataset.i18n = providerKey;
    billingProviderNote.textContent = billingText(
      providerKey,
      providerFallback,
    );
    billingProviderNote.appendChild(document.createTextNode(" "));
    const billingContact = document.createElement("a");
    billingContact.href = "mailto:billing@broadcasttoolpro.com";
    billingContact.textContent = billingText(
      "billing.contact",
      "Contact Billing",
    );
    billingProviderNote.appendChild(billingContact);
  }
  const subscription = payload.subscription;
  const approvedPlan = payload.approved_checkout?.plan_code;
  const pricing = (
    approvedPlan && approvedPlan !== payload.pricing.plan_code
      ? {
          ...payload.pricing,
          plan_code: approvedPlan,
          display_name: {
            programming_suite: "Programming Suite",
            professional: "Professional",
            enterprise: "Enterprise",
          }[approvedPlan],
          monthly_cents: {
            programming_suite: 3900,
            professional: 9900,
            enterprise: 19900,
          }[approvedPlan],
          billing_total_cents: {
            programming_suite: 3900,
            professional: 9900,
            enterprise: 19900,
          }[approvedPlan] + (
            payload.approved_checkout?.include_stream_monitoring ? 5900 : 0
          ),
        }
      : payload.pricing
  );
  latestBillingPayload = {...payload, pricing};
  const complimentary = subscription.payment_waived;
  const awaitingPayment = (
    subscription.provider === "stripe_pending"
    && subscription.status === "past_due"
  );
  const paymentGrace = subscription.access_state === "payment_grace";
  const paymentSuspended = (
    subscription.access_state === "payment_suspended"
  );
  let subscriptionValue = billingStatus(subscription.status);
  let subscriptionDetail = billingText(
    "billing.billingCycle",
    "{cycle} billing",
    {cycle: billingStatus(subscription.billing_cycle)},
  );
  if (complimentary) {
    subscriptionValue = billingText(
      "billing.complimentary",
      "Complimentary access",
    );
    subscriptionDetail = billingText(
      "billing.paymentWaived",
      "Payment waived by Broadcast Tool Pro",
    );
  } else if (awaitingPayment) {
    subscriptionValue = billingText(
      "billing.awaitingPayment",
      "Awaiting Payment",
    );
    subscriptionDetail = billingText(
      "billing.paymentRequired",
      "Complete secure Stripe Checkout to activate access",
    );
  } else if (paymentGrace) {
    subscriptionValue = billingText(
      "billing.paymentPastDue",
      "Payment Past Due",
    );
    subscriptionDetail = billingText(
      "billing.graceActive",
      "Access remains active during the {hours}-hour grace period",
      {hours: subscription.payment_grace_hours || 72},
    );
  } else if (paymentSuspended) {
    subscriptionValue = billingText(
      "billing.paymentSuspended",
      "Payment Suspended",
    );
    subscriptionDetail = billingText(
      "billing.restorePayment",
      "Pay the open invoice to restore access automatically",
    );
  }
  let timingLabel = billingText("billing.renews", "Renews");
  let timingValue = billingDate(subscription.current_period_end);
  let timingDetail = `${billingMoney(
    pricing.billing_total_cents,
    pricing.currency,
  )}/${pricing.billing_period}`;
  if (["canceled", "cancelled"].includes(subscription.status)) {
    timingLabel = billingText("billing.renewal", "Renewal");
    timingValue = billingText("billing.notScheduled", "Not scheduled");
    timingDetail = billingText(
      "billing.startNewSubscription",
      "Choose a plan to start a new subscription",
    );
  } else if (awaitingPayment) {
    timingLabel = billingText("billing.startsAfterPayment", "Starts After Payment");
    timingValue = billingText("billing.checkoutRequired", "Stripe Checkout required");
    timingDetail = billingText("billing.recurringAfterPayment", "Renews automatically after activation");
  } else if (paymentGrace || paymentSuspended) {
    timingLabel = paymentGrace
      ? billingText("billing.graceEnds", "Grace Ends")
      : billingText("billing.suspendedSince", "Suspended Since");
    timingValue = billingDateTime(subscription.grace_period_ends_at);
    timingDetail = billingText(
      "billing.dataPreserved",
      "Files, history, and settings remain preserved",
    );
  } else if (complimentary || subscription.cancel_at_period_end) {
    timingLabel = billingText("billing.accessUntil", "Access Until");
    timingValue = billingDate(
      subscription.waiver_expires_at || subscription.current_period_end,
    );
    timingDetail = complimentary
      ? billingText("billing.noPayment", "No payment due")
      : billingText("billing.willNotRenew", "Will not renew automatically");
  }
  billingSummary.replaceChildren(
    billingCard(
      billingText("billing.plan", "Plan"),
      pricing.display_name,
      subscription.organization_name,
    ),
    billingCard(
      billingText("billing.subscription", "Subscription"),
      subscriptionValue,
      subscriptionDetail,
    ),
    billingCard(
      timingLabel,
      timingValue,
      timingDetail,
    ),
  );
  billingSubscriptionActions.replaceChildren();
  if (subscription.pending_plan_code) {
    const pending = document.createElement("p");
    pending.className = "billing-pending-change";
    const pendingName = {
      programming_suite: "Programming Suite",
      professional: "Professional",
      enterprise: "Enterprise",
    }[subscription.pending_plan_code];
    pending.textContent = (
      `Scheduled change: ${pendingName}`
      + (subscription.pending_stream_monitoring ? " + Stream Monitoring" : "")
      + ` on ${billingDate(subscription.pending_change_at)}.`
    );
    billingSubscriptionActions.appendChild(pending);
  }
  if (subscription.provider === "stripe" && subscription.status !== "canceled") {
    const cancellationButton = document.createElement("button");
    cancellationButton.className = "button button-secondary";
    cancellationButton.type = "button";
    cancellationButton.textContent = subscription.cancel_at_period_end
      ? "Resume Subscription"
      : "Cancel at Period End";
    cancellationButton.addEventListener("click", () => {
      setCancellation(!subscription.cancel_at_period_end);
    });
    billingSubscriptionActions.appendChild(cancellationButton);
  }
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

billingChangeBack.addEventListener("click", closeBillingConfirmation);
billingChangeConfirm.addEventListener("click", confirmSubscriptionChange);
billingMonitoringChoiceInput.addEventListener("change", async () => {
  if (!pendingBillingChange) return;
  const planCode = pendingBillingChange.planCode;
  const previousMonitoring = pendingBillingChange.includeStreamMonitoring;
  const includeStreamMonitoring = billingMonitoringChoiceInput.checked;
  billingMonitoringChoiceInput.disabled = true;
  billingChangeConfirm.disabled = true;
  billingChangeNotice.textContent = "Recalculating your cost summary…";
  const updated = await requestSubscriptionChange(
    planCode, includeStreamMonitoring,
  );
  if (!updated) billingMonitoringChoiceInput.checked = previousMonitoring;
  billingMonitoringChoiceInput.disabled = false;
  billingChangeConfirm.disabled = false;
});

window.addEventListener("btp:languagechange", () => {
  if (latestBillingPayload) renderBilling(latestBillingPayload);
});
