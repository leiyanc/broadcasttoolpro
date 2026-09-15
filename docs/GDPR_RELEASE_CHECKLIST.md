# GDPR Release Checklist

This checklist separates the usable operational foundation from the remaining
conditions for publishing GDPR claims or intentionally marketing to Europe.

## Decided and documented

- [x] Controller/operator legal entity: Orion Media LLC, Florida, United States.
- [x] Privacy and security contact: `security@broadcasttoolpro.com`.
- [x] Product-owner approval of the initial retention baseline, September 8, 2026.
- [x] Authenticated bilingual intake for access, correction, export, deletion,
  and retention questions.
- [x] Identity, authority, organization-isolation, exception, and evidence steps
  for privacy requests.
- [x] Current core service providers identified internally.

## Publication blockers

- [x] Business mailing address supplied for Orion Media LLC: 18331 Pines Blvd,
  Unit #153, Pembroke Pines, FL 33029, United States. Confirmed by the product
  owner on September 8, 2026; publication still waits for the remaining legal
  and GDPR checks.
- [ ] Obtain jurisdiction-appropriate legal review of the bilingual GDPR notice,
  Terms, Data Processing Addendum, controller/processor role statements, legal
  bases, retention, and customer contracts.
- [ ] Determine with counsel whether Article 27 requires an EU representative;
  if required, appoint one and publish its contact details.
- [ ] Verify the active production contract, DPA, processing locations,
  subprocessors, deletion terms, and international-transfer mechanism for each
  provider in `GDPR_SUBPROCESSOR_REGISTER_DRAFT.md`.
- [ ] Prepare a customer Data Processing Addendum; include documented
  instructions, confidentiality, security, subprocessors, assistance, return or
  deletion, and audit terms.
- [x] Complete a cookie and browser-storage inventory. No analytics or
  advertising tracker is present; see `COOKIE_STORAGE_INVENTORY.md`. Add a
  consent mechanism only if a later non-essential technology makes it necessary.
- [ ] Decide the competent lead/contact supervisory authority when the EU
  operating model and representative, if any, are known.

## Operational verification before publication

- [ ] Run and record one access/export request and one deletion request against
  an isolated test organization.
- [x] Verify the 24-hour temporary-file cleanup and document evidence. Source
  configuration and isolated automated tests were verified September 8, 2026.
- [ ] Complete and schedule the approved post-closure controls. Explicit account
  closure and safe 90-day report purging are implemented and tested but are not
  yet exposed or scheduled. The 30-day account-data and 24-month support/audit
  controls remain to be implemented; until automated, assign an owner and track
  every deadline manually.
- [ ] Test that restoring a backup does not silently reintroduce information
  covered by a completed deletion request.
- [ ] Document the breach-assessment workflow, including processor escalation,
  incident evidence, and the GDPR supervisory-authority notification decision.
- [ ] Add the legally reviewed bilingual notice to the public Privacy route and
  Help & Guides, then test language switching, links, mobile layout, and contact
  intake in staging.

## Verification record — September 8, 2026

- Temporary storage defaults and deployment configuration both specify 24 hours.
- Local backup defaults and deployment configuration both specify 14 days.
- Remote backup logic retains seven daily and four weekly recovery points.
- Session cookie is HTTP-only and SameSite Strict, and is Secure in production.
- No analytics or advertising tracker was found in frontend or backend source.
- Twenty isolated tests passed for temporary cleanup, local backup rotation,
  remote backup rotation, report history, authentication sessions, and audit
  behavior.
- Gap confirmed: archived reports currently have no automatic 90-day
  post-closure cleanup. Account, support, audit, and email-event post-closure
  schedules also require implementation or a documented manual owner.

## Implementation record — September 8, 2026

- Added an explicit organization closure state and timestamp. Stripe
  cancellation and payment suspension do not start privacy-retention clocks.
- Added a constrained report purge that considers only explicitly closed
  organizations older than 90 days and only removes files inside the
  application-owned report directory.
- Verified that active organizations and recently closed organizations are not
  purged.
- Thirty focused tests and the complete 296-test regression suite passed in an
  isolated data environment.
- The new control is not connected to a public or administrative button and is
  not scheduled in production; no live customer record was changed.

## Release rule

Do not label Broadcast Tool Pro “GDPR compliant” or publish the GDPR draft
until every publication blocker is resolved. Product functionality may
continue to be tested while the draft remains internal.
