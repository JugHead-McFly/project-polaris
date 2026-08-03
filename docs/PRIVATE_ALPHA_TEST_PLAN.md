# Project Polaris private-alpha test plan

Status: preparation in progress  
Audience: a very small group of trusted smart-telescope users

## What this alpha is for

The first private alpha is not a public launch and is not a feature showcase.
It should answer four practical questions:

1. Can a new user create an account without Doug's help?
2. Can the user add an observing home and understand what location data Polaris
   stores?
3. Does Polaris produce a credible, understandable nightly recommendation?
4. Does the user return to Polaris for a second real observing decision?

## Entry gates

Do not invite an external tester until all of these are true:

- hosted account, password recovery, and observatory setup pass;
- two-user data isolation passes through the real hosted API;
- backup restoration and basic error monitoring have been rehearsed;
- the user has a clear way to report a problem;
- the invitation explains that this is an unfinished private alpha; and
- Doug knows how to disable an account and remove its stored data using
  [`HOSTED_ACCOUNT_REMOVAL.md`](HOSTED_ACCOUNT_REMOVAL.md).

The account, password-recovery, observatory-setup, data-isolation, tenant-export,
disposable-restore, retained encrypted recovery point, separate-project restore,
and production-host monitoring privacy gates passed on July 25–27, 2026.

On July 28, 2026, the first hosted nightly-loop update was deployed to the
private Render service. Doug refreshed a real hosted plan and recorded a
successful **Yes** usefulness response. The saved response proved the hosted
recommendation and feedback loop works without changing the local dashboard.

The first monitoring tests exposed Sentry's default IP-derived location and
device-hostname collection. Polaris now sends a minimal allowlisted event,
excludes host and request data, prevents geography derivation with an explicit
non-identifying IP placeholder, and refuses all monitoring transmission from
local and staging environments. The final production-host test on July 27
showed a null user IP and no city, coordinates, observatory name, URL, request
contents, or arbitrary text. Privacy-safe production monitoring is enabled.

## Hosted retest go/no-go checklist

Run this before a nontechnical onboarding retest after an alpha-facing code or
copy change.

1. Confirm the intended `develop` commit is pushed to GitHub.
2. Confirm the hosted Render service has deployed that commit intentionally;
   automatic deploys remain disabled.
3. Open the hosted `/health/live` and `/health/ready` endpoints.
4. Sign in as Doug and confirm the existing observing home still loads.
5. Refresh Tonight and confirm a recommendation or safe `Do Not Image` result
   appears without exposing local Portfolio, Quality, History, Locations, or
   Data Status views.
6. Record one Yes/No usefulness response and confirm the page reports that it
   was saved.
7. Use a separate tester or browser profile with no observatory and confirm the
   first screen is setup, not Doug's plan.
8. Confirm the setup screen shows **Fill this in for me**, the approximate
   coordinate fallback, and the **You're ready for tonight** handoff.
9. Confirm no tester sees another user's observatory, recommendation history,
   or feedback.
10. Only then run the human onboarding retest script in
    [`PRIVATE_ALPHA_INVITATION.md`](PRIVATE_ALPHA_INVITATION.md).

Stop before inviting the tester if sign-in, readiness, isolation, Tonight,
feedback saving, or the setup screen fails. Preserve only the safe request ID
and do not collect passwords, access tokens, or exact observing addresses.

## Hosted smoke-test record

On July 26, 2026, Doug completed the first real-browser smoke test against the
Render-hosted private alpha:

- hosted sign-in, sign-out, and sign-in persistence passed;
- observing-home setup and persistence passed;
- the Tonight recommendation loaded and refreshed successfully;
- password recovery returned to the hosted Polaris reset screen and the new
  password opened the personalized account successfully; and
- the privacy-first approximate-location default was corrected, tested, and
  deployed.

On July 27, 2026, Doug completed the second human-account isolation walkthrough
in a fresh Chrome Incognito session. A separately created test account saw an
empty observing-home setup screen, then saved its own approximate-location home
and received a new plan with no inherited capture progress, portfolio, or
history from Doug's account. The browser-level isolation check passed.

