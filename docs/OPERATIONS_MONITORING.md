# Operations Monitoring

## Stage 1 Monitoring Model

Broadcast Tool Pro uses a cost-conscious two-layer monitoring model for the
first 0–10 customers.

### Layer 1 — Application health

The public, read-only `/health` endpoint reports application availability,
verified-backup health, transactional email configuration, and
temporary-storage cleanup health. It does not expose credentials, customer
files, database paths, account data, or operational content.

### Layer 2 — External availability

GitHub Actions runs the **Staging Smoke Test** at minutes 7 and 37 of every
hour. The check executes outside Render and validates `/health`, `/privacy`,
`/terms`, and `/email-policy`. Each run makes three attempts before declaring
an incident to reduce false alerts from brief network interruptions.

When all attempts fail, the workflow opens one GitHub issue titled:

```text
[Monitoring] Broadcast Tool Pro staging unavailable
```

Repeated failures append evidence to the existing issue instead of creating
duplicates. A later successful check records recovery and closes the issue.
GitHub notification preferences determine which owners receive email or mobile
notifications for the issue.

Scheduled GitHub workflows run only from the repository's default branch.
This monitor is implemented but is not considered active until the workflow is
merged into the default branch and one scheduled run is observed.

## Incident Response

1. Open the failed workflow link recorded in the issue.
2. Check Render Events for a deploy, restart, crash, or infrastructure event.
3. Check Render application logs using the failure time and request ID.
4. Open `/health` directly.
5. If a recent release caused the failure, roll back to the last verified
   deployment.
6. Verify sign-in, organization isolation, report access, and email after
   recovery.
7. Record the cause and corrective action before closing a material incident.

Do not restore the database merely because the web service is unavailable.
Restoration is appropriate only after integrity or data-loss evidence and must
follow `BACKUP_RECOVERY.md`.

## Escalation Triggers

Move to a dedicated monitoring provider or centralized observability when:

- Paying-customer commitments require faster than 30-minute detection
- More than one production service or region must be monitored
- Log volume prevents efficient incident investigation
- Repeated intermittent failures require metrics or distributed tracing
- On-call routing, SMS, voice, or multi-person escalation becomes necessary

Until then, the GitHub monitor avoids another subscription while keeping
availability evidence outside the application it observes.
