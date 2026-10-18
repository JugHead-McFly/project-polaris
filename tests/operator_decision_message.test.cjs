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

test('ordinary imaging conditions use calm wording without hiding hazards or stale data', () => {
  const source = fs.readFileSync(path.join(__dirname, '../app/web/operator.js'), 'utf8');
  const code = source.slice(source.indexOf('const displayedDecisionLabel ='), source.indexOf('const softenAdvisoryNote ='));
  const {label, compact} = vm.runInNewContext(`${code}\n({label:displayedDecisionLabel,compact:compactConditionMessage});`);
  const fair = {temperature_f:70,wind_speed_mph:4,humidity_percent:40,planned_cloud_cover_percent:40};
  assert.equal(label('Use Caution', fair), 'Fair conditions');
  assert.equal(label('Use Caution', {...fair,cache_status:'stale'}), 'Check current conditions');
  assert.equal(label('Use Caution', {...fair,planned_cloud_forecast_spread:35}), 'Check the forecast');
  assert.equal(label('Use Caution', {...fair,planned_cloud_cover_percent:85}), 'Challenging conditions');
  assert.equal(label('Use Caution', {}), 'Review conditions');
  for (const weather of [{...fair,temperature_f:100}, {...fair,wind_speed_mph:18}, {...fair,humidity_percent:90}]) {
    assert.equal(label('Use Caution', weather), 'Use caution');
    assert.equal(compact({schedule:{decision:'Use Caution'},weather,message:'Specific equipment advisory.'}), 'Specific equipment advisory.');
  }
  assert.equal(label('Use Caution', {...fair,temperature_f:100,planned_temperature_f:70}), 'Use caution');
  assert.equal(label('Do Not Image', fair), 'Wait for better conditions');
});
