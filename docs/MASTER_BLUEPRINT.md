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

XMLTV validation must report unescaped ampersands as an actionable XML syntax
error. XMLTV Repair may safely replace bare ampersands with `&amp;`, but it must
preserve valid named and numeric XML entities and document every correction.

Generic Traffic imports must not depend on a customer filename. Operational
date resolution follows this order: an explicit date supplied by the user,
an embedded date or full event date-time in the source, and finally a date
detected in the filename. CSV and XLSX readers must accept the same full
event date-time representation. If no date is available, the interface may
require a manual date.

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

### Interface Localization

The product interface supports English and international Spanish. Internal
code, APIs, database fields, technical documentation, and canonical product
terminology remain in English.

- A single language preference is shared by the public landing page and the
  authenticated application.
- The first visit may use the browser language; an explicit user selection is
  remembered and takes precedence afterward.
- Language is represented by `EN` and `ES`, not national flags.
- Translation keys are centralized so modules can be localized incrementally
  without duplicating business logic.
- Interface localization is strictly presentational. It must not alter source
  data, XMLTV output, Excel workbooks, PDFs, report language selections, or
  validation behavior.
- Report-language controls remain independent because a user may operate the
  interface in one language and deliver a report in another.
- The XMLTV Generator and Programming Grid localize their complete operating
  surfaces, including validation states, EPG preview metrics, filters, and
  download feedback. Source metadata, XMLTV language fields, and report
  language selections remain independent and are never translated implicitly.
- XMLTV Validator and XMLTV Repair localize their upload, analysis, result,
  authorization, and download surfaces. Known validation and repair rule IDs
  provide controlled Spanish explanations while canonical backend messages,
  XML content, repaired files, and report formats remain unchanged.

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

### HLS Cost-Control Policy

The HLS Validator included in Programming Suite must remain a lightweight,
request-based inspection service with negligible marginal infrastructure cost.
It may inspect manifests, variants, declared codecs, resolutions, frame rates,
segment availability, and manifest-level signaling.

Compute-intensive analysis must never be silently included in the base plan.
The following capabilities require a separately funded entitlement, explicit
usage limits, concurrency controls, automatic timeouts, and measurable usage:

- Downloading and demultiplexing transport-stream segments
- Continuous SCTE-35 or closed-caption extraction
- Audio decoding and CALM Act loudness measurement
- Black-frame and freeze-frame detection
- Long-running or continuous stream monitoring
- Multi-region probes, archival, or retained media samples

If an advanced HLS capability cannot be operated within the revenue assigned
to its add-on, it must remain unavailable until pricing, quotas, and capacity
controls are approved. Broadcast-processing workloads must run outside the web
request path so they cannot reduce availability for XMLTV, Traffic Operations,
Billing, or Administration.

### Enterprise — $199/month

Enterprise includes all Professional capabilities, Stream Monitoring, higher
channel and user limits, advanced auditability, guided onboarding, and
priority support.

Media QC is explicitly marked as Coming Soon and remains unavailable until
resource governance, capacity limits, and operational costs have been
validated. Its planned capabilities are:

- ATSC A/85 and ITU-R BS.1770 loudness measurement
- Closed-caption presence, continuity, and synchronization
- Black-frame detection
- Freeze-frame detection

SCTE-35 monitoring reports must distinguish ad-break starts from continuation
markers. Duplicate representations of the same break (for example DATERANGE
and CUE-OUT signaling) must not inflate the summarized break count or planned
duration. The complete trigger timeline remains available as technical
evidence.

Future enterprise expansion may include higher concurrency and retention, API
access, SSO, contractual service levels, and additional identity controls.

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

Cancellation is distinct from organization suspension and request rejection.
An immediately canceled subscription blocks product modules while preserving
the user identity, organization, configuration, and history. A subscription
marked to cancel at period end remains usable through its recorded period end
and is blocked automatically afterward. The Super Admin organization view must
show the account owner, organization status, subscription status, effective
product access, and access end date as separate fields.

## Account Access and Trial Lifecycle

Account creation supports two distinct commercial paths:

- Start an optional 7-day free trial.
- Submit a Request Access form for a paid account without starting a trial.

