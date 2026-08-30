# Polaris Commercialization and Private-Alpha Plan

Last reviewed: 2026-08-30

## Honest assessment

Polaris is a legitimate opportunity worth validating as a disciplined side
business. It is not a proven business, and it would be irresponsible to treat
it as a reason to leave a primary job today.

The favorable signals are an engaged hobby market, meaningful equipment spend,
fragmented planning workflows, and smart telescopes lowering the barrier to
astrophotography. The material risks are a limited addressable market, fast
competition, vendor feature overlap, and the difficulty of acquiring and
retaining users after the software works.

The right question is not “Can Polaris become a venture-scale company?” It is:

> Can Polaris become a useful, trusted, and eventually profitable product for a
> clearly defined group of smart-telescope users?

The answer is unknown. It should be tested through behavior, not compliments.

## Evidence gates before financial dependence

Do not make career or large-spending decisions based on early interest alone.
These are future business-expansion gates, not V1.11 or V1.12 development
gates. They become active only if Doug later resumes external validation.
Use these gates in sequence:

1. 10–20 active private-alpha users.
2. 100 engaged closed-beta users.
3. Unprompted user recommendations to others.
4. First recurring revenue.
5. Consistent month-over-month revenue and retention growth.

Stronger evidence includes users returning every clear night, reducing the
number of other tools they check, volunteering for beta, and being disappointed
when Polaris is unavailable. “Cool idea” is not validation.

## Current scheduling decision

The former October 1, 2026 private-alpha target is retired. Polaris is currently
a Doug-first single-user product. Development continues without waiting for
tester replies, cohort behavior, clear weather, new imaging, or a minimum number
of matched forecast checks.

Existing captures, saved plans, hosted history, known outcomes, and
privacy-safe deterministic fixtures are the active test beds. External alpha
returns to the schedule only after Doug explicitly decides it would answer a
question that the single-user phase cannot answer.

## Launch order

### 1. Single-user web product — current

Improve Doug's nightly decision workflow and verify it against existing data.
Keep the secure hosted deployment and tenant boundaries healthy, but do not
make tester operations or public-facing materials current development gates.

### 2. Public landing page — later

Create a simple website before app-store distribution. It should explain the
problem Polaris solves, show a credible example recommendation, offer a beta
interest form when demand justifies it, and provide contact/support information.
Privacy and terms need professional review before handling meaningful user data
or payments.

### 3. Responsive web alpha — deferred

The first user-facing product should run well in a phone, tablet, or desktop
browser. This allows immediate fixes and avoids App Store review cycles while
the core recommendation is being validated.

The alpha workflow should be limited to:

- Create a user profile and basic observing setup.
- Set location and essential telescope preferences.
- See a nightly recommendation and a short ranked list.
- See a usable imaging window and plain-language rationale.
- Record whether the recommendation was useful.

### 4. Native mobile apps after workflow validation

Build or package native iOS and Android experiences only after the responsive
web flow proves repeat use. Native priorities later include notifications,
offline behavior, location permission, widgets, device image upload, and
store discovery.

## Current productization reality

Polaris now has both a local FastAPI/SQLite product and a secure hosted
FastAPI/PostgreSQL path with Supabase authentication. The hosted foundation has
passed tenant-isolation, deployment, monitoring, backup, restore, and recovery
checks. It is retained for Doug's use and for a possible later alpha, but that
later alpha is not active.

The following alpha foundations already exist and must remain healthy:

- Accounts and authentication.
- User/observatory tenancy and data isolation.
- Hosted production database and safe migrations.
- Per-user capture-library or upload strategy.
- Secure configuration and secrets handling.
- Audit logging, error monitoring, backups, and support workflow.
- Privacy, data retention, and account-deletion policy.
- Responsive onboarding and production deployment.

This means the difficult online foundation is preserved rather than rebuilt.
Current work should improve the personal product and its test beds instead of
reopening cohort operations.

## Architecture direction — accepted for v1.7

The audit selected a modular-monolith path that keeps the FastAPI/Python
recommendation engine and responsive web interface, hosts the application on
Render, and uses Supabase for authentication and PostgreSQL. Raw FITS uploads
and Doug's local capture archive are deliberately outside the first hosted
alpha.

The complete decision, security boundary, cost guardrail, alternatives, and
implementation slices are in
[`ALPHA_ARCHITECTURE_DECISION.md`](ALPHA_ARCHITECTURE_DECISION.md).

