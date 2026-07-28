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

### Professional — Initial Commercial Plan

Professional includes the complete XMLTV Suite:

- XMLTV Generator
- XMLTV Validator
- XMLTV Repair
- Programming Grid
- Branded Excel and CSV templates
- Instant HLS validation

The Excel and CSV templates may be offered as free acquisition resources. The
processing tools require an active account.

### Add-ons

The initial add-on structure is:

- Traffic Operations: Pre Logs and Post Logs
- Stream Monitoring: 5-, 10-, and 15-minute HLS monitoring, SCTE-35 cue
  monitoring, observed bandwidth timeline, and branded bilingual PDF reports

Add-ons are organization-level entitlements and must be enforced by both the
API and the user interface.

### Enterprise — Future Plan

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
