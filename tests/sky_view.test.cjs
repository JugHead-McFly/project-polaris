const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const api=require('../app/web/sky-view.js');
const source=fs.readFileSync(path.join(__dirname,'../app/web/sky-view.js'),'utf8');
const flush=async()=>{for(let i=0;i<10;i++)await new Promise(r=>setImmediate(r));};
const catalog=[{id:'M31',name:'Andromeda'},{id:'M57',name:'Ring Nebula'},{id:'M13',name:'Hercules'}];
const fixture={at_utc:'2026-10-08T00:00:00+00:00',at_local:'2026-10-08T00:00:00+00:00',location:{timezone_name:'UTC'},targets:[{id:'M31',name:'Synthetic position fixture',status:'above_horizon',azimuth_degrees:359.9,altitude_degrees:30},{id:'M57',name:'Synthetic position fixture',status:'below_horizon',azimuth_degrees:.1,altitude_degrees:-5}]};
const response=data=>({ok:true,json:async()=>data});
function harness(handler) {
 const dom=new JSDOM('<div data-sky-view></div>',{url:'https://example.invalid/operator',runScripts:'outside-only'}),w=dom.window,calls=[];
 w.TextEncoder=TextEncoder;w.Blob=Blob;w.confirm=()=>true;w.URL.createObjectURL=()=> 'blob:synthetic';w.URL.revokeObjectURL=()=>{};
 w.eval(source);w.PolarisSkyView.mountAll(w.document,async(url,options)=>{calls.push({url,options});if(handler)return handler(url,options);return response(url.endsWith('catalog')?catalog:fixture);});
 const q=s=>w.document.querySelector(s),input=(s,value)=>{q(s).value=value;q(s).dispatchEvent(new w.Event('input'));};
 const open=()=>{q('details').open=true;q('details').dispatchEvent(new w.Event('toggle'));};
 return {w,q,input,open,calls,close:()=>w.close()};
}

