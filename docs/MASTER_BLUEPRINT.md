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

### Starter

- Instant HLS validation
- Core XMLTV capabilities
- Limited channels, users, jobs, and report retention

The Starter plan does not include time-based stream monitoring or Media QC.

### Professional

- HLS Monitor Stream for 5- and 10-minute sessions
- SCTE-35 cue monitoring
- Observed bandwidth timeline
- Branded PDF reports in English or Spanish
- Higher operational limits and report retention

### Enterprise

- HLS Monitor Stream for 5-, 10-, and 15-minute sessions
- Media QC capabilities
- Loudness, captions, black frames, and freeze frames
- Higher concurrency
- Extended retention, auditability, API access, and support
- Organization-specific limits and contractual entitlements

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