This direction is not permission to purchase services. The v1.7 foundation has
now exercised PostgreSQL tenant isolation, restricted runtime access, backup
restoration, monitoring, and hosted readiness. Preserve those checks during
single-user development; re-review cost and external-user assumptions before a
future alpha is resumed.

## Current single-user work plan

- Build repeatable regression scenarios from existing captures, saved plans,
  hosted history, and deterministic fixtures.
- Improve Tonight, Goals, Portfolio, Quality, and Locations when a change makes
  Doug's workflow more useful or trustworthy.
- Let forecast history and any new captures accumulate opportunistically.
- Keep full automated tests, desktop/mobile visual checks, hosted readiness,
  backup, and tenant isolation as release gates.
- Do not require a tester response or a new imaging session to exit V1.11 or
  V1.12.

## Deferred alpha preparation plan

The original ten-week outline is retained as a future checklist, not an active
calendar. Its weeks begin only after Doug explicitly resumes external alpha.

### Future weeks 1–2: evidence and architecture review

- Run the customer-discovery sprint.
- Audit current data ownership, configuration, capture ingestion, and API
  boundaries.
- Decide alpha user, observatory, data-isolation, and upload assumptions.
- Select a minimal deployment architecture and estimate its actual operating
  cost.
- Reserve a domain only after a provisional name and availability check.

### Future weeks 3–6: smallest external-test product

- Add hosted deployment, authentication, and tenant isolation.
- Build essential onboarding for location and telescope context.
- Surface the nightly recommendation, top targets, window, and explanation.
- Add recommendation-feedback capture and operational monitoring.
- Test with Doug's own workflow before external access.

### Future weeks 7–8: alpha reliability

- Invite 5–10 highly engaged early users.
- Observe onboarding and recommendation comprehension.
- Fix reliability, privacy, and confusing-flow failures.
- Record usage and feedback in the Voice of Customer tracker.

### Future weeks 9–10: controlled alpha expansion

- Expand toward 10–20 users only if early users return and the core flow is
  credible.
- Decide whether the optional alpha should expand, remain small, pause, or end
  based on the exact question it was created to answer.

## Current cost guardrails

These are planning ranges, not a purchase authorization. Confirm prices and
terms at the point of account creation.

| Stage | Expected recurring infrastructure range | Notes |
| --- | --- | --- |
| Private development | $0–$25/month plus domain | Use free tiers and local development where safe; domain cost varies by name and registry |
| Small closed beta | Roughly $45–$150/month | Depends on hosting, database, email, monitoring, weather/API use, storage, and traffic; set hard spend alerts |
| Early public launch | Roughly $100–$300/month before payment fees | Grow only with usage; review costs monthly |

Current reference points, subject to provider and usage changes:

- [Vercel Pro](https://vercel.com/pricing) is listed at $20/month and uses
  metered infrastructure after included credit; its Hobby plan is for personal,
  non-commercial use.
- [Supabase Pro](https://supabase.com/pricing) starts at $25/month with one
  included project, daily backups, and usage limits/overages.
- [Expo](https://expo.dev/pricing) lists a free tier and a $19/month Starter
  plan, but native mobile build infrastructure is not needed for the web alpha.
- [Apple Developer Program](https://developer.apple.com/programs/enroll/) is
  $99/year when iOS distribution is needed.
- [Google Play Console](https://support.google.com/googleplay/android-developer/answer/6112435)
  currently has a $25 one-time registration fee for full distribution.
- [Stripe](https://stripe.com/pricing) lists no standard monthly setup fee and
  2.9% + 30¢ for successful domestic online-card transactions; use only when
  web payments are appropriate.
- [Cloudflare Registrar](https://developers.cloudflare.com/registrar/) sells
  supported domains at registry/ICANN cost without registrar markup; actual
  domain prices vary by extension and availability.

Mobile-store payment rules and commissions vary by product, region, and program.
Model them only when pricing and native distribution are in scope.

## Account-ownership rule

Doug must personally create and control business-critical accounts, payment
methods, legal identity verification, domains, recovery contacts, and
credentials. Codex can guide setup, prepare technical material, and work inside
the accounts only within explicit authorization; it cannot accept legal
agreements, make legal representations, or hold credentials on Doug's behalf.
