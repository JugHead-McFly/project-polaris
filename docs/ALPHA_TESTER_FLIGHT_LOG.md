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

## Cohort progress

| Tester | Invite | Account & home | First plan viewed | Explained plan correctly | Used for a real decision | Second visit | Biggest issue | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tester A | ☒ | ☒ | ☐ | ☐ | ☐ | ☐ | None reported during setup | First-time, novice-family tester completed account and observatory setup without coaching. |
| Tester B | ☒ | ☐ | ☐ | ☐ | ☐ | ☐ | Setup wording and location choice were unclear | Nontechnical family tester stopped before completing setup. |
| Tester C | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |  |  |
| Tester D | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |  |  |

## Observation log

| Date | Tester | What they were trying to do | Result | Evidence / quote | Severity | Follow-up |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  | Low / Medium / High / Critical |  |
| 2026-08-01 | Tester A | Create an account and set up an observing home | Completed without assistance | “It was very easy. No issues with setting it up.” | Low | Ask after a real nightly recommendation whether the decision and settings are equally clear. |
| 2026-08-01 | Tester B | Understand the first setup screen and choose an observing location | Did not complete | “What is this and what am I supposed to select for the location?” Later: “I looked at it and it made zero sense so I didn’t finish it.” | High | Redesign onboarding in plain English: explain the one-time purpose, offer a simple city/ZIP entry first, and keep coordinates behind an optional advanced path. Retest with a nontechnical user. |

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

See [PRIVATE_ALPHA_TEST_PLAN.md](PRIVATE_ALPHA_TEST_PLAN.md) for the scope,
tester journey, and pause conditions.
