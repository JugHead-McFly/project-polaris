const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');
const editor = require('../app/web/obstruction-editor.js');
const source = fs.readFileSync(path.join(__dirname, '../app/web/obstruction-editor.js'), 'utf8');
const fixture = require('./fixtures/obstruction_preview.json');
const clone = value => JSON.parse(JSON.stringify(value));
const flush = () => new Promise(resolve => setImmediate(resolve));
function harness(request = async () => ({ok:true,json:async () => clone(fixture)}), count=1) {
  const dom = new JSDOM('<!doctype html><body>'+ '<div data-obstruction-editor></div>'.repeat(count), {url:'https://polaris.example/operator',runScripts:'outside-only'});
  const w=dom.window;
  w.TextEncoder = TextEncoder; w.Blob = Blob; w.confirm = () => true;
  w.URL.createObjectURL = blob => { w.exportedBlob=blob; return 'blob:synthetic'; };
  w.URL.revokeObjectURL = () => {};
  w.HTMLAnchorElement.prototype.click = function () { w.downloaded=this.download; };
  w.eval(source); w.PolarisObstructionEditor.mountAll(w.document, request);
  const root = w.document.querySelector('[data-obstruction-editor]');
  const q = selector => root.querySelector(selector);
  const input = (selector,value) => {const element=q(selector); element.value=value; element.dispatchEvent(new w.Event('input',{bubbles:true}));};
  const confirm = () => {q('[data-complete]').checked=true; q('[data-complete]').dispatchEvent(new w.Event('input',{bubbles:true}));};
  const click = action => q(`[data-action=${action}]`).click();
  const submit = () => q('form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
  const importFile = file => {const element=q('[data-file]');Object.defineProperty(element,'files',{configurable:true,value:[file]});element.dispatchEvent(new w.Event('change',{bubbles:true}));};
  return {dom,w,q,input,confirm,click,submit,importFile,close:()=>dom.window.close()};
}

test('canonical draft export/import round-trip preserves incomplete coverage and rejects extra keys', () => {
  const draft=editor.example();
  assert.deepEqual(editor.parseImport(editor.exportDraft(draft)), draft);
  assert.equal(draft.complete_coverage,false);
  for (const mutate of [p=>p.horizon[0].altitude_degrees='',p=>p.horizon[0].azimuth_degrees=360,p=>p.clearance_degrees=true,p=>p.complete_coverage='true',p=>p.horizon.reverse(),p=>p.sectors[0].maximum_altitude_degrees=0,p=>p.sectors[0].end_azimuth_degrees=350,p=>p.owner='secret']) {
    const bad=clone(draft);mutate(bad);assert.throws(()=>editor.validateDraft(bad));
  }
  assert.throws(()=>editor.parseImport('{"format":"polaris-obstruction-profile","version":2,"profile":{}}'));
  assert.throws(()=>editor.parseImport(' '.repeat(128*1024+1)));
  assert.throws(()=>editor.parseImport('null'));
});

test('empty or unconfirmed geometry cannot make a preview request', async () => {
  let calls=0;const h=harness(async()=>{calls++;throw Error('should not send');});
  h.submit(); await flush();assert.equal(calls,0);assert.match(h.q('[data-status]').textContent,/blank|Fill/);
  h.click('example');h.submit();await flush();assert.equal(calls,0);assert.match(h.q('[data-status]').textContent,/Coverage unknown/);
  h.close();
});

test('validated preview uses backend endpoint, plots wrap sectors, and any geometry edit revokes confirmation',async()=>{
  const sent=[];const h=harness(async(url,options)=>{sent.push({url,options});return {ok:true,json:async()=>clone(fixture)};});
  h.click('example');h.confirm();h.submit();await flush();
  assert.equal(sent[0].url,'/obstructions/preview');assert.equal(sent[0].options.cache,'no-store');
  assert.deepEqual(JSON.parse(sent[0].options.body).profile,fixture.profile);
  assert.equal(h.q('[data-chart]').querySelectorAll('rect.obs-roof').length,2);
  assert.match(h.q('[data-status]').textContent,/not a full-frame/);
  h.input('[data-horizon] input[data-key=altitude_degrees]','22');
  assert.equal(h.q('[data-complete]').checked,false);assert.equal(h.q('[data-chart]').children.length,0);
  h.close();
});

test('stale response cannot redraw after edit, reset, or account reset',async()=>{
  for (const change of [h=>h.input('[data-probe-alt]','60'),h=>h.click('reset'),h=>h.w.PolarisObstructionEditor.resetAll()]) {
    let resolve;const h=harness(()=>new Promise(r=>resolve=r));h.click('example');h.confirm();h.submit();
    change(h);resolve({ok:true,json:async()=>clone(fixture)});await flush();
    assert.equal(h.q('[data-chart]').children.length,0);assert.equal(h.q('[type=submit]').disabled,false);h.close();
  }
});

test('import clears prior confirmation, rejects malicious data without replacing draft, and can repeat',async()=>{
  const h=harness();h.click('example');h.confirm();
  const contents=editor.exportDraft({...editor.example(),complete_coverage:true});
  h.importFile({size:contents.length,text:async()=>contents});await flush();
  assert.equal(h.q('[data-complete]').checked,false);assert.match(h.q('[data-origin]').textContent,/Imported/);
  const before=h.q('[data-horizon]').textContent;
  const evil=JSON.stringify({format:'polaris-obstruction-profile',version:1,profile:{...editor.example(),owner:'<img src=x onerror=alert(1)>'}});
  h.importFile({size:evil.length,text:async()=>evil});await flush();
  assert.equal(h.q('[data-horizon]').textContent,before);assert.equal(h.q('img'),null);
  h.importFile({size:contents.length,text:async()=>contents});await flush();assert.equal(h.q('[data-horizon]').children.length,4);
  h.close();
});

test('slow import cannot overwrite a newer edit and oversized import is never read',async()=>{
  const h=harness();h.click('example');let resolve;let reads=0;
  h.importFile({size:128*1024+1,text:async()=>{reads++;return '';}});await flush();assert.equal(reads,0);
  h.importFile({size:100,text:()=>new Promise(r=>resolve=r)});
  h.input('[data-horizon] input[data-key=altitude_degrees]','24');
  resolve(editor.exportDraft(editor.example()));await flush();assert.equal(h.q('[data-horizon] input[data-key=altitude_degrees]').value,'24');h.close();
});

test('export contains only geometry, cancellation preserves draft, and a reload starts empty',async()=>{
  const h=harness();h.click('example');h.click('export');
  const saved=JSON.parse(await h.w.exportedBlob.text());assert.deepEqual(Object.keys(saved),['format','version','profile']);
  assert.equal(saved.profile.complete_coverage,false);assert.equal(h.w.downloaded,'polaris-obstruction-profile.json');
  h.input('[data-horizon] input[data-key=altitude_degrees]','26');h.w.confirm=()=>false;h.click('reset');
  assert.equal(h.q('[data-horizon] input[data-key=altitude_degrees]').value,'26');h.close();
  const fresh=harness();assert.equal(fresh.q('[data-horizon] input[data-key=altitude_degrees]').value,'');assert.equal(fresh.q('[data-complete]').checked,false);fresh.close();
});

test('errors remain readable, render no diagram and reenable preview',async()=>{
  for(const status of [401,422,500]){
    const h=harness(async()=>({ok:false,status,json:async()=>({detail:'Request unavailable'})}));
    h.click('example');h.confirm();h.submit();await flush();
    assert.equal(h.q('[data-chart]').children.length,0);assert.equal(h.q('[type=submit]').disabled,false);
    assert.match(h.q('[data-status]').textContent,status===401?/Sign in/:/Request unavailable/);h.close();
  }
});

test('controls have labels and keyboard semantics, added rows focus inputs, and account reset clears every editor',()=>{
  const h=harness(undefined,2);h.click('example');h.click('add-point');
  assert.equal(h.w.document.activeElement,h.q('[data-horizon]').lastElementChild.querySelector('input'));
  for(const input of h.w.document.querySelectorAll('input'))assert.ok(input.closest('label') || input.labels.length);
  for(const button of h.w.document.querySelectorAll('button'))assert.ok(button.type==='button'||button.type==='submit');
  const ids=Array.from(h.w.document.querySelectorAll('[id]'),el=>el.id);assert.equal(ids.length,new Set(ids).size);
  h.w.PolarisObstructionEditor.resetAll();for(const checkbox of h.w.document.querySelectorAll('[data-complete]'))assert.equal(checkbox.checked,false);
  h.close();
});

test('editor performs no storage, telemetry, photo, sensor or innerHTML interpolation',()=>{
  assert.doesNotMatch(source,/localStorage|sessionStorage|indexedDB|sendBeacon|getUserMedia|geolocation/);
  assert.equal((source.match(/innerHTML\s*=/g)||[]).length,1);
  assert.match(source,/container.innerHTML = markup/);
});


test('duplicate import fields including escaped names are rejected rather than last-wins',()=>{
  const text=editor.exportDraft(editor.example());
  const duplicate=text.replace('"clearance_degrees": 1', '"clearance_degrees": 0, "clearance_degrees": 10');
  assert.throws(()=>editor.parseImport(duplicate), /unique/);
  const escaped=duplicate.replace('"clearance_degrees": 10', '"clearance_\\u0064egrees": 10');
  assert.throws(()=>editor.parseImport(escaped), /unique/);
  assert.deepEqual(editor.parseImport(text),editor.example());
});

test('ceiling clipping occurs after horizon interpolation and has unique IDs',()=>{
  const h=harness();const data=clone(fixture);
  data.profile.clearance_degrees=10;
  data.horizon=[{azimuth_degrees:0,altitude_degrees:90},{azimuth_degrees:180,altitude_degrees:0},{azimuth_degrees:360,altitude_degrees:90}];
  h.w.PolarisObstructionEditor.drawChart(h.q('[data-chart]'),data);
  const polygon=h.q('polygon');
  // Raw raised knots are altitude100 (y10) and altitude10 (y235): the
  // midpoint is altitude55, then the top is clipped by a separate SVG rectangle.
  assert.match(polygon.getAttribute('points'),/45,10 405,235 765,10/);
  assert.match(polygon.getAttribute('clip-path'),/^url\(#obs-chart-clip-/);
  assert.equal(h.q('clipPath rect').getAttribute('y'),'35');
  const first=h.q('clipPath').id;
  h.w.PolarisObstructionEditor.drawChart(h.q('[data-chart]'),data);
  assert.notEqual(h.q('clipPath').id,first);h.close();
});
