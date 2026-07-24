# Polaris Commercialization and Private-Alpha Plan

Last reviewed: 2026-07-23

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
Use these gates in sequence:

1. 10–20 active private-alpha users.
2. 100 engaged closed-beta users.
3. Unprompted user recommendations to others.
4. First recurring revenue.
5. Consistent month-over-month revenue and retention growth.

Stronger evidence includes users returning every clear night, reducing the
number of other tools they check, volunteering for beta, and being disappointed
when Polaris is unavailable. “Cool idea” is not validation.

## Calendar correction

The working private-alpha target is October 1, 2026. From July 23, that is
about ten weeks—not 30 days. Treat the next 30 days as a discovery and
productization-design window, then use the remaining time for a deliberately
small alpha.

October 1 is a forcing function, not a public promise. If reliability,
privacy, or a core workflow is not ready, reduce alpha scope rather than
shipping an untrustworthy recommendation.

## Launch order

### 1. Public landing page

Create a simple website before app-store distribution. It should explain the
problem Polaris solves, show a credible example recommendation, offer a beta
interest form when demand justifies it, and provide contact/support information.
Privacy and terms need professional review before handling meaningful user data
or payments.

### 2. Responsive web alpha

The first user-facing product should run well in a phone, tablet, or desktop
browser. This allows immediate fixes and avoids App Store review cycles while
the core recommendation is being validated.

The alpha workflow should be limited to:

- Create a user profile and basic observing setup.
- Set location and essential telescope preferences.
- See a nightly recommendation and a short ranked list.
- See a usable imaging window and plain-language rationale.
- Record whether the recommendation was useful.

### 3. Native mobile apps after workflow validation

Build or package native iOS and Android experiences only after the responsive
web flow proves repeat use. Native priorities later include notifications,
offline behavior, location permission, widgets, device image upload, and
store discovery.

## Current productization reality

The existing Polaris application is a local FastAPI application with a
file-backed SQLite database and a single-observatory dashboard. It is a strong
recommendation-engine foundation, but it is not yet a multi-user hosted product.

Private alpha requires explicit work for:

- Accounts and authentication.
- User/observatory tenancy and data isolation.
- Hosted production database and safe migrations.
- Per-user capture-library or upload strategy.
- Secure configuration and secrets handling.
- Audit logging, error monitoring, backups, and support workflow.
- Privacy, data retention, and account-deletion policy.
- Responsive onboarding and production deployment.

This means “move Polaris online” is not a one-click hosting task. It is a
separate productization milestone, and its architecture must be selected after
an audit of what can be safely reused from the current FastAPI planner.

## Architecture direction — proposal, not commitment

Keep one recommendation domain model and avoid three separate products. Two
credible paths should be evaluated:

| Option | Strength | Tradeoff |
| --- | --- | --- |
| Extend FastAPI with a responsive web frontend and hosted PostgreSQL | Reuses the current Python recommendation engine and minimizes rewrite risk | Requires careful web-product and multi-tenant design |
| Create a TypeScript/React web layer with shared services and migrate planner logic gradually | Strong web/mobile ecosystem and future cross-platform options | Adds an architectural rewrite before validation |

Do not commit to Next.js, Supabase, React Native, or Expo solely because they
are popular. The fastest credible alpha is likely the path that safely reuses
the existing planner while adding only the productization capabilities alpha
needs. A technical architecture decision record is required before a rewrite.

## 10-week alpha work plan

### Weeks 1–2: evidence and architecture

- Run the customer-discovery sprint.
- Audit current data ownership, configuration, capture ingestion, and API
  boundaries.
- Decide alpha user, observatory, data-isolation, and upload assumptions.
- Select a minimal deployment architecture and estimate its actual operating
  cost.
- Reserve a domain only after a provisional name and availability check.

### Weeks 3–6: smallest usable product

- Add hosted deployment, authentication, and tenant isolation.
- Build essential onboarding for location and telescope context.
- Surface the nightly recommendation, top targets, window, and explanation.
- Add recommendation-feedback capture and operational monitoring.
- Test with Doug's own workflow before external access.

### Weeks 7–8: alpha reliability

- Invite 5–10 highly engaged early users.
- Observe onboarding and recommendation comprehension.
- Fix reliability, privacy, and confusing-flow failures.
- Record usage and feedback in the Voice of Customer tracker.

### Weeks 9–10: controlled alpha expansion

- Expand toward 10–20 users only if early users return and the core flow is
  credible.
- Decide whether the October 1 alpha is ready, needs a smaller scope, or needs
  a short delay for a specific reliability concern.

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

