const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {webcrypto}=require('node:crypto');
const {JSDOM}=require('jsdom');
const api=require('../app/web/photo-reference.js');
const html=fs.readFileSync(path.join(__dirname,'../app/web/photo-reference.html'),'utf8');
const script=fs.readFileSync(path.join(__dirname,'../app/web/photo-reference.js'),'utf8');
const png=fs.readFileSync(path.join(__dirname,'fixtures/synthetic_reference.png'));
const waitFor=async(predicate)=>{const deadline=Date.now()+3000;while(!predicate()&&Date.now()<deadline)await new Promise(r=>setTimeout(r,5));assert.ok(predicate(),'Timed out waiting for async image decode');};
function file(bytes=png){return {type:'image/png',size:bytes.length,arrayBuffer:async()=>Uint8Array.from(bytes).buffer};}
function draftFile(value){const text=typeof value==='string'?value:JSON.stringify(value);return {size:Buffer.byteLength(text),text:async()=>text};}
function harness({deferDecode=false}={}) {
 const dom=new JSDOM(html,{url:'https://polaris.example/operator-assets/photo-reference.html',runScripts:'outside-only'});
 const w=dom.window,revoked=[],images=[];let id=0;
 w.confirm=()=>true;w.TextEncoder=TextEncoder;w.Blob=Blob;Object.defineProperty(w,'crypto',{value:webcrypto});
 w.URL.createObjectURL=blob=>{w.lastBlob=blob;return `blob:synthetic-${++id}`;};w.URL.revokeObjectURL=url=>revoked.push(url);
 w.HTMLAnchorElement.prototype.click=function(){w.download=this.download;};
 w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
 w.Image=class {constructor(){this.naturalWidth=256;this.naturalHeight=128;images.push(this);}set src(value){this.url=value;if(!deferDecode)setImmediate(()=>this.onload());}};
 w.fetch=()=>{throw Error('No network allowed');};
 w.eval(script);const workspace=w.PolarisPhotoReferences.workspace;
 const q=s=>w.document.querySelector(s);
 q('#reference-photo').getBoundingClientRect=()=>({left:10,top:20,width:256,height:128});
 return {w,q,workspace,revoked,images,close:()=>w.close(),click:(x,y)=>q('#reference-photo').dispatchEvent(new w.MouseEvent('click',{clientX:x,clientY:y,bubbles:true}))};
}

