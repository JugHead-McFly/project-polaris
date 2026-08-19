# Private Alpha Tester Flight Log

Use this lightweight record for the first trusted cohort. It captures product
evidence without collecting passwords, tokens, or exact observing addresses.

## How to use it

1. Assign each person a tester label (for example, `Tester A`). Keep their
   contact details in the invitation email—not in this file.
2. After each interaction, add only what Polaris needs to learn: whether the
   person completed the step, what confused them, and a short quote if useful.
3. Treat an observation as a signal, not a feature request. Look for the same
   issue across more than one tester before changing the core flow.
4. Escalate immediately if a tester cannot sign in, sees another person's data,
   cannot understand the recommendation, or reports a safety concern.

## Watched risks

- **Render cold start / slow first load:** expected on the current free private
  alpha host. Do not upgrade hosting for one family/novice report alone. Upgrade
  or pause invitations if a real smart-telescope tester abandons setup, distrusts
  Polaris, or if slow first load repeats across two testers.

## Cohort progress

| Tester | Invite | Account & home | First plan viewed | Explained plan correctly | Used for a real decision | Second visit | Biggest issue | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tester A | ☒ | ☒ | ☐ | ☐ | ☐ | ☐ | None reported during setup | First-time, novice-family tester completed account and observatory setup without coaching. |
| Tester B | ☒ | ☐ | ☐ | ☐ | ☐ | ☐ | Setup wording and location choice were unclear | Nontechnical family tester stopped before completing setup. |
| Tester C | ☒ | ☒ | ☒ | ☐ | ☐ | ☐ | Slow first load, auth confusion, and unexplained terms | Novice-family mobile walkthrough outside the core persona; useful reliability and comprehension signal. |
| Tester D | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |  |  |

## Observation log

| Date | Tester | What they were trying to do | Result | Evidence / quote | Severity | Follow-up |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  | Low / Medium / High / Critical |  |
| 2026-08-01 | Tester A | Create an account and set up an observing home | Completed without assistance | “It was very easy. No issues with setting it up.” | Low | Ask after a real nightly recommendation whether the decision and settings are equally clear. |
| 2026-08-01 | Tester B | Understand the first setup screen and choose an observing location | Did not complete | “What is this and what am I supposed to select for the location?” Later: “I looked at it and it made zero sense so I didn’t finish it.” | High | Redesign onboarding in plain English: explain the one-time purpose, offer a simple city/ZIP entry first, and keep coordinates behind an optional advanced path. Retest with a nontechnical user. |
| 2026-08-01 | Tester B follow-up | Reduce uncertainty after first observing-home setup | Local fix ready for retest | Added a one-time “You're ready for tonight” handoff after setup, with clear next steps before showing the plan. | Medium | Retest the full invitation-to-first-plan flow with a nontechnical user; city/ZIP entry remains a separate follow-up if coordinates still block completion. |
| 2026-08-02 | Clean test account | Retest hosted setup and account isolation steps 7-10 | Passed | Separate no-observatory account saw setup first, saved its own observing home, reached Tonight, saw no Doug data, and the `Do Not Image` recommendation now named 98% cloud cover with a Very Poor sky rating. | Low | Treat V1.6 onboarding as ready for the next invited alpha tester, pending Doug's milestone decision. |
| 2026-08-02 | Day 8 Facebook group scour | Interpret outside feedback before expanding alpha scope | Added to Voice of Customer | Users showed lightweight interest in a nightly shortlist, but many named existing tools. Most important risks: recommendation trust, local weather reliability, local horizon/obstructions, and repeat use for experienced planners who already maintain target lists. | Medium | In alpha, ask whether testers trusted the recommendation, understood why each target was suggested or deferred, and whether they would use Polaris again for a second real decision. |
| 2026-08-02 | Tester C | First mobile novice walkthrough by a non-astrophotographer | Eventually reached a complete plan after slow loading, auth confusion, unavailable intermediate data, and a visible `Plan unavailable / Load failed` state | “Took forever for starting page to load.” “Considered me existing user and had to reset password yet never had logged onto site before.” “What is a bortle?” “Moon position and sky quality say unavailable (eventually loaded with plan).” “Refuses to load tonight’s portfolio and keeps making it red and saying ‘plan unavailable. Load failed’.” After loading: “what do half of these words mean.” | High | Treat as novice/non-target-persona evidence, not broad demand. Investigate first-run mobile reliability and auth reset path; add comprehension prompts for terminology. Pause broader invitations if another tester hits auth confusion or repeated plan-load failure. |
| 2026-08-02 | Alpha metrics baseline | Capture the pre-next-tester aggregate funnel | Baseline recorded | Staging report showed 0 profiles, 0 observing homes, 0 saved plans, 0 feedback responses, and Review focus: Invite the next tester. | Low | Use this as the before-Nancy baseline; any next tester activity should move the funnel from zero. |
| 2026-08-02 | Hosted refresh privacy check | Switch from a tester account to Doug's main account and refresh Tonight | Fixed and retested | During refresh, stale target/settings/weather/schedule details briefly remained visible while the new account's plan was loading. The hosted loading state now clears prior plan details to neutral placeholders before fetching. Doug retested and confirmed the stale data no longer appears. | Critical | Resolved before the next external tester. Continue treating any cross-account visible data as an immediate stop condition. |
| 2026-08-08 | Experienced DWARF 3 power-user outreach | Invite a strong community contributor to private alpha | Declined | The user appreciated the invite but said they were probably "too far gone" to be a good tester, already use four apps that do some version of this, and believe climbing the learning curve with advanced tools like Telescopius was good for them after starting from scratch a year ago. | Medium | Treat as positioning evidence: Polaris may be more compelling for users who want faster confidence than for power users who value mastering advanced tools. Keep the next invite one-to-one, but consider targeting a thoughtful intermediate user rather than only top-end power users. |
| 2026-08-08 | Michael Glazier outreach | Invite a thoughtful UK astrophotographer to private alpha | Accepted initial request | Michael replied, "sounds interesting, always good to see people building new solutions. I would be happy to give it a test." Doug noted he is an amateur astrophotographer in the UK and associated with 365Astronomy. | Low | Collect setup email, approximate UK observing location, rig, and tracking style. Treat his test as global-weather, timezone, and experienced-user trust validation. |
| 2026-08-08 | Hosted weather reliability | Refresh alpha before sending Michael the link | Fixed enough for next invite, with monitoring | Open-Meteo returned HTTP 429 Too Many Requests after repeated hosted refreshes. Polaris now exposes weather diagnostics on the Tonight card, caches recent weather, avoids retrying 429 responses, and has optional WeatherAPI.com global fallback behind `POLARIS_WEATHERAPI_KEY`. A later hosted refresh produced a usable Use Caution recommendation with weather values. | High | Before wider outreach, configure the WeatherAPI.com key in Render or confirm Open-Meteo remains stable after cooldown. Ask Michael whether the UK weather and local timing feel credible. |
| 2026-08-19 | Michael Glazier follow-up decision | Wait for setup details after initial acceptance | Stalled | Michael had not replied with setup details after roughly two weeks. Treat him as a warm but inactive expert prospect, not the active alpha gate. | Medium | Move to one backup candidate at a time. If Doug follows up, keep it low-pressure and preserve the option for Michael to test later. |
| 2026-08-19 | James Kevin Ty outreach | Invite a Philippines-based smart-telescope/lunar imager to private alpha | Invite sent | Doug sent a one-to-one message after seeing James's lunar imaging work from Manila, Philippines. This candidate can help validate global weather, non-US timezone/location handling, and whether Polaris has value beyond deep-sky-only planning. | Low | Wait for response. If interested, collect setup email, approximate observing region, telescope model, and tracking style before creating the private invite. |

