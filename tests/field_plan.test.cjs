const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const source=name=>fs.readFileSync(path.join(__dirname,'../app/web',name),'utf8');
const flush=async()=>{for(let i=0;i<10;i++)await new Promise(r=>setImmediate(r));};
const snapshot={text:'Synthetic field plan',calendar:'Synthetic ICS',night:'2026-10-08',generated_at:'2026-10-08T00:00:00Z'};

test('downloads exact snapshot blobs, never fetches or stores, and resets on bfcache',async()=>{
 const dom=new JSDOM(source('operator.html'),{url:'https://example.invalid',runScripts:'outside-only'}),w=dom.window,downloads=[],blobs=[];
 try {
  w.Blob=Blob;w.URL.createObjectURL=b=>{blobs.push(b);return 'blob:synthetic';};w.URL.revokeObjectURL=()=>{};
  w.HTMLAnchorElement.prototype.click=function(){downloads.push(this.download);};w.fetch=()=>{throw Error('No network');};
  w.eval(source('field-plan.js'));const api=w.PolarisFieldPlan;api.mount(w.document);
  const q=s=>w.document.querySelector(s);
  assert.equal(q('[data-field-text]').disabled,true);
  api.set(snapshot);q('[data-field-text]').click();q('[data-field-calendar]').click();
  assert.deepEqual(downloads,['polaris-plan-2026-10-08.txt','polaris-plan-2026-10-08.ics']);
  assert.equal(await blobs[0].text(),snapshot.text);assert.equal(await blobs[1].text(),snapshot.calendar);
  const old=api.version;api.clear();assert.ok(api.version>old);assert.equal(q('[data-field-text]').disabled,true);
  api.set({...snapshot,calendar:null});assert.equal(q('[data-field-calendar]').disabled,true);
  const event=new w.Event('pageshow');Object.defineProperty(event,'persisted',{value:true});w.dispatchEvent(event);
  assert.equal(q('[data-field-text]').disabled,true);
  api.set({text:null,unavailable_reason:'<script>unsafe</script>'});assert.equal(q('[data-field-status] script'),null);
  assert.match(q('[data-field-status]').textContent,/<script>/);
 }finally{w.close();}
});

test('whole operator account, home, EQ, spot and loading paths clear an accepted export',async()=>{
 const dom=new JSDOM(source('operator.html'),{url:'https://example.invalid/operator',runScripts:'outside-only',pretendToBeVisual:true}),w=dom.window;
 let auth;
 try {
  w.Headers=Headers;w.TextEncoder=TextEncoder;w.Blob=Blob;w.confirm=()=>true;w.matchMedia=()=>({matches:false});
  w.POLARIS_AUTH_CONFIG={mode:'supabase',supabaseUrl:'https://example.invalid',supabasePublishableKey:'synthetic'};
  w.supabase={createClient:()=>({auth:{onAuthStateChange(fn){auth=fn;},getSession:async()=>({data:{session:{user:{id:'one'},access_token:'synthetic'}}})}})};
  const response=data=>({ok:true,json:async()=>data});
  w.fetch=async url=>{
   if(url==='/profile')return response({display_name:'Synthetic'});
   if(url==='/observatories')return response([{id:'home',name:'Home',latitude:0,longitude:0,timezone_name:'UTC'}]);
   if(url==='/rig-profiles')return response({profiles:[]});
   if(url.includes('obstruction-spots'))return response([]);
   return {ok:false,status:503,headers:new Headers(),json:async()=>({detail:'Synthetic failure'})};
  };
  for(const name of ['field-plan.js','obstruction-editor.js','obstruction-spots.js','operator.js'])w.eval(source(name));
  await flush();
  const q=s=>w.document.querySelector(s),seed=()=>{w.PolarisFieldPlan.set(snapshot);assert.equal(q('[data-field-text]').disabled,false);};
  seed();q('#hosted-edit-home-button').click();assert.equal(q('[data-field-text]').disabled,true);
  seed();q('#hosted-eq-mode-checkbox').dispatchEvent(new w.Event('change'));assert.equal(q('[data-field-text]').disabled,true);
  seed();q('#tonight-obstruction-spot').dispatchEvent(new w.Event('change'));assert.equal(q('[data-field-text]').disabled,true);
  seed();q('#hosted-refresh-button').click();assert.equal(q('[data-field-text]').disabled,true);await flush();assert.equal(q('[data-field-text]').disabled,true);
  seed();auth('SIGNED_IN',{user:{id:'two'},access_token:'other'});assert.equal(q('[data-field-text]').disabled,true);
  seed();auth('SIGNED_OUT',null);await flush();assert.equal(q('[data-field-text]').disabled,true);
 }finally{w.close();}
});

test('accepted real-shaped Tonight enables downloads but late success cannot revive changed context',async()=>{
 const fixture=require('./fixtures/field_plan_tonight.json');
 const dom=new JSDOM(source('operator.html'),{url:'https://example.invalid/operator',runScripts:'outside-only',pretendToBeVisual:true}),w=dom.window;
 let hold=false,resolvePlan;
 try {
  w.Headers=Headers;w.TextEncoder=TextEncoder;w.Blob=Blob;w.confirm=()=>true;w.matchMedia=()=>({matches:false});
  w.POLARIS_AUTH_CONFIG={mode:'supabase',supabaseUrl:'https://example.invalid',supabasePublishableKey:'synthetic'};
  w.supabase={createClient:()=>({auth:{onAuthStateChange(){},getSession:async()=>({data:{session:{user:{id:'one'},access_token:'synthetic'}}})}})};
  const response=data=>({ok:true,headers:new Headers(),json:async()=>data});
  w.fetch=async url=>{
   if(url==='/profile')return response({display_name:'Synthetic'});
   if(url==='/observatories')return response([{id:'home',name:'Home',latitude:0,longitude:0,timezone_name:'UTC'}]);
   if(url==='/rig-profiles')return response({profiles:[]});
   if(url.includes('obstruction-spots'))return response([]);
   if(url.startsWith('/tonight'))return hold?new Promise(r=>resolvePlan=r):response(fixture);
   return {ok:false,status:503,headers:new Headers(),json:async()=>({})};
  };
  for(const name of ['field-plan.js','obstruction-editor.js','obstruction-spots.js','operator.js'])w.eval(source(name));
  await flush();const q=s=>w.document.querySelector(s);
  assert.equal(q('[data-field-text]').disabled,false);
  assert.equal(q('[data-field-calendar]').disabled,false);
  assert.match(q('[data-field-status]').textContent,/2026-07-17/);
  for(const selector of ['#hosted-eq-mode-checkbox','#hosted-edit-home-button','#tonight-obstruction-spot']) {
   hold=true;q('#hosted-refresh-button').click();await flush();
   assert.equal(q('[data-field-text]').disabled,true);
   if(selector==='#hosted-edit-home-button')q(selector).click();
   else q(selector).dispatchEvent(new w.Event('change'));
   resolvePlan(response(fixture));await flush();
   assert.equal(q('[data-field-text]').disabled,true);
   hold=false;q('#hosted-refresh-button').click();await flush();
   assert.equal(q('[data-field-text]').disabled,false);
  }
 }finally{w.close();}
});
