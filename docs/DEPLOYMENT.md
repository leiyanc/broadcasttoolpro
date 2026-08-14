# Staging Deployment

## Purpose

The first public environment is an isolated staging service. It exists for
controlled product evaluation, public policy review, provider verification,
and deployment testing. Local development remains independent.

## Architecture

- One Render Starter web service
- One 1 GB persistent disk
- One Uvicorn worker
- SQLite and report history under the mounted data directory
- Automatic application-code deploys disabled; Blueprint configuration changes
  may still synchronize and trigger a service update
- Transactional email enabled for controlled SES sandbox recipients
- The verified custom domain terminates HTTPS at Render and currently routes to
  the staging service
- The Render-provided `onrender.com` address remains available as a platform
  fallback

## Verified staging environment

The initial staging environment was deployed and verified on July 30, 2026:

- Primary URL: `https://broadcasttoolpro.com/app`
- Render fallback URL: `https://broadcast-tool-pro-staging.onrender.com/app`
- Render service: `broadcast-tool-pro-staging`
- Estimated baseline cost: USD 7.25 per month before taxes or overages
- Persistent account, session, and plan data verified across a service restart
- Initial Super Admin authentication verified
- Super Admin organization plan verified as Enterprise
- Public health, privacy, terms, and email-policy routes verified
- SES sandbox delivery verified for controlled recipients
- Google Drive connection, encrypted upload, download, and isolated recovery
  drill verified
- Signed SNS delivery, permanent-bounce suppression, and complaint suppression
  verified end to end with the Amazon SES mailbox simulator
- Stripe Sandbox webhook delivery verified at
  `https://broadcasttoolpro.com/api/billing/stripe/webhook` with two real
  `customer.subscription.updated` events returning HTTP 200

No credentials or customer operational data are recorded in this document.

## Required Render secrets

The first Blueprint creation prompts for:

- `BTP_APPLICATION_URL`: the public application URL. The Blueprint sets this to
  `https://broadcasttoolpro.com/app`; change it only as part of an approved
  domain migration.
- `BTP_INITIAL_ORGANIZATION_NAME`: the owner organization
- `BTP_INITIAL_ADMIN_NAME`: the initial Super Admin display name
- `BTP_INITIAL_ADMIN_EMAIL`: the initial Super Admin email
- `BTP_INITIAL_ADMIN_PASSWORD`: a unique password of at least 10 characters
- `BTP_EMAIL_FROM`: the verified transactional sender
- `BTP_EMAIL_REPLY_TO`: the monitored support reply address
- `BTP_SES_SNS_TOPIC_ARN`: the authorized SNS topic for SES feedback
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`: restricted SES credentials
- `BTP_STRIPE_WEBHOOK_SECRET`: the signing secret for the active custom-domain
  Stripe event destination; never reuse the secret from a deleted destination

The password must not be copied from local development. After administrator
creation succeeds, remove `BTP_INITIAL_ADMIN_PASSWORD` from the Render
environment because it is no longer needed.

Existing Blueprint services are not prompted when a new `sync: false` key is
added. Set each new secret manually in the Render Dashboard before syncing.
Never store its value in `render.yaml`.

## Required Render secret files

Provision these files manually under **Environment → Secret Files**:

- `google-drive-token.json`
- `backup-encryption.key`

Do not commit either file. Copy them once into the persistent paths declared
by the Blueprint:

```text
/opt/render/project/src/data/google-drive/google-drive-token.json
/opt/render/project/src/data/google-drive/backup-encryption.key
```

The OAuth token is writable at its persistent location so Google can refresh
it. Preserve the original encryption key in a protected recovery vault; never
replace it while encrypted recovery points depend on it.

## Deployment sequence

1. Push the reviewed staging commit to the dedicated Git branch.
2. In Render, create a Blueprint from `render.yaml`.
3. Confirm the paid Starter service and 1 GB disk before approving creation.
4. Enter the required secret values.
5. Wait for the service and initial administrator hook
   (`python -m tools.bootstrap_admin`) to complete.
6. Open `/health`, `/privacy`, `/terms`, and `/email-policy`.
7. Sign in with the staging administrator and immediately verify Account,
   Control Panel, and organization access.
8. Remove the initial administrator password environment variable.
9. Keep automatic deploys disabled. Promote changes manually only after tests.

Before any commercial production promotion, complete every blocking gate in
[`COMMERCIAL_RELEASE_READINESS.md`](COMMERCIAL_RELEASE_READINESS.md) and attach
the exact commit, successful CI run, smoke-test result, backup evidence,
approver, and rollback target to the release record.

## Data and isolation

`BTP_DATA_DIR` controls the database and generated-report location. Staging
uses `/opt/render/project/src/data`, which is mounted to its own persistent
disk. It does not read the local development database, OAuth files, output
directories, or credentials.

The initial public environment uses exactly one process because SQLite and a
single attached disk are not designed for horizontal scaling. A later
PostgreSQL migration must occur before multiple application instances are
introduced.

## Email

Staging uses `BTP_EMAIL_PROVIDER=ses` with credentials stored only in Render's
secret manager. Delivery remains restricted by the provider's sandbox rules;
commercial customer delivery cannot begin until SES production access is
approved. SES bounce, complaint, and delivery notifications use the dedicated
SNS topic configured in `BTP_SES_SNS_TOPIC_ARN` and the signed HTTPS endpoint
`/api/email-events/amazon-sns`. The endpoint and automatic suppression were
verified with the SES mailbox simulator on August 13, 2026. Never commit
provider credentials or the topic ARN value.

## Blueprint synchronization

`autoDeployTrigger: off` prevents ordinary source changes from being deployed
without review. Render may nevertheless synchronize a changed `render.yaml`
through the connected Blueprint and update the service. Treat every Blueprint
change as deployment-impacting, review the Events page after it is pushed, and
run the staging smoke test when synchronization completes. The **Deployed**
status in Render is the successful live state for that service.

## Rollback

Render retains deploy history. If a release fails:

1. Roll back to the last verified deploy.
2. Check `/health`.
3. Verify the persistent database before accepting new customer activity.
4. Restore from the encrypted backup process only when database integrity is
   compromised.
