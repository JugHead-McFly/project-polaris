(function(global){
'use strict';
const instances=[];
const NS='http://www.w3.org/2000/svg';
const W=1560,H=390,L=60,B=310,SX=4,SY=3;
const empty=()=>({format:'polaris-skyline',version:1,source:'unknown',notes:'',segments:[]});
const demo=()=>({format:'polaris-skyline',version:1,source:'synthetic',notes:'Synthetic partial skyline, not a real observing site.',segments:[[{azimuth:0,altitude:20},{azimuth:60,altitude:10}],[{azimuth:300,altitude:10},{azimuth:360,altitude:20}]]});
function keys(v,allowed){if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).some(k=>!allowed.includes(k)))throw Error('Unsupported skyline fields.');}
function validateSkyline(v){
 keys(v,['format','version','source','notes','segments']);
 if(v.format!=='polaris-skyline'||v.version!==1||!['unknown','synthetic','user_approximate','user_measured'].includes(v.source)||typeof v.notes!=='string'||v.notes.length>300||!Array.isArray(v.segments)||v.segments.length>64)throw Error('Invalid skyline format or source.');
 let last=-1,lastHeight=null,count=0;
 for(const segment of v.segments){
  if(!Array.isArray(segment)||segment.length<2)throw Error('Each finished segment needs at least two direction/height points.');
  let previous=-1;
  for(const p of segment){keys(p,['azimuth','altitude']);if(typeof p.azimuth!=='number'||!Number.isFinite(p.azimuth)||p.azimuth<0||p.azimuth>360||p.azimuth<=previous||typeof p.altitude!=='number'||!Number.isFinite(p.altitude)||p.altitude<0||p.altitude>90)throw Error('Use ascending directions 0–360° and heights 0–90°. Split north-crossing outlines at 360°/0°.');previous=p.azimuth;count++;}
  if(segment[0].azimuth===last&&Math.abs(segment[0].altitude-lastHeight)>1e-9)throw Error('Shared directions must have the same skyline height.');
  if(segment[0].azimuth<last)throw Error('Skyline segments must be ordered and must not overlap.');
  last=segment.at(-1).azimuth;lastHeight=segment.at(-1).altitude;
 }
 if(v.segments.length&&v.segments[0][0].azimuth===0&&last===360&&Math.abs(v.segments[0][0].altitude-lastHeight)>1e-9)throw Error('North at 0° and 360° is the same direction; use the same skyline height.');
 if(count>720||v.source==='unknown'&&v.segments.length)throw Error('Unknown sky cannot contain a silhouette; at most 720 points are allowed.');
 return JSON.parse(JSON.stringify(v));
}
  function rejectDuplicateKeys(text) {
    // JSON.parse has already checked grammar. Scan structure iteratively to retain
    // duplicate keys that JSON.parse would otherwise silently discard (last wins).
    const stack = [];
    const tokens = text.match(/"(?:\\.|[^"\\])*"|[{}\[\]:,]|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null/g) || [];
    for (const token of tokens) {
      const current = stack[stack.length - 1];
      if (token === "{") stack.push({object: true, key: true, names: new Set()});
      else if (token === "[") stack.push({object: false});
      else if (token === "}" || token === "]") stack.pop();
      else if (token === "," && current?.object) current.key = true;
      else if (token === ":" && current?.object) current.key = false;
      else if (token.startsWith('"') && current?.object && current.key) {
        const name = JSON.parse(token);
        if (current.names.has(name)) throw new Error("JSON profile fields must be unique; duplicate fields are not supported.");
        current.names.add(name); current.key = false;
      }
    }
  }
