# Commercial Release Readiness

## Purpose

This document is the release gate for moving Broadcast Tool Pro from a
controlled staging pilot to commercial production. A feature being visible in
staging does not make it commercially ready. Every blocking gate below must be
verified with current evidence and approved by the product owner before the
production domain accepts paying customers.

## Current Decision

**Status: STAGING PILOT READY — NOT YET COMMERCIAL PRODUCTION READY**

The current environment is appropriate for invited evaluators using controlled
accounts. It must not yet be presented as the final paid production service.

## Release Gates

| Area | Gate | Current status | Evidence or remaining action |
|---|---|---|---|
| Product | Core modules pass automated regression tests | Ready | Complete test suite runs in GitHub Actions |
| Security | Dependency vulnerability audit passes | Ready | `pip-audit` runs on every change and weekly |
| Security | Authentication, organization isolation, permissions, and secure cookies are enforced | Ready for staging | Reverify with production configuration before launch |
| Recovery | Encrypted off-server backup and isolated restore drill pass | Ready | Verified SQLite backup, checksum, integrity, and recovery drill |
| Operations | Application health reports database backup, email, and temporary-storage status | Ready | Public `/health` endpoint |
| Operations | Actionable alerting reaches the operator when health or requests fail | **Blocking** | Configure external uptime/error alerts and escalation ownership |
| Operations | Rollback procedure is tested against the intended production service | **Blocking** | Perform and record one production-candidate rollback rehearsal |
| Legal | Privacy Policy, Terms, and Email Policy are publicly accessible | Draft ready | Routes exist and are linked publicly |
| Legal | Policies receive jurisdiction-appropriate professional review | **Blocking** | Legal review required before accepting paid customers |
| Email | Sending domain, DKIM, and controlled SES delivery are verified | Ready for staging | Verified domain and staging delivery |
| Email | SES production access and bounce/complaint event handling are operational | **Blocking** | Obtain production access and verify signed SNS events end to end |
| Domain | Production domain and HTTPS are connected without changing staging | **Blocking** | Create a separate production service and connect final domain only there |
| Billing | Published prices and server-side entitlements agree | Ready for manual pilots | Reverify plan catalog before launch |
| Billing | Payment, invoices, cancellation, refunds, and failed-payment ownership are defined | **Blocking** | Approve provider and operating procedure, or document a controlled manual contract process |
| Support | Customers can submit and follow support requests; Super Admin can reply and resolve | Ready | Help Center and Control Panel workflow |
| Privacy | Retention, deletion, and customer data-request procedure are operational | **Blocking** | Approve owner, response process, and retention schedule |
| Product | Pilot acceptance test succeeds with representative customer files | In progress | Complete second tester feedback and close release-blocking findings |

## Required Production Evidence

The release record must contain:

1. The exact Git commit deployed.
2. A successful GitHub **Quality and Security** run for that commit.
3. A successful staging smoke-test run.
4. A verified backup created before promotion.
5. Results for sign-in, password recovery, organization isolation, suspension,
   plan access, XMLTV workflows, Traffic workflows, HLS validation, report
   downloads, support requests, and transactional email.
6. The production configuration review, excluding all secret values.
7. The named release approver, approval time, and rollback target.

## Staging Smoke Test

Run the provider-neutral smoke test against the candidate environment:

```bash
python -m tools.release_readiness \
  https://broadcast-tool-pro-staging.onrender.com
```

It verifies the health response and the permanent public trust pages. It does
not sign in, mutate customer data, trigger email, or replace the full acceptance
test. GitHub also exposes this check as the manually triggered **Staging Smoke
Test** workflow.

## Production Promotion Rules

- Staging and production must use separate services, data, credentials, URLs,
  and persistent storage.
- Never promote directly from an unreviewed working directory.
- Never copy the staging database into production merely to preserve pilot
  accounts; migration requires an explicit data decision and backup.
- Never weaken secure cookies, tenant checks, upload limits, or provider-event
  authentication to resolve a deployment issue.
- A failed blocking gate stops the release. It is not converted into a warning
  without a written risk acceptance from the product owner.
- Roll back when authentication, tenant isolation, report ownership, database
  integrity, or paid entitlement enforcement is uncertain.

## Initial Operating Ownership

Until a larger team exists, the product owner is the release approver and
incident owner. The platform must make technical evidence visible, but it does
not replace human review of legal, billing, customer communication, or material
security decisions.
