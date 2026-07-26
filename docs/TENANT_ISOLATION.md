# Hosted tenant isolation

Status: database-level isolation, the restricted runtime connection, and an
authenticated API-level rehearsal have passed against the Project Polaris
Supabase staging database. The tenant boundary is ready for a small external
private-alpha rehearsal.

## Implemented controls

The hosted schema is separate from Doug's local capture workflow:

- `profiles`
- `observatories`
- `recommendation_runs`
- `recommendation_feedback`

Every table has a non-null UUID owner. Observatory-dependent records use
composite foreign keys that require the child `user_id` to match the owner of
the referenced observatory or recommendation run. A caller cannot attach a
record to another user's parent merely by knowing its UUID.

The profile and observatory APIs take ownership only from the validated access
token. Their request bodies reject an injected `user_id`. Every list,
direct-ID read, update, and delete query includes the authenticated owner
predicate. Cross-owner resources return the same not-found response as an
unknown UUID.

Migration `20260725_0003` creates a non-login `polaris_app` role with no
superuser, database-creation, role-creation, or RLS-bypass capability. It
receives schema usage and read/write access only to the four hosted tables.
Browser-facing `anon` and `authenticated` roles receive no direct table
privileges; the FastAPI service remains the sole hosted application-data
interface.

Migration `20260725_0004` makes the migration owner a member of
`polaris_app`. This does not give the application role more power; it lets the
administrator temporarily assume the restricted role during repeatable
security rehearsals.

The environment-specific login role `polaris_runtime` is created outside
source control with a generated password and membership in `polaris_app`.
Its credentials live only in the ignored `.env.staging` file. The checked-in
`.env.staging.example` documents the required settings without containing a
credential.

## PostgreSQL enforcement

Migration `20260724_0002` enables and forces Row Level Security on all four
hosted tables. Each policy applies the same expression to reads and writes:

```sql
user_id = NULLIF(
    current_setting('app.current_user_id', true),
    ''
)::uuid
```

Missing transaction identity therefore grants no row access.

The migration also enables and forces Row Level Security on the empty
local-product compatibility tables (`sessions`, `candidate_sites`, `captures`,
and `capture_analyses`) without granting them any policy. Those deferred
features are therefore deny-by-default in hosted PostgreSQL rather than
silently exposed through its Data API.

The Alembic version-tracking table has ordinary Row Level Security enabled
without a client policy. It contains no user data and remains writable by the
database owner for future migrations while browser roles receive no rows.

Each authenticated database session carries the validated user UUID.
SQLAlchemy's transaction-start hook calls:

```sql
SELECT set_config('app.current_user_id', :user_id, true)
```

The third argument makes the setting transaction-local. It is discarded at
commit or rollback instead of leaking through a pooled connection. The hook
runs again if application code commits and begins another transaction during
the same request.

## Verification completed locally

- Clean Alembic upgrade and model-drift check on a temporary SQLite database.
- Offline PostgreSQL migration compilation confirms `ENABLE ROW LEVEL
  SECURITY`, `FORCE ROW LEVEL SECURITY`, and owner policies for all four
  tables.
- Unit verification confirms PostgreSQL transactions receive the UUID and
  SQLite transactions do not execute PostgreSQL context SQL.
- A two-user API test creates Alice and Bob. Bob receives no Alice rows and
  cannot list, directly read, update, delete, or forge ownership of Alice's
  observatory.
- Hosted startup requires the complete hosted schema while local startup
  continues to require only Doug's existing local tables.

## Supabase staging proof

SQLite cannot execute PostgreSQL Row Level Security, so the database controls
were exercised against the Project Polaris Supabase staging database on
July 25, 2026.

The clean migration reached revision `20260725_0004`. The repeatable rehearsal
is stored in
`scripts/verify_postgresql_tenant_isolation.sql`. It uses recognizable
synthetic UUIDs, tests the restricted role, verifies transaction-local identity
reset, and deletes all synthetic rows before returning its result.

The rehearsal passed with:

- a non-superuser role with no `BYPASSRLS`;
- access to all four hosted tables and no access to local capture tables;
- Bob unable to see, update, delete, or forge ownership of Alice's data;
- no retained identity after a committed transaction;
- no visibility or inserts when the tenant identity is missing; and
- zero synthetic rows left behind.

The exact `polaris_runtime` login then connected from Doug's Mac through the
Supabase IPv4 session pooler. It remained non-superuser, kept RLS enforcement,
inherited `polaris_app`, could access the four hosted tables, and could not
access the local capture library.

## Authenticated hosted API proof

The end-to-end rehearsal passed on July 26, 2026. A temporary, auto-confirmed
Supabase user authenticated through the same password flow an alpha user will
use. Requests then passed through the running FastAPI service and its pooled
restricted PostgreSQL connection.

The temporary user:

- received a distinct validated identity;
- could not see Doug's observatory in list results;
- received the same not-found response for direct read, update, and delete
  attempts against Doug's observatory;
- could not inject Doug's `user_id` while creating a record;
- could create, read, update, and delete its own observatory normally; and
- left no observatory, profile, Auth user, credential file, or browser session
  behind after cleanup.

Doug's protected observatory was queried again after the attacks and remained
unchanged. The repeatable utility is
`scripts/verify_hosted_api_isolation.py`. It accepts temporary credentials only
through process environment or a restricted temporary file and never prints
the password or access token.

Database-level and authenticated API-level tenant isolation are now verified
hosted facts. A small external private alpha still needs to validate the human
onboarding and recommendation experience, but it is no longer blocked on this
specific data-separation proof.