test('ten-degree grid is exact in angular coordinates, seam directions share north, below horizon targets do not plot',()=>{
 const dom=new JSDOM('<div></div>'),container=dom.window.document.querySelector('div');
 api.draw(container,fixture,api.demo());
 const lines=[...container.querySelectorAll('line')];assert.equal(lines.length,37+10);
 assert.equal(Number(lines[1].getAttribute('x1'))-Number(lines[0].getAttribute('x1')),40);
 assert.equal(Number(lines[37].getAttribute('y1'))-Number(lines[38].getAttribute('y1')),30);
 assert.ok(container.querySelector('[data-target=M31]'));assert.equal(container.querySelector('[data-target=M57]'),null);
 assert.equal(container.querySelectorAll('.sky-silhouette').length,2);
 assert.equal(container.querySelectorAll('.sky-unknown').length,1);
 assert.match(container.textContent,/N \/ 0°/);assert.match(container.textContent,/N \/ 360°/);dom.window.close();
});
test('partial and absent skylines never infer clear gaps; north wrap uses boundary not a false join',()=>{
 assert.equal(api.skylineHeight(api.empty(),10),null);
 assert.equal(api.skylineHeight(api.demo(),0),20);assert.equal(api.skylineHeight(api.demo(),360),20);
 assert.equal(api.skylineHeight(api.demo(),180),null);
 assert.equal(api.targetState({...fixture.targets[0],azimuth_degrees:180},api.demo()),'Skyline unknown');
 assert.match(api.targetState({...fixture.targets[0],altitude_degrees:10},api.demo()),/^At\/below/);
 assert.throws(()=>api.validateSkyline({...api.demo(),segments:[[{azimuth:359,altitude:20},{azimuth:1,altitude:20}]]}));
 assert.throws(()=>api.validateSkyline({...api.demo(),segments:[[{azimuth:39,altitude:30}]]}));
});
test('opening repeatedly retains view without duplicate catalog calls; demo explicitly calculates real API positions',async()=>{
 const h=harness();try{
  h.open();await flush();h.q('[data-demo]').click();await flush();
  const sent=h.calls.find(c=>c.url.endsWith('positions'));assert.ok(sent);
  const payload=JSON.parse(sent.options.body);assert.equal(payload.at,'2026-10-08T00:00Z');assert.equal(payload.location.latitude,0);
  assert.match(h.q('[data-confidence]').textContent,/SYNTHETIC DEMO/);
  h.q('details').open=false;h.open();await flush();assert.equal(h.calls.filter(c=>c.url.endsWith('catalog')).length,1);
  h.q('[data-forward]').click();await flush();assert.equal(JSON.parse(h.calls.at(-1).options.body).at,'2026-10-08T01:00Z');
 }finally{h.close();}
});
test('location changes remove stale skyline and old positions; time edits invalidate pending positions',async()=>{
 let resolve;const h=harness(async(url)=>url.endsWith('catalog')?response(catalog):new Promise(r=>resolve=r));try{
  h.open();await flush();h.q('[data-demo]').click();await flush();
  h.input('[data-time]','2026-10-08T02:00');resolve(response(fixture));await flush();assert.equal(h.q('[data-results]').children.length,0);
  h.input('[data-lat]','40');assert.equal(h.q('.sky-silhouette'),null);assert.match(h.q('[data-confidence]').textContent,/Landscape unknown/);
 }finally{h.close();}
});
test('reset/account switch clears fields and suppresses pending home/catalog results',async()=>{
 let resolve;const h=harness(()=>new Promise(r=>resolve=r));try{
  h.open();await flush();h.w.PolarisSkyView.resetAll();resolve(response(catalog));await flush();
  assert.equal(h.q('[data-targets] input'),null);assert.equal(h.q('[data-lat]').value,'');assert.equal(h.q('details').open,false);
 }finally{h.close();}
});
test('one unfinished skyline point never becomes a filled obstruction; completing two points marks only that interval',async()=>{
 const h=harness();try{
  h.q('[data-start]').click();
  const click=(x,y)=>{h.q('svg').getBoundingClientRect=()=>({left:0,top:0,width:1560,height:390});h.q('svg').dispatchEvent(new h.w.MouseEvent('click',{clientX:x,clientY:y,bubbles:true}));};
  click(100,220);assert.equal(h.q('.sky-silhouette'),null);h.q('[data-finish]').click();assert.match(h.q('[data-status]').textContent,/at least two/);
  click(200,190);h.q('[data-finish]').click();assert.ok(h.q('.sky-silhouette'));assert.equal(h.q('[data-chart]').querySelectorAll('.sky-unknown').length,2);
 }finally{h.close();}
});
test('slow skyline import cannot overwrite clear or a newer sketch; duplicate fields rejected',async()=>{
 const h=harness();try{
  const input=h.q('[data-import]');let resolve;
  const imported=file=>{Object.defineProperty(input,'files',{configurable:true,value:[file]});input.dispatchEvent(new h.w.Event('change'));};
  imported({size:100,text:()=>new Promise(r=>resolve=r)});h.q('[data-clear]').click();resolve(JSON.stringify(api.demo()));await flush();assert.equal(h.q('.sky-silhouette'),null);
  const text=JSON.stringify(api.demo()).replace('"version":1','"version":2,"version":1');imported({size:text.length,text:async()=>text});await flush();assert.match(h.q('[data-status]').textContent,/unique/);
 }finally{h.close();}
});

