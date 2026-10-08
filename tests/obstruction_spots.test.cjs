const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const source=name=>fs.readFileSync(path.join(__dirname,'../app/web',name),'utf8');
const profile=require('./fixtures/obstruction_preview.json').profile;
const flush=async()=>{for(let i=0;i<10;i++)await new Promise(r=>setImmediate(r));};
const row=(revision=1)=>({id:'spot-one',name:'Patio',revision,profile,source_quality:'manual_measured',available_for_tonight:true});
function harness(request) {
 const dom=new JSDOM('<div data-obstruction-editor></div><div id="saved-obstruction-spots"></div><section id="tonight-obstruction-controls"><select id="tonight-obstruction-spot"></select><p id="tonight-obstruction-status"></p></section>',{url:'https://example.invalid',runScripts:'outside-only'});
 const w=dom.window;w.confirm=()=>true;w.TextEncoder=TextEncoder;w.Blob=Blob;
 w.eval(source('obstruction-editor.js'));w.PolarisObstructionEditor.mountAll(w.document,request);
 w.eval(source('obstruction-spots.js'));let changes=0;
 const api=w.PolarisObstructionSpots.mount(w.document,request,()=>changes++);
 const q=s=>w.document.querySelector(s);
 const change=(s,v)=>{q(s).value=v;q(s).dispatchEvent(new w.Event('change',{bubbles:true}));};
 return {w,api,q,change,get changes(){return changes;},close:()=>w.close()};
}
const response=data=>({ok:true,status:200,json:async()=>data});

test('saved spots start Off, explicit selection uses revision and reset removes account data',async()=>{
 const h=harness(async()=>response([row()]));try{
  await h.api.setHome('home');assert.equal(h.api.params(),'');
  h.change('#tonight-obstruction-spot','spot-one');assert.match(h.api.params(),/obstruction_revision=1/);
  h.api.reset();assert.equal(h.api.params(),'');assert.equal(h.q('[data-saved]').options.length,1);
  assert.equal(h.q('#saved-obstruction-spots').hidden,true);
 }finally{h.close();}
});
test('changed and deleted selections never silently become Off',async()=>{
 let rows=[row()];const h=harness(async()=>response(rows));try{
  await h.api.setHome('home');h.change('#tonight-obstruction-spot','spot-one');
  rows=[row(2)];await h.api.setHome('home');assert.throws(()=>h.api.params(),/changed/);
  h.change('#tonight-obstruction-spot','spot-one');assert.match(h.api.params(),/revision=2/);
  rows=[];await h.api.setHome('home');assert.throws(()=>h.api.params());
  h.change('#tonight-obstruction-spot','');assert.equal(h.api.params(),'');
 }finally{h.close();}
});
test('save requires review, sends declared source and never auto-enables',async()=>{
 const calls=[];const h=harness(async(url,opts)=>{calls.push({url,opts});return response(opts.method?row():[]);});try{
  await h.api.setHome('home');h.q('[data-action=example]').click();
  h.q('[data-save]').click();await flush();assert.equal(calls.length,1);
  h.q('[data-complete]').checked=true;h.q('[data-reviewed]').checked=true;h.q('[data-name]').value='Patio';
  h.q('[data-save]').click();await flush();
  const save=calls.find(c=>c.opts.method==='POST');assert.ok(save);
  assert.equal(JSON.parse(save.opts.body).source_quality,'synthetic');
  assert.equal(h.api.params(),'');
 }finally{h.close();}
});
test('late saved-list response cannot repopulate after logout',async()=>{
 let resolve;const h=harness(()=>new Promise(r=>resolve=r));try{
  const promise=h.api.setHome('home');h.api.reset();resolve(response([row()]));await promise;
  assert.equal(h.q('[data-saved]').options.length,1);assert.equal(h.q('#saved-obstruction-spots').hidden,true);
 }finally{h.close();}
});
test('actual operator sends selected spot to Tonight and shows fail-closed revision error',async()=>{
 const dom=new JSDOM(source('operator.html'),{url:'https://example.invalid/operator',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window,calls=[];try{
  w.Headers=Headers;w.TextEncoder=TextEncoder;w.Blob=Blob;w.confirm=()=>true;w.matchMedia=()=>({matches:false});
  w.POLARIS_AUTH_CONFIG={mode:'supabase',supabaseUrl:'https://example.invalid',supabasePublishableKey:'synthetic'};
  w.supabase={createClient:()=>({auth:{onAuthStateChange(){},getSession:async()=>({data:{session:{user:{id:'one'},access_token:'synthetic'}}})}})};
  w.fetch=async(url,opts)=>{
   calls.push({url,opts});
   if(url==='/profile')return response({display_name:'Synthetic'});
   if(url==='/observatories')return response([{id:'home',name:'Home',latitude:0,longitude:0,timezone_name:'UTC'}]);
   if(url==='/rig-profiles')return response({profiles:[]});
   if(url.includes('obstruction-spots'))return response([row()]);
   return {ok:false,status:409,json:async()=>({detail:'Selected spot changed. Review it or choose Off.'})};
  };
  for(const file of ['obstruction-editor.js','obstruction-spots.js','operator.js'])w.eval(source(file));
  await flush();assert.equal(calls.filter(c=>c.url.startsWith('/tonight')).length,1);
  const select=w.document.getElementById('tonight-obstruction-spot');select.value='spot-one';select.dispatchEvent(new w.Event('change'));
  w.document.getElementById('hosted-refresh-button').click();await flush();
  assert.match(calls.at(-1).url,/obstruction_spot_id=spot-one&obstruction_revision=1/);
  assert.match(w.document.getElementById('hosted-decision-message').textContent,/Selected spot changed/);
  assert.equal(calls.at(-1).opts.headers.get('Authorization'),'Bearer synthetic');
 }finally{w.close();}
});

test('reload invalidates the active planning generation including retrieval failure',async()=>{
 let fail=false;const h=harness(async()=>{if(fail)throw Error('Offline');return response([row(1)]);});try{
  await h.api.setHome('home');h.change('#tonight-obstruction-spot','spot-one');const before=h.api.version;
  await h.api.setHome('home');assert.ok(h.api.version>before);
  const next=h.api.version;fail=true;await h.api.setHome('home');assert.ok(h.api.version>next);assert.throws(()=>h.api.params());
 }finally{h.close();}
});
test('late save cannot switch the editing destination and existing spot requires its survey loaded',async()=>{
 const b={...row(),id:'spot-two',name:'Driveway'};let resolve;const writes=[];
 const h=harness(async(url,opts)=>{if(opts.method==='PUT'){writes.push(url);return new Promise(r=>resolve=r);}return response([row(),b]);});try{
  await h.api.setHome('home');h.change('[data-saved]','spot-one');
  h.q('[data-save]').click();await flush();assert.equal(writes.length,0);assert.match(h.q('[data-message]').textContent,/Load/);
  h.q('[data-load]').click();h.q('[data-complete]').checked=true;h.q('[data-reviewed]').checked=true;
  h.q('[data-save]').click();await flush();assert.equal(writes.length,1);
  h.change('[data-saved]','spot-two');resolve(response(row(2)));await flush();
  assert.equal(h.q('[data-saved]').value,'spot-two');assert.equal(h.q('[data-name]').value,'Driveway');
  h.q('[data-save]').click();await flush();assert.equal(writes.length,1);
 }finally{h.close();}
});