The trial must never be mandatory. A Request Access submission creates only a
pending commercial request and grants no product access. A Super Admin reviews
the request, assigns Professional or Enterprise, and creates a separate paid
organization account. The customer then uses a single-use activation link to
create a password. Activation links expire after seven days.

After submission, the request form is replaced by a dedicated confirmation
screen with the request reference and next steps. The platform queues an
acknowledgement for the requester and a review notification for every active
Super Admin. Email delivery depends on the configured provider; Amazon SES
sandbox restrictions remain in effect until production access is approved.

A rejected request does not prevent the same email address from submitting a
future request. Existing or suspended customer identities may also submit a
new commercial review request. Approval reactivates the existing organization
and preserves its history instead of creating duplicate users or workspaces.

Professional approval creates an active manual subscription at the published
Professional price and enables Programming plus Traffic Operations.
Enterprise approval creates an active manual subscription at the published
Enterprise price and enables the complete currently available Enterprise
entitlement set. Payment-provider integration may replace manual subscription
activation later without changing the onboarding domain model.

Super Admins may grant internal complimentary access when approving a trusted
Professional or Enterprise evaluator. This is an administrative waiver, not a
public plan:

- It is never displayed on the landing page or public pricing.
- A future expiration date and an internal reason are mandatory.
- The authorizing Super Admin, reason, and expiration are recorded.
- No invoice or payment is due during the complimentary period.
- Access ends automatically at expiration unless the grant is explicitly
  replaced by a paid subscription or extended by an authorized administrator.

Authentication requirements:

- Sign In, Request Access, Free Trial, and Account Activation entry points
  must preserve their
  requested mode.
- Sessions are temporary by default.
- An explicit Remember Me option may extend the authenticated session for 30
  days.
- Authentication cookies are HTTP-only and organization access is always
  enforced by the backend.
- Browser password-manager autofill is separate from product session
  persistence and must not be treated as authenticated access.

The free trial includes only XMLTV Validator, Pre-Logs, and HLS Validator.
Trial exports are limited to branded PDF files. Every trial PDF carries a
visible Broadcast Tool Pro watermark above the report content while preserving
the readability of operational data.

User preferences and remembered operational values must be scoped to the
authenticated organization or user. A new account must never inherit filters,
customer names, channel settings, or other operational values from another
account using the same browser.

Trial communications are scheduled as an auditable lifecycle:

- Welcome email when registration is completed
- Three-day remaining reminder
- One-day remaining reminder
- Trial-ended notification

These messages are stored in a provider-neutral email outbox. Amazon SES is
the initial production provider because it offers usage-based pricing without
a fixed monthly subscription. The delivery worker atomically claims queued
messages, records the SES message ID, retries transient failures with bounded
backoff, and preserves the final error for operational review. Production
requires an authenticated sending domain, SES production access, DKIM, SPF,
DMARC, bounce and complaint monitoring, and unsubscribe or preference handling
where legally required. Provider credentials must never be stored in source
code.

## Cost-Conscious Infrastructure Strategy

Broadcast Tool Pro must scale from revenue, measured demand, and operational
risk. Infrastructure must not be introduced merely because it may become
useful in the future.

> No infrastructure component will be introduced before customer demand,
> operational risk, or measured usage justifies its cost.

### Stage 1 — Validation and First Customers

Target: 0–10 paying customers.

- Keep the current FastAPI modular monolith.
- Keep SQLite while concurrency and reliability remain acceptable.
- Run one economical application service.
- Store only temporary processing files on local disk.
- Delete temporary uploads and generated working files according to a defined
  retention policy.

The first public staging environment uses one paid entry-level service, one
small persistent disk, one application worker, and a provider-generated URL.
It remains isolated from local development, disables automatic deployments,
and does not connect the production domain. Web-based Super Admin bootstrap is
disabled; the first administrator is created once from hosting secrets. This
environment was deployed and persistence-tested on July 30, 2026. Account,
session, and Enterprise plan state survived a service restart, and the initial
administrator password was removed from the hosting environment after
bootstrap.
- Maintain automatic off-server backups of the database and essential records.
- Use a free or low-cost transactional email tier when email delivery is
  connected.
- Limit HLS monitoring duration and allow only controlled concurrency.
- Reuse network security resources across HLS polling cycles and keep MPEG-TS
  inspection samples bounded so a monitoring session cannot progressively
  exhaust the web-service memory allocation.
