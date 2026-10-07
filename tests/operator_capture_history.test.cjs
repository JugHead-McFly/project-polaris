const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('target card distinguishes unassessed quality and synced sessions from zero', () => {
  const source = fs.readFileSync(path.join(__dirname, '../app/web/operator.js'), 'utf8');
  const code = source.slice(source.indexOf('const renderTargetProjectContext ='), source.indexOf('const renderLibraryHistory ='));
  const labels = {};
  const render = vm.runInNewContext(code + '\nrenderTargetProjectContext;', {
    setText: (id, value) => labels[id] = value,
    byId: () => ({}), displayHours: value => `${value} hr`,
  });
  render({best_quality: null, capture_count: 0, session_count: 2, current_hours: 3.11, goal_hours: 5, remaining_hours: 1.89});
  assert.equal(labels['hosted-target-quality'], 'Not assessed');
  assert.equal(labels['hosted-target-history'], '2 sessions');
  render({best_quality: 0, capture_count: 1});
  assert.equal(labels['hosted-target-quality'], '0%');
  assert.equal(labels['hosted-target-history'], '1 capture');
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
