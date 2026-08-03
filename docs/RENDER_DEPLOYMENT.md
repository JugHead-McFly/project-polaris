# Render private-alpha deployment

Status: Polaris has a reproducible, zero-dollar Render web-service blueprint.
The first deployment remains private through Supabase sign-in and uses the
existing Supabase PostgreSQL project for durable data.

## What Render does

Render runs the FastAPI application on an internet-accessible HTTPS address.
It does not receive the local capture archive or local SQLite database.
The free instance may sleep after 15 minutes without traffic and can take
about one minute to wake.

The checked-in `render.yaml` deliberately:

- selects the free web-service instance;
- pins the service to the `develop` branch;
- deploys pushed `develop` commits automatically, so every tester-facing code
  change must be reviewed, tested, pushed intentionally, and verified on the
  hosted service before a tester opens Polaris;
- starts one Uvicorn process;
- uses `/health/ready` to verify database access before Render routes traffic;
- keeps all database and Supabase values out of source control; and
- leaves Sentry transmission disabled for the initial deployment.

## Required secret values

Render prompts for these three values when the Blueprint is created:

- `POLARIS_DATABASE_URL` — the restricted `polaris_runtime` PostgreSQL URL;
- `POLARIS_SUPABASE_URL` — the HTTPS URL for the Supabase project; and
- `POLARIS_SUPABASE_PUBLISHABLE_KEY` — the browser-safe publishable key.

Copy them from the ignored staging environment configuration. Never put a
database password, Supabase secret key, or Sentry DSN in `render.yaml`, Git,
chat, screenshots, or documentation.

## Migration boundary on the free service

Render's pre-deploy command is available only for paid web services. The free
private-alpha deployment therefore has an explicit gate:

1. back up the hosted tenant data;
2. run `python -m alembic upgrade head` separately with the migration-owner
   credential;
3. verify the database revision and tenant-isolation checks;
4. push the reviewed source revision to `develop` and let Render deploy it; and
5. verify `/health/live`, `/health/ready`, sign-in, observatory setup, and
   Tonight over HTTPS.

The application starts only after its startup preflight confirms that the
required hosted schema is present. The Render runtime receives only the
restricted `polaris_runtime` credential, not the migration-owner credential.

## Monitoring boundary

The first hosted deploy keeps `POLARIS_SENTRY_ALLOW_TRANSMISSION=false` and
does not need a Sentry DSN. After HTTPS, authentication, and data isolation
pass, add the DSN as a Render secret and explicitly enable transmission for
one synthetic privacy test. Follow `docs/ERROR_MONITORING.md`.