Later on July 27, Doug completed the final controlled production-monitoring
privacy test. The expected synthetic error reached Sentry without observer,
observatory, request, or derived geographic information. The test switch and
synthetic issue were removed after verification.

Doug then configured a production Sentry alert, sent a test notification, and
confirmed with a second controlled synthetic issue that the saved alert
triggered. The temporary trigger and issue were removed, and the request-ID
lookup procedure was documented for tester support.

On August 2, 2026, the hosted onboarding retest passed with a separate clean
test account after the onboarding copy update reached GitHub `develop`. The
hosted `/health/live` and `/health/ready` endpoints returned HTTP 200 with
version `1.6.0`, the landing page loaded, and the hosted `/operator` shell
served the updated setup wording: **Fill this in for me**, approximate
coordinate fallback labels, and the **You're ready for tonight** handoff.
The separate no-observatory tester account saw first-time setup instead of
Doug's plan, saved its own observing home, reached Tonight, saw no Doug data,
and confirmed the cloud-cover explanation fix for a safe `Do Not Image`
recommendation.

Later on August 2, Brynlee, a 14-year-old non-astrophotographer family tester,
ran a mobile novice walkthrough. This was outside the core smart-telescope
persona, but it exposed alpha-exit risks: slow first load, an account flow that
appeared to treat her as an existing user and required password reset, temporary
Moon/sky-quality unavailability, and a visible `Plan unavailable / Load failed`
state before the plan eventually loaded. She also could not interpret several
terms, asking, “What is a bortle?” and “what do half of these words mean.” Treat
this as one novice usability signal, not broad market demand. If a second tester
hits the auth confusion or repeated plan-load failure, pause broader invitations
until first-run reliability is checked.

## Suggested first cohort

Start with two or three people who:

- use a DWARF, Seestar, Vespera, or similar smart telescope;
- are comfortable testing unfinished software;
- will make at least two real observing decisions during the test;
- will report confusion, not just bugs; and
- are not relying on Polaris for equipment safety.

Avoid a broad Facebook invitation at this stage.

## Invitation and support materials

Use the ready-to-send wording and the short tester worksheet in
[`PRIVATE_ALPHA_INVITATION.md`](PRIVATE_ALPHA_INVITATION.md). The first trusted
cohort uses `drogers08121@gmail.com` for support. Keep all invitation and
support communication one-to-one during this tiny cohort; do not post an access
link publicly.

When a tester says yes, follow
[`NEXT_ALPHA_TESTER_PACKET.md`](NEXT_ALPHA_TESTER_PACKET.md) for the private
invite, first-use questions, second-night follow-up, and sanitized Codex
handoff format.

For a live or near-live tester conversation, use
[`ALPHA_FEEDBACK_CAPTURE_SHEET.md`](ALPHA_FEEDBACK_CAPTURE_SHEET.md) as the
temporary note-taking sheet, then transfer only the alias-level evidence into
[`ALPHA_TESTER_FLIGHT_LOG.md`](ALPHA_TESTER_FLIGHT_LOG.md).

## Tester journey

Each tester should:

1. Accept the private invitation and choose a password.
2. Add an observing home using approximate coordinates if preferred.
3. Read tonight's recommendation without coaching.
4. Explain, in their own words, what Polaris recommends and why.
5. Decide whether they would follow the recommendation.
6. Return on another night and repeat the decision.
7. Report anything confusing, missing, incorrect, or untrustworthy.

## First-time onboarding retest

Use this after an onboarding wording change, before inviting additional
testers. The one-page runbook is
[`ALPHA_ONBOARDING_RETEST_RUNBOOK.md`](ALPHA_ONBOARDING_RETEST_RUNBOOK.md). Do
not explain the screen before the tester acts.

1. Send one private invitation link.
2. Ask the tester to share their screen or narrate what they think each step is
   asking for.
3. Watch whether they choose **Fill this in for me** without coaching, or
   whether latitude/longitude still stops them.
