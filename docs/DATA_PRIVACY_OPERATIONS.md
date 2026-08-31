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

## Current Retention Baseline

| Data | Current baseline | Control |
|---|---|---|
| Temporary uploads and generated working files | Rotated by configured temporary-storage retention | Automated cleanup and health reporting |
| Local database backups | 14 days by default | Backup manager |
| Google Drive recovery copies | Seven daily and four weekly recovery points | Encrypted backup rotation |
| Authentication and security audit records | Retained for active pilot operations | Restricted administrative access |
| Support and privacy-request history | Retained with the account during the pilot | Customer and administrator case history |
| Provider email delivery events | Retained for delivery diagnostics and suppression enforcement | Email Health |
| Inactive-channel identity, reports, invoices, and audit references | Retained with the organization under the applicable record schedule; channel removal is not a deletion request | Organization-scoped access and controlled privacy-request review |

The final post-account-closure retention schedule requires product-owner and
legal approval before commercial launch. Until then, account deletion cannot
be represented as immediate deletion of every audit, backup, billing, or legal
record.

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
