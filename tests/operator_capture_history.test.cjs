const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('older records stay collapsed and separate from verified hours', () => {
  const source = fs.readFileSync(path.join(__dirname, '../app/web/operator.js'), 'utf8');
  const code = source.slice(source.indexOf('const renderLibraryHistory ='), source.indexOf('const renderHostedTonight ='));
  const labels = {}, children = [];
  const container = {replaceChildren: () => children.length = 0, appendChild: el => children.push(el)};
  const context = {setText: (id,value) => labels[id] = value, byId: () => container,
    document: {createElement: tag => ({tag, open: false, children: []})},
    appendTextElement: (parent,tag,_class,text) => (parent === container ? children : parent.children).push({tag,text})};
  const render = vm.runInNewContext(code + '\nrenderLibraryHistory;',context);
  render({session_count:3, targets:[{object:'M31',hours:9.67,goal_hours:8,remaining_hours:0}],
    legacy:{record_count:20,basis:'Older stacks; no verified credit.',targets:[{object:'M31',record_count:1}]}});
  assert.equal(labels['hosted-library-summary'],'3 sessions');
  assert.match(children[0].text,/9.67 h recorded/);
  assert.equal(children[1].tag,'details');
  assert.equal(children[1].open,false);
  assert.equal(children[1].children[0].text,'20 older capture records');
  assert.equal(children[1].children[2].text,'M31: 1 older record');
  render(null);
  assert.equal(children.length,0);
});

const projectRenderer = () => {
  const source = fs.readFileSync(path.join(__dirname, '../app/web/operator.js'), 'utf8');
  const code = source.slice(source.indexOf('const renderTargetProjectContext ='), source.indexOf('const renderLibraryHistory ='));
  const labels = {};
  const container = {};
  const render = vm.runInNewContext(code + '\nrenderTargetProjectContext;', {
    setText: (id, value) => labels[id] = value,
    byId: () => container, displayHours: value => `${value} hr`, renderFilterProgress: () => {},
  });
  return {render, labels, container};
};

test('target card shows only total verified capture time, without date or frame count', () => {
  const {render, labels} = projectRenderer();
  render({best_quality: null, capture_count: 0, session_count: 2,
    current_hours: 3.11, goal_hours: 5, remaining_hours: 1.89,
    synced_capture_history: {session_count: 2, latest_session_at: '2026-10-31T23:30:00-07:00',
      total_integration_seconds: 8100, frame_count: 270}});
  assert.equal(labels['hosted-target-quality'], 'Not assessed');
  assert.equal(labels['hosted-target-history'], 'Total captured: 2h 15m (verified records)');
  assert.doesNotMatch(labels['hosted-target-history'], /session|Nov|2026|UTC|frame|270/i);
  render({best_quality: 0, capture_count: 1});
  assert.equal(labels['hosted-target-quality'], '0%');
  assert.equal(labels['hosted-target-history'], 'Verified capture time unavailable');
});

test('unknown capture time never falls back to recorded or planned frames, or becomes zero', () => {
  const {render, labels} = projectRenderer();
  const history = {session_count: 1, latest_session_at: null, total_integration_seconds: null, frame_count: 1200};
  render({synced_capture_history: history, planned_subframes: 9000, additional_subframes_needed: 8000});
  assert.equal(labels['hosted-target-history'], 'Verified capture time unavailable');
  render({synced_capture_history: {...history, frame_count: null}, planned_subframes: 9000});
  assert.equal(labels['hosted-target-history'], 'Verified capture time unavailable');
  render({synced_capture_history: {...history, latest_session_at: 'malformed', total_integration_seconds: 0}});
  assert.equal(labels['hosted-target-history'], 'Total captured: 0s (verified records)');
  render({synced_capture_history: {...history, total_integration_seconds: 30}});
  assert.equal(labels['hosted-target-history'], 'Total captured: 30s (verified records)');
  for (const seconds of [undefined, NaN, Infinity, -1]) {
    render({synced_capture_history: {...history, total_integration_seconds: seconds}});
    assert.equal(labels['hosted-target-history'], 'Verified capture time unavailable');
  }
});

test('switching targets clears stale history, including empty, legacy-only and no target', () => {
  const {render, labels, container} = projectRenderer();
  render({synced_capture_history: {session_count: 1, latest_session_at: '2026-10-31T00:00:00Z', total_integration_seconds: 3600}});
  assert.equal(labels['hosted-target-history'], 'Total captured: 1h (verified records)');
  render({synced_capture_history: {session_count: 0, legacy_record_count: 2}, planned_subframes: 500});
  assert.equal(labels['hosted-target-history'], 'No synced capture records · older stack records only');
  render({synced_capture_history: {session_count: 0, legacy_record_count: 0}});
  assert.equal(labels['hosted-target-history'], 'No synced capture records');
  render({synced_capture_history: null});
  assert.equal(labels['hosted-target-history'], 'Verified capture time unavailable');
  render(null);
  assert.equal(labels['hosted-target-history'], '—');
  assert.equal(container.hidden, true);
});

test('plan loading and errors never become empty history and superseded requests cannot overwrite it', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../app/web/operator.js'), 'utf8');
  const code = source.slice(source.indexOf('const loadHostedTonight ='), source.indexOf('const saveHostedPlanFeedback ='));
  const labels = {}, results = [];
  let resolveRequest, rejectRequest, current = true;
  const run = {current: () => current, request: () => new Promise((resolve, reject) => {resolveRequest = resolve; rejectRequest = reject;}), finish: () => {}};
  const load = vm.runInNewContext(code + '\nloadHostedTonight;', {
    targetArtPreviewMode: false, loadingRun: null, latestHostedTonightData: {},
    loadingCoordinator: {begin: () => run}, setHostedRefreshState: () => {}, showHostedTonight: () => {},
    setText: (id, value) => labels[id] = value, byId: () => ({checked: false}),
    renderHostedTonight: value => results.push(value),
  });
  let pending = load();
  assert.equal(labels['hosted-target-history'], 'Loading capture time…');
  rejectRequest(new Error('Fixture failure'));
  await pending;
  assert.equal(labels['hosted-target-history'], 'Verified capture time unavailable');
  pending = load();
  current = false;
  labels['hosted-target-history'] = 'New target history';
  resolveRequest({recommended_target: {object: 'Old target'}});
  await pending;
  assert.equal(labels['hosted-target-history'], 'New target history');
  assert.deepEqual(results, []);
});

test('hosted progress shows imported time and completed goal without inventing quality', () => {
  const source = fs.readFileSync(path.join(__dirname, '../app/web/operator.js'), 'utf8');
  const code = source.slice(source.indexOf('const renderLibraryHistory ='), source.indexOf('const renderHostedTonight ='));
  const text = {};
  const rows = [];
  const context = {setText: (id, value) => text[id] = value,
    byId: () => ({replaceChildren: () => rows.length = 0}),
    appendTextElement: (_parent, _tag, _class, value) => rows.push(value)};
  vm.runInNewContext(code + '\nrenderLibraryHistory({session_count: 2, targets: [{object:"C 20",hours:9.04,goal_hours:8,remaining_hours:0}]});', context);
  assert.equal(text['hosted-library-summary'], '2 sessions');
  assert.equal(rows[0], 'C 20: 9.04 h recorded / 8 h goal; goal reached');
  vm.runInNewContext('renderLibraryHistory(null);', context);
  assert.equal(text['hosted-library-summary'], 'Not synced yet');
  assert.equal(rows.length, 0);
});
