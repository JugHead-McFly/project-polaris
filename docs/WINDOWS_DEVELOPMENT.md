# Windows local development

Doug's active product is the Render/Supabase hosted app. The legacy capture-library
transfer steps below are optional and do not block hosted-product development.
Automated tests are ready locally. A full signed-in hosted preview needs a separate
PostgreSQL/Supabase staging configuration; setup is in progress on this PC.
Do not connect experimental local changes to the live database by default.
`scripts/run_recovery_drill_app.py` provides an existing loopback-only viewer for a
separate Supabase recovery project; confirm its target and schema before reuse.

### Development database verified September 12, 2026

The separate Supabase project **Polaris Development** (`vqfvedywwahpqpnuivrp`)
was verified empty, then migrated from this checkout to `20260901_0008`.
The existing PostgreSQL tenant-isolation rehearsal passed: the application role
is neither superuser nor RLS-bypassing, can access hosted and forecast tables,
cannot access local captures, and left zero synthetic profiles behind.
Its IPv4 session pooler is `aws-0-ca-central-1.pooler.supabase.com:5432`.
The project URL and publishable key are configured in ignored `.env.staging`.
The approved `polaris_runtime` login is configured and verified: no superuser,
no RLS bypass, no local-capture access, and no profile visibility without a tenant
identity. Local startup and `/health/ready` pass with commit `cbdeafc` on `develop`.
The browser renders the sign-in page at `http://127.0.0.1:8002/operator`.
Development Auth's Site URL points to that address. The development user has
signed in successfully, saved an observing home, and loaded a weather-backed
imaging plan. The operator corrected the longitude sign, then reloaded the plan.
The verified page now displays an overnight window of 8:00 PM–4:15 AM, updated
weather, and a cloud-related wait recommendation. The local setup walkthrough
is complete; this verifies operation, not the accuracy of the weather forecast.
These checks did not modify the live Supabase project.

Tile 06 development fixture: at Doug's request, 93 matched forecast snapshots
were copied read-only from the live account's `Test Site` into the development
observing home. They represent 11 distinct forecast hours/checks. Ownership and
observatory IDs were mapped to the development account; measurements, timestamps,
and snapshot IDs were preserved. They are imported historical test data, not
observations collected by this development installation. Pending source records
were not imported. The live database was not modified.

Start the hosted development preview from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --env-file .env.staging --host 127.0.0.1 --port 8002
```

This checkout uses Python 3.11, as specified by `.python-version`.
Run commands from the repository root in PowerShell. Activation is optional;
calling the virtual environment's interpreter directly avoids execution-policy
issues.

## Setup

On a machine with Python 3.11 installed:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

On Doug's September 12 Windows checkout, Python 3.11.16 was provisioned under
`.cache/python` and `.venv` is already installed. Keep that interpreter directory
while using this environment. Both directories are ignored by Git. The bundled
Codex Python 3.12 installation was not changed.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
node --test tests/operator_chart_resize.test.cjs
.\.venv\Scripts\python.exe scripts/nightly_test_bed_report.py
.\.venv\Scripts\python.exe scripts/check_startup.py
```

The Python suite uses isolated databases. Dashboard tests read UTF-8 explicitly
and ignore checkout line-ending differences in multiline asset assertions.
The version endpoint test creates its own in-memory schema rather than relying
on an operator database.

The nightly report also checks the real local database read-only. All five
synthetic scenarios can pass while the overall report exits with code 1 because
`polaris.db` is absent. Report those outcomes separately.

## Personal data and startup

Git does not supply Doug's private database, FITS library, or settings. The
September 12 checkout does not have those assets. Startup remains blocked until
the required database and library are restored and their paths verified.
Use the matched-pair backup procedure in [OPERATIONS.md](OPERATIONS.md); preserve
the original data and validate a copied database/library pair before using it.
The older Mac paths in that runbook are source-machine references, not Windows
installation paths. Do not create an empty operator database merely to hide the
missing-data condition.

After the startup check reports Ready:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/operator`. Local tests do not verify the live Render
deployment. The Render blueprint deploys `develop` automatically, so a push may
trigger deployment.

## Transfer checklist from the original computer

1. Confirm the original repository, current branch/commit, and any uncommitted
   or unpushed work. Do not assume GitHub includes work still local to that machine.
2. Stop the local Polaris server before copying its database. Preserve the source
   installation and create a dated folder containing `polaris.db` and the complete
   `ProjectPolaris` library, maintaining filenames and directory structure.
3. On the source machine, run `scripts/verify_backup_pair.py` against that dated
   folder with the project's Python interpreter. Keep its report with the backup.
4. Transfer the verified backup privately to this PC and rerun verification here.
   Do not put the database, images, or private configuration in GitHub or chat.
5. Review private configuration locally and resolve source-machine paths using a
   working copy. The current Windows library default is
   `C:\Users\Doug\ProjectPolaris`. Stored Mac asset paths may require relocation;
   inspect before changing any records and retain the untouched backup.
6. Require passing startup preflight, read-only library audit, expected inventory,
   and a browser walkthrough before declaring the personal installation ready.

Source-machine paths documented previously are
`/Users/doug/dougs-observatory/polaris.db` and `/Users/doug/ProjectPolaris`.
Confirm them on the source machine before copying. A source-machine check should
also establish whether any newer unpushed code needs transferring separately.
