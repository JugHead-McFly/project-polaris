# Project Polaris next alpha tester packet

Status: operator checklist  
Audience: Doug

Use this when the next carefully chosen tester says yes. It is written for one
tester at a time; do not use it for a public group invitation.

If the first preferred tester is quiet, use the backup-candidate guidance in
[`PRIVATE_ALPHA_INVITATION.md`](PRIVATE_ALPHA_INVITATION.md). Do not onboard
two testers at the same time during V1.8.

## 1. Before sending the account invite

- Assign a tester alias, such as `Tester D`.
- Keep their real name, email, and private messages outside Git.
- Confirm the latest intended `develop` commit is pushed to GitHub and deployed
  on Render before the tester opens Polaris.
- Open the hosted `/health/live` and `/health/ready` endpoints after deployment.
- Confirm they understand this is unfinished private-alpha software.
- Confirm they will use an approximate observing location if they prefer.
- Do not ask for a password, exact address, access token, or invite-link
  screenshot.

## 2. Day-of tester checklist

Use this when a real tester says yes so the first visit does not become
improvised support.

1. Confirm only one tester is active in V1.8 right now.
2. Confirm the hosted app is on the latest intended commit.
3. Open the hosted health endpoints and confirm they respond.
4. Create one private invite for that tester.
5. Send the invite and the short private message.
6. Wait for the tester to act before explaining the screens.
7. Capture notes in
   [`ALPHA_FEEDBACK_CAPTURE_SHEET.md`](ALPHA_FEEDBACK_CAPTURE_SHEET.md).
8. Bring only the sanitized summary back to Codex using the template below.
9. Update
   [`ALPHA_TESTER_FLIGHT_LOG.md`](ALPHA_TESTER_FLIGHT_LOG.md) after the visit.
10. Decide whether to hold, fix, or invite the next person.

## 3. Send the private account invite

1. Create the tester invitation in Supabase.
2. Send the short private reply from
   [`PRIVATE_ALPHA_INVITATION.md`](PRIVATE_ALPHA_INVITATION.md).
3. Tell them the invite lets them choose their own password.
4. Ask them to open Polaris when they have a real or plausible observing
   decision to make.

## 4. Let the tester act before coaching

The first signal is whether Polaris makes sense without Doug explaining it.
Only step in if they are completely blocked.

Watch for whether they:

- can sign in;
- see first-time setup instead of Doug's plan;
- understand that an observing home is an approximate planning location;
- use **Fill this in for me** or complete the coordinate fallback;
- reach **You're ready for tonight**;
- open Tonight;
- understand the recommendation or `Do Not Image` reason; and
- save a Yes/No usefulness response.

## 5. Ask the first-use questions

After they have seen Tonight, ask:

> What did Polaris tell you to do tonight?
>
> What do you think was the main reason?
>
> What did you trust?
>
> What did you doubt?
>
> What felt missing, confusing, or too complicated?
>
> Would you use Polaris before a real observing session? Why or why not?

Use [`ALPHA_FEEDBACK_CAPTURE_SHEET.md`](ALPHA_FEEDBACK_CAPTURE_SHEET.md) for
live notes. Paste the sanitized answers into the main Codex project task so the
evidence can be summarized into the flight log.

## 6. Send the second-night follow-up

Send this only after the tester has completed the first visit.

> Hi <FIRST NAME> — thank you again. The most important next test is whether
> Polaris is useful a second time, on a different night. When you have another
> real or plausible observing decision, could you open Polaris again before your
> usual planning tools and tell me:
>
> 1. What did it recommend this time?
> 2. Did the reason make sense?
> 3. Did anything feel more trustworthy or less trustworthy than the first
>    visit?
> 4. Would you actually use it again?
>
> Short, blunt answers are perfect. Please avoid sending passwords, exact home
> addresses, or invite links.

## 7. What to paste into Codex

Use this format when bringing tester feedback back to the main project task:

```text
Tester alias:
Date:
Device:
Telescope:
Approximate region:
First visit or return visit:
Recommendation shown:
Tester explanation:
What they trusted:
What they doubted:
What confused them:
Would use again:
Usefulness response saved: yes/no/unknown
Bug or request ID:
Screenshot received: yes/no
Doug's read:
```

## 8. Decide what happens next

After each tester, choose one:

- Keep inviting one tester at a time.
- Hold and fix onboarding.
- Hold and fix sign-in or load reliability.
- Hold and fix recommendation explanation.
- Park a feature request until the same need repeats.

Do not expand the cohort until at least one real smart-telescope tester
understands the recommendation and returns for a second observing decision.