test('conflicting north or shared endpoints cannot disagree with displayed silhouettes',()=>{
 assert.throws(()=>api.validateSkyline({...api.demo(),segments:[[{azimuth:0,altitude:10},{azimuth:20,altitude:10}],[{azimuth:340,altitude:60},{azimuth:360,altitude:60}]]}),/North/);
 assert.throws(()=>api.validateSkyline({...api.demo(),segments:[[{azimuth:0,altitude:10},{azimuth:20,altitude:10}],[{azimuth:20,altitude:60},{azimuth:50,altitude:60}]]}),/Shared/);
});
test('home response invalidates a skyline import started while home was loading',async()=>{
 let homeResolve,importResolve;
 const h=harness(async(url)=>url.endsWith('home')?new Promise(r=>homeResolve=r):response(catalog));try{
  h.q('[data-home]').click();await flush();
  const input=h.q('[data-import]');Object.defineProperty(input,'files',{value:[{size:100,text:()=>new Promise(r=>importResolve=r)}]});input.dispatchEvent(new h.w.Event('change'));
  homeResolve(response({latitude:40,longitude:50,elevation_meters:0,timezone_name:'UTC'}));await flush();
  importResolve(JSON.stringify(api.demo()));await flush();
  assert.equal(h.q('[data-lat]').value,'40');assert.equal(h.q('.sky-silhouette'),null);
 }finally{h.close();}
});

test('selected-time reasons distinguish floor, darkness, partial landscape and uncertainty',()=>{
 const conditions={minimum_imaging_altitude_degrees:20,darkness_state:'astronomical_darkness'};
 const target={...fixture.targets[0],imaging_altitude_state:'at_or_above_minimum'};
 const above=api.selectedTimeReason(target,api.demo(),conditions);
 assert.match(above,/Meets 20° imaging floor/);assert.match(above,/Astronomical darkness/);
 assert.match(above,/Above supplied skyline; overhead clearance unknown/);
 assert.match(above,/synthetic outline/);assert.match(above,/Weather not evaluated/);
 const blocked=api.selectedTimeReason({...target,altitude_degrees:10,imaging_altitude_state:'below_minimum'},
   {...api.demo(),source:'user_approximate'}, {...conditions,darkness_state:'not_astronomical_darkness'});
 assert.match(blocked,/Below 20° imaging floor/);assert.match(blocked,/Outside astronomical darkness/);
 assert.match(blocked,/At\/below supplied skyline/);assert.match(blocked,/approximate outline/);
 const unknown=api.selectedTimeReason({...target,azimuth_degrees:180},api.demo(),{});
 assert.match(unknown,/Skyline unknown/);assert.match(unknown,/Darkness unavailable/);
 const missing=api.selectedTimeReason({status:'unavailable'},api.empty(),conditions);
 assert.match(missing,/Position unavailable/);assert.match(missing,/Imaging altitude unavailable/);
});

test('inspector uses current skyline and labels selected instant and site; input changes invalidate facts',async()=>{
 const result={...fixture,location:{latitude:33,longitude:-112,elevation_meters:250,timezone_name:'America/Phoenix'},
   at_local:'2026-10-07T17:00:00-07:00',selected_time_conditions:{minimum_imaging_altitude_degrees:20,darkness_state:'not_astronomical_darkness'},
   targets:[{...fixture.targets[0],imaging_altitude_state:'at_or_above_minimum'}]};
 const h=harness(async url=>response(url.endsWith('catalog')?catalog:result));try{
  h.open();await flush();h.q('[data-demo]').click();await flush();
  assert.match(h.q('[data-time-label]').textContent,/2026-10-07T17:00:00-07:00.*America\/Phoenix.*33° latitude, -112° east, 250 m/);
  assert.match(h.q('[data-results]').textContent,/synthetic outline/);
  h.q('[data-clear]').click();assert.match(h.q('[data-results]').textContent,/Skyline unknown/);
  for(const [selector,value] of [['[data-zone]','UTC'],['[data-time]','2026-10-08T05:00'],['[data-lat]','34']]){
   h.input(selector,value);assert.equal(h.q('[data-results]').children.length,0);
   assert.match(h.q('[data-time-label]').textContent,/Inputs changed/);
   h.q('[data-calculate]').click();await flush();assert.equal(h.q('[data-results]').children.length,1);
  }
 }finally{h.close();}
});
