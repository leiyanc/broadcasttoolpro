# GDPR Provider Register — Internal Draft

> **DO NOT PUBLISH.** Contractual terms, processing locations, and transfer
> safeguards must be verified against the active production accounts before
> this becomes a customer-facing subprocessor list.

| Provider | Current purpose | Information involved | Verification required before EU launch |
|---|---|---|---|
| Render | Application hosting and infrastructure | Account, organization, operational content, reports, and technical logs handled by the hosted application | Public DPA includes EU SCCs and DPF fallback; code config identifies Virginia, USA. Confirm live Dashboard region, contracting account, DPA applicability, subprocessors, and deletion terms. |
| Amazon Web Services (SES) | Transactional email and delivery-event handling | Recipient address, message metadata and content, bounce/complaint events | AWS states its GDPR DPA and SCCs apply automatically when required; code config identifies `us-east-1`. Confirm the live account, Service Terms, subprocessors, SES retention, and transfer assessment. |
| Google | Authorized service communications and encrypted off-site backup storage | Communication data; encrypted database backup artifact and manifest | Google publishes Workspace/Cloud data-processing terms and SCCs. Confirm the exact Google account/product, acceptance of the applicable terms, storage location, subprocessors, and deletion controls. |
| Stripe | Subscription, checkout, invoices, and payment administration | Account and organization billing references, subscription events, payment information handled by Stripe | Public DPA and Data Transfers Addendum include controller/processor roles, DPF and SCC mechanisms. Confirm Orion Media LLC is the account entity and retain the applicable contractual record. |

## Public source verification — September 8, 2026

- Render DPA: `https://render.com/dpa`
- Render regions: `https://render.com/docs/regions`
- AWS GDPR DPA information: `https://aws.amazon.com/compliance/eu-data-protection/`
- Google GDPR and processing terms: `https://cloud.google.com/privacy/gdpr`
- Stripe DPA: `https://stripe.com/legal/dpa`
- Stripe DPA FAQ: `https://stripe.com/legal/dpa/faqs`

Public terms establish that mechanisms are offered; they do not prove that the
correct Orion Media LLC production account, product, configuration, and
contract are in scope. That account-level evidence remains required.

## Operating rule

No additional production provider may receive customer or user information
until its purpose, minimum required data, access, retention, contract, security
review, and international-transfer position are recorded here. A material
provider change must be evaluated before customer data is transferred.
