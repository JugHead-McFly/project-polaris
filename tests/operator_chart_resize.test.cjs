const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('accuracy chart redraws only for meaningful width changes', () => {
  const source = fs.readFileSync(path.join(__dirname, '../app/web/operator.js'), 'utf8');
  const setup = source.slice(source.indexOf('const accuracyChart ='), source.lastIndexOf('bootApplication();'));
  let resize;
  const chart = {};
  const data = { matched_samples: 10 };
  const renders = [];
  const context = {
    byId: () => chart,
    latestForecastAccuracy: data,
    renderForecastAccuracyHistory: value => renders.push(value),
    ResizeObserver: class {
      constructor(callback) { resize = callback; }
      observe(element) { assert.equal(element, chart); }
    },
  };
  vm.runInNewContext(setup, context);
  for (const width of [1440, 1440, 0, 290, 290.1, 1440]) {
    resize([{ contentRect: { width } }]);
  }
  assert.deepEqual(renders, [data, data, data]);
  context.latestForecastAccuracy = null;
  resize([{ contentRect: { width: 360 } }]);
  assert.equal(renders.length, 3);
});
