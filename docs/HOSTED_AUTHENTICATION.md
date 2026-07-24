# Polaris hosted authentication boundary

Status: implemented foundation for the hosted alpha; tenant ownership and the
browser sign-in flow are intentionally separate follow-on slices.

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
POLARIS_SUPABASE_AUDIENCE=authenticated
```

Polaris derives the issuer and public-key endpoint from that project URL. It
accepts only Supabase's asymmetric `ES256` and `RS256` signing algorithms and
validates the signature, issuer, audience, expiration, issued-at time, role,
and UUID subject. Signing keys are cached for five minutes; private JWT secrets
are neither needed nor accepted by this implementation.

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
- `/operator-preview/*`
- `/parse-fits`
- `/planner/*`
- `/portfolio`
- `/sessions/*`
- `/system`
- `/tonight`

The operator HTML and static assets remain public so the future login screen can
load. In Supabase mode, its data requests fail with HTTP 401 until the browser
supplies a valid access token.

## Security boundary and known gap

This slice establishes authentication: Polaris can determine who is making a
request and rejects missing or invalid hosted credentials.

It does **not** yet establish tenant authorization. Existing domain tables do
not have an owner ID, so the next database slice must add user/observatory
ownership and enforce it in both application queries and PostgreSQL Row Level
Security policies before any external alpha user is invited.

Reference:

- Supabase JWT verification:
  https://supabase.com/docs/guides/auth/jwts
- Supabase JWT claims:
  https://supabase.com/docs/guides/auth/jwt-fields
- PyJWT API:
  https://pyjwt.readthedocs.io/en/stable/api.html
