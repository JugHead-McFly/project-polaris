"use strict";

const byId = (id) => document.getElementById(id);

const setText = (id, value, fallback = "—") => {
  byId(id).textContent = value ?? fallback;
};

const displayNumber = (value, suffix = "") => {
  if (value === null || value === undefined) return "—";
  return `${value}${suffix}`;
};

const shortTime = (value) => {
  if (!value) return "—";
  const match = value.match(/(\d{1,2}:\d{2} [AP]M)$/);
  return match ? match[1] : value;
};

const durationLabel = (minutes) => {
  if (minutes === null || minutes === undefined) return "—";
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  if (!hours) return `${remaining} min`;
  if (!remaining) return `${hours} hr`;
  return `${hours} hr ${remaining} min`;
};

const displayDate = (value) => {
  if (!value) return "Date unavailable";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

const appendTextElement = (parent, tag, className, text) => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  parent.appendChild(element);
  return element;
};

const renderDecision = (data) => {
  const schedule = data.schedule;
  const decision = schedule.decision || "Conditions Unknown";
  const statusClass = `status-${decision.toLowerCase().replaceAll(" ", "-")}`;
  const panel = byId("decision-panel");

  panel.className = `decision-panel ${statusClass}`;
  setText("decision", decision);
  setText("decision-message", data.message);

  const recommended = data.recommended_target;
  const target = recommended || data.backup_target;
  setText("target-label", recommended ? "Primary target" : "Fallback if conditions improve");

  if (!target) {
    setText("target-name", "No target");
    setText("target-reason", "No target currently meets the planner requirements.");
    setText("target-altitude", null);
    setText("target-transit", null);
    setText("target-moon-separation", null);
    return;
  }

  setText("target-name", target.object);
  setText("target-reason", target.reason, "Planner recommendation available.");
  setText("target-altitude", displayNumber(target.current_altitude, "°"));
  setText("target-transit", shortTime(target.transit_time));
  setText(
    "target-moon-separation",
    displayNumber(target.moon_separation_degrees, "°"),
  );
};

const equipmentChips = (block) => {
  const chips = [];
  if (block.recommended_sub_exposure_seconds !== null) {
    chips.push(`${block.recommended_sub_exposure_seconds} sec subs`);
  }
  if (block.recommended_gain !== null) chips.push(`Gain ${block.recommended_gain}`);
  if (block.recommended_filter) chips.push(block.recommended_filter);
  if (block.planned_subframes !== null) chips.push(`${block.planned_subframes} frames`);
  chips.push(`${block.imaging_minutes} min imaging`);
  return chips;
};

const renderSchedule = (schedule) => {
  const list = byId("schedule-list");
  list.replaceChildren();
  const blocks = schedule.blocks || [];
  setText("schedule-count", `${blocks.length} block${blocks.length === 1 ? "" : "s"}`);

  if (!blocks.length) {
    appendTextElement(
      list,
      "div",
      "empty-state",
      schedule.decision === "Do Not Image"
        ? "No imaging blocks—conditions are currently unsuitable."
        : "No block met the visibility and minimum-duration requirements.",
    );
    return;
  }

  blocks.forEach((block) => {
    const row = appendTextElement(list, "article", "schedule-block", "");
    const time = appendTextElement(row, "div", "schedule-time", "");
    appendTextElement(time, "strong", "", shortTime(block.start));
    appendTextElement(time, "span", "", ` → ${shortTime(block.end)}`);

    const card = appendTextElement(row, "div", "schedule-card", "");
    const heading = appendTextElement(card, "div", "block-heading", "");
    appendTextElement(heading, "strong", "", block.object);
    appendTextElement(heading, "span", "", durationLabel(block.duration_minutes));

    const chips = appendTextElement(card, "div", "equipment-row", "");
    equipmentChips(block).forEach((label) => {
      appendTextElement(chips, "span", "equipment-chip", label);
    });

    if (block.setup_changes && block.setup_changes.length) {
      const setup = appendTextElement(card, "ul", "setup-list", "");
      block.setup_changes.forEach((change) => appendTextElement(setup, "li", "", change));
    }
  });
};

