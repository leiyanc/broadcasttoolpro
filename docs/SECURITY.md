# Security Baseline

## Authentication

- Passwords are hashed with `scrypt`, a unique random salt, and constant-time
  verification.
- Raw session tokens are never stored in the database. Only SHA-256 token
  hashes are retained.
- Browser sessions use HTTP-only, same-site cookies.
- Standard sessions expire after 12 hours. Explicitly remembered sessions
  expire after 30 days.
- Expired sessions are removed automatically.
- Password changes revoke every active session for the account.

## Login Protection

- Five failed sign-in attempts within 15 minutes trigger a 15-minute lock.
- Unknown accounts follow the same password-verification path to reduce timing
  differences.
- Login success, login failure, lock enforcement, logout, password reset, and
  session revocation are recorded in the security audit log.
- Super Admins can review recent security events in the Control Panel.

## Password Recovery

- Password recovery responses never disclose whether an email address exists.
- Recovery tokens are random, stored only as hashes, expire after 30 minutes,
  and can be used once.
- Creating a new recovery token invalidates older unused tokens.
- Completing recovery revokes all existing sessions.
- Recovery messages are queued in the email outbox and delivered through
  Amazon SES. Delivery failures, bounces, and complaints remain observable.

## Production Configuration

Production must set:

```text
BTP_ENV=production
BTP_COOKIE_SECURE=true
BTP_APPLICATION_URL=https://your-production-domain/app
BTP_EMAIL_PROVIDER=ses
BTP_EMAIL_FROM=Broadcast Tool Pro <notifications@your-domain.com>
BTP_EMAIL_REPLY_TO=support@your-domain.com
BTP_SES_REGION=us-east-1
BTP_SES_SNS_TOPIC_ARN=arn:aws:sns:us-east-1:ACCOUNT_ID:TOPIC_NAME
```

`BTP_ENV=production` enables secure cookies and HTTP Strict Transport Security.
The application also sends anti-framing, MIME-sniffing, referrer, permissions,
and no-store authentication headers.

Production deployment must use HTTPS. Secure cookies must not be disabled to
work around an incorrect proxy or TLS configuration.

For local development, copy `.env.example` to `.env.local` and enter the
restricted SES IAM credentials. `.env.local` and every other environment file
are excluded from Git. Production credentials must be entered directly in the
hosting provider's secret-variable manager, not uploaded as a file.

## Operational Requirements

- Keep channel identity, reports, and operational history scoped to the owning
  organization. Channel deactivation must not expose or transfer those records.
- Treat removal from future channel billing as an access-state change, not a
  destructive deletion. Historical records remain subject to documented
  retention and authorized privacy-request controls.
- Every push and pull request must pass the complete automated test suite and
  the production-dependency vulnerability audit in GitHub Actions.
- Dependabot checks Python packages weekly and GitHub Actions monthly. Updates
  are reviewed and tested; they are never merged automatically.
- Review critical vulnerability notices within one business day, high-severity
  notices within seven days, and routine dependency updates monthly.
- Apply dependency changes on staging first. Confirm authentication, exports,
  backups, email, and organization isolation before a commercial deployment.
- Restrict access to the database, OAuth files, encryption key, and backups.
- Review rejected sign-ins and temporary locks in the Control Panel.
- Amazon SES is the transactional email provider. Production access is enabled
  in `us-east-1`; the verified sending domain uses DKIM, SPF, DMARC, custom
  MAIL FROM, and monitored bounce and complaint handling. Continue to send only
  expected transactional mail and review SES reputation metrics regularly.
- Configure the SES notification topic to use the HTTPS endpoint
  `/api/email-events/amazon-sns`. The endpoint verifies the SNS signature,
  certificate URL, signature version, and exact configured topic ARN before it
  confirms a subscription or processes an event.
- Never expose the SNS endpoint without `BTP_SES_SNS_TOPIC_ARN`. Messages from
  any other topic are rejected.
- Use the standard AWS credential chain. Never place AWS access keys in source
  code or commit them to the repository.
- Stage 1 applies process-local request limits to sensitive public account
  routes in addition to database-backed account locks. Move limiting to a
  shared edge or data service before adding multiple workers or instances.
- Every application response includes a request identifier. Operational logs
  record method, path, status, duration, and client address without recording
  credentials, tokens, query strings, request bodies, or uploaded content.
- Test login, logout, password recovery, organization suspension, and Super
  Admin access before every commercial release.
