const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {createMapLibraryLoader} = require('../app/web/loading.js');

function fixture(timeout) {
  const scripts = [];
  const scope = {};
  const doc = {
    createElement: () => ({remove() { this.removed = true; }}),
    head: {append: script => scripts.push(script)},
  };
  return {scripts, scope, load: createMapLibraryLoader(doc, scope, timeout)};
}

test('optional library does not load at construction and concurrent callers share one script', async () => {
  const f = fixture();
  assert.equal(f.scripts.length, 0);
  const first = f.load(), second = f.load();
  assert.equal(first, second);
  assert.equal(f.scripts.length, 1);
  assert.equal(f.scripts[0].src, '/operator-assets/leaflet.js');
  f.scope.L = {ready: true}; f.scripts[0].onload();
  assert.equal(await first, f.scope.L);
  assert.equal(await f.load(), f.scope.L);
  assert.equal(f.scripts.length, 1);
});

test('failure and missing global permit retry, without leaked script handlers', async () => {
  const f = fixture();
  for (const event of ['onerror', 'onload']) {
    const pending = f.load();
    const script = f.scripts.at(-1);
    script[event]();
    await assert.rejects(pending, /Map controls/);
    assert.equal(script.removed, true);
    assert.equal(script.onload, null);
    assert.equal(script.onerror, null);
  }
  const retry = f.load(); f.scope.L = {}; f.scripts.at(-1).onload();
  await retry;
});

test('timeout allows another attempt', async () => {
  const f = fixture(5);
  await assert.rejects(f.load(), /timed out/);
  assert.equal(f.scripts[0].removed, true);
  const next = f.load(); f.scope.L = {}; f.scripts[1].onload(); await next;
});

test('page has no blocking map script and map callers await loading before consuming it', () => {
  const html = fs.readFileSync('app/web/operator.html', 'utf8');
  assert.doesNotMatch(html, /<script[^>]+leaflet\.js/);
  const source = fs.readFileSync('app/web/operator.js', 'utf8');
  const candidates = source.slice(source.indexOf('const loadCandidateSites ='), source.indexOf('const updateCandidateSite ='));
  assert.ok(candidates.indexOf('await ensureMapLibrary()') < candidates.indexOf('renderCandidateSites(origin, sites)'));
  const capture = source.slice(source.indexOf('const renderCaptureLocations ='), source.indexOf('const candidateSiteDistanceLabel ='));
  assert.ok(capture.indexOf('await ensureMapLibrary()') < capture.indexOf('window.L.map'));
});

test('saved sites survive optional map failure, and superseded loads cannot render', async () => {
  const vm = require('node:vm');
  const source = fs.readFileSync('app/web/operator.js', 'utf8');
  const fn = source.slice(source.indexOf('const loadCandidateSites ='), source.indexOf('const updateCandidateSite ='));
  let current = true;
  const calls = [];
  const sites = [{id: 'saved-site'}];
  const context = {
    loadingRun: {current: () => current},
    apiFetch: async () => ({ok: true, json: async () => sites}),
    ensureMapLibrary: async () => { throw new Error('offline'); },
    renderCandidateSites: (...args) => calls.push(args),
  };
  vm.createContext(context);
  vm.runInContext(fn + '; globalThis.load = loadCandidateSites;', context);
  await context.load('origin');
  assert.deepEqual(calls, [['origin', sites]]);
  current = false;
  await context.load('stale');
  assert.equal(calls.length, 1);
});