const renderConditions = (data) => {
  const weather = data.weather;
  const moon = data.moon;
  const darkness = data.darkness;

  setText(
    "darkness-window",
    `${shortTime(darkness.astronomical_darkness_start)}–${shortTime(
      darkness.astronomical_darkness_end,
    )}`,
  );
  setText("sunset", `Sunset ${shortTime(darkness.sunset)}`);
  setText("allocated-time", durationLabel(data.schedule.allocated_minutes));
  setText(
    "unscheduled-time",
    `${durationLabel(data.schedule.unscheduled_dark_minutes)} unscheduled`,
  );
  setText("night-rating", `${data.night_rating.score} · ${data.night_rating.quality}`);
  setText("weather-status", weather.status);
  setText("cloud-cover", displayNumber(weather.cloud_cover_percent, "%"));
  setText("humidity", displayNumber(weather.humidity_percent, "%"));
  setText("wind", displayNumber(weather.wind_speed_mph, " mph"));
  setText("temperature", displayNumber(weather.temperature_f, "°F"));
  setText("moon-illumination", displayNumber(moon.illumination_percent, "% lit"));
  setText("moon-altitude", displayNumber(moon.altitude_degrees, "°"));
};

const renderNotes = (notes) => {
  const list = byId("planner-notes");
  list.replaceChildren();

  if (!notes || !notes.length) {
    appendTextElement(list, "li", "", "No additional planner cautions tonight.");
    return;
  }

  notes.forEach((note) => appendTextElement(list, "li", "", note));
};

const renderSystem = (data) => {
  const library = data.capture_library;
  setText("system-status", data.status);
  setText("library-status", `Capture library ${library.status.toLowerCase()}`);
  setText("version", `v${data.version}`);
  setText("capture-count", data.captures);
  setText("target-count", data.targets);
  setText("session-count", data.sessions);
  setText("matched-count", library.matched_count);
  setText("conflict-count", library.conflict_count);
};

const renderPortfolio = (data) => {
  const container = byId("target-portfolio");
  container.replaceChildren();
  setText(
    "portfolio-summary",
    `${data.metrics.targets} targets · ${data.metrics.total_integration_hours} hours`,
  );

  if (!data.targets.length) {
    appendTextElement(container, "div", "empty-state", "No captured targets yet.");
    return;
  }

  data.targets.forEach((target) => {
    const card = appendTextElement(container, "article", "target-card", "");
    const heading = appendTextElement(card, "div", "target-card-heading", "");
    appendTextElement(heading, "strong", "", target.object);
    appendTextElement(heading, "span", "", target.portfolio_level);

    const progress = document.createElement("progress");
    progress.max = 125;
    progress.value = Math.min(target.progress_percent, 125);
    progress.setAttribute(
      "aria-label",
      `${target.object} integration progress ${target.progress_percent} percent`,
    );
    card.appendChild(progress);

    const progressCopy = appendTextElement(card, "div", "target-progress-copy", "");
    appendTextElement(
      progressCopy,
      "span",
      "",
      `${target.current_hours} / ${target.goal_hours} hr`,
    );
    appendTextElement(progressCopy, "span", "", `${target.progress_percent}%`);

    appendTextElement(
      card,
      "p",
      "target-quality",
      target.best_quality === null
        ? `${target.capture_count} capture${target.capture_count === 1 ? "" : "s"}`
        : `${target.capture_count} capture${target.capture_count === 1 ? "" : "s"} · best quality ${target.best_quality}`,
    );
  });
};