4. After they save setup, ask what they expect Polaris to do next before they
   click **Show tonight's plan**.
5. Record whether they reached the first Tonight plan, whether they could
   explain it, and the first point where they hesitated.
6. Ask the tester to explain any terms they noticed, especially Bortle,
   astronomical darkness, sub-exposure, gain, filter, frames, integration hours,
   Moon impact, and sky quality.

Passing this retest means the person reaches the first Tonight plan without
live help and understands that Polaris saved only an observing location for
planning. If manual coordinates still block completion, make city/ZIP entry
the next onboarding fix instead of adding more explanatory text. The bounded
implementation plan is in
[`ONBOARDING_LOCATION_ENTRY.md`](ONBOARDING_LOCATION_ENTRY.md).

## What Doug records

For each tester, record:

- invitation sent and account activated;
- onboarding completed without help, with help, or abandoned;
- first recommendation viewed;
- recommendation understood correctly;
- recommendation used for a real session;
- second visit completed;
- highest-severity problem;
- most valuable part of Polaris; and
- whether the tester would be disappointed if access ended.

Do not record the tester's password, access token, exact street address, or
unnecessary personal information.

For account removal or cleanup of throwaway accounts, follow
[`HOSTED_ACCOUNT_REMOVAL.md`](HOSTED_ACCOUNT_REMOVAL.md).

## Weekly alpha review

Run the aggregate metrics report before deciding whether to invite another
tester:

```bash
python scripts/alpha_metrics_report.py --env-file .env.staging
```

Use the report's **Review focus** as the first question for the weekly review,
then compare it with the qualitative notes in
[`ALPHA_TESTER_FLIGHT_LOG.md`](ALPHA_TESTER_FLIGHT_LOG.md). The report is
read-only and intentionally excludes names, emails, user IDs, observatory
names, coordinates, target names, and written feedback comments.

Do not expand the cohort just because the counts look healthy. The metrics
answer what happened; the flight log explains whether people understood and
trusted it.

## V1.8 exit criteria

V1.8 is not complete because the feedback tools exist. It exits only when the
first real smart-telescope evidence shows that the loop can teach Polaris what
to improve next.

Minimum exit evidence:

- at least one real smart-telescope tester accepts an invite and completes
  first-time setup without Doug coaching the screen;
- the tester views a real Tonight recommendation or safe `Do Not Image` result;
- the tester can explain, in their own words, what Polaris recommended and the
  main reason it gave that advice;
- the tester records or gives a clear usefulness response;
- at least one tester returns for a second real or plausible observing decision;
  and
- no unresolved privacy, account-access, data-loss, or misleading-safety issue
  remains.

Use these decision rules after each tester:

- **Onboarding confusion:** fix only if the tester cannot reach Tonight or
  misunderstands what observing-location data Polaris saved.
- **Recommendation confusion:** fix the explanation before adding new target,
  search, calendar, or opportunity-mode features.
- **Weather distrust:** compare Polaris's stated weather reason with the
  tester's local reality before changing scoring.
- **Slow first load:** keep the free Render host for one-at-a-time testing
  unless a target tester abandons, distrusts Polaris, or the problem repeats.
- **Feature request:** park it unless it directly affects the nightly decision
  or repeats across testers.
- **Compliment without return use:** record it as encouragement, not validation.
- **Second-night return:** treat this as stronger evidence than a positive
  first impression.

## Stop conditions

Pause invitations immediately if:

- one user can see or alter another user's data;
- an account cannot be disabled or its data cannot be removed;
- recommendations present stale or simulated conditions as live;
- repeated errors prevent onboarding or nightly use; or
- a tester interprets Polaris as autonomous equipment-safety control.

## Passing result

The private alpha is ready to expand only when:

- every tester remains isolated from every other tester;
- most testers complete onboarding without live coaching;
- recommendations are understood correctly;
- at least two testers return for a second real decision; and
- no unresolved privacy, data-loss, or misleading-safety issue remains.
