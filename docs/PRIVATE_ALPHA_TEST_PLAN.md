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
- Doug knows how to disable an account and remove its stored data.

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
[`PRIVATE_ALPHA_INVITATION.md`](PRIVATE_ALPHA_INVITATION.md). Before sending
the first invitation, replace the support-email placeholder in that document
with the address Doug wants testers to use. Keep all invitation and support
communication one-to-one during this tiny cohort; do not post an access link
publicly.

## Tester journey

Each tester should:

1. Accept the private invitation and choose a password.
2. Add an observing home using approximate coordinates if preferred.
3. Read tonight's recommendation without coaching.
4. Explain, in their own words, what Polaris recommends and why.
5. Decide whether they would follow the recommendation.
6. Return on another night and repeat the decision.
7. Report anything confusing, missing, incorrect, or untrustworthy.

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
