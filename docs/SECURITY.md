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
- Recovery messages are queued in the email outbox. Commercial launch requires
  connecting and monitoring an email delivery provider.

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

- Keep application and dependency security updates current.
- Restrict access to the database, OAuth files, encryption key, and backups.
- Review rejected sign-ins and temporary locks in the Control Panel.
- Amazon SES is the transactional email provider. Verify the sending domain,
  enable DKIM, SPF, and DMARC, request SES production access, and monitor
  bounces and complaints before enabling customer delivery.
- Use the standard AWS credential chain. Never place AWS access keys in source
  code or commit them to the repository.
- Add infrastructure-level request limiting before public launch; the current
  database-backed account lock protects individual accounts but does not
  replace edge-level abuse protection.
- Test login, logout, password recovery, organization suspension, and Super
  Admin access before every commercial release.
