# Broadcast Tool Pro — Master Blueprint

## Product Positioning

Broadcast Tool Pro is a cloud-based Broadcast Operations Platform that
automates programming, traffic, validation, reporting, compliance, and
distribution workflows for broadcasters, FAST channels, cable networks, and
content distributors.

The platform is organized around reusable workflows and engines rather than
customer-specific code. Customer requirements must be implemented through
configuration, templates, profiles, and entitlements whenever possible.

## Core Product Domains

### Broadcast Operations

- XMLTV generation, validation, repair, and programming grids
- Pre Log generation
- Post Log certification
- As-Run processing
- Broadcast reporting

### Streaming Quality Control

- Instant HLS validation
- Time-bounded stream monitoring
- SCTE-35 track and cue detection
- Observed bandwidth analysis
- Branded bilingual PDF reports
- Future Media QC analysis:
  - ATSC A/85 and ITU-R BS.1770 loudness measurement
  - Closed-caption presence, continuity, and technical synchronization
  - Black-frame detection
  - Freeze-frame detection

### SaaS Foundation

- Organizations
- Workspaces
- Channels
- Users, roles, and permissions
- Module entitlements
- Job history
- Audit logs
- Report archive
- Billing and subscriptions

## Commercial Packaging

Broadcast Tool Pro will launch with one primary commercial plan. A three-tier
structure must not be marketed until the product has enough differentiated
capabilities to make each tier valuable and easy to understand.

### Programming Suite — $39/month

Programming Suite includes the complete XMLTV Suite:

- XMLTV Generator
- XMLTV Validator
- XMLTV Repair
- Programming Grid
- Branded Excel and CSV templates
- Instant HLS validation

The Excel and CSV templates may be offered as free acquisition resources. The
processing tools require an active account.

### Professional — $99/month

Professional combines Programming Suite with Traffic Operations. Traffic
Operations contributes $60/month to the $99/month package and includes Pre
Logs and Post Logs.

### Add-ons

The initial add-on structure is:

- Traffic Operations: $60/month; Pre Logs and Post Logs
- Stream Monitoring: $59/month; 5-, 10-, and 15-minute HLS monitoring, SCTE-35 cue
  monitoring, observed bandwidth timeline, and branded bilingual PDF reports

Add-ons are organization-level entitlements and must be enforced by both the
API and the user interface.

### Enterprise — From $249/month

Enterprise is architecturally supported but will not be actively marketed at
launch. It will be introduced when the platform includes sufficient
enterprise-specific value:

- Media QC capabilities
- Loudness, captions, black frames, and freeze frames
- Higher concurrency and retention
- Advanced auditability
- API access
- SSO and enterprise identity controls
- Contractual limits, support, and service levels

Enterprise will include all Professional capabilities and purchased add-ons.

## Billing and Subscription Architecture

Billing is organization-scoped and separated from product entitlements.

- The organization plan defines the core product package.
- Add-ons define optional product access.
- The subscription records the commercial lifecycle: status, billing cycle,
  renewal period, cancellation state, currency, and payment-provider
  references.
- Invoices are immutable billing records linked to the organization.
- Product access must not depend directly on browser state or payment-provider
  responses.

The initial billing foundation is provider-neutral and uses manual subscription
management. Commercial prices are calculated from the server-side pricing
catalog; no payment method is stored until a payment provider is connected.
A future provider integration must
use webhooks as the authoritative source for payment status and must be
idempotent, auditable, and isolated from broadcast-processing workflows.

## Customer Support Workflow

Authenticated users can create support requests from the contextual Help
Center. Each request records the organization, reporting user, active module,
category, priority, summary, details, optional exact error message, status, and
timestamps.

- Users can review the status of requests they submitted.
- Users can exchange customer-visible messages and reopen resolved requests.
- Super Admins manage all requests from the Control Panel.
- Super Admins can send customer-visible replies and maintain private internal
  notes.
- Every status change and message is recorded in the ticket activity history.
- A written resolution is mandatory before a request can be marked Resolved.
- Supported states are Open, Investigating, and Resolved.
- Support remains available to authenticated users whose organization is
  suspended.
- Operational files, schedules, XMLTV files, playlists, and As-Run data are
  never attached automatically.
- Future attachment support must require explicit user action, file validation,
  access controls, retention limits, and secure storage.

## Media QC Resource Governance

Media QC must never execute inside the primary web application process.

All time-based or media-decoding analysis must:

- Run as an asynchronous job on an isolated worker.
- Enter a queue when worker capacity is unavailable.
- Enforce plan-specific concurrency limits.
- Enforce 5-, 10-, or 15-minute maximum durations.
- Stop automatically when the selected period ends.
- Apply CPU, memory, bandwidth, and execution-time limits.
- Support a circuit breaker that disables Media QC without affecting other
  Broadcast Tool Pro modules.
- Record resource consumption and estimated cost for each job.

Capacity decisions must be based on monitored operational metrics:

- Queue depth
- Queue wait time
- Processing duration
- Worker CPU and memory
- Bandwidth consumption
- Failure rate
- Estimated cost per analysis

Media QC should initially launch as a controlled beta. It must not be enabled
in production until worker isolation, limits, monitoring, and failure
containment are verified.

## Compliance Reporting Principle

Broadcast Tool Pro provides measured technical findings against a selected
profile. Reports must not claim to be definitive legal certifications.

The report must identify:

- The selected technical profile
- The observation period
- The measurements performed
- The detected findings
- The applicable limitations
- Recommended corrective actions

Reports must be available in English and Spanish and carry Broadcast Tool Pro
branding.
