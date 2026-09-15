# Data Privacy Operations

## Purpose

This procedure governs account-data access, correction, export, and deletion
requests during the controlled pilot. It is an internal operating standard,
not a substitute for jurisdiction-specific legal advice.

## Request Intake

Authenticated account contacts submit requests through:

`Help Center → Report a Problem → Privacy or data request`

The request must identify the organization, requested action, and categories
of information involved. Operational source files are not attached
automatically. Requests from people who cannot sign in must be submitted to
`security@broadcasttoolpro.com` and matched to an existing authorized
organization contact before any account information is disclosed or changed.

Privacy requests are classified under `Account & Privacy` regardless of which
product module was open when the Help Center was launched. They must not be
misclassified as an XMLTV, Traffic, or HLS product defect.

## Supported Actions

- **Access:** describe the applicable account and operational information held.
- **Correction:** correct inaccurate account or organization information.
- **Export:** prepare an organization-scoped export of applicable records.
- **Deletion:** remove eligible account information after approval and a
  verified backup; preserve only records required for security, disputes,
  billing, or legal obligations.

## Verification and Authorization

Before releasing or deleting information, the Super Administrator must:

1. Confirm the requester is an active authorized contact for the organization.
2. Confirm the request scope and affected users, channels, reports, and support
   records.
3. Check for active disputes, payment records, security incidents, legal holds,
   or another documented retention requirement.
4. Record the verification result as an internal note on the request.

Email possession alone does not authorize organization-wide export or
deletion. A requester must not receive another organization's information.

## Handling Standard

1. Set the request to `Investigating`.
2. Add internal notes documenting identity verification, scope, exclusions,
   and the intended action.
3. Acknowledge the request to the customer and ask for clarification when
   needed.
4. Create and verify a protected backup before an approved destructive change.
5. Perform the approved action with organization-scoped tools or a reviewed
   maintenance procedure.
6. Record what was exported, corrected, retained, or deleted without attaching
   secrets or unnecessary customer content.
7. Send the customer-facing response and mark the request `Resolved`.

No destructive privacy operation is automatic during the pilot.

## Approved Retention Baseline

The product owner approved this operational baseline on September 8, 2026.
It is suitable for implementation as the initial commercial schedule, subject
to jurisdiction-specific legal review and any documented legal hold. The
periods below are maximum operating targets, not permission to retain data
that is no longer needed.

| Data | Approved baseline | Control |
|---|---|---|
| Temporary uploads and generated working files | 24 hours | Automated cleanup and health reporting |
| Local database backups | 14 days by default | Backup manager |
| Google Drive recovery copies | Seven daily and four weekly recovery points | Encrypted backup rotation |
| Active account and organization records | For the life of the account | Organization-scoped access |
| Eligible account and organization records after closure | Delete or de-identify within 30 days | Verified, controlled privacy procedure |
| Generated and archived operational reports after closure | 90 days | Organization-scoped report history and controlled cleanup |
| Support, privacy-request, authentication, and security audit history | 24 months after closure or case resolution, whichever is later | Restricted case and audit access |
| Provider email delivery events | Up to 24 months when required for delivery diagnostics, abuse prevention, or suppression enforcement | Email Health |
| Billing, invoice, tax, dispute, and legally required records | Applicable statutory, contractual, or legal period | Restricted billing access and documented retention exception |

Account closure does not mean immediate erasure from every backup. Eligible
live records are removed or de-identified within the target above; residual
encrypted backup copies expire through the normal 14-day local and seven-daily
plus four-weekly remote rotation. Restoration from a backup must reapply any
completed deletion request before normal service resumes.

Channel deactivation is not account closure or a deletion request. Historical
channel records remain organization-scoped until the applicable account or
record retention period ends.

## Evidence

Every completed request must retain:

- Request reference and organization
- Verified requester and authorizing administrator
- Scope and decision
- Internal notes and customer-visible response
- Completion date
- Backup reference for destructive changes
- Any retained categories and the documented reason

## Escalation

Stop the request and obtain legal or security guidance when ownership is
uncertain, another organization may be affected, a legal hold or dispute may
exist, or the requested operation cannot be safely isolated.
