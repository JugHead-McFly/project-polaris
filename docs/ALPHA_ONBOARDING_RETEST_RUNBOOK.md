# Alpha onboarding retest runbook

Use this as the one-page checklist for the next nontechnical onboarding retest.
It combines the hosted go/no-go gate, human retest script, and evidence record.

## Before deploying or testing

1. Confirm the local working tree has no unintended changes except an active
   timer entry.
2. Run the focused account/operator tests:

       .venv/bin/python -m pytest tests/test_operator_dashboard.py tests/test_hosted_account_api.py

3. Confirm the intended `develop` commit is pushed to GitHub.
4. If this is more than a copy-only change, create or confirm a recent verified
   backup before touching hosted data.

## Hosted go/no-go

1. Deploy the intended GitHub `develop` commit intentionally in Render.
2. Open:

       https://project-polaris-private-alpha.onrender.com/health/live
       https://project-polaris-private-alpha.onrender.com/health/ready

3. Sign in as Doug and confirm the saved observing home still loads.
4. Refresh Tonight and confirm Polaris shows either a recommendation or a safe
   `Do Not Image` result.
5. Save one Yes/No usefulness response and confirm the page says it saved.
6. Use a separate tester account or browser profile with no observatory and
   confirm setup appears first.
7. Confirm setup shows:

   - **Fill this in for me**;
   - approximate latitude/longitude fallback wording; and
   - **You're ready for tonight** after saving.

Stop if sign-in, readiness, Tonight, feedback saving, setup, or isolation
fails. Preserve only the safe request ID and do not collect passwords, access
tokens, or exact observing addresses.

## Human retest

Use one tester at a time. Do not explain the setup screen before the tester
acts.

Before opening the link, say:

> I’m going to watch where Polaris is clear or confusing. Please say out loud
> what you think each screen wants you to do. I won’t explain anything unless
> you get completely stuck.

Record whether the tester:

- understands “observing home”;
- chooses **Fill this in for me** without prompting;
- hesitates at latitude/longitude;
- understands that Polaris does not need a street address;
- understands the **You're ready for tonight** handoff; and
- reaches the first Tonight plan without live help.

After the first plan appears, ask:

> In your own words, what did Polaris just save, and what is it using that
> information for?

Then use the worksheet in
[`PRIVATE_ALPHA_INVITATION.md`](PRIVATE_ALPHA_INVITATION.md) for the Tonight
recommendation questions.

## Decision after retest

Record the evidence in
[`ALPHA_TESTER_FLIGHT_LOG.md`](ALPHA_TESTER_FLIGHT_LOG.md).

- If the tester reaches the first Tonight plan without help, keep the current
  browser-location setup for the tiny cohort.
- If latitude/longitude still blocks completion, build the city/ZIP path in
  [`ONBOARDING_LOCATION_ENTRY.md`](ONBOARDING_LOCATION_ENTRY.md).
- If the tester misunderstands the recommendation or safety boundary, pause
  invitations and fix the Tonight explanation before adding more users.
- If another user's data appears anywhere, pause immediately and investigate
  tenant isolation before continuing.
