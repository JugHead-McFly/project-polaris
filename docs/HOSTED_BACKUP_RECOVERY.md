# Hosted-alpha backup and recovery

Status: the tenant export, integrity check, disposable rehearsal, retained
encrypted off-device recovery point, and full restore into a separate Supabase
project passed by July 27, 2026. The remaining business decision is whether
manual exports provide an acceptable recovery point objective for the external
alpha.

## Current Supabase plan boundary

The Project Polaris staging project is currently on Supabase Free. Supabase
recommends that Free projects regularly create their own off-site logical
exports. Automatic daily backups with seven-day retention are a Pro feature.

Official references:

- https://supabase.com/docs/guides/platform/backups
- https://supabase.com/docs/guides/platform/clone-project

Do not treat the current Free project as having a dependable operator-accessible
daily restore point. Do not upgrade the plan or enable a paid recovery feature
without Doug's explicit approval.

## What the Polaris tenant export contains

The tenant-safe export contains only records owned by the selected authenticated
Polaris user:

- profile;
- observatories;
- hosted recommendation runs; and
- hosted recommendation feedback.

The restricted runtime database role remains subject to Row Level Security
during export. It cannot export another tenant merely because the caller knows
another UUID.

The JSON file includes an embedded SHA-256 checksum. It is created with
owner-only file permissions and refuses to overwrite an existing path.

## What it does not contain

The export does not contain:

- Supabase Auth users or password hashes;
- Supabase project, email, or provider configuration;
- secret keys or database passwords;
- future Storage objects;
- Doug's local FITS capture library; or
- the local `polaris.db` database.

If this tenant export is the only available recovery source, accounts must be
re-invited before restored users can sign in. The local database and capture
library continue to use their separate matched-pair backup procedure.

## Create a tenant export

Load the ignored staging environment, then provide the exact user UUID and a
new output filename:

```text
set -a
source .env.staging
set +a
.venv/bin/python scripts/export_hosted_tenant.py \
  <user-uuid> \
  /path/on/encrypted-backup-media/polaris-hosted-YYYY-MM-DD.json
```

The destination folder must already exist. The script will stop rather than
replace an existing file.

The output contains observing-location data. Store it only on encrypted media
or in an approved encrypted backup destination. File permissions alone are not
encryption.

## Verify and rehearse the restore

Run:

```text
.venv/bin/python scripts/verify_hosted_tenant_backup.py \
  /path/to/polaris-hosted-YYYY-MM-DD.json
```

The verifier:

1. validates the format and complete table inventory;
2. checks that every record belongs to the declared user;
3. checks observatory, recommendation, and feedback relationships;
4. recalculates the SHA-256 checksum; and
5. restores the document into a disposable in-memory database and compares all
   restored record counts.

It does not write to the live Supabase project.

## July 26 rehearsal evidence

Doug's real hosted tenant was exported through the restricted runtime role.
The file was created with owner-only permissions. Verification and disposable
restore passed with:

- one profile;
- one observatory;
- zero recommendation runs; and
- zero recommendation-feedback records.

The zero recommendation counts are expected because hosted recommendation
history has not been enabled yet. The temporary export was removed after the
rehearsal.

## July 27 retained recovery point

Doug created and retained an encrypted off-device export of the real hosted
account on the Polaris Backup drive. The export and its disposable restore
rehearsal passed with one profile, one observatory, and no recommendation runs
or feedback records. The export payload checksum was
`d3b6cd1e2f4da2b3d8b3ba7ca0c6ca26a551b796cabf66701adb93dd93cb63c1`.
The code baseline was commit `c8c8e0f` (`Clarify exposure planning
requirements`).

## July 27 separate-project recovery drill

The retained encrypted export was restored into a newly created, otherwise
empty Supabase project rather than into the live source project. The recovery
command refused the live project reference, applied the complete Alembic
schema, and remapped all restored ownership to a newly recreated Supabase Auth
user.

The real PostgreSQL restore passed with:

- the expected payload checksum;
- one profile and one observatory;
- zero recommendation runs and zero recommendation-feedback records;
- all restored rows owned by the recreated Auth user; and
- a second unrelated user identity seeing zero restored rows through Row Level
  Security.

The recovered application then started through the restricted `polaris_app`
database role. The recreated user signed in successfully, skipped onboarding,
saw the restored `Home` observatory, and received a normal live nightly
recommendation. The live source project and its account were not changed.

After verification, the disposable `Polaris Recovery Drill` Supabase project
was permanently deleted. The encrypted export and reusable recovery scripts
were retained; future drills should create a new empty recovery project so the
test also proves recovery does not depend on leftover infrastructure.

The observed first full drill took approximately 90 minutes from separate
project setup through application verification. That includes creation of the
reusable recovery tooling and diagnosis of one safely rolled-back insertion
ordering failure. A future repeat drill should be timed separately to establish
the steady-state recovery time.

Reusable commands:

- `scripts/restore_hosted_tenant_to_postgres.py` migrates and restores a
  verified export into a separate Supabase project.
- `scripts/run_recovery_drill_app.py` starts a local recovery viewer against
  that project through the restricted application role without saving
  credentials to a file.

## Remaining recovery gates

Before an external tester is invited:

1. decide the acceptable recovery point objective;
2. upgrade to a plan with daily backups or formally accept and document the
   manual-export risk; and
3. retain a written export cadence and owner if the manual-export approach is
   accepted.

Storage objects need their own backup design before user uploads are enabled.
Supabase database backups do not restore deleted Storage objects.
