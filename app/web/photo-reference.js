(function(global) {
  'use strict';
  const MAX_IMAGE=25*1024*1024, MAX_DRAFT=256*1024, MAX_POINTS=100;
  const kinds=['true_north','level','landmark','measured_elevation'];
  const sources=['unknown','original_photo','panorama','illustration'];
  const titles={true_north:'True north · azimuth 0°',level:'Known level · elevation 0°',landmark:'Landmark · angles unknown',measured_elevation:'Measured elevation · approximate'};
  const unknown=()=>({calibrated:false,projection:'unknown',angular_scale:'unknown',camera_pose:'unknown',coverage:'unknown'});
  function keys(value, allowed) {
    if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).some(k=>!allowed.includes(k)))throw Error('Unsupported draft fields.');
  }
  function validate(value) {
    keys(value,['format','version','image','source','notes','references','geometry']);
    if(value.format!=='polaris-photo-references'||![1,2].includes(value.version))throw Error('Unsupported reference draft version.');
    keys(value.image,['sha256','width','height']);
    if(typeof value.image.sha256!=='string'||!/^[a-f0-9]{64}$/.test(value.image.sha256)||![value.image.width,value.image.height].every(n=>Number.isInteger(n)&&n>0)||value.image.width*value.image.height>100000000)throw Error('Invalid image identity or dimensions.');
    if(!sources.includes(value.source)||typeof value.notes!=='string'||value.notes.length>300)throw Error('Invalid source or notes.');
    keys(value.geometry,Object.keys(unknown()));
    if(Object.entries(unknown()).some(([k,v])=>value.geometry[k]!==v))throw Error('This prototype cannot import a calibrated map or assumed angular scale.');
    if(!Array.isArray(value.references)||value.references.length>MAX_POINTS)throw Error('Use at most 100 reference points.');
    const ids=new Set();
    for(const p of value.references) {
      keys(p,p.kind==='measured_elevation'?['id','kind','x','y','label','measurement']:['id','kind','x','y','label']);
      if(p.kind==='measured_elevation'){
        if(value.version===1)throw Error('Measured elevations require draft version 2.');
        validateMeasurement(p.measurement);
      }
      if(!Number.isSafeInteger(p.id)||p.id<1||ids.has(p.id)||!kinds.includes(p.kind)||typeof p.label!=='string'||p.label.length>80||![p.x,p.y].every(n=>typeof n==='number'&&Number.isFinite(n)&&n>=0&&n<=1))throw Error('Invalid reference point.');
      ids.add(p.id);
    }
    return JSON.parse(JSON.stringify(value));
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
        if (current.names.has(name)) throw new Error("JSON reference fields must be unique; duplicate fields are not supported.");
        current.names.add(name); current.key = false;
      }
    }
  }
  function validateMeasurement(m) {
    keys(m,['elevation_degrees','provenance','approximate','absolute_accuracy','same_setup_confirmed']);
    if(typeof m.elevation_degrees!=='number'||!Number.isFinite(m.elevation_degrees)||m.elevation_degrees < -90||m.elevation_degrees > 90)throw Error('Enter a finite measured elevation from −90° to 90°.');
    if(typeof m.provenance!=='string'||!m.provenance.trim()||m.provenance.length>300)throw Error('Describe the measurement source and aiming notes (up to 300 characters).');
    if(m.approximate!==true||m.absolute_accuracy!=='unknown'||typeof m.same_setup_confirmed!=='boolean')throw Error('Measured references must remain approximate with unknown absolute accuracy and explicit setup status.');
    return m;
  }
  function referenceTitle(p) {return p.kind==='measured_elevation'?`${titles[p.kind]}: ${p.measurement.elevation_degrees ?? 'unset'}°; ${p.measurement.same_setup_confirmed?'same setup confirmed by user':'setup unconfirmed'}`:titles[p.kind];}
  function summary(points) {
    const north=points.some(p=>p.kind==='true_north'), level=points.some(p=>p.kind==='level');
    return `${north?'North reference marked':'North unknown'} · ${level?'Level reference marked':'Level unknown'} · ${points.filter(p=>p.kind==='measured_elevation').length} approximate measured elevation(s). Not calibrated: scale, projection, camera pose and unseen coverage remain unknown.`;
  }
  function mount(document) {
    const byId=id=>document.getElementById(id), dialog=byId('workspace');
    let image=null, points=[], source='unknown', notes='', mode='true_north', pending=null;
    let activeURL=null, dirty=false, generation=0, nextId=1, dragging=null;
    const pendingURLs=new Set();
    const say=text=>{byId('reference-status').textContent=text;};
    const markDirty=()=>{dirty=true;invalidatePending();};
    const identity=()=>({sha256:image.sha256,width:image.width,height:image.height});
    const snapshot=()=>validate({format:'polaris-photo-references',version:2,image:identity(),source,notes,references:points,geometry:unknown()});
    const sameImage=(a,b)=>a.sha256===b.sha256&&a.width===b.width&&a.height===b.height;
    function resetMeasurementEntry(){byId('measured-degrees').value='';byId('measurement-provenance').value='';byId('measurement-same-setup').checked=false;}
    function release(url) {if(url)global.URL.revokeObjectURL(url);pendingURLs.delete(url);}
    function invalidatePending() {generation++;for(const url of [...pendingURLs])release(url);}
    function sync() {
      byId('source-kind').value=source;byId('setup-notes').value=notes;
      byId('source-kind').disabled=!image;byId('setup-notes').disabled=!image;
      byId('geometry-status').textContent=summary(points);
      byId('outside-status').textContent=image?`${points.length} reference(s) in this tab. Not calibrated.`:pending?'Draft waiting for its exact original image.':'No image loaded.';
      byId('photo-placeholder').hidden=Boolean(image);byId('reference-photo').hidden=!image;
      byId('add-center').disabled=!image;byId('export-draft').disabled=!image;
      byId('marker-layer').replaceChildren();byId('reference-list').replaceChildren();
      for(const p of points) {
        const button=document.createElement('button');button.type='button';button.className='marker';button.dataset.id=p.id;button.dataset.kind=p.kind;
        button.style.left=`${p.x*100}%`;button.style.top=`${p.y*100}%`;button.textContent=p.id;
        button.setAttribute('aria-label',`${referenceTitle(p)}: ${p.label||'unlabeled'}. Use arrow keys to adjust.`);
        button.addEventListener('click',event=>event.stopPropagation());
        button.addEventListener('pointerdown',event=>{event.stopPropagation();dragging={id:p.id,pointer:event.pointerId,element:button};button.setPointerCapture?.(event.pointerId);});
        button.addEventListener('pointermove',event=>{if(dragging?.id!==p.id)return;const xy=position(event);if(!xy)return;p.x=xy.x;p.y=xy.y;button.style.left=`${p.x*100}%`;button.style.top=`${p.y*100}%`;markDirty();});
        const finish=()=>{if(dragging?.id===p.id){dragging=null;sync();byId('marker-layer').querySelector(`[data-id="${p.id}"]`)?.focus();}};
        button.addEventListener('pointerup',finish);button.addEventListener('pointercancel',finish);
        button.addEventListener('keydown',event=>{
          const movement={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];if(!movement)return;
          event.preventDefault();const step=event.shiftKey ? 0.02 : 0.005;p.x=Math.max(0,Math.min(1,p.x+movement[0]*step));p.y=Math.max(0,Math.min(1,p.y+movement[1]*step));markDirty();sync();byId('marker-layer').querySelector(`[data-id="${p.id}"]`)?.focus();
        });
        byId('marker-layer').append(button);
        const li=document.createElement('li'), label=document.createElement('label'), input=document.createElement('input'), remove=document.createElement('button');
        label.textContent=`${p.id}. ${referenceTitle(p)}`;input.value=p.label;input.maxLength=80;input.setAttribute('aria-label',`Label for reference ${p.id}`);
        input.addEventListener('input',()=>{p.label=input.value;markDirty();button.setAttribute('aria-label',`${referenceTitle(p)}: ${p.label||'unlabeled'}. Use arrow keys to adjust.`);});
        label.append(input);
        if(p.kind==='measured_elevation') {
          const refreshTitle=()=>{label.firstChild.nodeValue=`${p.id}. ${referenceTitle(p)}`;button.setAttribute('aria-label',referenceTitle(p));};
          const box=document.createElement('fieldset'),legend=document.createElement('legend');legend.textContent='Approximate measurement · absolute accuracy unknown';box.append(legend);
          const field=(text,control)=>{const label=document.createElement('label');label.textContent=text;label.append(control);box.append(label);};
          const angle=document.createElement('input');angle.type='number';angle.min='-90';angle.max='90';angle.step='any';angle.value=p.measurement.elevation_degrees??'';angle.setAttribute('aria-label',`Elevation for reference ${p.id}`);
          const provenance=document.createElement('textarea');provenance.maxLength=300;provenance.value=p.measurement.provenance;provenance.setAttribute('aria-label',`Measurement provenance for reference ${p.id}`);
          const setup=document.createElement('input');setup.type='checkbox';setup.checked=p.measurement.same_setup_confirmed;
          angle.addEventListener('input',()=>{p.measurement.elevation_degrees=angle.value.trim()===''?null:Number(angle.value);markDirty();refreshTitle();});
          provenance.addEventListener('input',()=>{p.measurement.provenance=provenance.value;markDirty();});
          setup.addEventListener('change',()=>{p.measurement.same_setup_confirmed=setup.checked;markDirty();refreshTitle();});
          field('Elevation above level (°)',angle);field('Measurement source, readings and aiming notes',provenance);field('Same telescope position and height confirmed',setup);li.append(box);
        }
        remove.type='button';remove.textContent='Remove reference';remove.setAttribute('aria-label',`Remove reference ${p.id}`);remove.addEventListener('click',()=>{points=points.filter(q=>q.id!==p.id);markDirty();sync();byId('add-center').focus();});li.append(label,remove);byId('reference-list').append(li);
      }
    }
    function position(event) {const r=byId('reference-photo').getBoundingClientRect();if(!r.width||!r.height)return null;return {x:Math.max(0,Math.min(1,(event.clientX-r.left)/r.width)),y:Math.max(0,Math.min(1,(event.clientY-r.top)/r.height))};}
    function add(x,y) {
      if(!image)return;if(points.length>=MAX_POINTS)return say('Use at most 100 reference points.');
      const point={id:nextId,kind:mode,x,y,label:''};
      if(mode==='measured_elevation') {
        try {
          const raw=byId('measured-degrees').value;
          point.measurement=validateMeasurement({elevation_degrees:raw.trim()===''?null:Number(raw),provenance:byId('measurement-provenance').value,approximate:true,absolute_accuracy:'unknown',same_setup_confirmed:byId('measurement-same-setup').checked});
        } catch(error){say(error.message);return;}
      }
      while(points.some(p=>p.id===nextId))nextId++;point.id=nextId++;points.push(point);markDirty();sync();say('Reference added. Name the landmark and review its position. This does not calibrate the image.');
    }
    function decode(url) {return new Promise((resolve,reject)=>{const img=new global.Image();img.onload=()=>resolve({width:img.naturalWidth,height:img.naturalHeight});img.onerror=()=>reject(Error('Image could not be decoded. Use JPEG, PNG or WebP.'));img.src=url;});}
    async function load(file) {
      if(!file)return;
      invalidatePending();const stamp=generation;
      let url=null;
      try {
        if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>MAX_IMAGE||file.size<1)throw Error('Choose JPEG, PNG or WebP up to 25 MiB. HEIC and SVG are not supported here.');
        if(!global.crypto?.subtle)throw Error('This browser cannot fingerprint the original image. Open the workspace on localhost or HTTPS.');
        const bytes=await file.arrayBuffer();if(stamp!==generation)return;
        const digest=await global.crypto.subtle.digest('SHA-256',bytes);if(stamp!==generation)return;
        const sha256=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
        url=global.URL.createObjectURL(file);pendingURLs.add(url);
        const dimensions=await decode(url);if(stamp!==generation){release(url);return;}
        if(!dimensions.width||!dimensions.height||dimensions.width*dimensions.height>100000000)throw Error('Image dimensions are unsupported (limit 100 megapixels).');
        const candidate={sha256,...dimensions};
        if(pending&&!sameImage(candidate,pending.image))throw Error('This is not the exact image for the imported draft. Choose the original file or clear the draft first.');
        const repeated=image&&sameImage(image,candidate);
        if(!pending&&!repeated&&image&&dirty&&!global.confirm('Replace this image and its reference notes? Export first to keep the draft.')){release(url);return;}
        if(!repeated || pending)resetMeasurementEntry();
        if(pending){points=pending.references;source=pending.source;notes=pending.notes;pending=null;dirty=false;}
        else if(!repeated){points=[];source='unknown';notes='';dirty=false;}
        release(activeURL);activeURL=url;pendingURLs.delete(url);image=candidate;dragging=null;nextId=1;
        byId('reference-photo').src=activeURL;sync();say(repeated?'Same image loaded; references retained.':'Image ready. Mark true north only where you know its visible landmark.');
      } catch(error){release(url);if(stamp===generation)say(error.message);}
    }
    async function importDraft(file) {
      if(!file)return;
      invalidatePending();const stamp=generation;
      try {
        if(file.size>MAX_DRAFT)throw Error('Reference draft is limited to 256 KiB.');
        const text=await file.text();if(stamp!==generation)return;
        if(new TextEncoder().encode(text).length>MAX_DRAFT)throw Error('Reference draft is too large.');
        const parsed=JSON.parse(text);rejectDuplicateKeys(text);
        const draft=validate(parsed);
        if(dirty&&!global.confirm('Replace the reference notes? Export the current draft first.'))return;
        resetMeasurementEntry();
        if(image&&sameImage(image,draft.image)){points=draft.references;source=draft.source;notes=draft.notes;pending=null;dirty=false;nextId=1;sync();say('References restored on the matching image. Still not calibrated.');}
        else {release(activeURL);activeURL=null;image=null;points=[];pending=draft;source=draft.source;notes=draft.notes;dirty=false;byId('reference-photo').removeAttribute('src');sync();say('Choose the exact original image to restore these references. No points are applied to a different image.');}
      } catch(error){if(stamp===generation)say(error.message||'Invalid reference draft.');}
    }
    function clear(force=false) {
      if(!force&&(image||pending)&&!global.confirm('Clear this image and reference draft? Export first to keep your notes.'))return;
      invalidatePending();release(activeURL);activeURL=null;image=null;pending=null;points=[];source='unknown';notes='';dirty=false;dragging=null;nextId=1;
      byId('reference-photo').removeAttribute('src');byId('photo-file').value='';byId('draft-file').value='';resetMeasurementEntry();sync();say('Draft cleared. No image or references retained in this tab.');
    }
    byId('open-workspace').addEventListener('click',()=>{dialog.showModal();});
    byId('close-workspace').addEventListener('click',()=>dialog.close());
    byId('photo-file').addEventListener('change',event=>{void load(event.target.files[0]);event.target.value='';});
    byId('draft-file').addEventListener('change',event=>{void importDraft(event.target.files[0]);event.target.value='';});
    byId('clear-draft').addEventListener('click',()=>clear());
    byId('reference-photo').addEventListener('click',event=>{const xy=position(event);if(xy)add(xy.x,xy.y);});
    byId('add-center').addEventListener('click',()=>add(.5,.5));
    document.querySelectorAll('[data-kind]').forEach(button=>button.addEventListener('click',()=>{
      mode=button.dataset.kind;byId('measurement-entry').hidden=mode!=='measured_elevation';document.querySelectorAll('.modes [data-kind]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
      byId('mode-help').textContent=mode==='true_north'?'Tap the visible landmark that you know lies toward true north. Its elevation is unknown.':mode==='level'?'Mark a point you independently know is level with the telescope. Its direction is unknown; a roofline or photo center is not automatically level.':mode==='measured_elevation'?'Enter the measured elevation and its source, then mark the exact point you aimed at. North remains separate; accuracy and angular scale are unknown.':'Mark a landmark and describe it. No angles are inferred.';
    }));
    ['measured-degrees','measurement-provenance','measurement-same-setup'].forEach(id=>byId(id).addEventListener('input',markDirty));
    byId('source-kind').addEventListener('change',event=>{source=event.target.value;markDirty();});
    byId('setup-notes').addEventListener('input',event=>{notes=event.target.value;markDirty();});
    byId('export-draft').addEventListener('click',()=>{
      if(!image)return;
      let draft;try{draft=snapshot();}catch(error){say(error.message);return;}
      const url=global.URL.createObjectURL(new Blob([JSON.stringify(draft,null,2)],{type:'application/json'}));
      const a=document.createElement('a');a.href=url;a.download='polaris-photo-references.json';document.body.append(a);a.click();a.remove();global.setTimeout(()=>release(url),1000);dirty=false;say('Reference draft downloaded without the image. Keep the exact original image to restore it.');
    });
    global.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
    global.addEventListener('pageshow',event=>{if(event.persisted)clear(true);});
    sync();return {load,importDraft,clear,snapshot:()=>image?snapshot():null};
  }
  const api={validate,summary,mount};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else {global.PolarisPhotoReferences=api;api.workspace=mount(global.document);}
})(typeof window!=='undefined'?window:globalThis);
