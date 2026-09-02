# Manual Billing Operations

## Purpose

This procedure controls self-service Stripe subscriptions, per-channel quantity
changes, and approved complimentary or manual exceptions.

## Stripe recurring access

1. The customer creates an organization and enters only the customer-facing
   name of its required first channel. BTP generates the initial Channel ID;
   time zone and language are configured later in the relevant workflow.
2. The customer selects a plan and continues to hosted Stripe Checkout.
3. Only the confirmed webhook activates recurring paid access and establishes
   the organization's renewal date.
4. Administrators verify plan, channel quantity, add-ons, and invoice status in
   Billing when support intervention is required.

An access request, approval, Checkout redirect, or return page is not proof of
payment. Stripe stores the payment method and performs monthly renewal; Broadcast
Tool Pro stores no card details.

If renewal fails, access remains active for the configured 72-hour grace period.
At grace expiration, module access is suspended without deleting customer data.
Confirmed recovery restores access automatically.

## Per-channel subscription operations

- Every paid organization has one recurring subscription and one renewal date.
- Each plan includes one active registered channel. Additional channels use the
  plan-specific Stripe Price and quantity; they are not separate subscriptions.
- Programming Suite additional channels are $25/month, Professional additional
  channels are $49/month, and Enterprise additional channels are $79/month.
- Professional Stream Monitoring is $59/month for each channel on which it is
  enabled. Enterprise includes Stream Monitoring.

### Adding a channel

1. Confirm the customer is an organization Owner or Admin.
2. Confirm the channel name and whether Professional Stream Monitoring
   applies. BTP creates the stable Channel ID automatically.
3. Require the customer to review Stripe's exact prorated amount before
   confirmation.
4. Activate the channel only after Stripe accepts the subscription quantity
   change. The new channel joins the existing organization billing cycle.
5. Confirm that Billing and the active-channel selector show the new channel.
6. In Channel Settings, confirm the channel's primary language before its first
   XMLTV export. Original-language and rating-system metadata belong to each
   programme and are not channel billing attributes.

If Stripe rejects the update, do not create or activate the channel.

### Removing a channel

1. Confirm that at least two channels are active; the final active channel
   cannot be removed.
2. Show the customer the effective renewal date, the monthly reduction, and a
   $0 amount due or credited today.
3. Schedule the Stripe quantity reduction for the current period end with no
   proration. Keep the channel active through that date.
4. At the effective date, mark the channel inactive while preserving its
   reports, invoices, configuration references, and audit history.
5. If the customer reverses the request before renewal, release the Stripe
   schedule and clear the channel's scheduled deactivation.

Only one Stripe subscription schedule may control the subscription at a time.
A scheduled plan change must be completed or canceled before a channel removal
can be scheduled, and vice versa.

## Stripe webhook operations

- The active Sandbox destination is
  `https://broadcasttoolpro.com/api/billing/stripe/webhook`.
- It listens for subscription created, updated, and deleted events plus invoice
  paid and payment-failed events.
- Its signing secret is stored only in the Render environment as
  `BTP_STRIPE_WEBHOOK_SECRET`.
- When rotating or migrating the destination, deploy the new signing secret,
  verify a real reversible subscription update returns HTTP 200, restore the
  subscription state, and only then delete the old destination.
- Stripe-generated test payloads are not an entitlement test because they may
  omit the Broadcast Tool Pro organization metadata.

## Complimentary access

1. Select **Complimentary access** under Payment Approval.
2. Set a mandatory access expiration date.
3. Record a clear internal reason.
4. Approve the request.

Complimentary access expires automatically. Extending it requires a new,
documented administrative decision.

## Current limitations

- Broadcast Tool Pro never collects or stores payment methods; Stripe hosts the
  payment form.
- Manual subscriptions, if exceptionally used, require independent proof of
  cleared payment.
- Refund exceptions remain controlled outside the platform. Channel removals
  are scheduled in BTP for period end and never create an automatic mid-cycle
  refund or credit.
- Self-service launch still requires the complete live subscription and
  per-channel lifecycle to pass release acceptance.