function skylineHeight(skyline,azimuth){
 const az=((azimuth%360)+360)%360;
 const heights=[];
 for(const segment of skyline.segments)for(let i=1;i<segment.length;i++){
  const a=segment[i-1],b=segment[i];
  for(const q of az===0?[0,360]:[az])if(q>=a.azimuth&&q<=b.azimuth)heights.push(a.altitude+(b.altitude-a.altitude)*(q-a.azimuth)/(b.azimuth-a.azimuth));
 }
 return heights.length?Math.max(...heights):null;
}
function targetState(target,skyline){
 if(target.status==='unavailable')return 'Position unavailable';
 if(target.altitude_degrees<0)return 'Below geometric horizon';
 const height=skylineHeight(skyline,target.azimuth_degrees);
 return height===null?'Skyline unknown':target.altitude_degrees<=height?'At/below supplied skyline':'Above supplied skyline; overhead clearance unknown';
}
function draw(container,data,skyline,active=[]){
 const doc=container.ownerDocument,svg=doc.createElementNS(NS,'svg');svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('role','img');svg.setAttribute('aria-label','360 degree azimuth and elevation chart, 10 degree grid. North is the same direction at both ends.');
 const add=(tag,attrs,text)=>{const el=doc.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);if(text!==undefined)el.textContent=text;svg.append(el);return el;};
 const x=az=>L+az*SX,y=alt=>B-alt*SY;
 // Gaps are explicitly unsurveyed; no interpolation joins separate segments.
 let end=0;
 for(const seg of skyline.segments){if(seg[0].azimuth>end)add('rect',{x:x(end),y:y(90),width:(seg[0].azimuth-end)*SX,height:90*SY,class:'sky-unknown'});end=seg.at(-1).azimuth;}
 if(end<360)add('rect',{x:x(end),y:y(90),width:(360-end)*SX,height:90*SY,class:'sky-unknown'});
 for(const seg of skyline.segments)add('polygon',{points:`${x(seg[0].azimuth)},${y(0)} ${seg.map(p=>`${x(p.azimuth)},${y(p.altitude)}`).join(' ')} ${x(seg.at(-1).azimuth)},${y(0)}`,class:'sky-silhouette'});
 for(let az=0;az<=360;az+=10){add('line',{x1:x(az),x2:x(az),y1:y(90),y2:y(0),class:'sky-grid'});add('text',{x:x(az),y:B+23,'text-anchor':'middle',class:'sky-tick'},String(az));}
 for(let alt=0;alt<=90;alt+=10){add('line',{x1:x(0),x2:x(360),y1:y(alt),y2:y(alt),class:'sky-grid'});add('text',{x:L-10,y:y(alt)+4,'text-anchor':'end',class:'sky-tick'},`${alt}°`);}
 for(const [az,label] of [[0,'N / 0°'],[90,'E'],[180,'S'],[270,'W'],[360,'N / 360°']])add('text',{x:x(az),y:B+53,'text-anchor':'middle',class:'sky-cardinal'},label);
 for(const [index,t] of (data?.targets||[]).entries()){
  if(t.status==='unavailable'||t.altitude_degrees<0)continue;
  const xx=x(t.azimuth_degrees),yy=y(t.altitude_degrees),blocked=targetState(t,skyline).startsWith('At/below');
  add('circle',{cx:xx,cy:yy,r:5,class:blocked?'sky-target sky-blocked':'sky-target','data-target':t.id});
  add('text',{x:xx+(t.azimuth_degrees>345?-9:9),y:Math.max(18,yy-9-(index%2)*12),'text-anchor':t.azimuth_degrees>345?'end':'start',class:'sky-target-label'},t.id);
 }
 if(active.length){add('polyline',{points:active.map(p=>`${x(p.azimuth)},${y(p.altitude)}`).join(' '),class:'sky-draft-line'});for(const p of active)add('circle',{cx:x(p.azimuth),cy:y(p.altitude),r:5,class:'sky-draft-point'});}
 container.replaceChildren(svg);return svg;
}
function markup(i){return `<details class="sky-view"><summary>Sky view <span>Read-only prototype</span></summary><div class="sky-body"><h2>Your sky, by direction and time</h2><p>A 10° azimuth/elevation diagram, not a calibrated photograph. Calculated target centers and user-supplied silhouettes do not change Tonight. No atmospheric refraction is applied; available Earth-orientation data can limit position precision.</p><div class="sky-fields"><label>Latitude (°)<input data-lat type="number" min="-90" max="90" step="any"></label><label>Longitude east (°)<input data-lon type="number" min="-180" max="180" step="any"></label><label>Elevation (m)<input data-height type="number" min="-500" max="9000" step="any" value="0"></label><label>Display timezone (IANA)<input data-zone value="UTC" maxlength="64"></label><label>Instant (UTC)<input data-time type="datetime-local" step="60"></label></div><div class="sky-actions"><button type="button" data-home>Use observing home</button><button type="button" data-demo>Load synthetic demo</button><button type="button" data-now>Now (UTC)</button><button type="button" data-back>−1 hour</button><button type="button" data-forward>+1 hour</button><button type="button" data-calculate>Calculate sky</button></div><fieldset><legend>Selected catalog targets (up to 12)</legend><div data-targets class="sky-target-picker">Open this panel to load the catalog.</div></fieldset><p data-time-label>Enter an explicit location and UTC time.</p><p data-status role="status" aria-live="polite"></p><div data-chart class="sky-chart" tabindex="0" role="region" aria-label="Scrollable horizon chart; use the horizontal scrollbar or Shift and mouse wheel"></div><p class="sky-legend">Black: supplied skyline · Shaded columns: unsurveyed directions · Orange targets: at/below supplied skyline. North wraps from 360° to 0°. Scroll horizontally to see every direction.</p><p data-confidence>Landscape unknown. No photo-derived silhouette is loaded.</p><details><summary>Edit display-only skyline</summary><p>Sketch approximately on the angular chart or import known angular points. A lone point cannot define a skyline. Finish each continuous segment separately; gaps remain unknown. Split a north-crossing outline at 360°/0°. Overhead roofs are not modeled here.</p><div class="sky-actions"><button type="button" data-start>Start approximate segment</button><button type="button" data-finish>Finish segment</button><button type="button" data-undo>Undo point</button><button type="button" data-clear>Clear skyline</button><label>Import skyline JSON<input data-import type="file" accept=".json,application/json"></label><button type="button" data-export>Export skyline</button></div><p data-sketch-status>No segment being drawn.</p></details><ul data-results></ul></div></details>`;}
function mount(root,request,index){
 root.innerHTML=markup(index);const q=s=>root.querySelector(s),doc=root.ownerDocument;
 let skyline=empty(),active=[],sketch=false,data=null,loaded=false,epoch=0,controller=null,catalogEpoch=0,catalogController=null,landscapeEpoch=0;
 const say=text=>{q('[data-status]').textContent=text;};
 function render(){draw(q('[data-chart]'),data,skyline,active);q('[data-confidence]').textContent=skyline.source==='unknown'?'Landscape unknown. No photo-derived silhouette is loaded.':`${skyline.source==='synthetic'?'SYNTHETIC DEMO — not your landscape':skyline.source==='user_measured'?'User-declared measurements; accuracy unverified':'Approximate hand-supplied skyline; accuracy unknown'}. ${skyline.notes} Gaps and overhead clearance remain unknown.`;
  q('[data-results]').replaceChildren();for(const t of data?.targets||[]){const li=doc.createElement('li');li.textContent=`${t.id} · ${t.name}: ${t.status==='unavailable'?'position unavailable':`${t.azimuth_degrees.toFixed(1)}° az, ${t.altitude_degrees.toFixed(1)}° elevation — ${targetState(t,skyline)}`}`;q('[data-results]').append(li);}
  q('[data-sketch-status]').textContent=sketch?`Unfinished segment: ${active.length} point(s). Click the chart in increasing azimuth order; finish to apply it to this view.`:'No segment being drawn.';
 }
 function invalidate(){epoch++;controller?.abort();controller=null;data=null;q('[data-time-label]').textContent='Inputs changed. Calculate sky for the displayed location and time.';render();}
 async function json(url,options={}){const response=await request(url,{...options,cache:'no-store'});const result=await response.json();if(!response.ok)throw Error(response.status===401?'Sign in to calculate your sky.':typeof result.detail==='string'?result.detail:'Check location, UTC time, timezone and selected targets.');return result;}
 async function loadCatalog(){if(loaded)return;const stamp=++catalogEpoch;catalogController?.abort();catalogController=new global.AbortController();try{const rows=await json('/sky-view/catalog',{signal:catalogController.signal});if(stamp!==catalogEpoch)return;q('[data-targets]').replaceChildren();for(const row of rows){const label=doc.createElement('label'),input=doc.createElement('input');input.type='checkbox';input.value=row.id;input.checked=['M31','M57','M13'].includes(row.id);input.addEventListener('change',invalidate);label.append(input,doc.createTextNode(`${row.id} · ${row.name}`));q('[data-targets]').append(label);}loaded=true;}catch(e){if(stamp===catalogEpoch)say(e.message);}}
 function number(selector){const raw=q(selector).value;if(raw.trim()===''||!Number.isFinite(Number(raw)))throw Error('Enter latitude, longitude and elevation explicitly.');return Number(raw);}
 async function calculate(){invalidate();const stamp=epoch;controller=new global.AbortController();try{await loadCatalog();if(stamp!==epoch)return;const at=q('[data-time]').value;if(!at)throw Error('Choose a UTC date and time.');const result=await json('/sky-view/positions',{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({at:at+'Z',location:{latitude:number('[data-lat]'),longitude:number('[data-lon]'),elevation_meters:number('[data-height]'),timezone_name:q('[data-zone]').value.trim()},targets:[...q('[data-targets]').querySelectorAll('input:checked')].map(e=>e.value)})});if(stamp!==epoch)return;data=result;q('[data-time-label]').textContent=`UTC ${result.at_utc} · Local ${result.at_local} (${result.location.timezone_name})`;say('Calculated positions. This is not a plan, full-frame clearance or a photo calibration.');render();}catch(e){if(stamp===epoch)say(e.name==='AbortError'?'Calculation cancelled.':e.message);}}
 function reset(){landscapeEpoch++;invalidate();catalogEpoch++;catalogController?.abort();loaded=false;q('[data-targets]').textContent='Open this panel to load the catalog.';skyline=empty();active=[];sketch=false;q('[data-lat]').value='';q('[data-lon]').value='';q('[data-height]').value='0';q('[data-zone]').value='UTC';q('[data-time]').value='';q('[data-import]').value='';q('details').open=false;say('Enter a location, or choose a clearly labeled synthetic demo.');render();}
 q('details').addEventListener('toggle',()=>{if(q('details').open)void loadCatalog();});
 root.querySelectorAll('.sky-fields input').forEach(el=>el.addEventListener('input',()=>{if(el.matches('[data-lat],[data-lon],[data-height]')){landscapeEpoch++;skyline=empty();active=[];sketch=false;}invalidate();}));
 q('[data-calculate]').addEventListener('click',calculate);
 q('[data-home]').addEventListener('click',async()=>{landscapeEpoch++;invalidate();const stamp=epoch;controller=new global.AbortController();try{const home=await json('/sky-view/home',{signal:controller.signal});if(stamp!==epoch)return;landscapeEpoch++;q('[data-lat]').value=home.latitude;q('[data-lon]').value=home.longitude;q('[data-height]').value=home.elevation_meters;q('[data-zone]').value=home.timezone_name;skyline=empty();active=[];sketch=false;render();say('Home location loaded; no skyline inferred. Choose UTC time and calculate.');}catch(e){if(stamp===epoch)say(e.message);}});
 q('[data-now]').addEventListener('click',()=>{q('[data-time]').value=new Date().toISOString().slice(0,16);invalidate();});
 for(const [selector,hours] of [['[data-back]',-1],['[data-forward]',1]])q(selector).addEventListener('click',()=>{const at=new Date(q('[data-time]').value+'Z');if(!Number.isFinite(at.getTime()))return say('Choose a UTC time first.');q('[data-time]').value=new Date(at.getTime()+hours*3600000).toISOString().slice(0,16);void calculate();});
 q('[data-demo]').addEventListener('click',()=>{landscapeEpoch++;q('[data-lat]').value='0';q('[data-lon]').value='0';q('[data-height]').value='0';q('[data-zone]').value='UTC';q('[data-time]').value='2026-10-08T00:00';skyline=demo();active=[];sketch=false;void calculate();});
 q('[data-start]').addEventListener('click',()=>{landscapeEpoch++;if(skyline.source!=='user_approximate'&&skyline.segments.length&&!global.confirm('Replace this example/imported skyline with an approximate sketch?'))return;if(skyline.source!=='user_approximate')skyline={...empty(),source:'user_approximate',notes:'Hand-sketched on angular axes, not traced from a calibrated photo.'};active=[];sketch=true;render();});
 q('[data-chart]').addEventListener('click',event=>{if(!sketch)return;const svg=q('svg'),r=svg.getBoundingClientRect();if(!r.width||!r.height)return;const xx=(event.clientX-r.left)*W/r.width,yy=(event.clientY-r.top)*H/r.height;const az=(xx-L)/SX,alt=(B-yy)/SY;if(az<0||az>360||alt<0||alt>90)return;if(active.length&&az<=active.at(-1).azimuth)return say('Add points clockwise. Split north-crossing outlines into two segments.');landscapeEpoch++;active.push({azimuth:az,altitude:alt});render();});
 q('[data-finish]').addEventListener('click',()=>{landscapeEpoch++;try{skyline=validateSkyline({...skyline,segments:[...skyline.segments,active].sort((a,b)=>(a[0]?.azimuth??0)-(b[0]?.azimuth??0))});active=[];sketch=false;render();say('Approximate segment added to this display only.');}catch(e){say(e.message);}});
 q('[data-undo]').addEventListener('click',()=>{landscapeEpoch++;active.pop();render();});q('[data-clear]').addEventListener('click',()=>{landscapeEpoch++;skyline=empty();active=[];sketch=false;render();});
 q('[data-import]').addEventListener('change',async event=>{const file=event.target.files[0];event.target.value='';if(!file)return;const stamp=epoch,landscapeStamp=++landscapeEpoch;try{if(file.size>128*1024)throw Error('Skyline JSON is limited to 128 KiB.');const text=await file.text();if(stamp!==epoch||landscapeStamp!==landscapeEpoch)return;if(new TextEncoder().encode(text).length>128*1024)throw Error('Skyline JSON is too large.');const parsed=JSON.parse(text);rejectDuplicateKeys(text);const candidate=validateSkyline(parsed);skyline=candidate;active=[];sketch=false;render();say('Skyline imported for this display only; source claims are not verified.');}catch(e){if(stamp===epoch&&landscapeStamp===landscapeEpoch)say(e.message);}});
 q('[data-export]').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(validateSkyline(skyline),null,2)],{type:'application/json'}),url=global.URL.createObjectURL(blob),link=doc.createElement('a');link.href=url;link.download='polaris-skyline.json';doc.body.append(link);link.click();link.remove();global.setTimeout(()=>global.URL.revokeObjectURL(url),1000);});
 reset();return {reset};
}
const api={validateSkyline,skylineHeight,targetState,draw,demo,empty,mountAll(root,request){root.querySelectorAll('[data-sky-view]').forEach((el,i)=>instances.push(mount(el,request,i)));},resetAll(){instances.forEach(i=>i.reset());}};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else {global.PolarisSkyView=api;global.addEventListener('pageshow',event=>{if(event.persisted)api.resetAll();});}
})(typeof window!=='undefined'?window:globalThis);
