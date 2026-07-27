# Polaris hosted authentication boundary

Status: hosted sign-in, password recovery, first observing-home setup, and
authenticated tenant isolation have passed against the Supabase staging
project. Invitation-only external-user testing remains outstanding.

## Runtime modes

- `POLARIS_AUTH_MODE=local` returns one stable local operator identity. This is
  the default for Doug's existing local application and automated tests.
- `POLARIS_AUTH_MODE=supabase` requires a Supabase access token in the
  `Authorization: Bearer <token>` header.
- `staging` and `production` refuse to start unless auth mode is `supabase`.
- Hosted Supabase URLs must use HTTPS.

For Supabase mode, configure:

```text
POLARIS_AUTH_MODE=supabase
POLARIS_SUPABASE_URL=https://<project-ref>.supabase.co
POLARIS_SUPABASE_PUBLISHABLE_KEY=sb_publishable_<browser-safe-project-key>
POLARIS_SUPABASE_AUDIENCE=authenticated
```

Polaris derives the issuer and public-key endpoint from that project URL. It
accepts only Supabase's asymmetric `ES256` and `RS256` signing algorithms and
validates the signature, issuer, audience, expiration, issued-at time, role,
and UUID subject. Signing keys are cached for five minutes; private JWT secrets
are neither needed nor accepted by this implementation.

The browser receives only the Supabase project URL and its publishable key.
That key is designed for browser use; it does not grant server or database
administrator access. The restricted `polaris_runtime` database password and
all Supabase secret keys remain in ignored environment settings and are never
rendered into HTML.

## Hosted browser flow

When `POLARIS_AUTH_MODE=supabase`, the public operator shell initially shows a
sign-in form. A successful email-and-password sign-in provides the browser
access token to Polaris data requests. The first signed-in screen collects only
the display name and observing location needed for later personalized planning.
Users may mark coordinates as approximate instead of saving an exact observing
address.

An invitation link opens a short password-setup screen first. The invited
person chooses their own password there; Polaris never stores or displays it.
Existing users can request a password-recovery message from the Polaris sign-in
screen. The recovery link returns to the same Polaris origin and displays the
password-update screen before restoring the signed-in session.

This is intentionally not a hosted copy of Doug's existing dashboard yet. The
current local dashboard reads the personal capture library, and that library is
deliberately denied to the hosted runtime. The hosted planning engine now uses
the signed-in user's saved latitude, longitude, elevation, and timezone for
weather, darkness, Moon, visibility, transit, and schedule calculations. It
uses shared catalog settings instead of Doug's capture history or priorities.
The signed-in browser still shows setup only until the hosted Tonight
presentation and recommendation-record work are complete.

For the private alpha, configure Supabase to disallow public sign-ups and
invite individual testers. Supabase documents that disabling new sign-ups still
allows existing invited users to sign in, and its browser client is intended to
use the project URL plus a publishable key.

## Route inventory

Public shell and discovery routes:

- `/`
- `/operator` and its section URLs
- `/operator-assets/*`
- FastAPI schema/documentation URLs

Authenticated data and file routes:

- `/advisor/*`
- `/auth/me`
- `/candidate-sites/*`
- `/captures/*`
- `/dashboard`
- `/ingest-fits`
- `/mission/*`
- `/objects/*`
- `/observatories/*`
- `/operator-preview/*`
- `/parse-fits`
- `/planner/*`
- `/portfolio`
- `/profile`
- `/sessions/*`
- `/system`
- `/tonight`

The operator HTML and static assets remain public so the future login screen can
load. In Supabase mode, its data requests fail with HTTP 401 until the browser
supplies a valid access token.

## Security boundary and known gap

This slice establishes authentication: Polaris can determine who is making a
request and rejects missing or invalid hosted credentials.

The hosted `profiles`, `observatories`, `recommendation_runs`, and
`recommendation_feedback` tables now carry tenant ownership and PostgreSQL Row
Level Security policies. Existing capture/session/analysis/candidate-site
tables remain local-product data and are not approved for the hosted alpha.

See `docs/TENANT_ISOLATION.md` for the implemented controls and the remaining
staging-database proof required before any external alpha user is invited.

Reference:

- Supabase JWT verification:
  https://supabase.com/docs/guides/auth/jwts
- Supabase JWT claims:
  https://supabase.com/docs/guides/auth/jwt-fields
- PyJWT API:
  https://pyjwt.readthedocs.io/en/stable/api.html
