"use strict";

// One generation owns the screen. Aborted or late responses cannot replace it.
const createLoadCoordinator = (render, timeoutMs = 90000) => {
  let active = null;
  return {
    cancel() { active?.controller.abort(); active = null; },
    begin(stages, retained = false) {
      active?.controller.abort();
      const run = { controller: new AbortController(), stages: { ...stages }, retained, message: "", failed: false };
      active = run;
      run.current = () => active === run && !run.controller.signal.aborted;
      run.update = (key, state) => {
        if (!run.current()) return;
        run.stages[key] = state;
        render(run);
      };
      run.request = async (key, action) => {
        if (!run.current()) throw new Error("Superseded request");
        run.update(key, "loading");
        const timingStart = globalThis.performance?.now();
        let timer;
        const controller = new AbortController();
        const cancel = () => controller.abort();
        run.controller.signal.addEventListener("abort", cancel, { once: true });
        try {
          const timeout = new Promise((_, reject) => {
            timer = setTimeout(() => {
              controller.abort();
              reject(new Error("This is taking longer than expected. Please try again."));
            }, timeoutMs);
          });
          const aborted = new Promise((_, reject) => {
            controller.signal.addEventListener("abort", () => reject(new Error("Request stopped. Please try again.")), { once: true });
          });
          const value = await Promise.race([action(controller.signal), timeout, aborted]);
          if (!run.current()) throw new Error("Superseded request");
          run.update(key, "done");
          return value;
        } catch (error) {
          run.update(key, "error");
          throw error;
        } finally {
          clearTimeout(timer);
          run.controller.signal.removeEventListener("abort", cancel);
          // Local DevTools timing only: no session, account or response data.
          // Keep one measure per stage instead of growing the performance buffer.
          if (timingStart != null && globalThis.performance?.measure) {
            try {
              const name = `polaris:${key}`;
              performance.clearMeasures(name);
              performance.measure(name, { start: timingStart, end: performance.now() });
            } catch (_) { /* Optional diagnostics must not interrupt loading. */ }
          }
        }
      };
      run.finish = (message = "") => {
        if (!run.current()) return;
        run.failed = Boolean(message);
        run.message = message;
        run.finished = true;
        render(run);
      };
      render(run);
      return run;
    },
  };
};
// Optional maps must not hold up authentication or the hosted night plan.
const createMapLibraryLoader = (doc, scope, timeoutMs = 15000) => {
  let pending = null;
  return () => {
    if (scope.L) return Promise.resolve(scope.L);
    if (pending) return pending;
    pending = new Promise((resolve, reject) => {
      const script = doc.createElement("script");
      script.src = "/operator-assets/leaflet.js";
      script.async = true;
      const finish = (error) => {
        clearTimeout(timer);
        script.onload = script.onerror = null;
        if (error) {
          script.remove();
          reject(error);
        } else resolve(scope.L);
      };
      const timer = setTimeout(() => finish(new Error("Map library timed out. Refresh to retry.")), timeoutMs);
      script.onload = () => finish(scope.L ? null : new Error("Map controls are unavailable. Refresh to retry."));
      script.onerror = () => finish(new Error("Map controls could not load. Refresh to retry."));
      doc.head.append(script);
    }).catch(error => { pending = null; throw error; });
    return pending;
  };
};
if (typeof module !== "undefined") module.exports = { createLoadCoordinator, createMapLibraryLoader };