test('true north and level remain independent and even both do not calibrate',async()=>{
 const h=harness();try{
  await h.workspace.load(file());assert.match(h.q('#geometry-status').textContent,/North unknown.*Level unknown/);
  h.click(138,84);assert.equal(h.workspace.snapshot().references[0].kind,'true_north');
  assert.equal(h.workspace.snapshot().references[0].x,.5);
  assert.match(h.q('#geometry-status').textContent,/North reference marked.*Level unknown.*Not calibrated/);
  h.q('.modes [data-kind=level]').click();h.q('#add-center').click();
  assert.match(h.q('#geometry-status').textContent,/Level reference marked.*Not calibrated/);
  assert.equal(h.workspace.snapshot().geometry.angular_scale,'unknown');
  assert.equal(h.workspace.snapshot().geometry.calibrated,false);
 }finally{h.close();}
});
test('close and reopen retains references, same image reload retains them, different image clears them',async()=>{
 const h=harness();try{
  h.q('#open-workspace').click();await h.workspace.load(file());h.q('#add-center').click();
  h.q('#close-workspace').click();assert.equal(h.q('#workspace').open,false);
  h.q('#open-workspace').click();assert.equal(h.workspace.snapshot().references.length,1);
  await h.workspace.load(file());assert.equal(h.workspace.snapshot().references.length,1);
  await h.workspace.load(file(Buffer.concat([png,Buffer.from('different original')])));
  assert.equal(h.workspace.snapshot().references.length,0);assert.ok(h.revoked.length>=2);
 }finally{h.close();}
});
test('reference labels and keyboard adjustments are editable without HTML execution',async()=>{
 const h=harness();try{
  await h.workspace.load(file());h.q('#add-center').click();
  const label=h.q('#reference-list input');label.value='<img src=x onerror=alert(1)>';label.dispatchEvent(new h.w.Event('input'));
  h.q('.marker').dispatchEvent(new h.w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
  assert.equal(h.workspace.snapshot().references[0].x,.505);
  assert.equal(h.q('#reference-list img'),null);
  h.q('#reference-list button').click();assert.equal(h.workspace.snapshot().references.length,0);
 }finally{h.close();}
});
test('export excludes image bytes and imports only onto matching original',async()=>{
 const h=harness();try{
  await h.workspace.load(file());h.q('#add-center').click();h.q('#export-draft').click();
  const exported=JSON.parse(await h.w.lastBlob.text());assert.equal(h.w.download,'polaris-photo-references.json');
  assert.deepEqual(Object.keys(exported.image),['sha256','width','height']);assert.equal(JSON.stringify(exported).includes('data:image'),false);
  h.workspace.clear(true);await h.workspace.importDraft(draftFile(exported));assert.equal(h.workspace.snapshot(),null);
  await h.workspace.load(file(Buffer.concat([png,Buffer.from('different')])));assert.equal(h.workspace.snapshot(),null);assert.match(h.q('#reference-status').textContent,/not the exact image/);
  await h.workspace.load(file());assert.equal(h.workspace.snapshot().references.length,1);
 }finally{h.close();}
});
test('calibration claims and duplicate JSON keys are rejected without changing current draft',async()=>{
 const h=harness();try{
  await h.workspace.load(file());h.q('#add-center').click();const draft=h.workspace.snapshot();
  for(const change of [d=>d.geometry.calibrated=true,d=>d.geometry.projection='equirectangular',d=>d.references[0].x=1.2,d=>d.references[0].altitude_degrees=0,d=>d.image.sha256=[d.image.sha256]]) {
   const bad=JSON.parse(JSON.stringify(draft));change(bad);assert.throws(()=>api.validate(bad));
  }
  await h.workspace.importDraft(draftFile(JSON.stringify(draft).replace('"version":2','"version":1,"version":2')));
  assert.match(h.q('#reference-status').textContent,/unique/);assert.equal(h.workspace.snapshot().references.length,1);
 }finally{h.close();}
});
test('late decode cannot restore cleared image or supersede newer image',async()=>{
 const h=harness({deferDecode:true});try{
  const first=h.workspace.load(file());await waitFor(()=>h.images.length===1);
  h.workspace.clear(true);h.images[0].onload();await first;assert.equal(h.workspace.snapshot(),null);
  const older=h.workspace.load(file());await waitFor(()=>h.images.length===2);const newer=h.workspace.load(file(Buffer.concat([png,Buffer.from('new')])));await waitFor(()=>h.images.length===3);
  h.images[2].onload();await newer;const hash=h.workspace.snapshot().image.sha256;
  h.images[1].onload();await older;assert.equal(h.workspace.snapshot().image.sha256,hash);assert.ok(h.revoked.includes(h.images[1].url));
 }finally{h.close();}
});
test('late draft import cannot overwrite a new reference edit',async()=>{
 const h=harness();try{
  await h.workspace.load(file());const draft=JSON.stringify(h.workspace.snapshot());let resolve;
  const pending=h.workspace.importDraft({size:draft.length,text:()=>new Promise(r=>resolve=r)});
  h.q('#add-center').click();resolve(draft);await pending;assert.equal(h.workspace.snapshot().references.length,1);
 }finally{h.close();}
});
test('invalid image/oversize draft keep previous image and confirmation cancel preserves draft',async()=>{
 const h=harness();try{
  await h.workspace.load(file());h.q('#add-center').click();const before=h.workspace.snapshot().image.sha256;
  await h.workspace.load({...file(),type:'image/svg+xml'});assert.equal(h.workspace.snapshot().image.sha256,before);
  let read=false;await h.workspace.importDraft({size:300000,text:async()=>{read=true;}});assert.equal(read,false);
  h.w.confirm=()=>false;await h.workspace.load(file(Buffer.concat([png,Buffer.from('other')])));
  assert.equal(h.workspace.snapshot().references.length,1);assert.equal(h.workspace.snapshot().image.sha256,before);
 }finally{h.close();}
});
test('BFCache clears local photo state; standalone page prohibits connections and has no planner API',async()=>{
 const h=harness();try{
  await h.workspace.load(file());h.q('#add-center').click();
  h.w.dispatchEvent(new h.w.PageTransitionEvent('pageshow',{persisted:true}));assert.equal(h.workspace.snapshot(),null);
  assert.match(h.q('meta[http-equiv="Content-Security-Policy"]').content,/connect-src 'none'/);
  assert.doesNotMatch(script,/fetch\(|XMLHttpRequest|localStorage|sessionStorage/);
  assert.equal(h.q('#source-kind').disabled,true);
 }finally{h.close();}
});

test('large valid imported IDs do not break later editing or export',async()=>{
 const h=harness();try{
  await h.workspace.load(file());h.q('#add-center').click();const draft=h.workspace.snapshot();
  draft.references[0].id=Number.MAX_SAFE_INTEGER;
  await h.workspace.importDraft(draftFile(draft));h.q('#add-center').click();
  assert.equal(h.workspace.snapshot().references.length,2);
  assert.equal(h.workspace.snapshot().references[1].id,1);
  h.q('#export-draft').click();assert.equal(JSON.parse(await h.w.lastBlob.text()).references.length,2);
 }finally{h.close();}
});

test('measured elevation requires an explicit angle and provenance, remains approximate and separate from north/level',async()=>{
 const h=harness();try{
  await h.workspace.load(file());h.q('.modes [data-kind=measured_elevation]').click();
  assert.equal(h.q('#measurement-entry').hidden,false);
  h.q('#add-center').click();assert.equal(h.workspace.snapshot().references.length,0);
  h.q('#measured-degrees').value='27.5';h.q('#add-center').click();assert.equal(h.workspace.snapshot().references.length,0);
  h.q('#measurement-provenance').value='Synthetic inclinometer example; repeated readings near this point.';
  h.click(100,60);const draft=h.workspace.snapshot();const m=draft.references[0].measurement;
  assert.equal(m.elevation_degrees,27.5);assert.equal(m.approximate,true);assert.equal(m.absolute_accuracy,'unknown');assert.equal(m.same_setup_confirmed,false);
  assert.match(h.q('#geometry-status').textContent,/North unknown.*Level unknown.*1 approximate.*Not calibrated/);
  assert.equal(draft.geometry.angular_scale,'unknown');assert.equal(draft.version,2);
  h.q('#export-draft').click();const exported=JSON.parse(await h.w.lastBlob.text());
  h.workspace.clear(true);await h.workspace.importDraft(draftFile(exported));await h.workspace.load(file());
  assert.equal(h.workspace.snapshot().references[0].measurement.provenance,m.provenance);
 }finally{h.close();}
});
test('measurement bounds/types/accuracy claims are strict and v1 reference drafts remain supported',async()=>{
 const h=harness();try{
  await h.workspace.load(file());h.q('#add-center').click();const legacy=h.workspace.snapshot();legacy.version=1;
  await h.workspace.importDraft(draftFile(legacy));assert.equal(h.workspace.snapshot().references[0].kind,'true_north');
  const draft=h.workspace.snapshot();draft.references[0].kind='measured_elevation';
  draft.references[0].measurement={elevation_degrees:27.5,provenance:'Synthetic measurement',approximate:true,absolute_accuracy:'unknown',same_setup_confirmed:false};
  for(const value of [-90,0,90]){draft.references[0].measurement.elevation_degrees=value;assert.doesNotThrow(()=>api.validate(draft));}
  for(const value of [-90.1,90.1,null,'27.5',true,Infinity,NaN]){draft.references[0].measurement.elevation_degrees=value;assert.throws(()=>api.validate(draft));}
  draft.references[0].measurement.elevation_degrees=27.5;
  for(const change of [m=>m.approximate=false,m=>m.absolute_accuracy='0.1 degrees',m=>m.provenance='',m=>m.same_setup_confirmed='yes']) {
   const bad=JSON.parse(JSON.stringify(draft));change(bad.references[0].measurement);assert.throws(()=>api.validate(bad));
  }
  draft.version=1;assert.throws(()=>api.validate(draft));
 }finally{h.close();}
});
test('measurement edits remain editable, invalid values block export, and replacement clears pending measurement fields',async()=>{
 const h=harness();try{
  await h.workspace.load(file());h.q('.modes [data-kind=measured_elevation]').click();h.q('#measured-degrees').value='27.5';h.q('#measurement-provenance').value='Synthetic device reading';h.q('#measurement-same-setup').checked=true;h.q('#add-center').click();
  const angle=h.q('input[aria-label="Elevation for reference 1"]');angle.value='';angle.dispatchEvent(new h.w.Event('input'));
  h.q('#export-draft').click();assert.match(h.q('#reference-status').textContent,/finite measured elevation/);assert.equal(h.w.download,undefined);
  angle.value='28';angle.dispatchEvent(new h.w.Event('input'));assert.equal(h.workspace.snapshot().references[0].measurement.elevation_degrees,28);
  assert.match(h.q('#reference-list > li > label').textContent,/28°/);
  assert.doesNotMatch(h.q('#reference-list > li > label').textContent,/27.5°/);
  const setup=h.q('#reference-list input[type=checkbox]');setup.checked=false;setup.dispatchEvent(new h.w.Event('change'));
  assert.match(h.q('#reference-list > li > label').textContent,/setup unconfirmed/);
  setup.checked=true;setup.dispatchEvent(new h.w.Event('change'));
  h.q('#close-workspace').click();h.q('#open-workspace').click();assert.equal(h.workspace.snapshot().references[0].measurement.same_setup_confirmed,true);
  await h.workspace.load(file(Buffer.concat([png,Buffer.from('new photo')])));
  assert.equal(h.q('#measured-degrees').value,'');assert.equal(h.q('#measurement-provenance').value,'');assert.equal(h.q('#measurement-same-setup').checked,false);
  assert.equal(h.workspace.snapshot().references.length,0);
 }finally{h.close();}
});


test('sky view and photo workspace link without transferring draft state or accepting the other format',async()=>{
 const skySource=fs.readFileSync(path.join(__dirname,'../app/web/sky-view.js'),'utf8');
 const skyApi=require('../app/web/sky-view.js');
 const dom=new JSDOM('<div data-sky-view></div>',{url:'https://polaris.example/operator',runScripts:'outside-only'});
 const h=harness();try{
  dom.window.eval(skySource);dom.window.PolarisSkyView.mountAll(dom.window.document,()=>{throw Error('Linking must not calculate or upload');});
  const link=dom.window.document.querySelector('[data-photo-reference]');
  assert.equal(link.getAttribute('href'),'/operator-assets/photo-reference.html');
  assert.equal(link.target,'_blank');assert.equal(link.rel,'noopener');
  assert.match(dom.window.document.body.textContent,/Photo markers are not angular skyline points/);
  const back=h.q('nav a');assert.equal(back.getAttribute('href'),'/operator');assert.equal(back.target,'_blank');assert.equal(back.rel,'noopener');
  await h.workspace.load(file());h.q('#add-center').click();const photo=h.workspace.snapshot();
  assert.throws(()=>skyApi.validateSkyline(photo));assert.throws(()=>api.validate(skyApi.demo()));
  await h.workspace.importDraft(draftFile(skyApi.demo()));
  assert.equal(h.workspace.snapshot().image.sha256,photo.image.sha256);
  assert.equal(h.workspace.snapshot().references.length,1);
 }finally{h.close();dom.window.close();}
});
