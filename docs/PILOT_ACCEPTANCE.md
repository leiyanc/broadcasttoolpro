# Pilot Acceptance Test

## Purpose

This checklist records repeatable evidence from invited Broadcast Tool Pro
evaluators. It validates shared product behavior; it must not introduce
customer-specific logic or expose operational source files.

## Test Record

- Tester reference:
- Organization:
- Test date:
- Staging URL:
- Deployed commit:
- Browser and operating system:
- Result: Pending / Passed / Passed with findings / Failed

Do not record passwords, access tokens, customer media, or confidential source
data in this document.

## Severity

- **Blocking:** prevents sign-in, processing, export, tenant isolation, or safe
  use of the product.
- **Major:** a workflow completes incorrectly or requires an unreasonable
  workaround.
- **Minor:** clarity, presentation, or usability issue that does not alter the
  result.
- **Suggestion:** optional improvement for roadmap review.

## Account and Access

- [ ] Access request displays a clear confirmation and reference number.
- [ ] Requester and Super Administrator receive the expected email messages.
- [ ] Approved credentials activate only the assigned organization and plan.
- [ ] Unauthorized modules remain unavailable.
- [ ] Sign-out ends the session; Remember Me behaves as described.
- [ ] Password recovery delivers one valid, time-limited reset link.

## XMLTV Generator

- [ ] Official Excel template downloads and opens correctly.
- [ ] Official CSV template downloads correctly.
- [ ] A representative schedule validates without losing valid metadata.
- [ ] Unsupported structure directs the user to the official templates.
- [ ] Suggested corrections require authorization before generation.
- [ ] Generated XMLTV validates successfully in XMLTV Validator.
- [ ] Programming Grid is optional and reflects the original EPG schedule.
- [ ] Only programmes marked Live receive the shared Live highlight and legend.

## XMLTV Validator and Repair

- [ ] Valid XMLTV produces a clear successful report.
- [ ] Invalid XMLTV identifies actionable errors and warnings.
- [ ] A bare ampersand is identified clearly and repaired as `&amp;` without
  changing existing valid XML entities.
- [ ] Repair changes only supported safe issues and documents every change.
- [ ] Repaired XMLTV passes a new independent validation.
- [ ] Trial downloads follow trial format and watermark restrictions.

## Pre Logs

- [ ] Representative CSV playlist imports successfully.
- [ ] Representative XML playlist imports successfully.
- [ ] Representative TXT playlist imports successfully.
- [ ] Prefix, exact ID, text, date, and broadcast-day filters return the
  expected occurrences.
- [ ] Optional client, product, agency, and logo values appear only when set.
- [ ] Asset IDs are left-aligned in generated reports.
- [ ] Excel and PDF exports contain the same selected occurrences.

## Post Logs

- [ ] Representative XLSX, CSV, XML, JSON, or TXT As-Run source imports using
  common structural detection rather than a customer filename.
- [ ] Generic CSV sources accept either an explicit operational date or an
  embedded date-time before falling back to the filename.
- [ ] Equivalent Amagi CSV and XLSX exports produce the same internal event
  dates, times, durations, and asset IDs.
- [ ] Click selection and drag-and-drop behave consistently.
- [ ] Each selected asset produces an independent certification.
- [ ] Dates, times, durations, channel, optional client data, and branding are
  correct in Excel and PDF outputs.
- [ ] Asset IDs are left-aligned in generated reports.

## HLS Validator and Stream Monitoring

- [ ] Reachable HLS URL returns playlist type, variants, codecs, resolution,
  frame rate, segments, and SCTE-35 track presence accurately.
- [ ] Unreachable URLs return an actionable error.
- [ ] Monitoring stops automatically after 5, 10, or 15 minutes.
- [ ] Monitoring records SCTE-35 observations without claiming repair.
- [ ] SCTE-35 summary separates ad-break starts from continuation markers,
  avoids duplicate break counting, and totals reported planned durations.
- [ ] Bandwidth chart covers the exact monitoring start and end timestamps.
- [ ] Branded PDF report clearly separates validation from monitoring evidence.
- [ ] Monitoring access follows the assigned plan or add-on.

## Help and Operational Feedback

- [ ] Quick Guide content is available from each module.
- [ ] A support request can be submitted with module, description, and exact
  error information.
- [ ] Super Administrator can reply, add internal notes, and resolve the case.
- [ ] Customer sees the current case status and appropriate response.

## Findings

| ID | Module | Severity | Summary | Evidence | Status |
|---|---|---|---|---|---|
| PILOT-001 |  |  |  |  | Open |

## Acceptance

The pilot passes when no Blocking findings remain, all Major findings have an
approved resolution or documented risk decision, and the product owner records
the deployed commit and final result.

- Tester confirmation:
- Product owner decision:
- Decision date:
- Follow-up release or commit:
