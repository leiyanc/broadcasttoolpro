# Rollback Procedure

## Objective

Restore the last verified application release without damaging persistent
customer data. Application rollback and database restoration are separate
operations. A failed deployment does not by itself authorize a database
restore.

## Before Every Production Promotion

Record:

- Candidate Git commit
- Last verified rollback commit
- Successful Quality and Security run
- Successful staging smoke test
- Latest verified backup manifest and creation time
- Release approver

Run the isolated code rehearsal:

```bash
python -m tools.rehearse_rollback LAST_VERIFIED_COMMIT
```

The tool exports the selected revision into a temporary directory, assigns an
isolated database directory, starts one local application worker, verifies
`/health`, stops the worker, and deletes the rehearsal files. It never deploys
to Render and never opens the live database.

## Render Application Rollback

Use this procedure only when the active release is unhealthy or has a material
regression and the previous release is known to be compatible with the current
database schema.

1. Pause new administrative changes and record the incident time.
2. Create or confirm a verified backup before rollback when the application can
   still do so safely.
3. In Render, open the production service Events page.
4. Select the last verified deployment and choose the rollback/redeploy action.
5. Do not change the disk, data directory, environment secrets, or custom
   domain during application rollback.
6. Wait for Render to report **Deployed**.
7. Run `tools.release_readiness` against the service origin.
8. Verify sign-in, organization isolation, entitlements, report ownership,
   support, and transactional email.
9. Record the outcome and corrective follow-up in the incident.

## Stop Conditions

Stop and investigate instead of rolling backward when:

- The previous application expects an incompatible database schema
- Database integrity is uncertain
- Tenant isolation or report ownership is uncertain
- The failure is caused by infrastructure, DNS, certificates, or provider
  credentials rather than application code
- The rollback target has a known security vulnerability

## Database Restoration

Database restoration follows `BACKUP_RECOVERY.md` and is used only for proven
corruption or data loss. Always preserve the pre-restore safety copy. Never use
a database restore as a routine application rollback.

## Current Verification State

On August 3, 2026, revision
`f1134dff262dc068e452d1512efe13dbddf5ff0c` was exported and booted with a
temporary database directory. Its health endpoint reported a healthy
application, backup subsystem, and temporary-storage subsystem. Transactional
email was deliberately disabled inside the rehearsal. The tool confirmed that
the live environment was not touched and removed the temporary environment
after shutdown.

The commercial release gate remains open until the deployment-level procedure
is rehearsed on the intended production service and the result is recorded
without exposing customer data or secrets.
