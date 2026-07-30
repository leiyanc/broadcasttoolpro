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
- Automatic deploys disabled
- Transactional email disabled until the provider grants production access
- No custom domain during initial verification

The service uses its Render-provided `onrender.com` address. The production
domain is not connected at this stage.

## Verified staging environment

The initial staging environment was deployed and verified on July 30, 2026:

- URL: `https://broadcast-tool-pro-staging.onrender.com/app`
- Render service: `broadcast-tool-pro-staging`
- Estimated baseline cost: USD 7.25 per month before taxes or overages
- Persistent account, session, and plan data verified across a service restart
- Initial Super Admin authentication verified
- Super Admin organization plan verified as Enterprise
- Public health, privacy, terms, and email-policy routes verified

No credentials or customer operational data are recorded in this document.

## Required Render secrets

The first Blueprint creation prompts for:

- `BTP_APPLICATION_URL`: the final Render URL followed by `/app`
- `BTP_INITIAL_ORGANIZATION_NAME`: the owner organization
- `BTP_INITIAL_ADMIN_NAME`: the initial Super Admin display name
- `BTP_INITIAL_ADMIN_EMAIL`: the initial Super Admin email
- `BTP_INITIAL_ADMIN_PASSWORD`: a unique password of at least 10 characters

The password must not be copied from local development. After administrator
creation succeeds, remove `BTP_INITIAL_ADMIN_PASSWORD` from the Render
environment because it is no longer needed.

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

Staging begins with `BTP_EMAIL_PROVIDER=disabled`. Email remains queued and
auditable without external delivery. After provider production approval, add
the SES variables through Render's secret manager and configure the signed SNS
event endpoint. Never commit provider credentials.

## Rollback

Render retains deploy history. If a release fails:

1. Roll back to the last verified deploy.
2. Check `/health`.
3. Verify the persistent database before accepting new customer activity.
4. Restore from the encrypted backup process only when database integrity is
   compromised.
