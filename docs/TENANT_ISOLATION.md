# Hosted tenant isolation

Status: application boundary and migration are implemented; execution against
a real PostgreSQL staging database remains an alpha blocker.

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

## Required staging proof

SQLite cannot execute PostgreSQL Row Level Security. Before inviting an alpha
user, a real PostgreSQL staging test must:

1. connect with the exact restricted runtime role intended for Render;
2. verify that the role is not the table owner and does not have `BYPASSRLS`;
3. migrate a blank database to the current Alembic head;
4. create Alice and Bob through separate authenticated transactions;
5. attempt cross-user list, direct-ID read, forged-owner insert, update, and
   delete at both the API and raw-SQL levels;
6. commit and reuse a pooled connection to prove the prior UUID is gone;
7. run the same checks with the tenant setting missing;
8. record the results and database role grants in this document.

Until that exercise passes, RLS behavior is a compiled design rather than a
verified hosted fact. No production or external-alpha claim should say tenant
isolation is complete.
