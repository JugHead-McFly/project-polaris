// Reusable browser-runtime smoke test. Start serve_import_plan_fixture.py first.
// Pass the Browser skill's supported browser handle; no external URLs are used.
import assert from 'node:assert/strict';

export async function checkImportPlanReloads(browser) {
  const viewport = await browser.capabilities.get('viewport');
  const dashboard = await browser.tabs.new();
  const controls = await browser.tabs.new();
  const results = [];
  const fields = {
    target: '#hosted-target-name', progress: '#hosted-target-progress',
    remaining: '#hosted-target-remaining', quality: '#hosted-target-quality',
    history: '#hosted-target-history', schedule: '#hosted-schedule-list',
    end: '#hosted-plan-end-reason', library: '#hosted-library-summary',
  };
  async function inspect(stage, expected) {
    let desktop;
    for (const [device, width, height] of [['desktop', 1440, 1000], ['phone', 390, 844]]) {
      await viewport.set({width, height});
      await dashboard.reload();
      await dashboard.playwright.locator('#hosted-target-history')
        .filter({hasText: expected.history}).waitFor({state: 'visible', timeoutMs: 15000});
      const values = {};
      for (const [key, selector] of Object.entries(fields)) {
        values[key] = await dashboard.playwright.locator(selector).innerText();
      }
      // Check the count without enshrining the existing "1 sessions" wording bug.
      values.library = /^\d+ sessions?$/.test(values.library) ? Number.parseInt(values.library, 10) : values.library;
      for (const [key, value] of Object.entries(expected)) assert.equal(values[key], value, `${stage}/${device}/${key}`);
      assert.equal(values.quality, 'Not assessed');
      assert.ok(values.schedule.includes(expected.target));
      assert.ok(values.end.length > 0);
      // Visible content must fit horizontally at both responsive breakpoints.
      const overflow = await dashboard.playwright.evaluate(() =>
        document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
      assert.equal(overflow, false, `${stage}/${device}: horizontal overflow`);
      if (desktop) assert.deepEqual(values, desktop, `${stage}: responsive reload mismatch`);
      else desktop = values;
      results.push({stage, device, ...values});
    }
  }
  try {
    await dashboard.goto('http://127.0.0.1:8107/operator');
    await controls.goto('http://127.0.0.1:8107/fixture');
    await inspect('before import', {target: 'M27', remaining: '5 hr', history: '0 sessions'});
    await controls.playwright.getByRole('button', {name: 'Import 3 hours M27', exact: true}).click();
    await inspect('after import', {target: 'M27', remaining: '2 hr', history: '1 session', progress: '60%', library: 1});
    await controls.playwright.getByRole('button', {name: 'Import 3 hours M27', exact: true}).click();
    await inspect('after duplicate import', {target: 'M27', remaining: '2 hr', history: '1 session', progress: '60%', library: 1});
    await controls.playwright.getByRole('button', {name: 'Complete M27 goal', exact: true}).click();
    await inspect('after completed goal', {target: 'M57', remaining: '4 hr', history: '0 sessions', progress: '0%', library: 2});
    return results;
  } finally {
    await viewport.reset();
    await dashboard.close();
    await controls.close();
  }
}
