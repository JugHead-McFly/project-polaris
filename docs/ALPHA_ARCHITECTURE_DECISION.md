# Polaris Hosted-Alpha Architecture Decision

Status: **Accepted for v1.7 implementation**

Decision date: 2026-07-24

Revisit after: the first 5–10 private-alpha users complete the nightly
recommendation loop, or earlier if a security, reliability, or cost assumption
fails.

## Decision in plain English

Polaris will become a small hosted web product without rewriting the astronomy
engine.

- Keep the existing FastAPI application, Python recommendation logic, and
  responsive web interface as one deployable application.
- Host that application as one Render web service.
- Use Supabase for managed PostgreSQL, user authentication, and—only when it is
  actually needed—private object storage.
- Add an authenticated user and observatory boundary to every piece of
  user-owned data.
- Keep raw FITS ingestion, the local capture archive, portfolio, and quality
  analysis out of the first hosted alpha.

This is a modular monolith, not a microservice system. It is intentionally the
smallest architecture that can safely test whether users return to Polaris for
a nightly observing recommendation.

## Why this decision is needed

The v1.6 application is a strong local product, but its hosting shell assumes
one trusted operator:

- one SQLite database;
- one hard-coded observatory and timezone;
- one home-folder capture library;
- absolute local file paths;
- API routes with no authenticated user context;
- tables with no user or observatory owner;
- ad hoc schema changes rather than a migration system.

The astronomy, scheduling, scoring, dashboard, and explanatory logic are
valuable reusable assets. The current data and configuration boundary is not a
safe multi-user boundary.

The audit evidence is visible in the current code:

| Current boundary | Evidence |
| --- | --- |
| Local database | `app/core/config.py` constructs a SQLite URL for `polaris.db` |
| Global database access | API modules instantiate the shared `SessionLocal` directly |
| Single observatory | `app/core/observatory.py` contains Doug-specific name, coordinates, postal code, and timezone |
| Local file library | `app/core/storage.py` roots storage at `~/ProjectPolaris` |
| No record owner | Capture, session, analysis, and candidate-site models have no authenticated `user_id` |
| No migration framework | The repository has no Alembic configuration or migration history |

## Alpha scope

### Included in v1.7

- Invitation-only Supabase email authentication and session management.
- A Polaris profile linked to the authenticated Supabase user UUID.
- One or more user-owned observing locations.
- PostgreSQL schema and Alembic migrations.
- Request-scoped database sessions.
- User ownership and isolation for every hosted table.
- Secure environment configuration.
- A reproducible Render deployment and health check.
- Error monitoring with sensitive-data scrubbing.
- Database backup and restore exercises.
- Automated two-user isolation tests.

### Included in v1.8

- Phone-friendly onboarding for location and essential telescope context.
- Tonight's recommendation, alternatives, usable window, and explanation.
- A small recommendation-feedback record: useful/not useful plus an optional
  reason.

### Explicitly deferred

- Migrating Doug's current SQLite capture library to the hosted product.
- Raw FITS uploads or persistent raw-image storage.
- Hosted portfolio, quality, history, and location-discovery features.
- Background image-processing workers.
- Native iOS or Android applications.
- Subscriptions, teams, social sharing, and a broad device matrix.

Doug's current database and `DWARF Archive` remain the source of truth for the
local v1.6 product until a separate, tested migration is approved. No production
deployment may silently move, rewrite, or delete those files.

## Chosen component model

| Concern | v1.7 decision | Reason |
| --- | --- | --- |
| Web application | Existing FastAPI backend and static web UI | Reuses the working planner and avoids a validation-delaying rewrite |
| Application hosting | One Render web service | FastAPI is directly supported; deployment, secrets, logs, and health checks are available without operating servers |
| Authentication | Supabase Auth | Provides managed users, sessions, signed JWTs, and a direct identity key for data ownership |
| Relational database | Supabase PostgreSQL | Replaces local SQLite and keeps authentication, PostgreSQL, and future private storage under one managed project |
| Schema changes | Alembic migrations executed by a migration-only credential | Makes changes reviewable and repeatable; the runtime application must not own schema administration |
| User files | No raw files in the first hosted loop; Supabase private Storage is reserved for later | The recommendation habit can be tested without accepting high-volume, sensitive FITS uploads |
| Monitoring | Structured application logs, Render health/notifications, and Sentry error reporting | Gives Doug deploy and application failure visibility without building an operations platform |
| Delivery model | Responsive web alpha | Enables fast fixes and avoids native-store work before the workflow is validated |

## Request and data flow

1. The browser signs in through Supabase Auth.
2. Supabase issues a short-lived signed access token.
3. The browser calls the Polaris FastAPI service with that bearer token.
4. FastAPI validates the token signature, issuer, audience, expiry, and subject
   using Supabase's published signing keys.
5. FastAPI opens a request-scoped database transaction and establishes the
   authenticated user UUID as transaction-local context.
6. Application queries include an explicit owner predicate. PostgreSQL row
   security supplies a second enforcement layer.
7. FastAPI returns only the authenticated user's observatory, recommendation,
   and feedback data.

