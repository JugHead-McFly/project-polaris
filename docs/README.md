# Project Polaris documentation map

Status: orientation index  
Audience: Doug and Codex

Start here when the documentation feels scattered. Most files are operator or
project-manager notes, not public user documentation.

## Current state and roadmap

- [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md) — current implementation
  state, latest product gate, and next planned work.
- [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md) — executive roadmap from the
  single-user product through optional later alpha, beta, and launch decisions.
- [`LAUNCH_READINESS.md`](LAUNCH_READINESS.md) — product, business, legal, and
  beta readiness checklist.
- [`PRODUCT_OPERATING_CONTEXT.md`](PRODUCT_OPERATING_CONTEXT.md) — durable
  operating brief for product, research, branding, and review boundaries.
- [`PRODUCT_BIBLE.md`](PRODUCT_BIBLE.md) — product source of truth and decision
  principles.
- [`EXISTING_DATA_TEST_BEDS.md`](EXISTING_DATA_TEST_BEDS.md) — baseline
  monsoon-season rules for using existing captures, saved plans, hosted history,
  and deterministic fixtures without waiting for new imaging.

## Deferred private-alpha operator workflow

These runbooks are preserved for a possible V1.13 reconsideration. External
tester recruitment is not active during V1.11 or V1.12 and must not block
single-user development.

- [`PRIVATE_ALPHA_TEST_PLAN.md`](PRIVATE_ALPHA_TEST_PLAN.md) — main private
  alpha test plan, gates, journey, V1.8 exit criteria, and stop conditions.
- [`NEXT_ALPHA_TESTER_PACKET.md`](NEXT_ALPHA_TESTER_PACKET.md) — future steps
  if Doug later approves an optional tester.
- [`PRIVATE_ALPHA_INVITATION.md`](PRIVATE_ALPHA_INVITATION.md) — invitation,
  first-use check-in, and support reply templates.
- [`ALPHA_FEEDBACK_CAPTURE_SHEET.md`](ALPHA_FEEDBACK_CAPTURE_SHEET.md) — live
  note-taking sheet for tester conversations.
- [`ALPHA_TESTER_FLIGHT_LOG.md`](ALPHA_TESTER_FLIGHT_LOG.md) — sanitized
  tester evidence log.
- [`ALPHA_TESTER_PIPELINE.md`](ALPHA_TESTER_PIPELINE.md) — one-active-tester
  pipeline and backup-candidate tracker.
- [`ALPHA_ONBOARDING_RETEST_RUNBOOK.md`](ALPHA_ONBOARDING_RETEST_RUNBOOK.md) —
  hosted onboarding retest checklist.
- [`ALPHA_METRICS.md`](ALPHA_METRICS.md) — aggregate private-alpha health report
  and review command.
- [`ALPHA_PERFORMANCE_BASELINE.md`](ALPHA_PERFORMANCE_BASELINE.md) — internal
  public-endpoint timing baseline; not tester homework.
- [`FORECAST_ACCURACY_TRACKING.md`](FORECAST_ACCURACY_TRACKING.md) — privacy,
  retention, matching, and calibration boundaries for forecast history.
- [`HOSTED_ACCOUNT_REMOVAL.md`](HOSTED_ACCOUNT_REMOVAL.md) — manual hosted
  account/data cleanup runbook.

## Secure hosted infrastructure

- [`ALPHA_ARCHITECTURE_DECISION.md`](ALPHA_ARCHITECTURE_DECISION.md) — chosen
  web-first hosted alpha architecture and rejected alternatives.
- [`HOSTED_AUTHENTICATION.md`](HOSTED_AUTHENTICATION.md) — Supabase auth,
  hosted browser flow, and tenant boundary.
- [`TENANT_ISOLATION.md`](TENANT_ISOLATION.md) — database ownership and
  isolation proof.
- [`HOSTED_BACKUP_RECOVERY.md`](HOSTED_BACKUP_RECOVERY.md) — hosted tenant
  export, verification, and restore rehearsal.
- [`RENDER_DEPLOYMENT.md`](RENDER_DEPLOYMENT.md) — private Render deployment
  boundary and hosted verification gate.
- [`ERROR_MONITORING.md`](ERROR_MONITORING.md) — Sentry privacy boundary,
  request-ID support workflow, and alerting.

## Product discovery and market work

- [`VOICE_OF_CUSTOMER.md`](VOICE_OF_CUSTOMER.md) — structured customer evidence
  and product response tracker.
- [`CUSTOMER_DISCOVERY_SPRINT.md`](CUSTOMER_DISCOVERY_SPRINT.md) — staged
  discovery prompts and research plan.
- [`COMPETITIVE_LANDSCAPE.md`](COMPETITIVE_LANDSCAPE.md) — competitive
  comparison and positioning.
- [`COMMERCIALIZATION_AND_ALPHA_PLAN.md`](COMMERCIALIZATION_AND_ALPHA_PLAN.md)
  — commercialization path, private-alpha strategy, and cost guardrails.
- [`NAMING_BRIEF.md`](NAMING_BRIEF.md) — public-name process and naming
  guardrails.

## Product design and future candidates

- [`ONBOARDING_LOCATION_ENTRY.md`](ONBOARDING_LOCATION_ENTRY.md) — possible
  city/ZIP location-entry path if coordinates keep blocking the workflow.
- [`OPPORTUNITY_MODE_CONCEPT.md`](OPPORTUNITY_MODE_CONCEPT.md) — parked concept
  for productive poor-night alternatives.
- [`C20_EXPOSURE_VALIDATION_PLAN.md`](C20_EXPOSURE_VALIDATION_PLAN.md) —
  controlled validation plan for C20 15-second versus 30-second sub-exposures.
- [`TARGET_OPPORTUNITY_SCORING.md`](TARGET_OPPORTUNITY_SCORING.md) —
  experimental target-scoring foundation based on altitude, usable window,
  Moon, sky brightness, field fit, exposure confidence, and the V1.10
  Beaconsfield-style opportunity-score research direction.
- [`RIG_PROFILES.md`](RIG_PROFILES.md) — starter smart-telescope rig catalog
  and source/confidence policy for equipment-specific scoring.
- [`GOAL_ENGINE.md`](GOAL_ENGINE.md) — imaging goal and integration-target
  rules.
- [`QUALITY_SCORING_V2.md`](QUALITY_SCORING_V2.md) — capture-quality scoring
  design and boundaries.

## Local operations and release

- [`OPERATIONS.md`](OPERATIONS.md) — local startup, backup, recovery, logging,
  and operating procedures.
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) — release gates, backup
  verification, tag, publish, and rollback sequence.

## Rule of thumb

For active V1.12 work, use only these first unless a problem points elsewhere:

1. [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md)
2. [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md)
3. [`EXISTING_DATA_TEST_BEDS.md`](EXISTING_DATA_TEST_BEDS.md)
4. [`TARGET_OPPORTUNITY_SCORING.md`](TARGET_OPPORTUNITY_SCORING.md)
5. [`FORECAST_ACCURACY_TRACKING.md`](FORECAST_ACCURACY_TRACKING.md)
6. [`RIG_PROFILES.md`](RIG_PROFILES.md)
