# Manual Billing Operations

## Purpose

This procedure controls paid and complimentary account activation when Stripe
Checkout is unavailable or an approved commercial exception requires manual
handling.

## Paid access

1. Confirm that cleared payment was received outside the platform.
2. Open the access request in the Control Panel.
3. Select the approved plan.
4. Select **Payment received** under Payment Approval.
5. Approve the request.

An access request or plan selection is not proof of payment. Never select
**Payment received** until the payment has been independently verified.

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
- Manual subscriptions still require independent proof of cleared payment.
- Refunds and manual cancellations remain controlled outside the platform until
  the Stripe Customer Portal and final commercial policies are approved.
- Self-service checkout must not be advertised until the Sandbox webhook and
  complete subscription lifecycle have passed release acceptance.
