const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('loading account history never claims zero saved records', () => {
  const source = fs.readFileSync(path.join(__dirname, '../app/web/operator.js'), 'utf8');
  const code = source.slice(source.indexOf('let latestForecastAccuracy ='), source.indexOf('const clampPercent ='));
  const labels = {};
  const render = vm.runInNewContext(`${code}\nrenderForecastAccuracyHistory;`, {
    setText: (id, text) => { labels[id] = text; },
    byId: () => ({ replaceChildren() {}, hidden: false }),
  });
  render(null);
  assert.equal(labels['forecast-accuracy-history-count'], 'Loading history…');
  assert.equal(labels['forecast-accuracy-link-count'], 'Loading…');
  assert.doesNotMatch(Object.values(labels).join(' '), /0 saved|No forecasts saved/);
});
