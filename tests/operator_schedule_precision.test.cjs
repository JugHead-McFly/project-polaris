const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('schedule durations round only their presentation to whole minutes', () => {
  const source = fs.readFileSync(path.join(__dirname, '../app/web/operator.js'), 'utf8');
  const code = source.slice(source.indexOf('const shortTime ='), source.indexOf('const uptimeLabel ='));
  const labels = vm.runInNewContext(code + '\n({shortTime, durationLabel});');
  assert.equal(labels.shortTime('2026-07-18 01:14:45 AM'), '01:15 AM');
  assert.equal(labels.shortTime('2026-07-18 11:59:45 PM'), '12:00 AM');
  assert.equal(labels.durationLabel(129.25), '2 hr 9 min');
  assert.equal(labels.durationLabel(999 * 10 / 60), '2 hr 47 min');
  assert.equal(labels.durationLabel(0.1), '<1 min');
  assert.equal(labels.durationLabel(59.8), '1 hr');
  assert.equal(labels.durationLabel(480), '8 hr');
});
