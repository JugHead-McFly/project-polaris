/* Downloads only the currently accepted Tonight response; never recalculates. */
(function (global) {
  'use strict';
  let snapshot = null, revision = 0, root = null;
  const find = name => root?.querySelector(`[data-field-${name}]`);
  function clear() {
    revision++; snapshot = null;
    if (!root) return;
    find('text').disabled = true; find('calendar').disabled = true;
    find('status').textContent = 'Refresh the plan to download its current scheduled blocks.';
  }
  function set(value) {
    clear();
    if (!value?.text) {
      if (root) find('status').textContent = value?.unavailable_reason || 'Portable plan unavailable.';
      return;
    }
    snapshot = {...value};
    if (!root) return;
    find('text').disabled = false; find('calendar').disabled = !snapshot.calendar;
    find('status').textContent = `Snapshot ${snapshot.generated_at}. Downloads do not update automatically. Calendar times include setup; no telescope or calendar is controlled.`;
  }
  function download(kind) {
    if (!snapshot || !snapshot[kind]) return;
    const isCalendar = kind === 'calendar';
    const blob = new Blob([snapshot[kind]], {type: isCalendar ? 'text/calendar;charset=utf-8' : 'text/plain;charset=utf-8'});
    const url = global.URL.createObjectURL(blob), link = root.ownerDocument.createElement('a');
    link.href = url;
    link.download = `polaris-plan-${snapshot.night}.${isCalendar ? 'ics' : 'txt'}`;
    root.ownerDocument.body.append(link); link.click(); link.remove();
    global.setTimeout(() => global.URL.revokeObjectURL(url), 1000);
  }
  function mount(document) {
    root = document.querySelector('[data-field-plan]');
    if (!root) return;
    find('text').addEventListener('click', () => download('text'));
    find('calendar').addEventListener('click', () => download('calendar'));
    clear();
  }
  global.PolarisFieldPlan = {mount, clear, set, get version() {return revision;}};
  global.addEventListener('pageshow', event => {if (event.persisted) clear();});
})(window);
