# Hosted-alpha account removal

Status: private-alpha operator runbook

Use this when an invited tester leaves the alpha, asks for removal, or when a
throwaway test account should be cleaned up. This is a manual operator process,
not an application feature.

## Safety rules

- Remove only one tester at a time.
- Do not record passwords, access tokens, invitation links, exact addresses, or
  private feedback comments in Git.
- Use the Supabase Auth user ID as the join point between Auth and Polaris
  hosted data.
- Export first when the tester's data should be retained for recovery,
  debugging, or audit. Delete first only for obvious throwaway accounts.
- If another user's data appears under the tester account, stop and investigate
  tenant isolation before deleting evidence.

## Data Polaris stores for hosted alpha

The hosted alpha stores:

- one profile row;
- zero or more observatory rows;
- hosted recommendation runs; and
- hosted Yes/No feedback rows.

It does not store passwords, Supabase Auth credentials, Doug's local FITS
library, or Doug's local `polaris.db`.

## Remove a throwaway test account

Use this for accounts created only for internal checks.

1. In Supabase Authentication, find the test user's Auth record.
2. Copy the Auth user UUID.
3. In the hosted database, remove rows owned by that UUID in this order:

   ```sql
   delete from recommendation_feedback where user_id = '<auth-user-uuid>';
   delete from recommendation_runs where user_id = '<auth-user-uuid>';
   delete from observatories where user_id = '<auth-user-uuid>';
   delete from profiles where user_id = '<auth-user-uuid>';
   ```

4. Delete the Supabase Auth user.
5. Run the aggregate alpha metrics report:

   ```bash
   .venv/bin/python scripts/alpha_metrics_report.py --env-file .env.staging
   ```

6. Record only that the throwaway account was removed. Do not record the email
   address in project docs unless Doug has a separate private operator tracker.

## Remove an invited tester

Use this for a real external tester.

1. Confirm the tester request or Doug's reason for removal outside Git.
2. If data should be retained, create a tenant export first:

   ```bash
   set -a
   source .env.staging
   set +a
   .venv/bin/python scripts/export_hosted_tenant.py \
     <auth-user-uuid> \
     /path/on/encrypted-backup-media/polaris-hosted-YYYY-MM-DD.json
   ```

3. Verify the export before deleting live rows:

   ```bash
   .venv/bin/python scripts/verify_hosted_tenant_backup.py \
     /path/on/encrypted-backup-media/polaris-hosted-YYYY-MM-DD.json
   ```

4. In Supabase Authentication, either prevent sign-in using the available Auth
   control if a temporary support pause is needed, or delete the Auth user if
   removal is final.
5. Remove Polaris hosted rows for that UUID in the same order as the throwaway
   cleanup.
6. Run the aggregate alpha metrics report and confirm the counts changed as
   expected.
7. Record the removal in Doug's private operator tracker with the date, tester
   alias, and whether an encrypted export was retained.

## When not to delete yet

Pause before deletion when:

- the tester reports seeing another user's data;
- the tester reports a safety-risk misunderstanding;
- the account is part of an active bug investigation;
- the export verification failed; or
- Doug is unsure whether the account belongs to a real tester.

In those cases, disable sign-in if needed, preserve the minimum evidence, and
resolve the investigation before removing rows.

## Future product requirement

Before closed beta, Polaris should replace this manual runbook with a reviewed
admin process for account disablement, data export, deletion, and confirmation.
