# Operator tile and forecast copy cleanup

Base: d49496572a35d04dc6eee94261b667dae37d630b. Branch: codex/tile-copy-cleanup. This branch is separate from weather-cache correctness work.

User-requested changes: use Cloud forecasts vary for mixed/split forecasts, retain broadly-agree/partial/unavailable distinctions, remove the technical agreement paragraph. Remove repeated category-starting-settings, setup-included and mini-chart captions; keep actual charts, the 35-degree line and accessible description, capture values, incomplete-settings guidance and mosaic warnings. Remove generic Framing details. Remove Rig profile and Target fit from Capture Settings and use two columns for its four remaining fields. Replace detailed forecast history/counts/methodology with one truthful reliability summary; remove the history navigation link.

Reliability building and ready_for_calibration both say Still being assessed: sample thresholds do not establish a calibrated reliability claim. Missing/unavailable/unknown data says Unavailable. The summary is an accessible live status. No invented percentage, reliability claim, pending job or user-action requirement is introduced.

Only frontend files and tests change. No database, forecast persistence, collection, scoring, eligibility, setup allowance, equipment calculation, minimum altitude or mosaic implementation changes. Historical API data remains supplied/stored; the operator UI simply does not render the detailed history.

Validation: 30 Python tests passed (dashboard, forecast accuracy persistence and collection); 17 Node tests passed (capture history, decision messages, concise reliability, loading, map loading and schedule presentation). Two focused browser suites passed at 1440, 768, 390 and 320 widths with no overflow or page errors: agreement/filter quality states and full/partial/mosaic tile variants. Desktop/mobile screenshots visually inspected: ../tile-cleanup-1440.png and ../tile-cleanup-390.png (outside repository). Synthetic fixture only, memory database, localhost8122; no live account data or provider requests. Old chart-resize test removed with the deleted history chart; loading-browser assertion updated to the new summary, but that separate legacy fixture suite was not counted as executed.

Independent review found no application blockers; reviewer checked JavaScript syntax and independently passed the reliability unit test. Review suggestions implemented: unknown-state allowlist, per-state agreement test assertions, stale test references, and live-status accessibility. Full browser visual checks performed by author, not claimed as independent.

Local only. No push, merge or deployment until reviewed release approval. Rollback is a revert of this UI commit; the paid compute YAML is unchanged. Weather branch codex/weather-startup-overlap at 1aa7c56058a217b66824d45b8cc92db383a5ba49 remains separate and unpublished.