### Severity guide

- **Critical** — data privacy, account access, or a safety-risk misunderstanding.
- **High** — prevents a person from getting a usable recommendation.
- **Medium** — the user can continue, but needs explanation or loses confidence.
- **Low** — wording, layout, or enhancement feedback that does not block use.

## Weekly decision summary

Complete this after the first group has had a genuine chance to use Polaris.

| Question | Evidence | Decision |
| --- | --- | --- |
| Can a new user get from invitation to a credible plan without help? |  |  |
| Do people understand the recommendation and its reason? |  |  |
| Did people return for a second observing decision? |  |  |
| What is the single most repeated point of confusion? |  |  |
| What is the single most valued part of Polaris? |  |  |
| Is it safe to invite one more tester? |  | Yes / No / Not yet |

## Support response checklist

When a tester reports a problem, ask for only what is needed:

1. What page were you on and what were you trying to do?
2. What did you expect to happen?
3. What actually happened?
4. If Polaris shows a request ID, what is it?
5. A screenshot is helpful; ask them to avoid sharing passwords or exact home
   coordinates.

## Onboarding retest fields

When running the first-time onboarding retest, add these details to the
observation log:

- whether the tester understood “observing home”;
- whether they chose **Fill this in for me** without prompting;
- whether latitude/longitude caused hesitation;
- whether the ready-for-tonight handoff made the next step clear; and
- whether city/ZIP entry is now justified by the evidence.

## Recommendation trust retest fields

When a tester reviews a nightly recommendation, capture:

- whether they understood why each target was recommended;
- whether they understood why any obvious target was excluded or deferred;
- whether the weather guidance matched their local reality;
- whether Moon, darkness, target altitude, and framing/FoV felt credible;
- whether they needed more detail before trusting the recommendation;
- whether they used Polaris for a planned session, a backup target, or a
  spur-of-the-moment "grab and go" decision; and
- whether they returned for a second real observing decision.

Suggested tester prompt:

> Before looking at your usual planning tools, ask Polaris for tonight's top
> three targets. Afterward, compare against your normal workflow and record:
> what you trusted, what you doubted, what was missing, and whether you would
> actually use it again tomorrow.

See [PRIVATE_ALPHA_TEST_PLAN.md](PRIVATE_ALPHA_TEST_PLAN.md) for the scope,
tester journey, and pause conditions.