- Do not introduce Redis, Celery, Kubernetes, dedicated media storage, or
  multiple application services at this stage.

Commercial launch still requires:

- HTTPS
- Secure password hashing and HTTP-only session cookies
- Backend-enforced organization isolation and permissions
- Upload size, type, and processing limits
- Error logging and operational alerts
- Automated backups and a tested restoration procedure
- Temporary-file cleanup

Commercial promotion is governed by
[`COMMERCIAL_RELEASE_READINESS.md`](COMMERCIAL_RELEASE_READINESS.md). The
current decision is **staging pilot ready, not commercial production ready**.
Technical readiness, legal approval, payment operations, production email,
external alerting, and customer-data procedures are independent gates; a
successful deployment does not silently approve any of them.

The Stage 1 security baseline now includes:

- Scrypt password hashing with unique salts
- Hashed server-side sessions in HTTP-only, same-site cookies
- 12-hour standard sessions and optional 30-day remembered sessions
- Automatic expired-session cleanup
- Temporary account lock after repeated failed sign-ins
- Single-use, 30-minute password recovery tokens
- Revocation of every active session after password recovery
- Security event auditing visible to the Super Admin
- Production-only secure cookies, HSTS, and standard browser security headers
- Organization-scoped report history and artifact downloads; every archived
  Pre Log and Post Log records its owning organization and generating user,
  and cross-organization report access returns no artifact
- Request identifiers and structured operational logging without recording
  credentials, tokens, query strings, uploaded content, or request bodies
- Process-local rate limits on login, password recovery, trial registration,
  access requests, and web bootstrap. This has no external infrastructure
  cost and is intentionally scoped to the single-worker Stage 1 deployment;
  a shared limiter becomes necessary only when the service scales to multiple
  workers or instances
- GitHub Actions quality gates that run the complete test suite and a
  production-dependency vulnerability audit on every change and every week
- Weekly Python dependency review and monthly GitHub Actions review through
  Dependabot, with staging verification and no automatic merging

The provider-neutral email outbox is connected to Amazon SES. Delivery is
controlled through production environment variables and least-privilege AWS
credentials. The Stage 1 request limiter runs within the existing application
process; infrastructure-level limiting remains a future scaling requirement.

Stage 1 external availability monitoring uses a scheduled GitHub Actions smoke
test at 30-minute intervals. It runs outside Render, retries transient failures,
opens one deduplicated GitHub incident, and closes that incident after verified
recovery. This adds no monitoring subscription during the pilot stage. It must
be replaced or supplemented when contractual response times, multiple services,
or on-call routing justify dedicated observability.

Application rollback is separated from database recovery. Every production
candidate records a known-good Git revision and proves that revision can boot
with isolated data before promotion. Render deployment rollback preserves the
persistent disk and is followed by smoke, authentication, tenant-isolation,
entitlement, report-ownership, and email checks. Database restoration remains
reserved for verified corruption or data loss.

The Stage 1 implementation includes a cost-free SQLite backup foundation:

- Automatic verified backups every 24 hours
- Manual verified backup from the Super Admin Control Panel
- SQLite integrity validation and SHA-256 manifests
- Configurable retention
- A protected offline restoration tool that preserves a pre-restore copy
- Backup health visibility through the application health endpoint and Control
  Panel
- Encrypted off-server backups in the owner's Google Drive using the
  least-privilege `drive.file` scope
- Automatic remote retention of seven daily and four weekly recovery points
- A 4 GB operating target and 5 GB hard Drive-usage ceiling with recycling of
  the oldest Broadcast Tool Pro backup sets
- A tested download, decryption, checksum, and SQLite-integrity recovery path
- An isolated recovery drill that restores a verified backup into a temporary
  database and proves the live database path was never touched
- Hourly cleanup of application-owned technical working files after 24 hours,
  explicitly excluding customer reports, verified backups, the active
  database, and pre-restore safety copies

The initial Google Drive recovery path is appropriate for the pre-revenue
stage. It must be replaced with organization-owned managed storage when
commercial scale, operational ownership, or recovery-time requirements justify
the change.

The operating-cost target for this stage is approximately USD 10–30 per month,
excluding variable payment-provider and email-delivery fees.

