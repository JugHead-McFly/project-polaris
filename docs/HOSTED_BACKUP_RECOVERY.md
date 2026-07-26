# Hosted-alpha backup and recovery

Status: the tenant export, integrity check, and disposable restore rehearsal
passed on July 26, 2026. A retained encrypted off-device recovery point and a
full restore into a separate Supabase project remain required before external
alpha access.

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

## Remaining recovery gates

Before an external tester is invited:

1. retain a dated export on encrypted off-device media;
2. record the export checksum and source commit;
3. decide the acceptable recovery point objective;
4. upgrade to a plan with daily backups or formally accept and document the
   manual-export risk;
5. restore into a separate Supabase test project and verify account
   re-invitation, schema, Row Level Security, and application behavior; and
6. document the observed recovery time.

Storage objects need their own backup design before user uploads are enabled.
Supabase database backups do not restore deleted Storage objects.
