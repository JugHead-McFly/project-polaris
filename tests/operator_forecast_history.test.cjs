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

test('individual-time comparisons do not inflate the nightly confidence card', () => {
  const source = fs.readFileSync(path.join(__dirname, '../app/web/operator.js'), 'utf8');
  const code = source.slice(source.indexOf('const renderNightlyConfidence ='), source.indexOf('const clampPercent ='));
  const labels = {};
  const render = vm.runInNewContext(`${code}\nrenderNightlyConfidence;`, {
    setText: (id, text) => { labels[id] = text; },
    byId: () => ({ replaceChildren() {} }),
  });
  render({satellite_reliability: {check_count: 39}, saved_forecast_count: 40});
  assert.equal(labels['forecast-accuracy-history-label'], 'Building forecast confidence');
  assert.equal(labels['forecast-accuracy-insight'], 'Afternoon: 0/30 nights · Dusk: 0/30 nights');
});
