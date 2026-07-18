# Project Polaris Release Checklist

This checklist is the required release path for Project Polaris v1.5 and later.
It does not authorize equipment control, data deletion, a Git tag, or a remote
push. Tagging and pushing remain explicit operator decisions.

## Required inputs

- Exact release version, such as `1.5.1`.
- Clean `develop` branch containing the intended release code and documentation.
- New timestamped backup folder containing matched `polaris.db` and
  `ProjectPolaris` copies.
- Local Polaris API running at the URL used for smoke testing.

Stop the release if any required input is unavailable or any automated gate
reports `Blocked`.

## 1. Freeze the release candidate

1. Finish active changes and review `git status`.
2. Set the version once in `app/core/config.py` and update its version test.
3. Run the complete test suite.
4. Commit the release candidate so the working tree is clean.
5. Record the candidate commit ID. Do not tag yet.

Commands:

    git status --short
    .venv/bin/python -m pytest
    git log -1 --oneline

## 2. Create and verify the recovery point

1. Stop Project Polaris so the database copy is consistent.
2. Create a new timestamped folder outside the live repository and capture
   library, preferably on a separate disk.
3. Copy `polaris.db` and the complete `ProjectPolaris` folder into it.
4. Record the release version, candidate commit, backup date, and destination.
5. Verify the copied pair before restarting the application:

       .venv/bin/python scripts/verify_backup_pair.py /path/to/timestamped-backup

The report must set `valid` to `true`. A database-only copy, library-only copy,
or mismatched pair blocks the release.

## 3. Start and smoke-test the candidate

Start the candidate using the normal operations runbook. Confirm the startup
preflight reports `Ready`, then run the complete release gate:

    .venv/bin/python scripts/release_check.py \
        --expected-version 1.5.1 \
        --backup-root /path/to/timestamped-backup \
        --base-url http://127.0.0.1:8000

The release gate verifies:

1. The expected branch is clean.
2. Application version matches exactly.
3. All startup-preflight checks pass.
4. The complete automated test suite passes.
5. The timestamped backup pair is valid.
6. `/`, `/operator`, `/system`, `/tonight`, and `/dashboard` return HTTP 200;
   version-bearing responses match the expected version.

The final report must say `Release Ready` with zero failures. Save the report
with the release record.

## 4. Operator review

Before tagging, confirm:

- The operator dashboard clearly displays the safety decision.
- Capture-library health has zero conflicts.
- Weather failure still produces `Do Not Image`.
- Moving-target ephemeris failure still excludes the affected target.
- No observatory equipment-control behavior was introduced.
- The verified backup can be located without relying on the live data paths.

## 5. Tag and publish

Only after explicit operator approval:

1. Create an annotated tag matching the application version, such as `v1.5.1`.
2. Push the `develop` branch.
3. Push the exact release tag.
4. Confirm the remote branch and tag point to the reviewed candidate commit.

Do not move or replace an existing release tag. If the candidate changes after
verification, commit the correction and restart this checklist from step 1.

## 6. Post-release and rollback boundary

After publishing, rerun the startup preflight and live smoke endpoints. If code
validation fails, stop the candidate and diagnose before continued use. If data
integrity is in question, stop all writes and follow the matched-pair recovery
procedure in `docs/OPERATIONS.md`; do not automatically overwrite live data.