The browser will not receive a PostgreSQL credential or a Supabase service-role
key. The browser will not call hosted Polaris tables through the Supabase Data
API during the alpha. The FastAPI service remains the only application-data
interface so the existing domain logic has one controlled boundary.

Public self-registration is disabled for the private alpha. Doug invites the
small tester cohort through a controlled operator workflow. Administrative
credentials and invite operations are never exposed in browser code.

## Tenant-isolation rules

Security does not depend on hiding buttons or using hard-to-guess IDs.

1. Every hosted user-owned table has a non-null `user_id` UUID.
2. Observatory-dependent records also have a non-null `observatory_id`.
3. Public API identifiers are UUIDs; UUIDs improve enumeration resistance but
   are not treated as authorization.
4. Every read, create, update, and delete operation is authorized against the
   authenticated owner.
5. The PostgreSQL runtime role is a restricted `polaris_app` role. It is not
   the database owner, `postgres`, or a role with `BYPASSRLS`.
6. Row-level security is enabled and forced on hosted tenant tables.
7. At transaction start, the trusted backend sets a transaction-local user UUID
   after it validates the JWT. Policies compare each row's `user_id` with that
   value.
8. Migration and backup credentials are separate from runtime credentials and
   are never available to the browser.
9. Automated tests create Alice and Bob and attempt cross-user list, direct-ID
   read, create-with-forged-owner, update, and delete operations.
10. The v1.7 exit test fails if any Alice/Bob crossover succeeds, even when the
    route is not linked from the interface.

RLS policy design and connection-pool behavior must be exercised in PostgreSQL,
not only in SQLite unit tests. Transaction-local identity must be reset
automatically at transaction end so pooled connections cannot retain a prior
user's context.

## Initial hosted data model

### `profiles`

- `user_id` UUID primary key, matching the Supabase Auth user.
- display name and onboarding state only.
- no password or authentication secret.

### `observatories`

- UUID primary key.
- non-null `user_id`.
- user-visible name, latitude, longitude, elevation, timezone, and optional
  postal/Bortle context.
- no street address is required or stored.

### `recommendation_runs`

- UUID primary key.
- non-null `user_id` and `observatory_id`.
- planner timestamp, forecast timestamp, recommendation outcome, compact input
  provenance, and planner version.
- enough information to explain and debug a recommendation without storing
  unnecessary weather payloads.

### `recommendation_feedback`

- UUID primary key.
- non-null `user_id`, `observatory_id`, and `recommendation_run_id`.
- useful/not useful, optional short reason, and timestamp.

Existing capture/session/analysis/candidate-site models remain part of the local
product. Before any one becomes hosted, it must receive the same ownership,
privacy, migration, and isolation treatment.

## Location and privacy boundary

Astronomy calculations require coordinates, but Polaris does not need a home
address. The hosted product stores latitude/longitude, elevation, and timezone.
The onboarding UI must explain why location is required and may offer an
approximate-location option if testing shows that users prefer it.

Logs, error events, and support exports must not contain:

- access tokens or credentials;
- raw FITS data;
- exact coordinates by default;
- street addresses;
- full weather-provider payloads;
- user email addresses unless a support action specifically requires them.

## Deployment and configuration

- Add a `render.yaml` blueprint only after the local PostgreSQL/auth boundary
  passes tests.
- Pin a supported Python version rather than accepting the host's changing
  default.
- Start one Uvicorn web process; do not introduce a worker service until a
  measured task requires it.
- Store database, auth, weather, ephemeris, monitoring, and signing
  configuration in environment secrets.
- Provide separate local/test/staging/production settings and reject unsafe
  production defaults.
- Run Alembic migrations as a controlled pre-deploy step with the migration
  credential.
- Expose separate liveness and readiness endpoints. Readiness performs a small
  database check and does not disclose global row counts or private state.
- Keep production data out of developer fixtures and test databases.

## Backups and recovery

For an external alpha, use a paid Supabase plan with daily database backups.
Supabase documents seven-day daily-backup retention for Pro. Those database
backups do not include Storage objects, so future file storage requires its own
backup and retention plan.

Polaris also requires:

- a periodic encrypted logical database export kept outside the live Supabase
  project;
- a documented restore procedure;
- one successful restore into a separate test project before external alpha;
- a written recovery point and recovery time observed during that drill;
- a separate Storage-object recovery design before uploads are enabled.

A backup is not considered proven merely because a provider says it exists.

## Cost guardrail

No infrastructure purchase is authorized by this decision.

Current official pricing lists Supabase Pro from $25/month with one Micro
project, 8 GB database disk, 100 GB file storage, and seven days of daily
backups. Render pricing and instance choices must be reconfirmed at
provisioning. The private-alpha infrastructure target is **no more than
$50/month before domain, external weather/API use, and email**. Doug must
approve any recurring account or paid upgrade.

Free tiers may be used for disposable development experiments. They are not the
external-alpha reliability plan: Supabase Free does not include automatic
backups, and free hosted services may pause or expire.

## Alternatives considered

