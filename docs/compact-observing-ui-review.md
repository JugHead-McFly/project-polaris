# Compact observing UI review — October 17, 2026

Branch `codex/compact-observing-ui` starts from deployed develop
`2fccd11ab982593cec931e0f69d51db6baecccb7`. No push, merge or deployment is part
of this review. Existing observations, backups and other worktrees are preserved.

## Requested changes

- The timeline is the sole hosted schedule display. Best imaging window and
  Session plan sections are removed, not collapsed.
- Conditions alerts/Notify me controls, preference reads, polling, permission
  requests and notification handlers are removed from this page.
- Targets, times, settings and setup actions lead. Ranking, framing, score factors
  and forecast explanations use native keyboard-accessible details disclosures.
- Unallocated-time panels and copied warnings are removed. Meaningful pauses,
  including leading/trailing gaps, remain chronological compact rows labeled
  “No capture scheduled.” Sub-minute rounding residuals are not large panels.
- Time labels and durations round to whole minutes; exact backend instants and
  exposure budgets are unchanged. Exact block times remain in the timeline title.
- Essential weather, dew, unknown settings, horizon and mosaic limitations remain
  visible. Dark/teal styling is retained with compact cards and no numbered badges.
- Mobile account controls use separate rows, wrapping long emails and retaining
  44px button targets. Refresh and Sign Out remain functional.

## Mosaic correction and long-gap investigation

Single-frame size is no longer a categorical exclusion. M31/C20-sized objects
remain eligible as explicitly labeled mosaic candidates when otherwise suitable.
Their scheduled entries are visibility opportunities, not ready-to-run captures:
no panel count, overlap, capture settings, subframe total or setup duration is
invented. The user must confirm a mosaic plan. Existing completed goals, darkness,
weather and visibility constraints remain applicable.

An isolated October 17 astronomy calculation at the code-default Arizona location
closely matched the screenshot's M22/M16/IC4665/M11 evening endpoints and M97's
03:13 rise window. M31 was visible through the night and C20 for 390 minutes;
both had been rejected by the single-frame fit filter. This strongly supports
that filter as a contributor to the gap. It is not an authenticated replay of
Doug's precise account or capture history. The catalog remains finite and genuine
remaining gaps are not concealed or filled with ineligible targets.

## Forecast reliability

The previous frontend unconditionally rendered “Learning.” It now distinguishes
Collecting from Review ready. The threshold is 30 comparable nights separately
for afternoon and dusk, with matched location/provider mix/method, at least 90%
forecast and satellite coverage, and no satellite gap over 30 minutes. Earlier
individual-time checks do not count. Readiness is not calibrated reliability.

The collector's completion diagnostic also counted exhausted attempts as completed
despite inadequate observations. It now reports processed, adequate-completed,
inadequate nights and failed sample attempts separately. Persistence, retry and
collection semantics are unchanged. Production counts/allowlist/job health have
not been inspected; these fixes do not establish that the live collector works.

## Feedback storage

The “Was this plan useful?” / “What made it unclear, untrustworthy, or less useful?”
feedback uses `PUT /recommendations/{recommendation_run_id}/feedback`. Saved notes
are the `reason` field (500 characters) in hosted `recommendation_feedback`, linked
to user, observatory and run. The service commits them; they survive reload/deploy.
Unsaved text is not persisted. Account backup formats 1 and 2 include this table.
The dashboard has no feedback inbox; authorized database access or an account
export can read it. The aggregate alpha metrics report intentionally excludes text.

## Validation and preview

103 Python regressions passed across dashboard, mosaic/full-night planning,
scheduler, checklist, forecast collection and hosted APIs; nine JavaScript tests
passed. Independent code review found no remaining blockers. Dependency/IERS
warnings remain; astronomy tests disable remote downloads.

Run `python tests/serve_compact_ui_fixture.py` for an in-memory synthetic preview
at `http://127.0.0.1:8110/operator`. It deliberately includes a real schedule gap
and a mosaic opportunity; it does not reproduce live conditions or read user data.

With Playwright available, run `tests/compact_ui_visual_check.cjs` from the desired
screenshot output directory. Set `CHROME_EXECUTABLE` if using installed Chrome;
optionally set `POLARIS_PREVIEW_URL`. Fresh headless Chrome checks passed desktop
1440px and phone widths320/375/390/430 plus844px landscape, with a long account
email, no overlap/overflow, refresh, sign-out, keyboard disclosures, edge gaps and
no page errors. This is Chromium viewport testing, not physical iPhone/Safari.

Screenshot/review artifacts are retained in the parent task folder:
`compact-desktop.png`, `compact-390.png`, the other width-specific PNGs,
`compact-visual-results.json`, and `compact-python-results.txt`.

Release requires approval. Rollback for this scope is unchanged deployed `2fccd11`.