### Stage 2 — Early Growth

Target: approximately 10–50 customers, or earlier if measured risk requires it.

Introduce components independently rather than performing a full replatform:

- Migrate SQLite to managed PostgreSQL when concurrent writes, backup
  requirements, tenant volume, or availability risk justify the change.
- Introduce object storage when local retention, report history, or disk
  durability becomes a customer requirement.
- Isolate Media QC or other CPU-intensive processing in one worker when it
  begins competing with interactive application requests.
- Keep the primary application as a modular monolith.

### Stage 3 — Measured Scale

Target: sustained usage beyond the safe capacity of Stage 2.

Only then consider:

- A durable job queue
- Multiple background workers
- Redis, SQS, or an equivalent queue dependency
- Replicated API instances
- Expanded object-storage retention
- Centralized metrics, tracing, and higher availability

### Infrastructure Upgrade Triggers

An upgrade must be justified by one or more recorded signals:

- Database lock contention or unacceptable write latency
- Backup or restoration objectives that SQLite cannot satisfy
- Local disk growth or customer retention requirements
- Application response degradation during report or monitoring jobs
- Repeated queueing or rejected Media QC requests
- CPU, memory, bandwidth, or storage thresholds
- Customer contractual requirements
- Security, compliance, or availability risk

Architecture decisions must preserve migration paths without requiring the
business to pay for unused capacity.

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

## Transactional Email Governance

Transactional email is provider-neutral and passes through an auditable
outbox. Public sending remains disabled while the selected provider account is
restricted to sandbox operation.

- Every accepted send records the provider message identifier.
- Permanent bounces and complaints immediately suppress the recipient.
- Queued messages for suppressed recipients are canceled before delivery.
- Temporary bounces are audited but do not automatically suppress a recipient.
- Suppression removal requires an explicit administrative action.
- Delivery, bounce, complaint, reject, and send events are retained for
  operational review.
- Super Administrators can inspect recent delivery attempts by recipient,
  status, attempt count, and exact last error without exposing message bodies
  or provider credentials.
- Queued or failed messages can be explicitly retried after recipient
  eligibility is confirmed. Suppressed recipients remain blocked until an
  administrator removes the suppression.
- While Amazon SES remains in sandbox, every external test recipient must be
  verified in SES. Production launch remains blocked until SES production
  access is approved.
- Production integration must authenticate provider event notifications before
  recording them.
- Amazon SNS notifications are accepted only after cryptographic signature
  verification and exact topic authorization. Subscription confirmation links
  must also use a trusted Amazon SNS HTTPS host.
- The platform must never repeatedly send to a permanently bounced address or
  to a recipient who submitted a complaint.
- Authenticated recipients can disable optional three-day and one-day trial
  reminders from their account panel. Account access, password recovery,
  billing, security, support, welcome, and trial-expiration messages remain
  operational because they are essential transactional communications.

## Public Trust and Compliance Pages

The public website exposes permanent, provider-neutral pages for:

- Privacy Policy at `/privacy`
- Terms of Service at `/terms`
- Transactional Email Policy at `/email-policy`

The landing-page footer links to each page. The email policy documents the
transactional purpose of messages, recipient sources, authenticated provider
events, and the suppression process for permanent bounces and complaints.
These pages form the initial operational compliance baseline and must receive
jurisdiction-appropriate legal review before commercial launch.

## Pilot Feedback Quality Standard

External pilot feedback is treated as product evidence and must improve shared
platform behavior rather than create customer-specific code paths.

The first staging pilot established these cross-module requirements:

- XMLTV import failures must direct the user to the official Excel and CSV
  templates so structural and formatting errors are actionable.
- Programming Grid exports must use the XML `Live` value as the only special
  status highlight. All live programmes use the same color and a compact Live
  legend; Premiere and Replay are not highlighted.
- Optional client identity entered for Pre Logs or Post Logs must be included
  in generated deliverables and omitted completely when left blank.
- Every multi-file upload area must support reliable click selection and
  drag-and-drop with explicit supported-format validation.
- Stream-monitoring reports must preserve and display the exact analyzed
  start and end timestamps, including those timestamps on bandwidth charts.

These behaviors are part of the common reporting and workflow standards and
must remain covered by automated regression tests.