| Alternative | Decision | Reason |
| --- | --- | --- |
| Keep SQLite on a persistent hosted disk | Rejected | Preserves the single-machine boundary, complicates safe scaling/deploys, and does not solve tenancy |
| Rewrite the product in Next.js/React before alpha | Rejected | Replaces working domain code and introduces a broad rewrite before demand is validated |
| Build native mobile apps first | Rejected | Adds two release channels and store constraints before proving repeat web use |
| Split planner, weather, portfolio, and scoring into microservices | Rejected | Creates operational complexity without a measured scale or team need |
| Let the browser query hosted Polaris tables directly | Rejected for alpha | Duplicates authorization/data-access behavior and increases the exposed surface during the first multi-user release |
| Render web service plus Render PostgreSQL plus separate auth and object-storage vendors | Not selected | Technically valid, but adds more service boundaries than the integrated Supabase Auth/Postgres/Storage option |
| Store all existing FITS and processed images in hosted storage immediately | Rejected | Large uploads, retention, processing, privacy, and cost do not help validate the core recommendation habit |

## v1.7 implementation sequence

### Slice 1 — configuration and PostgreSQL compatibility

- Introduce typed environment settings.
- Make the database URL configurable.
- Add PostgreSQL driver support.
- Add Alembic and baseline the current schema.
- Keep local SQLite operation working.
- Add PostgreSQL to automated integration tests.

**Done when:** the same safe, non-file workflows run against local SQLite and a
clean PostgreSQL database created entirely from migrations.

### Slice 2 — authentication boundary

- Create Supabase development and staging configuration.
- Configure invitation-only access and add sign-in/sign-out/session UI.
- Validate JWTs in FastAPI through one `CurrentUser` dependency.
- Replace global `SessionLocal()` creation in route modules with a
  request-scoped database dependency.
- Add explicit public, authenticated, and operator-only route classifications.

**Done when:** unauthenticated requests cannot access user data and expired,
wrong-issuer, wrong-audience, or malformed tokens fail closed.

### Slice 3 — user and observatory ownership

- Add `profiles` and `observatories`.
- Replace hard-coded observatory constants in hosted planner paths with an
  authenticated observatory context.
- Add `user_id` and `observatory_id` to new hosted recommendation and feedback
  records.
- Keep local v1.6 data unchanged behind an explicit local-development mode.

**Done when:** Alice and Bob can configure different locations and receive
recommendations calculated from their own location and timezone.

**Status (2026-07-26):** complete in the planning core and protected APIs.
Hosted planning uses the shared target catalog and does not query Doug's
private capture library. Browser presentation and persisted recommendation
runs remain v1.8 work.

### Slice 4 — defense-in-depth isolation

- Create restricted runtime and migration database roles.
- Add and force RLS policies.
- Establish transaction-local user identity.
- Add explicit owner filters in repositories/services.
- Test all verbs, direct IDs, forged payload owners, pooled-connection reuse,
  and administrator-only operations against PostgreSQL.

**Done when:** the full two-user isolation suite passes and a deliberate
cross-user regression is caught by both tests and database policy.

### Slice 5 — deploy, observe, and recover

- Pin Python and add reproducible build/start configuration.
- Add staging Render service and health checks.
- Add scrubbed structured logs, Sentry, and deployment/failure notifications.
- Create backup procedure and encrypted export.
- Restore into a separate test project.
- Record actual monthly cost and configure spend alerts where supported.

**Done when:** a clean staging deployment works from source, a simulated
application error is visible, an unhealthy database fails readiness, and a
backup restore is verified.

### Slice 6 — v1.7 acceptance

- Run the two-user scenario from separate browser sessions.
- Review the route inventory for missing authentication.
- Verify no local archive path or Doug-specific observatory default appears in
  production responses.
- Run dependency, secret, migration, and deployment checks.
- Write the v1.7 release evidence and a rollback procedure.

**Done when:** two users cannot see or affect each other's data, and backup,
monitoring, rollback, and recovery evidence are recorded.

## Stop conditions

Pause implementation and revisit this decision if:

- safe RLS identity propagation cannot be proven with pooled SQLAlchemy
  connections;
- scientific dependencies cannot run reliably inside the selected web-service
  memory limit;
- recurring infrastructure exceeds the $50/month alpha guardrail;
- authentication introduces onboarding friction that prevents the core test;
- discovery evidence shows that the alpha cannot provide value without image
  ingestion;
- a provider constraint would lock Polaris into an expensive rewrite before
  20 active users.

## Primary references checked

- [Render: Deploy a FastAPI app](https://render.com/docs/deploy-fastapi)
- [Render: Deploying on Render](https://render.com/docs/deploys)
- [Render: Health checks](https://render.com/docs/health-checks)
- [Render: Environment variables and secrets](https://render.com/docs/environment-variables)
- [Supabase: Auth architecture](https://supabase.com/docs/guides/auth/architecture)
- [Supabase: JSON Web Tokens](https://supabase.com/docs/guides/auth/jwts)
- [Supabase: Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase: Connect to PostgreSQL](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase: Storage access control](https://supabase.com/docs/guides/storage/security/access-control)
- [Supabase: Database backups](https://supabase.com/docs/guides/platform/backups)
- [Supabase: Pricing](https://supabase.com/pricing)