const renderRecentCaptures = (data) => {
  const container = byId("recent-captures");
  container.replaceChildren();
  setText("capture-summary", `${data.metrics.captures} total`);

  if (!data.recent_captures.length) {
    appendTextElement(container, "div", "empty-state", "No captures recorded yet.");
    return;
  }

  data.recent_captures.forEach((capture) => {
    const card = appendTextElement(container, "article", "activity-card", "");
    const heading = appendTextElement(card, "div", "activity-heading", "");
    appendTextElement(heading, "strong", "", capture.object || "Unknown target");
    appendTextElement(heading, "span", "", displayDate(capture.observation_utc));

    const meta = appendTextElement(card, "div", "activity-meta", "");
    appendTextElement(meta, "span", "", capture.polaris_id);
    appendTextElement(meta, "span", "", durationLabel(Math.round(capture.total_integration_seconds / 60)));
    if (capture.filter_name) appendTextElement(meta, "span", "", capture.filter_name);
    if (capture.quality_score !== null) {
      appendTextElement(meta, "span", "", `Quality ${capture.quality_score}`);
    }
  });
};

const renderRecentSessions = (data) => {
  const container = byId("recent-sessions");
  container.replaceChildren();
  setText("session-summary", `${data.metrics.sessions} total`);

  if (!data.recent_sessions.length) {
    appendTextElement(container, "div", "empty-state", "No observing sessions recorded yet.");
    return;
  }

  data.recent_sessions.forEach((session) => {
    const card = appendTextElement(container, "article", "activity-card", "");
    const heading = appendTextElement(card, "div", "activity-heading", "");
    appendTextElement(heading, "strong", "", session.targets.join(", ") || "No linked targets");
    appendTextElement(heading, "span", "", displayDate(session.date));

    const meta = appendTextElement(card, "div", "activity-meta", "");
    appendTextElement(meta, "span", "", session.session_id);
    appendTextElement(
      meta,
      "span",
      "",
      `${session.capture_count} capture${session.capture_count === 1 ? "" : "s"}`,
    );
    appendTextElement(meta, "span", "", `${session.total_integration_hours} hr`);
  });
};

const renderHistoryError = () => {
  setText("portfolio-summary", "Unavailable");
  setText("capture-summary", "Unavailable");
  setText("session-summary", "Unavailable");
  ["target-portfolio", "recent-captures", "recent-sessions"].forEach((id) => {
    const container = byId(id);
    container.replaceChildren();
    appendTextElement(container, "div", "empty-state", "History is temporarily unavailable.");
  });
};

const showPlanError = (message) => {
  const panel = byId("decision-panel");
  panel.className = "decision-panel status-error";
  setText("decision", "Plan unavailable");
  setText("decision-message", "Polaris could not safely build tonight's plan.");
  const error = byId("load-error");
  error.textContent = message;
  error.hidden = false;
};

const loadDashboard = async () => {
  const refresh = byId("refresh-button");
  refresh.disabled = true;
  refresh.textContent = "Refreshing…";
  byId("load-error").hidden = true;

  const [planResult, systemResult, dashboardResult] = await Promise.allSettled([
    fetch("/tonight", { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`Tonight endpoint returned ${response.status}.`);
      return response.json();
    }),
    fetch("/system", { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`System endpoint returned ${response.status}.`);
      return response.json();
    }),
    fetch("/dashboard", { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`Dashboard endpoint returned ${response.status}.`);
      return response.json();
    }),
  ]);

  if (planResult.status === "fulfilled") {
    const data = planResult.value;
    renderDecision(data);
    renderSchedule(data.schedule);
    renderConditions(data);
    renderNotes(data.schedule.notes);
  } else {
    showPlanError(planResult.reason.message);
  }

  if (systemResult.status === "fulfilled") {
    renderSystem(systemResult.value);
  } else {
    setText("system-status", "Unavailable");
    setText("library-status", "Health check failed");
  }

  if (dashboardResult.status === "fulfilled") {
    renderPortfolio(dashboardResult.value);
    renderRecentCaptures(dashboardResult.value);
    renderRecentSessions(dashboardResult.value);
  } else {
    renderHistoryError();
  }

  setText("last-updated", `Last refreshed ${new Date().toLocaleString()}`);
  refresh.disabled = false;
  refresh.textContent = "Refresh conditions";
};

byId("refresh-button").addEventListener("click", loadDashboard);
loadDashboard();
