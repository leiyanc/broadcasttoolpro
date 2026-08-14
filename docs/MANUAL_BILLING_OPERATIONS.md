# Manual Billing Operations

## Purpose

This procedure controls paid and complimentary account activation when Stripe
Checkout is unavailable or an approved commercial exception requires manual
handling.

## Stripe recurring access

1. Open the access request in the Control Panel.
2. Confirm or override the requested plan.
3. Select **Stripe checkout required** under Payment Setup.
4. Approve the request. This creates an account awaiting payment, not active
   paid access.
5. The customer completes hosted Stripe Checkout. Only the confirmed webhook
   activates recurring access and establishes the renewal date.

An access request, approval, Checkout redirect, or return page is not proof of
payment. Stripe stores the payment method and performs monthly renewal; Broadcast
Tool Pro stores no card details.

If renewal fails, access remains active for the configured 72-hour grace period.
At grace expiration, module access is suspended without deleting customer data.
Confirmed recovery restores access automatically.

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
- Refunds and manual cancellations remain controlled outside the platform until
  the Stripe Customer Portal and final commercial policies are approved.
- Self-service checkout must not be advertised until the Sandbox webhook and
  complete subscription lifecycle have passed release acceptance.
