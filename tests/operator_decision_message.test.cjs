const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('caution preserves the server explanation, with a fallback when absent', () => {
  const source = fs.readFileSync(path.join(__dirname, '../app/web/operator.js'), 'utf8');
  const code = source.slice(source.indexOf('const displayedDecisionMessage ='), source.indexOf('const softenAdvisoryNote ='));
  const format = vm.runInNewContext(`${code}\ndisplayedDecisionMessage;`);
  const message = 'Use caution: heat is a concern. Forecast temperature is 100°F.';
  assert.equal(format('Use Caution', message), message);
  assert.match(format('Use Caution', ''), /need attention/);
  assert.match(format('Do Not Image', 'Do not image: cloud cover is 100%.'), /^Cloud cover is 100%\./);
});
