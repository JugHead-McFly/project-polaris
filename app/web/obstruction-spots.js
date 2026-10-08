/* Saved hosted setup spots. Selection stays in memory and is always explicit. */
(function(global) {
  "use strict";
  function mount(document, request, changed) {
    const root=document.getElementById('saved-obstruction-spots');
    const controls=document.getElementById('tonight-obstruction-controls');
    const select=document.getElementById('tonight-obstruction-spot');
    const status=document.getElementById('tonight-obstruction-status');
    const editor=document.querySelector('[data-obstruction-editor]');
    root.innerHTML='<h3>Saved setup spots</h3><p>Save a reviewed survey for one exact telescope position and height. Saving never enables it for Tonight. Photos are not measured automatically.</p><label>Saved survey <select data-saved><option value="">New spot</option></select></label><button type="button" data-load>Load into editor</button><label>Spot name <input data-name maxlength="80" placeholder="Patio tripod"></label><label>Survey source <select data-source><option value="">Choose source</option><option value="manual_measured">Manually measured at this spot</option><option value="synthetic">Synthetic example — testing only</option></select></label><label><input type="checkbox" data-reviewed> I reviewed the complete survey for this exact telescope position and height.</label><button type="button" data-save>Save reviewed survey</button><button type="button" data-delete>Delete saved survey</button><button type="button" data-reload>Reload saved spots</button><p data-message role="status" aria-live="polite"></p>';
    const q=s=>root.querySelector(s);
    let home=null, rows=[], selected=null, editing=null, epoch=0, version=0, editToken=0, loadedRevision=null;
    const controllers=new Set();
    const say=text=>{q('[data-message]').textContent=text;};
    const option=(value,label)=>{const node=document.createElement('option');node.value=value;node.textContent=label;return node;};
    const url=()=>`/observatories/${encodeURIComponent(home)}/obstruction-spots`;
    function render() {
      q('[data-saved]').replaceChildren(option('','New spot'),...rows.map(r=>option(r.id,r.name)));
      if(editing) q('[data-saved]').value=editing.id;
      select.replaceChildren(option('','Off — local obstructions not checked'),...rows.map(r=>{const o=option(r.id,`${r.name} · ${r.source_quality === 'manual_measured'?'user measured':r.source_quality === 'synthetic'?'synthetic':'unsupported source'}${r.available_for_tonight?'':' · review required'}`);o.disabled=!r.available_for_tonight;return o;}));
      if(selected) {
        const r=rows.find(r=>r.id===selected.id);
        const stale=!r || r.revision!==selected.revision || !r.available_for_tonight;
        if(stale) {
          const value=`stale:${selected.id}`;
          select.append(option(value,`${selected.name} · previous selection unavailable`));
          select.value=value;
          status.textContent='Selected survey changed or needs review. Re-select a reviewed spot or explicitly choose Off.';
        } else {
          select.value=selected.id;
          status.textContent=`Selected: ${selected.name}. Refresh plan to apply this reviewed survey.`;
        }
      } else status.textContent='Off — local obstructions are not checked.';
    }
    function reset() {
      epoch++;version++;editToken++;loadedRevision=null;controllers.forEach(c=>c.abort());controllers.clear();home=null;rows=[];selected=null;editing=null;
      q('[data-name]').value='';q('[data-source]').value='';q('[data-reviewed]').checked=false;
      root.hidden=true;controls.hidden=true;render();say('');
    }
    async function send(path, options={}) {
      const controller=new global.AbortController();controllers.add(controller);
      try {
        const response=await request(path,{...options,cache:'no-store',signal:controller.signal});
        const data=response.status===204?null:await response.json();
        if(!response.ok) throw Error(typeof data?.detail==='string'?data.detail:'Survey could not be saved. Check its complete geometry and confirmation.');
        return data;
      } finally {controllers.delete(controller);}
    }
    async function reload() {
      if(!home)return;
      const stamp=++epoch;
      try {const data=await send(url());if(stamp!==epoch)return;rows=data;if(selected){version++;changed();}render();say('Saved surveys loaded. Saving and loading do not enable Tonight.');}
      catch(error){if(stamp===epoch){rows=[];if(selected){version++;changed();}render();say(error.message);}}
    }
    async function setHome(value) {
      if(home!==value){reset();home=value;}
      root.hidden=!home;controls.hidden=!home;
      if(home)await reload();
    }
    select.addEventListener('change',()=>{
      const row=rows.find(r=>r.id===select.value);
      selected=select.value?(row?{id:row.id,revision:row.revision,name:row.name}:{id:select.value,revision:0,name:'Unavailable spot'}):null;
      version++;render();changed();
    });
    q('[data-saved]').addEventListener('change',()=>{
      editToken++;loadedRevision=null;
      editing=rows.find(r=>r.id===q('[data-saved]').value)||null;
      q('[data-name]').value=editing?.name||'';q('[data-source]').value=editing?.source_quality||'';q('[data-reviewed]').checked=false;
      say(editing?'Load its survey before editing or replacing it.':'New spot. Enter or load a complete survey in the editor.');
    });
    q('[data-load]').addEventListener('click',()=>{
      if(!editing)return say('Choose a saved survey first.');
      try {
        if(editor.obstructionEditor.loadDraft(editing.profile)) {editToken++;loadedRevision=`${editing.id}:${editing.revision}`;q('[data-reviewed]').checked=false;say('Survey loaded. Reconfirm coverage and source before saving.');}
      } catch(error) {say('Saved survey is invalid. Delete it and save a newly reviewed survey.');}
    });
    editor.addEventListener('input',()=>{editToken++;q('[data-reviewed]').checked=false;});
    editor.addEventListener('click',event=>{editToken++;q('[data-reviewed]').checked=false;if(event.target.dataset.action==='example')q('[data-source]').value='synthetic';});
    q('[data-source]').addEventListener('change',()=>{editToken++;q('[data-reviewed]').checked=false;});
    q('[data-name]').addEventListener('input',()=>{editToken++;});
    q('[data-reviewed]').addEventListener('change',()=>{editToken++;});
    q('[data-save]').addEventListener('click',async()=>{
      if(!home)return;
      const stamp=epoch, editStamp=editToken;
      try {
        if(editing && loadedRevision!==`${editing.id}:${editing.revision}`)throw Error("Load the selected saved survey before editing or replacing it.");
        const profile=editor.obstructionEditor.readDraft();
        if(!profile.complete_coverage || !q('[data-reviewed]').checked)throw Error('Confirm complete coverage and review this exact setup first.');
        const payload={name:q('[data-name]').value,profile,source_quality:q('[data-source]').value,reviewed:true,expected_revision:editing?.revision??null};
        const saved=await send(url()+(editing?`/${editing.id}`:''),{method:editing?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
        if(stamp!==epoch)return;
        if(editStamp!==editToken){await reload();return;}
        editing=saved;loadedRevision=`${saved.id}:${saved.revision}`;q('[data-name]').value=saved.name;q('[data-source]').value=saved.source_quality;q('[data-reviewed]').checked=false;version++;changed();await reload();say('Survey saved. Tonight selection was not enabled or updated.');
      } catch(error){if(stamp===epoch)say(error.message);}
    });
    q('[data-delete]').addEventListener('click',async()=>{
      if(!editing||!global.confirm('Delete this saved survey? Export a draft first to retain a copy.'))return;
      const stamp=epoch, editStamp=editToken;
      try {await send(`${url()}/${editing.id}?expected_revision=${editing.revision}`,{method:'DELETE'});if(stamp!==epoch)return;if(editStamp===editToken){editing=null;loadedRevision=null;}version++;changed();await reload();}
      catch(error){if(stamp===epoch)say(error.message);}
    });
    q('[data-reload]').addEventListener('click',reload);
    global.addEventListener('pageshow',event=>{if(event.persisted){reset();changed();}});
    reset();
    return {setHome,reset,get version(){return version;},params(){
      if(!selected)return '';
      const row=rows.find(r=>r.id===selected.id);
      if(!row||row.revision!==selected.revision||!row.available_for_tonight)throw Error('Selected survey changed or needs review. Re-select a reviewed spot or choose Off.');
      return `&obstruction_spot_id=${encodeURIComponent(selected.id)}&obstruction_revision=${selected.revision}`;
    },applied(data){status.textContent=data?.mode==='applied'?`Applied: ${data.name}, revision ${data.revision}. User-measured, advisory target-center clearance.`:'Off — local obstructions were not checked for this plan.';}};
  }
  global.PolarisObstructionSpots={mount};
})(window);
