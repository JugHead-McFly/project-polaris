/* Stateless manual-survey editor. Geometry decisions come from Polaris's backend. */
(function (global) {
  "use strict";
  const MAX_BYTES = 128 * 1024;
  const FORMAT = "polaris-obstruction-profile";
  const instances = [];
  function keys(value, allowed, label) {
    if (!value || typeof value !== "object" || Array.isArray(value)
        || Object.keys(value).some(key => !allowed.includes(key))
        || allowed.some(key => !Object.hasOwn(value, key))) {
      throw new Error(`${label}: use only the required fields (${allowed.join(", ")}).`);
    }
  }
  function number(value, min, max, label, exclusive = false) {
    if (typeof value !== "number" || !Number.isFinite(value) || value < min
        || (exclusive ? value >= max : value > max)) {
      throw new Error(`${label}: enter a number from ${min} to ${max}${exclusive ? " (excluding " + max + ")" : ""}.`);
    }
    return value;
  }
  function validateDraft(value) {
    keys(value, ["complete_coverage", "horizon", "sectors", "clearance_degrees"], "Profile");
    if (typeof value.complete_coverage !== "boolean") throw new Error("Complete coverage must be true or false.");
    number(value.clearance_degrees, 0, 10, "Clearance");
    if (!Array.isArray(value.horizon) || value.horizon.length < 2 || value.horizon.length > 720) {
      throw new Error("Enter 2–720 horizon points in clockwise order.");
    }
    let last = -1;
    value.horizon.forEach((point, i) => {
      keys(point, ["azimuth_degrees", "altitude_degrees"], `Horizon point ${i + 1}`);
      number(point.azimuth_degrees, 0, 360, `Point ${i + 1} direction`, true);
      number(point.altitude_degrees, 0, 90, `Point ${i + 1} height`);
      if (point.azimuth_degrees <= last) throw new Error("Horizon directions must be unique and sorted clockwise. Use Sort points.");
      last = point.azimuth_degrees;
    });
    if (!Array.isArray(value.sectors) || value.sectors.length > 64) throw new Error("Use at most 64 roof sectors.");
    value.sectors.forEach((sector, i) => {
      keys(sector, ["start_azimuth_degrees", "end_azimuth_degrees", "minimum_altitude_degrees", "maximum_altitude_degrees"], `Roof ${i + 1}`);
      number(sector.start_azimuth_degrees, 0, 360, `Roof ${i + 1} start`, true);
      number(sector.end_azimuth_degrees, 0, 360, `Roof ${i + 1} end`, true);
      number(sector.minimum_altitude_degrees, 0, 90, `Roof ${i + 1} lower edge`);
      number(sector.maximum_altitude_degrees, 0, 90, `Roof ${i + 1} upper edge`);
      if (sector.start_azimuth_degrees === sector.end_azimuth_degrees) throw new Error("Roof start and end must differ; split full-circle coverage into sectors.");
      if (sector.minimum_altitude_degrees >= sector.maximum_altitude_degrees) throw new Error("A roof's lower edge must be below its upper edge.");
    });
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
        if (current.names.has(name)) throw new Error("JSON profile fields must be unique; duplicate fields are not supported.");
        current.names.add(name); current.key = false;
      }
    }
  }
  function parseImport(text) {
    if (new TextEncoder().encode(text).length > MAX_BYTES) throw new Error("Import is limited to 128 KiB.");
    let data;
    try { data = JSON.parse(text); } catch (_) { throw new Error("Choose a valid Polaris JSON profile file."); }
    rejectDuplicateKeys(text);
    keys(data, ["format", "version", "profile"], "Import file");
    if (data.format !== FORMAT || data.version !== 1) throw new Error("This profile format or version is not supported.");
    return validateDraft(data.profile);
  }
  function exportDraft(draft) {
    return JSON.stringify({format: FORMAT, version: 1, profile: validateDraft(draft)}, null, 2) + "\n";
  }
  function example() {
    return {complete_coverage: false, clearance_degrees: 1,
      horizon: [{azimuth_degrees: 0, altitude_degrees: 15}, {azimuth_degrees: 90, altitude_degrees: 35},
                {azimuth_degrees: 180, altitude_degrees: 10}, {azimuth_degrees: 270, altitude_degrees: 25}],
      sectors: [{start_azimuth_degrees: 350, end_azimuth_degrees: 20, minimum_altitude_degrees: 60, maximum_altitude_degrees: 90}]};
  }
  function inputNumber(input) {
    if (input.value.trim() === "") {
      input.focus();
      throw new Error("Fill every numeric field; blank directions are unknown, not zero.");
    }
    return Number(input.value);
  }
  function markup(id) {
    return `<details class="obstruction-editor"><summary>Local obstructions <span>Manual entry &amp; preview</span></summary>
      <div class="obstruction-body">
      <p class="obstruction-kicker">Optional · Draft only</p><h2>Map the sky you can see</h2>
      <p>Add measured house, tree, and roof limits from the telescope's exact setup position.</p>
      <p class="obstruction-notice">This preview does not change Tonight's plan. Export a copy to keep your draft; reloading or signing out clears it. No photos or device sensors are used.</p>
      <p><a href="/operator-assets/photo-reference.html" target="_blank" rel="noopener">Open local photo reference workspace</a> — mark known references in a separate tab. Photo notes do not supply angular skyline points or change Tonight.</p>
      <div class="obstruction-actions"><button type="button" data-action="example">Load synthetic example</button>
        <label class="obstruction-import">Import JSON<input type="file" accept=".json,application/json" data-file></label>
        <button type="button" data-action="export">Export draft</button><button type="button" data-action="reset">Clear draft</button></div>
      <p data-origin>Empty draft. No directions have been measured.</p>
      <form novalidate>
        <fieldset><legend>1. Horizon points</legend>
          <p id="${id}-directions">Direction is degrees clockwise from <strong>true north</strong>: N 0°, E 90°, S 180°, W 270°. Height is degrees above level. Do not enter 360° or substitute zero for an unknown height.</p>
          <div data-horizon aria-describedby="${id}-directions"></div>
          <div class="obstruction-actions"><button type="button" data-action="add-point">Add point</button><button type="button" data-action="sort">Sort points clockwise</button></div>
        </fieldset>
        <fieldset><legend>2. Roofs and overhead obstacles <small>optional</small></legend>
          <p>Sectors run clockwise, including across north: 350° → 20°. Enter the lower and upper edges, so open sky below a roof stays open. Include all known overhead obstacles.</p>
          <div data-sectors></div><button type="button" data-action="add-sector">Add roof sector</button>
        </fieldset>
        <div class="obstruction-controls"><label>Vertical clearance (°)<input data-clearance type="number" min="0" max="10" step="any" inputmode="decimal" value="1" required></label>
          <p>A design margin, not a measured sensor accuracy. Polaris keeps its separate 20° imaging floor.</p></div>
        <label class="obstruction-confirm"><input type="checkbox" data-complete>
          <span>I have checked the complete horizon and overhead obstacles for this setup, or I am testing the synthetic example. Interpolated directions between points are part of this confirmation.</span></label>
        <fieldset><legend>3. Check one target-center direction</legend>
          <p>Enter a direction and height to test the geometry. This does not calculate a real target's path, darkness, or weather.</p>
          <div class="obstruction-controls"><label>Direction (°)<input data-probe-az type="number" min="0" max="359.999999" step="any" inputmode="decimal" value="0" required></label>
          <label>Height (°)<input data-probe-alt type="number" min="0" max="90" step="any" inputmode="decimal" value="45" required></label></div>
        </fieldset>
        <button type="submit" class="obstruction-preview-button">Validate &amp; preview</button>
      </form>
      <p data-status role="status" aria-live="polite">Coverage unknown — enter and confirm a complete survey before previewing.</p>
      <div data-chart class="obstruction-chart" role="region" tabindex="0" aria-label="Validated obstruction diagram; scroll horizontally on small screens"></div>
      <p class="obstruction-limits">A clear center is not a guarantee that the full image frame is clear. A panorama is not an automatically calibrated sky map. Check north alignment and your actual surroundings before imaging.</p>
      </div></details>`;
  }
  const svgNS = "http://www.w3.org/2000/svg";
  let chartId = 0;
  function drawChart(container, data) {
    container.replaceChildren();
    const document = container.ownerDocument;
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 800 300"); svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "True-north horizon with shaded obstructions, dashed 20 degree floor, and the tested center point. The text above gives the clearance result.");
    const add = (tag, attributes, text) => {
      const element = document.createElementNS(svgNS, tag);
      Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
      if (text !== undefined) element.textContent = text;
      svg.append(element); return element;
    };
    const x = az => 45 + az * 2;
    const y = alt => 260 - alt * 2.5;
    [0, 30, 60, 90].forEach(alt => {
      add("line", {x1: 45, x2: 765, y1: y(alt), y2: y(alt), class: "obs-grid"});
      add("text", {x: 8, y: y(alt) + 5}, `${alt}°`);
    });
    [[0,"N 0°"],[90,"E 90°"],[180,"S 180°"],[270,"W 270°"],[360,"N 360°"]].forEach(([az, name]) => add("text", {x: x(az), y: 285, "text-anchor": "middle"}, name));
    const clipId = `obs-chart-clip-${++chartId}`;
    const clip = add("clipPath", {id: clipId});
    const clipBounds = document.createElementNS(svgNS, "rect");
    Object.entries({x: 45, y: 35, width: 720, height: 225}).forEach(([key, value]) => clipBounds.setAttribute(key, String(value)));
    clip.append(clipBounds);
    // Clip after interpolation; clamping knots first understates sloping horizons.
    const points = data.horizon.map(p => `${x(p.azimuth_degrees)},${y(p.altitude_degrees + data.profile.clearance_degrees)}`);
    add("polygon", {points: `${x(0)},${y(0)} ${points.join(" ")} ${x(360)},${y(0)}`, class: "obs-horizon", "clip-path": `url(#${clipId})`});
    data.sectors.forEach(s => add("rect", {x: x(s.start), y: y(s.high), width: (s.end-s.start)*2, height: (s.high-s.low)*2.5, class: "obs-roof"}));
    add("polyline", {points: data.horizon.map(p => `${x(p.azimuth_degrees)},${y(p.altitude_degrees)}`).join(" "), class: "obs-measured"});
    add("line", {x1: 45, x2: 765, y1: y(20), y2: y(20), class: "obs-floor"});
    add("text", {x: 755, y: y(20)-5, "text-anchor": "end"}, "20° imaging floor");
    add("circle", {cx: x(data.probe.azimuth_degrees), cy: y(data.probe.altitude_degrees), r: 6, class: data.probe.clear ? "obs-clear" : "obs-blocked"});
    container.append(svg);
    const legend = document.createElement("p");
    legend.textContent = "Teal line: measured horizon · Shading: horizon/roof plus vertical clearance · Dashed line: quality floor · Dot: tested target center";
    container.append(legend);
  }
  function mount(container, request, index = 0) {
    container.innerHTML = markup(`obs-${index}`); // fixed markup only; imported values never become HTML
    const document = container.ownerDocument;
    const find = selector => container.querySelector(selector);
    const form = find("form");
    let revision = 0, controller = null, rowId = 0, dirty = false;
    const say = text => { find("[data-status]").textContent = text; };
    function invalidate(message = "Draft changed — validate again. Coverage is unknown until confirmed.") {
      revision++; controller?.abort(); controller = null;
      find("[type=submit]").disabled = false;
      find("[data-chart]").replaceChildren(); say(message);
    }
    function row(parent, fields, values) {
      const wrapper = document.createElement("div"); wrapper.className = "obstruction-row";
      fields.forEach(([key, title, max]) => {
        const label = document.createElement("label"); label.textContent = title;
        const input = document.createElement("input"); input.type = "number"; input.min = "0"; input.max = String(max);
        input.step = "any"; input.inputMode = "decimal"; input.required = true; input.dataset.key = key;
        input.id = `obs-${index}-field-${rowId++}`; label.htmlFor = input.id;
        input.value = values[key] ?? ""; label.append(input); wrapper.append(label);
      });
      const remove = document.createElement("button"); remove.type = "button"; remove.textContent = "Remove";
      remove.setAttribute("aria-label", parent === find("[data-horizon]") ? "Remove this horizon point" : "Remove this roof sector");
      remove.addEventListener("click", () => { wrapper.remove(); changed(); find(parent === find("[data-horizon]") ? "[data-action=add-point]" : "[data-action=add-sector]").focus(); });
      wrapper.append(remove); parent.append(wrapper);
    }
    const addPoint = values => row(find("[data-horizon]"), [["azimuth_degrees", "Direction (°)", 359.999999], ["altitude_degrees", "Height (°)", 90]], values);
    const addSector = values => row(find("[data-sectors]"), [["start_azimuth_degrees", "Start (°)", 359.999999], ["end_azimuth_degrees", "End (°)", 359.999999], ["minimum_altitude_degrees", "Lower edge (°)", 90], ["maximum_altitude_degrees", "Upper edge (°)", 90]], values);
    function changed() { dirty = true; find("[data-complete]").checked = false; invalidate(); }
    function populate(profile, origin) {
      invalidate();
      find("[data-horizon]").replaceChildren(); find("[data-sectors]").replaceChildren();
      profile.horizon.forEach(addPoint); profile.sectors.forEach(addSector);
      find("[data-clearance]").value = profile.clearance_degrees;
      find("[data-complete]").checked = false; // always reconfirm imported geometry for this setup
      find("[data-origin]").textContent = origin;
    }
    function reset() {
      populate({horizon: [{azimuth_degrees: 0}, {azimuth_degrees: 180}], sectors: [], clearance_degrees: 1}, "Empty draft. No directions have been measured.");
      find("[data-probe-az]").value = "0"; find("[data-probe-alt]").value = "45";
      find("[data-file]").value = ""; dirty = false;
      say("Coverage unknown — enter and confirm a complete survey before previewing.");
    }
    function readRows(selector) { return Array.from(find(selector).children, element => Object.fromEntries(Array.from(element.querySelectorAll("input"), input => [input.dataset.key, inputNumber(input)]))); }
    function draft() { return validateDraft({complete_coverage: find("[data-complete]").checked, horizon: readRows("[data-horizon]"), sectors: readRows("[data-sectors]"), clearance_degrees: inputNumber(find("[data-clearance]"))}); }
    form.addEventListener("input", event => {
      if (event.target.matches("[data-probe-az], [data-probe-alt]")) { invalidate("Test direction changed — validate again."); }
      else if (event.target.matches("[data-complete]")) { dirty = true; invalidate("Coverage confirmation changed — validate to see the result."); }
      else changed();
    });
    form.addEventListener("submit", async event => {
      event.preventDefault(); invalidate();
      const stamp = revision;
      try {
        const profile = draft();
        if (!profile.complete_coverage) throw new Error("Coverage unknown. Confirm a complete survey before previewing; partial coverage is not treated as clear sky.");
        const probe = {azimuth_degrees: number(inputNumber(find("[data-probe-az]")), 0, 360, "Test direction", true), altitude_degrees: number(inputNumber(find("[data-probe-alt]")), 0, 90, "Test height")};
        controller = new AbortController(); find("[type=submit]").disabled = true; say("Validating with Polaris…");
        const response = await request("/obstructions/preview", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({profile, probe}), cache: "no-store", signal: controller.signal});
        const data = await response.json();
        if (stamp !== revision) return;
        if (!response.ok) {
          if (response.status === 401 || response.status === 403) throw new Error("Sign in again to preview. Your draft has not been saved.");
          throw new Error(Array.isArray(data.detail) ? data.detail.map(item => `${item.loc.join(" / ")}: ${item.msg}`).join("; ") : data.detail || "Preview could not be validated.");
        }
        drawChart(find("[data-chart]"), data);
        say(data.probe.clear ? "Tested center clears the supplied geometry and 20° floor. This is not a full-frame or Tonight visibility guarantee." : `Tested center is blocked: ${data.probe.reason}.`);
      } catch (error) {
        if (stamp === revision) say(error.name === "AbortError" ? "Preview cancelled — validate again." : error.message || "Preview unavailable. Try again.");
      } finally { if (stamp === revision) { controller = null; find("[type=submit]").disabled = false; } }
    });
    container.addEventListener("click", event => {
      const action = event.target.dataset.action;
      if (!action) return;
      try {
        if (action === "add-point" || action === "add-sector") {
          const list = find(action === "add-point" ? "[data-horizon]" : "[data-sectors]");
          if (list.children.length >= (action === "add-point" ? 720 : 64)) throw new Error("Maximum row count reached.");
          (action === "add-point" ? addPoint : addSector)({}); changed(); list.lastElementChild.querySelector("input").focus();
        } else if (action === "example") {
          if (dirty && !global.confirm("Replace this draft with the synthetic example? Export first to keep it.")) return;
          populate(example(), "Synthetic example only — these are not measurements of your observing site."); dirty = true;
        } else if (action === "reset") {
          if (dirty && !global.confirm("Clear this draft? Export first to keep a copy.")) return;
          reset();
        } else if (action === "sort") {
          const points = readRows("[data-horizon]").sort((a,b) => a.azimuth_degrees-b.azimuth_degrees);
          find("[data-horizon]").replaceChildren(); points.forEach(addPoint); changed();
        } else if (action === "export") {
          const profile = draft();
          const url = URL.createObjectURL(new Blob([exportDraft(profile)], {type: "application/json"}));
          const link = document.createElement("a"); link.href = url; link.download = "polaris-obstruction-profile.json";
          document.body.append(link); link.click(); link.remove(); global.setTimeout(() => URL.revokeObjectURL(url), 1000);
          dirty = false; say(profile.complete_coverage ? "Profile exported. Import and reconfirm it for the correct setup before use." : "Incomplete draft exported. Coverage remains unknown; it is not ready for planning.");
        }
      } catch (error) { say(error.message); }
    });
    find("[data-file]").addEventListener("change", async event => {
      const file = event.target.files[0]; if (!file) return;
      invalidate("Reading profile…"); const stamp = revision;
      try {
        if (file.size > MAX_BYTES) throw new Error("Import is limited to 128 KiB.");
        const profile = parseImport(await file.text());
        if (stamp !== revision) return;
        if (dirty && !global.confirm("Replace this draft with the imported profile? Export first to keep it.")) { say("Import cancelled; your draft is unchanged."); return; }
        populate(profile, "Imported draft — check it against this setup and reconfirm complete coverage."); dirty = true;
      } catch (error) { if (stamp === revision) say(error.message); }
      finally { if (stamp === revision || !controller) event.target.value = ""; }
    });
    reset();
    const handle = {reset, isDirty: () => dirty, readDraft: draft,
      loadDraft(profile) { if (dirty && !global.confirm("Replace this draft with the saved survey?")) return false; populate(validateDraft(profile), "Saved survey — review this exact setup and reconfirm coverage."); dirty = true; return true; }};
    container.obstructionEditor = handle;
    return handle;
  }
  const api = {validateDraft, parseImport, exportDraft, example, markup, drawChart, mount,
    mountAll(root, request) { root.querySelectorAll("[data-obstruction-editor]").forEach((element, i) => instances.push(mount(element, request, i))); },
    resetAll() { instances.forEach(instance => instance.reset()); }};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else {
    global.PolarisObstructionEditor = api;
    global.addEventListener("beforeunload", event => { if (instances.some(instance => instance.isDirty())) { event.preventDefault(); event.returnValue = ""; } });
    global.addEventListener("pageshow", event => { if (event.persisted) api.resetAll(); });
  }
})(typeof window !== "undefined" ? window : globalThis);
