# Cookie and Browser Storage Inventory

Verified from the application source on September 8, 2026. Recheck before each
material frontend or third-party integration change.

## Cookies

| Name | Type and purpose | Lifetime | Consent assessment |
|---|---|---|---|
| `btp_session` | Secure authentication session; HTTP-only, SameSite Strict, Secure in production | Browser session by default; 30 days only when the user selects the remembered-session option | Strictly necessary for authenticated service access; do not use for analytics or advertising |

## Local browser storage

| Storage | Purpose | Scope or lifetime |
|---|---|---|
| `broadcastToolPro.language` | Remembers English or Spanish interface preference | Until browser data is cleared |
| `broadcastToolPro.theme` | Remembers light or dark theme | Until browser data is cleared |
| `btp.active-channel.<organization>` | Remembers the selected channel identifier for the signed-in organization | Until browser data is cleared |
| Scoped Pre Log filter values and mode | Restores the user's operational filter choices | Until browser data is cleared |
| Post Log filter values | Restores the user's operational filter choices | Until browser data is cleared |
| IndexedDB Post Log profiles | Saves user-created Post Log settings and an optional logo locally in that browser | Until the user deletes the profile or clears browser data |

## Third-party tracking result

No analytics SDK, advertising pixel, third-party behavioral tracker, or
client-side payment script was found in the application source. Stripe
Checkout is opened as an external secure checkout flow rather than embedded as
a tracking component.

On the verified implementation, a marketing-cookie consent banner is not
needed because no non-essential tracking technology was identified. The public
privacy information should still disclose essential session storage and local
preferences. This conclusion must be revisited before adding analytics,
advertising, chat widgets, embedded media, A/B testing, or another third-party
browser component.
