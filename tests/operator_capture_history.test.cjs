const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

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
