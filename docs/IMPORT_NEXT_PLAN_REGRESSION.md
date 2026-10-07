# Import → next nightly plan regression

V1.12 test-bed slice, 2026-10-07. All observations below use synthetic data,
not Doug's capture records or measured sky conditions.

## Scope and evidence

The fixture uses an in-memory SQLite database, two synthetic accounts, a
two-target catalog selection (M27 and M57), and fixed clear-sky/visibility
inputs. Real import endpoints, library aggregation, ranking, integration goals,
scheduler, account filtering, response validation, and dashboard rendering run
unchanged. During the fixture, calls through Python's `socket.socket.connect`
are rejected unless the destination is the literal address `127.0.0.1` or
`::1`. This is a limited test guard, not complete network isolation: it does
not intercept DNS, `connect_ex`, UDP sends, subprocesses, or native clients.
Provider inputs are replaced with synthetic values and all database
dependencies use the memory database; the guard alone does not prove that
arbitrary future code cannot contact the network. The browser fixture binds
only to 127.0.0.1 and its dashboard CSP restricts connections to the same origin.

M27 starts ahead under the fixed geometry. Importing three hours leaves two
hours of its five-hour goal. Repeating that import changes nothing. A second
two-hour session reaches the goal and lets M57 rank first. This demonstrates a
controlled scenario, not a rule that every completed target must always lose
to every unfinished target.

| Required check | Coverage |
| --- | --- |
| Import updates hours, remaining goal, session count | API workflow before/after three-hour import; browser labels |
| Repeat import does not double-count | API response, identical target/schedule/totals, browser reload |
| Goal completion affects ranking | Real planner moves M27 behind M57 under fixed inputs |
| Schedule respects remaining integration and explains end | Both targets' remaining minutes, frame exposure totals, setup, nonoverlap, darkness bounds, goal-end explanation |
| No invented image quality | Null quality in API; “Not assessed” in the dashboard |
| Other account sees no imported history or ranking change | Separate account plan/history, rejection of another account's sync token, and shared source identifiers in both import orders with independent deduplication and updates |
| Desktop/mobile agree after reload | Real dashboard at 1440×1000 and 390×844, before import, after import, repeat import, and completed goal; matching values/schedule and no horizontal overflow |

## Running

From the repository root:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_import_next_plan.py tests/test_capture_history.py tests/test_plan_consistency.py tests/test_scheduler_service.py tests/test_hosted_planning.py tests/test_tonight_api.py tests/test_operator_dashboard.py -q
node --test tests/operator_capture_history.test.cjs tests/operator_decision_message.test.cjs
```

For browser checks, start a fresh fixture process (it must have an empty memory
database at the start of each run):

```powershell
.venv/Scripts/python.exe tests/serve_import_plan_fixture.py
```

Using the Browser skill's initialized runtime, import
`tests/import_plan_browser.mjs` by absolute file URL and call
`checkImportPlanReloads(browser)`. It uses only supported browser APIs and
visible DOM assertions. It returns eight verified states, closes its tabs,
and resets its temporary viewport override even on failure. Stop the fixture
server afterward; all its records disappear. Do not mount this test fixture
in the production application.

On this Windows machine, pytest's default temporary directory can be
inaccessible. Use a new, disposable workspace `--basetemp` if needed. Windows
event-loop loopback sockets also require execution outside the restricted
shell sandbox.

## Results and limits

- Relevant Python suite: 72 tests passed (including both shared-source import orders).
- Targeted JavaScript suite: 3 tests passed.
- Browser: all eight stage/viewport combinations passed.
- No production code, database migrations, or live data changes.
- Existing cosmetic issue: the library summary renders “1 sessions.” The
  count is tested without requiring that grammatical error; the target card
  correctly renders “1 session.” Left unchanged in this regression-only slice.
- SQLite verifies application ownership/filtering, not PostgreSQL RLS or
  production concurrency. Authentication is deliberately synthetic; real
  Supabase sign-in is not tested here.
- Phone coverage is a responsive browser viewport, not a physical iPhone or
  Android device. The reusable browser check is separate from pytest.
- These tests start at session-metadata import; they do not verify telescope
  discovery, FITS copying/hashing, NAS publication, or source cleanup.
- Fixed sky inputs cannot establish forecast accuracy or image quality.

## Deployment check (read-only, 2026-10-07)

The live Render web-service settings show branch `develop`, Auto-Deploy
`On Commit`, and Pull Request Previews `Off`. The repository's `render.yaml`
also selects `develop` with `autoDeployTrigger: commit` for the web service
and forecast cron. No `.github` workflow directory is present in this checkout.

Pushing `codex/import-next-plan-regression` as that feature branch would not
update the currently configured production web service. A commit pushed or
merged into `develop` would trigger its automatic deployment. This conclusion
describes the settings inspected today; it is not a guarantee about future
settings or other services that were not inspected. No push was used to test it.

No commit, push, merge, or deployment is part of this test run.
