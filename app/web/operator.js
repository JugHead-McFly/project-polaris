"use strict";

const byId = (id) => document.getElementById(id);

const VIEW_PATHS = {
  "/operator": "tonight",
  "/operator/portfolio": "portfolio",
  "/operator/quality": "quality",
  "/operator/history": "history",
  "/operator/data": "data",
};

const VIEW_TITLES = {
  tonight: "Night Operations",
  portfolio: "Portfolio",
  quality: "Quality by Target",
  history: "History",
  data: "Data Status",
};

const currentPath = window.location.pathname.replace(/\/$/, "") || "/operator";
const activeView = VIEW_PATHS[currentPath] || "tonight";
const demoMode = new URLSearchParams(window.location.search).get("demo");
const isImmaculateDemo = activeView === "tonight" && demoMode === "immaculate";
const isMapOverlapDemo = activeView === "history" && demoMode === "map-overlap";
let historyExpanded = false;
const refreshButtonLabel = () => (
  isImmaculateDemo
    ? "Refresh simulation"
    : activeView === "tonight" ? "Refresh conditions" : "Refresh data"
);

const activateCurrentView = () => {
  document.querySelectorAll("[data-app-view]").forEach((view) => {
    view.hidden = view.dataset.appView !== activeView;
  });
  document.querySelectorAll("[data-view-link]").forEach((link) => {
    if (link.dataset.viewLink === activeView) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
  document.title = `Project Polaris — ${VIEW_TITLES[activeView]}`;
  if (isImmaculateDemo || isMapOverlapDemo) document.title += " (Simulation)";
  document.querySelector(".skip-link").textContent = `Skip to ${VIEW_TITLES[
    activeView
  ].toLowerCase()}`;
  byId("refresh-button").textContent = refreshButtonLabel();
  byId("simulation-banner").hidden = !isImmaculateDemo;
};

const setText = (id, value, fallback = "—") => {
  byId(id).textContent = value ?? fallback;
};

const displayNumber = (value, suffix = "") => {
  if (value === null || value === undefined) return "—";
  return `${value}${suffix}`;
};

const displayMeasuredNumber = (value) => {
  if (value === null || value === undefined) return "—";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return value;
  if (Number.isInteger(numeric)) return `${numeric}`;
  return numeric.toFixed(2).replace(/\.?0+$/, "");
};

const friendlyFilterLabel = (value) => {
  if (!value) return "Not recorded";
  const descriptions = {
    "duo-band": "Duo-Band · emphasizes glowing nebula gases",
    astro: "Astro · general deep-sky imaging",
    vis: "VIS · natural-color visible light",
    uhc: "UHC · increases nebula contrast",
    clear: "Clear · no light-filtering effect",
    none: "No filter · full available light",
  };
  return descriptions[value.trim().toLowerCase()] || value;
};

const qualityInterpretation = (score) => {
  if (score === null || score === undefined) return "Not scored";
  if (score >= 85) return "Strong result";
  if (score >= 70) return "Acceptable result";
  return "Review recommended";
};

const bortleLabel = (bortleClass) => {
  if (bortleClass === null || bortleClass === undefined) {
    return "Not recorded";
  }
  const labels = {
    1: "excellent dark sky",
    2: "average dark sky",
    3: "rural sky",
    4: "rural/suburban transition",
    5: "suburban",
    6: "bright suburban",
    7: "suburban/urban transition",
    8: "city sky",
    9: "inner city sky",
  };
  return `Class ${bortleClass} · ${labels[bortleClass] || "unclassified"}`;
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

const uptimeLabel = (seconds) => {
  if (seconds === null || seconds === undefined) return "—";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days) return `${days}d ${hours}h`;
  if (hours) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
};

const setStatusText = (id, status) => {
  const element = byId(id);
  element.textContent = status || "Unknown";
  element.className = `status-${(status || "unknown")
    .toLowerCase()
    .replaceAll(" ", "-")}`;
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

const displayDateTime = (value) => {
  if (!value) return "Time unavailable";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
};

const integrationLabel = (seconds) => {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 60) return `${seconds} sec`;
  return durationLabel(Math.round(seconds / 60));
};

const targetWindowLabel = (start, end) => {
  if (!start || !end) return "No usable window";
  return `${shortTime(start)}–${shortTime(end)}`;
};

const addMinutesToScheduleTime = (value, minutes) => {
  const match = value?.match(
    /^(\d{4})-(\d{2})-(\d{2}) (\d{1,2}):(\d{2}) (AM|PM)$/,
  );
  if (!match) return null;

  const [, year, month, day, hourText, minuteText, period] = match;
  let hour = Number(hourText) % 12;
  if (period === "PM") hour += 12;
  const result = new Date(
    Number(year),
    Number(month) - 1,
    Number(day),
    hour,
    Number(minuteText) + minutes,
  );
  const resultHour = result.getHours();
  const displayHour = resultHour % 12 || 12;
  const displayPeriod = resultHour >= 12 ? "PM" : "AM";
  const pad = (number) => `${number}`.padStart(2, "0");
  return `${result.getFullYear()}-${pad(result.getMonth() + 1)}-${pad(
    result.getDate(),
  )} ${pad(displayHour)}:${pad(result.getMinutes())} ${displayPeriod}`;
};

const applyImmaculateDemo = (data, dashboard) => {
  const target = data.recommended_target || data.backup_target;
  const now = new Date().toISOString();
  const settings = target?.recommended_settings || {};
  const sessionStart = data.darkness.astronomical_darkness_start;
  const portfolioTargets = dashboard?.targets || [];
  const targetByObject = (objectName) => portfolioTargets.find(
    (candidate) => candidate.object === objectName,
  );
  const preferredTargets = [
    targetByObject("M16"),
    target,
    targetByObject("M27"),
    ...portfolioTargets,
  ].filter(Boolean);
  const demoTargets = preferredTargets.filter(
    (candidate, index, candidates) => candidates.findIndex(
      (item) => item.object === candidate.object,
    ) === index,
  ).slice(0, 3);
  const blockMinutes = 120;
  const setupMinutes = 5;
  const imagingMinutes = blockMinutes - setupMinutes;

  const blocks = demoTargets.map((candidate, index) => {
    const candidateSettings = candidate.recommended_settings || settings;
    const exposureSeconds = candidateSettings.exposure_seconds || 15;
    const start = addMinutesToScheduleTime(sessionStart, index * blockMinutes)
      || ["9:15 PM", "11:15 PM", "1:15 AM"][index];
    const end = addMinutesToScheduleTime(sessionStart, (index + 1) * blockMinutes)
      || ["11:15 PM", "1:15 AM", "3:15 AM"][index];
    const previous = demoTargets[index - 1];
    const previousSettings = previous?.recommended_settings || settings;
    const setupChanges = index === 0
      ? [
        `Center and focus on ${candidate.object}`,
        candidateSettings.filter_name
          ? `Confirm ${candidateSettings.filter_name} filter`
          : "Confirm filter selection",
      ]
      : [`Slew to and center ${candidate.object}`];

    if (
      index > 0
      && candidateSettings.filter_name
      && candidateSettings.filter_name !== previousSettings.filter_name
    ) {
      setupChanges.push(`Change to ${candidateSettings.filter_name} filter`);
    }

    return {
      object: candidate.object,
      common_name: candidate.common_name,
      start,
      end,
      duration_minutes: blockMinutes,
      setup_minutes: setupMinutes,
      imaging_minutes: imagingMinutes,
      planner_score: 100 - index * 5,
      reason: index === 0
        ? "Scheduled first because its strongest window closes earlier."
        : "Scheduled next as the previous target's preferred window ends.",
      recommended_sub_exposure_seconds: exposureSeconds,
      recommended_gain: candidateSettings.gain ?? null,
      recommended_filter: candidateSettings.filter_name ?? null,
      recommendation_source: candidateSettings.source || "simulation",
      planned_subframes: Math.floor(imagingMinutes * 60 / exposureSeconds),
      setup_changes: setupChanges,
    };
  });
  const allocatedMinutes = blocks.reduce(
    (total, block) => total + block.duration_minutes,
    0,
  );
  const primaryBlock = blocks.find((block) => block.object === target?.object);

  data.weather = {
    ...data.weather,
    status: "Simulated immaculate conditions",
    cloud_cover_percent: 0,
    humidity_percent: 20,
    wind_speed_mph: 1,
    observed_at: now,
    fetched_at: now,
  };
  data.night_rating = {
    score: 100,
    quality: "Excellent (simulated)",
  };
  data.message = blocks.length > 1
    ? `Simulation: immaculate weather supports a ${blocks.length}-target session (${blocks
      .map((block) => block.object)
      .join(", ")}).`
    : target
      ? `Simulation: immaculate weather supports a full ${target.object} imaging session.`
    : "Simulation: immaculate weather supports imaging throughout astronomical darkness.";

  if (target) {
    target.reason = (
      "Simulation preview: clear skies, low wind, and low humidity provide an "
      + "uninterrupted target window."
    );
    target.recommended_start = primaryBlock?.start || target.recommended_start;
    target.recommended_end = primaryBlock?.end || target.recommended_end;
    data.recommended_target = target;
    data.backup_target = null;
  }

  data.schedule = {
    ...data.schedule,
    decision: "Proceed",
    allocated_minutes: allocatedMinutes,
    unscheduled_dark_minutes: blocks.length ? 37 : 420,
    notes: [
      "Simulation only—these are not live weather or equipment-safety conditions.",
      "Immaculate weather scenario: 0% cloud cover, 1 mph wind, and 20% humidity.",
      "Each target block includes a five-minute setup allowance for centering, focusing, and any equipment change.",
      "The live planner would choose the actual sequence from target visibility, Moon separation, portfolio goals, and equipment-change cost.",
    ],
    blocks,
  };

  return data;
};

const appendTextElement = (parent, tag, className, text) => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  parent.appendChild(element);
  return element;
};

const appendTargetIdentity = (parent, objectName, commonName) => {
  const identity = appendTextElement(parent, "div", "target-identity", "");
  appendTextElement(identity, "strong", "", objectName || "Unknown target");
  if (commonName) appendTextElement(identity, "span", "", commonName);
  return identity;
};

const appendFact = (parent, label, value) => {
  const fact = appendTextElement(parent, "div", "activity-fact", "");
  appendTextElement(fact, "span", "activity-fact-label", label);
  appendTextElement(fact, "strong", "", value ?? "—");
};

let imageViewerItems = [];
let imageViewerIndex = 0;

const pointsLabel = (points) => `${points > 0 ? "+" : ""}${points} pts`;

const qualityAnalysisSummary = (components) => {
  if (!components) return "This image has not been broken down into individual quality measurements yet.";
  const trailing = components.trailing_detected === null
    ? "Not measured"
    : components.trailing_detected ? "Detected" : "Not detected";
  return [
    `Stars detected: ${displayNumber(components.stars_detected)} (${pointsLabel(components.star_points)} / 20)`,
    `Background level: ${displayMeasuredNumber(components.background_level)} (${pointsLabel(components.background_points)} / 10)`,
    `Background variation: ${displayMeasuredNumber(components.background_variation)} (${pointsLabel(components.variation_points)} / 15)`,
    `Star trailing: ${trailing} (${pointsLabel(components.trailing_points)} / 5)`,
  ].join(" · ");
};

const renderImageViewerItem = () => {
  const item = imageViewerItems[imageViewerIndex];
  if (!item) return;

  const image = byId("image-dialog-image");
  const error = byId("image-dialog-error");
  image.hidden = true;
  error.hidden = true;
  image.removeAttribute("src");
  image.alt = `${item.object || "Capture"}${
    item.common_name ? ` — ${item.common_name}` : ""
  } preview`;
  image.src = item.preview_url;

  setText(
    "image-dialog-title",
    item.common_name ? `${item.object} — ${item.common_name}` : item.object,
    "Capture image",
  );
  setText(
    "image-dialog-position",
    imageViewerItems.length > 1
      ? `Image ${imageViewerIndex + 1} of ${imageViewerItems.length}`
      : "Single capture",
  );
  setText("image-dialog-captured", displayDateTime(item.observation_utc));
  setText("image-dialog-integration", integrationLabel(item.total_integration_seconds));
  setText("image-dialog-subframes", item.subframe_count);
  setText("image-dialog-exposure", displayNumber(item.sub_exposure_seconds, " sec"));
  setText("image-dialog-gain", displayNumber(item.gain));
  setText("image-dialog-filter", friendlyFilterLabel(item.filter_name));
  setText(
    "image-dialog-quality",
    item.quality_score === null ? "Not scored" : `${item.quality_score}/100`,
  );
  setText(
    "image-dialog-recommendation",
    item.quality_recommendation || "Quality analysis is not available for this capture yet.",
  );
  setText("image-dialog-analysis", qualityAnalysisSummary(item.components));

  const previous = byId("image-dialog-previous");
  const next = byId("image-dialog-next");
  previous.hidden = imageViewerItems.length <= 1;
  next.hidden = imageViewerItems.length <= 1;
  previous.disabled = imageViewerIndex === 0;
  next.disabled = imageViewerIndex === imageViewerItems.length - 1;
};

const openImageViewer = (items, startIndex = 0) => {
  imageViewerItems = items.filter((item) => item.preview_url);
  if (!imageViewerItems.length) return;
  imageViewerIndex = Math.max(0, Math.min(startIndex, imageViewerItems.length - 1));
  renderImageViewerItem();
  const dialog = byId("image-dialog");
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
};

const appendImageButton = (parent, label, items, className = "image-view-button") => {
  const availableItems = items.filter((item) => item.preview_url);
  if (!availableItems.length) return null;
  const button = appendTextElement(parent, "button", className, label);
  button.type = "button";
  button.addEventListener("click", () => openImageViewer(availableItems));
  return button;
};

const qualityComponentInfo = {
  stars: {
    title: "Stars detected",
    body: "This is the number of star-like points Polaris can identify in the image. More detected stars often suggests clear skies and good focus, but the count also depends on the target, exposure, camera, and how crowded that part of the sky is—so it is only one clue, not a verdict on the image.",
    range: "Best-scoring range: 5,000 or more stars. 2,500–4,999 earns 15 of 20 points; 1,000–2,499 earns 10; 300–999 earns 5. Fewer than 100 deducts points.",
  },
  background: {
    title: "Background level",
    body: "This is the overall brightness of the image background—the sky glow behind the target. A lower background is not automatically better: Polaris looks for a usable, well-exposed image rather than one that is too dark or washed out.",
    range: "Best-scoring range: 5,000–40,000. Below 1,000 is too dark and above 60,000 is too bright. Values in between may earn fewer points.",
  },
  variation: {
    title: "Background variation",
    body: "This measures how evenly bright the background is across the frame. Large swings can come from clouds, gradients, light pollution, or uneven illumination.",
    range: "Best-scoring range: 150–1,200. 50–150 or 1,200–3,000 receives partial credit; above 5,000 is a strong warning sign.",
  },
  trailing: {
    title: "Star trailing",
    body: "This checks whether stars look stretched instead of round. Stretching can be caused by tracking or guiding issues while the telescope follows the sky.",
    range: "Expected result: Not detected. Round stars earn 5 points; detected trailing deducts 25 points because it noticeably affects image sharpness.",
  },
};

const openQualityInfo = (infoKey) => {
  const info = qualityComponentInfo[infoKey];
  if (!info) return;
  setText("quality-info-title", info.title);
  setText("quality-info-body", info.body);
  setText("quality-info-range", info.range);
  const dialog = byId("quality-info-dialog");
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
};

const appendQualityComponent = (parent, label, value, points, maxPoints, infoKey = null) => {
  const component = appendTextElement(parent, "div", "quality-component", "");
  const labelElement = appendTextElement(component, "span", "", label);
  if (infoKey) {
    const button = appendTextElement(labelElement, "button", "quality-info-button", "i");
    button.type = "button";
    button.setAttribute("aria-label", `About ${label}`);
    button.addEventListener("click", () => openQualityInfo(infoKey));
  }
  appendTextElement(component, "strong", "", value);
  appendTextElement(component, "small", "", `${pointsLabel(points)} / ${maxPoints} pts`);
};

const appendObjectProfile = (
  parent,
  objectName,
  profile,
  includeDetails = false,
  starsDetected = null,
) => {
  if (!profile) return;
  appendTextElement(parent, "p", "target-profile-snippet", profile.summary);
  if (!includeDetails) return;

  const details = document.createElement("details");
  details.className = "object-profile";
  appendTextElement(details, "summary", "", `About ${objectName}`);
  if (profile.story) {
    appendTextElement(details, "p", "object-story", profile.story);
  }
  const facts = appendTextElement(details, "dl", "object-profile-facts", "");
  const type = appendTextElement(facts, "div", "", "");
  appendTextElement(type, "dt", "", "Object type");
  appendTextElement(type, "dd", "", profile.object_type);
  const distance = appendTextElement(facts, "div", "", "");
  appendTextElement(distance, "dt", "", "Distance");
  appendTextElement(distance, "dd", "", profile.distance);
  const age = appendTextElement(facts, "div", "", "");
  appendTextElement(age, "dt", "", "Age or stage");
  appendTextElement(age, "dd", "", profile.age);
  const stars = appendTextElement(facts, "div", "", "");
  appendTextElement(stars, "dt", "", "Stars detected in this image");
  appendTextElement(
    stars,
    "dd",
    "",
    starsDetected === null || starsDetected === undefined
      ? "Not measured"
      : Number(starsDetected).toLocaleString(),
  );
  if (profile.wow_fact) {
    const wow = appendTextElement(details, "aside", "object-wow", "");
    appendTextElement(wow, "span", "", "Why it’s remarkable");
    appendTextElement(wow, "strong", "", profile.wow_fact);
  }
  const imageNote = appendTextElement(details, "div", "object-image-note", "");
  appendTextElement(imageNote, "span", "", "What the image colors can show");
  appendTextElement(imageNote, "p", "object-color-note", profile.color_note);
  const source = appendTextElement(
    details,
    "a",
    "object-source",
    `Colors and science of ${objectName}`,
  );
  source.href = profile.source_url;
  source.target = "_blank";
  source.rel = "noreferrer";
  parent.appendChild(details);
};

const renderMoonVisual = (moon) => {
  const canvas = byId("moon-visual");
  const context = canvas.getContext("2d");
  if (!context) return;

  const width = canvas.width;
  const height = canvas.height;
  const radius = Math.min(width, height) / 2 - 3;
  const centerX = width / 2;
  const centerY = height / 2;
  const fraction = Math.max(0, Math.min(1, moon.illumination_percent / 100));
  const lightZ = 2 * fraction - 1;
  const phaseName = moon.phase_name || "Moon phase unavailable";
  const waning = phaseName.startsWith("Waning") || phaseName === "Last Quarter";
  const lightX = Math.sqrt(Math.max(0, 1 - lightZ * lightZ)) * (waning ? -1 : 1);
  const image = context.createImageData(width, height);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const normalizedX = (x + 0.5 - centerX) / radius;
      const normalizedY = (y + 0.5 - centerY) / radius;
      const distanceSquared = normalizedX ** 2 + normalizedY ** 2;
      if (distanceSquared > 1) continue;

      const surfaceZ = Math.sqrt(1 - distanceSquared);
      const isIlluminated = normalizedX * lightX + surfaceZ * lightZ > 0;
      const limbShade = 0.72 + surfaceZ * 0.28;
      const baseColor = isIlluminated ? 238 : 27;
      const color = Math.round(baseColor * limbShade);
      const edgeAlpha = Math.min(1, (1 - Math.sqrt(distanceSquared)) * radius);
      const offset = (y * width + x) * 4;

      image.data[offset] = color;
      image.data[offset + 1] = isIlluminated ? color : Math.round(color * 1.16);
      image.data[offset + 2] = isIlluminated ? Math.min(255, color + 4) : Math.round(color * 1.3);
      image.data[offset + 3] = Math.round(255 * edgeAlpha);
    }
  }

  context.clearRect(0, 0, width, height);
  context.putImageData(image, 0, 0);
  context.beginPath();
  context.arc(centerX, centerY, radius, 0, Math.PI * 2);
  context.strokeStyle = "rgba(207, 225, 230, 0.35)";
  context.lineWidth = 1;
  context.stroke();
  canvas.setAttribute(
    "aria-label",
    `${phaseName}, ${moon.illumination_percent}% illuminated`,
  );
};

const renderDecision = (data) => {
  const schedule = data.schedule;
  const decision = schedule.decision || "Conditions Unknown";
  const statusClass = `status-${decision.toLowerCase().replaceAll(" ", "-")}`;
  const panel = byId("decision-panel");

  panel.className = `decision-panel ${statusClass}`;
  setText("observatory-name", data.observatory?.name, "Local observatory");
  setText("decision", decision);
  setText("decision-message", data.message);

  const recommended = data.recommended_target;
  const target = recommended || data.backup_target;
  setText("target-label", recommended ? "Primary target" : "Fallback if conditions improve");

  if (!target) {
    setText("target-name", "No target");
    setText("target-common-name", "");
    setText("target-reason", "No target currently meets the planner requirements.");
    setText("target-altitude", null);
    setText("target-transit", null);
    setText("target-moon-separation", null);
    setText("target-usable-window", "No usable window");
    setText("target-exposure", null);
    setText("target-gain", null);
    setText("target-filter", null);
    return;
  }

  setText("target-name", target.object);
  setText("target-common-name", target.common_name, "");
  setText("target-reason", target.reason, "Planner recommendation available.");
  setText("target-altitude", displayNumber(target.current_altitude, "°"));
  setText("target-transit", shortTime(target.transit_time));
  setText(
    "target-moon-separation",
    displayNumber(target.moon_separation_degrees, "°"),
  );
  setText(
    "target-usable-window",
    targetWindowLabel(target.recommended_start, target.recommended_end),
  );

  const settings = target.recommended_settings || {};
  setText("target-exposure", displayNumber(settings.exposure_seconds, " sec"));
  setText("target-gain", displayNumber(settings.gain));
  setText("target-filter", friendlyFilterLabel(settings.filter_name));
};

const equipmentChips = (block) => {
  const chips = [];
  if (block.recommended_sub_exposure_seconds !== null) {
    chips.push(`${block.recommended_sub_exposure_seconds} sec subs`);
  }
  if (block.recommended_gain !== null) chips.push(`Gain ${block.recommended_gain}`);
  if (block.recommended_filter) {
    chips.push(friendlyFilterLabel(block.recommended_filter));
  }
  if (block.planned_subframes !== null) chips.push(`${block.planned_subframes} frames`);
  chips.push(`${block.imaging_minutes} min imaging`);
  if (block.setup_minutes) chips.push(`${block.setup_minutes} min setup`);
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
    appendTargetIdentity(heading, block.object, block.common_name);
    appendTextElement(heading, "span", "", durationLabel(block.duration_minutes));

    if (block.reason) {
      appendTextElement(card, "p", "schedule-reason", block.reason);
    }

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
  byId("scheduled-summary").hidden = data.schedule.allocated_minutes === 0;
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
  setText(
    "moon-illumination",
    displayNumber(moon.illumination_percent, "% illuminated"),
  );
  setText("moon-phase", moon.phase_name, "Moon phase unavailable");
  setText(
    "moon-altitude",
    `Altitude ${displayNumber(moon.altitude_degrees, "°")}`,
  );
  renderMoonVisual(moon);

  const target = data.recommended_target || data.backup_target;
  const moonPosition = moon.above_horizon ? "above the horizon" : "below the horizon";
  const nextMoonEvent = moon.above_horizon
    ? `sets ${shortTime(moon.next_moonset)}`
    : `rises ${shortTime(moon.next_moonrise)}`;
  const moonImpact = target?.moon_warning
    ? target.moon_warning.replace(/^(None|Minimal) — /, "")
    : "Target impact is unavailable.";
  setText(
    "moon-context",
    `${moon.phase_name || "Moon phase unavailable"} · now ${moonPosition}; ${nextMoonEvent}. During the target window: ${moonImpact}`,
  );
  setText(
    "weather-updated",
    `Weather observed ${displayDateTime(weather.observed_at)} · fetched ${displayDateTime(
      weather.fetched_at,
    )}`,
  );
};

const renderNotes = (notes, decision) => {
  const list = byId("planner-notes");
  list.hidden = decision === "Proceed";
  list.replaceChildren();

  if (list.hidden) return;

  if (!notes || !notes.length) {
    appendTextElement(list, "li", "", "No additional planner cautions tonight.");
    return;
  }

  notes.forEach((note) => appendTextElement(list, "li", "", note));
};

const renderSystem = (data) => {
  const library = data.capture_library;
  const diagnostics = data.diagnostics;
  setText("version", `v${data.version}`);
  setText(
    "matched-count",
    `${library.matched_count} of ${library.database_capture_count}`,
  );
  setText("conflict-count", library.conflict_count);
  const freshness = diagnostics.data_freshness;
  const latestCapture = byId("latest-capture-time");
  latestCapture.textContent = displayDateTime(freshness.latest_capture_observation_utc);
  latestCapture.className = `status-${freshness.status.toLowerCase().replaceAll(" ", "-")}`;
  setText(
    "capture-data-updated",
    displayDateTime(freshness.latest_database_update_utc),
  );
  const libraryStatus = byId("capture-library-status");
  libraryStatus.textContent = library.clean
    ? "Every capture record is linked to its FITS file."
    : library.message || "The capture library needs attention.";
  libraryStatus.className = `library-status status-${library.status
    .toLowerCase()
    .replaceAll(" ", "-")}`;
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
    const top = appendTextElement(card, "div", "target-card-top", "");
    if (target.preview_url) {
      const previewButton = document.createElement("button");
      previewButton.className = "portfolio-preview-button";
      previewButton.type = "button";
      previewButton.setAttribute(
        "aria-label",
        `View ${target.object} portfolio image`,
      );
      const preview = document.createElement("img");
      preview.className = "target-preview";
      preview.width = 76;
      preview.height = 76;
      preview.src = target.preview_url;
      preview.alt = `${target.object}${target.common_name ? ` — ${target.common_name}` : ""} preview`;
      preview.decoding = "async";
      preview.addEventListener(
        "error",
        () => {
          previewButton.remove();
          top.classList.remove("has-preview");
        },
        { once: true },
      );
      top.classList.add("has-preview");
      previewButton.appendChild(preview);
      previewButton.addEventListener("click", () => {
        if (target.preview_image) openImageViewer([target.preview_image]);
      });
      top.appendChild(previewButton);
    }
    const heading = appendTextElement(top, "div", "target-card-heading", "");
    appendTargetIdentity(heading, target.object, target.common_name);
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
      `${target.current_hours} / ${target.goal_hours} hr collected`,
    );
    appendTextElement(progressCopy, "span", "", `${target.progress_percent}%`);
    appendTextElement(
      card,
      "p",
      "target-goal-note",
      `Project integration goal: ${target.goal_hours} hr · ${target.integration_goal_note}`,
    );

    appendTextElement(
      card,
      "p",
      "target-quality",
      target.status === "Complete"
        ? `${target.capture_count} capture${target.capture_count === 1 ? "" : "s"} · integration goal reached`
        : `${target.capture_count} capture${target.capture_count === 1 ? "" : "s"} · ${target.remaining_hours} hr remaining`,
    );
    const displayedScore = target.preview_image?.quality_score;
    appendTextElement(
      card,
      "p",
      "target-image-quality",
      displayedScore === null || displayedScore === undefined
        ? "Displayed image quality: Not scored"
        : `Displayed image quality: ${displayedScore}/100 · ${qualityInterpretation(displayedScore)}`,
    );
    const displayedAnalysis = target.quality_captures.find(
      (capture) => capture.preview_url === target.preview_url,
    );
    appendObjectProfile(
      card,
      target.object,
      target.profile,
      true,
      displayedAnalysis?.components?.stars_detected,
    );
  });
};

const renderQualityByTarget = (data) => {
  const container = byId("quality-targets");
  container.replaceChildren();

  const scoredTargets = [...data.targets]
    .filter((target) => target.average_quality !== null)
    .sort((left, right) => left.object.localeCompare(right.object));

  setText(
    "quality-summary",
    `${scoredTargets.length} scored target${scoredTargets.length === 1 ? "" : "s"}`,
  );

  if (!scoredTargets.length) {
    appendTextElement(
      container,
      "div",
      "empty-state",
      "No targets have quality scores yet.",
    );
    return;
  }

  scoredTargets.forEach((target) => {
    const card = appendTextElement(container, "article", "quality-target-card", "");
    const top = appendTextElement(card, "div", "quality-target-top", "");

    if (target.preview_url) {
      const previewButton = document.createElement("button");
      previewButton.className = "quality-preview-button";
      previewButton.type = "button";
      previewButton.setAttribute(
        "aria-label",
        `View ${target.object} capture images`,
      );
      const preview = document.createElement("img");
      preview.className = "quality-preview";
      preview.width = 76;
      preview.height = 76;
      preview.src = target.preview_url;
      preview.alt = `${target.object}${target.common_name ? ` — ${target.common_name}` : ""} preview`;
      preview.decoding = "async";
      preview.addEventListener(
        "error",
        () => {
          previewButton.replaceWith(
            appendTextElement(
              document.createDocumentFragment(),
              "span",
              "quality-preview quality-preview-placeholder",
              target.object,
            ),
          );
        },
        { once: true },
      );
      previewButton.appendChild(preview);
      previewButton.addEventListener("click", () => {
        const availableImages = target.quality_captures.filter(
          (capture) => capture.preview_url,
        );
        const startIndex = Math.max(
          0,
          availableImages.findIndex(
            (capture) => capture.preview_url === target.preview_url,
          ),
        );
        openImageViewer(availableImages, startIndex);
      });
      top.appendChild(previewButton);
    } else {
      appendTextElement(
        top,
        "span",
        "quality-preview quality-preview-placeholder",
        target.object,
      );
    }

    const heading = appendTextElement(top, "div", "quality-target-heading", "");
    appendTargetIdentity(heading, target.object, target.common_name);
    if (target.scored_capture_count < target.capture_count) {
      appendTextElement(
        heading,
        "span",
        "quality-sample",
        `${target.scored_capture_count} of ${target.capture_count} scored`,
      );
    }

    appendObjectProfile(card, target.object, target.profile);
    const facts = appendTextElement(card, "dl", "quality-facts", "");
    const averageFact = appendTextElement(facts, "div", "", "");
    appendTextElement(averageFact, "dt", "", "Average score");
    appendTextElement(averageFact, "dd", "", `${target.average_quality}/100`);
    const bestFact = appendTextElement(facts, "div", "", "");
    appendTextElement(bestFact, "dt", "", "Best score");
    appendTextElement(bestFact, "dd", "", `${target.best_quality}/100`);
    const latestFact = appendTextElement(facts, "div", "", "");
    appendTextElement(latestFact, "dt", "", "Latest capture");
    appendTextElement(latestFact, "dd", "", displayDate(target.latest_capture));

    const scoreBar = document.createElement("progress");
    scoreBar.className = "quality-score-bar";
    scoreBar.max = 100;
    scoreBar.value = target.average_quality;
    scoreBar.setAttribute(
      "aria-label",
      `${target.object} average quality ${target.average_quality} out of 100`,
    );
    card.appendChild(scoreBar);

    const breakdown = document.createElement("details");
    breakdown.className = "quality-breakdown";
    const summary = appendTextElement(
      breakdown,
      "summary",
      "",
      `Score components for ${target.scored_capture_count} capture${
        target.scored_capture_count === 1 ? "" : "s"
      }`,
    );
    summary.setAttribute("aria-label", `Show ${target.object} score components`);
    const captureList = appendTextElement(
      breakdown,
      "div",
      "quality-capture-list",
      "",
    );
    target.quality_captures.forEach((capture) => {
      const captureRow = appendTextElement(
        captureList,
        "article",
        "quality-capture-row",
        "",
      );
      const captureHeading = appendTextElement(
        captureRow,
        "div",
        "quality-capture-heading",
        "",
      );
      appendTextElement(
        captureHeading,
        "strong",
        "",
        displayDateTime(capture.observation_utc),
      );
      appendTextElement(
        captureHeading,
        "span",
        "",
        `${capture.quality_score}/100`,
      );

      const components = capture.components;
      const componentGrid = appendTextElement(
        captureRow,
        "div",
        "quality-component-grid",
        "",
      );
      appendQualityComponent(
        componentGrid,
        "Base score",
        "Starting value",
        components.base_points,
        50,
      );
      appendQualityComponent(
        componentGrid,
        "Stars detected",
        displayNumber(components.stars_detected),
        components.star_points,
        20,
        "stars",
      );
      appendQualityComponent(
        componentGrid,
        "Background level",
        displayMeasuredNumber(components.background_level),
        components.background_points,
        10,
        "background",
      );
      appendQualityComponent(
        componentGrid,
        "Background variation",
        displayMeasuredNumber(components.background_variation),
        components.variation_points,
        15,
        "variation",
      );
      appendQualityComponent(
        componentGrid,
        "Trailing",
        components.trailing_detected === null
          ? "Not measured"
          : components.trailing_detected ? "Detected" : "Not detected",
        components.trailing_points,
        5,
        "trailing",
      );
      appendImageButton(captureRow, "View image", [capture]);
    });
    card.appendChild(breakdown);
  });
};

const renderRecentCaptures = (data) => {
  const container = byId("recent-captures");
  container.replaceChildren();
  setText(
    "capture-summary",
    data.recent_captures.length === data.metrics.captures
      ? `${data.metrics.captures} total`
      : `${data.recent_captures.length} of ${data.metrics.captures}`,
  );

  if (!data.recent_captures.length) {
    appendTextElement(container, "div", "empty-state", "No captures recorded yet.");
    return;
  }

  data.recent_captures.forEach((capture) => {
    const card = appendTextElement(container, "article", "activity-card", "");
    const top = appendTextElement(card, "div", "activity-card-top", "");
    const heading = appendTextElement(top, "div", "activity-heading", "");
    appendTargetIdentity(heading, capture.object, capture.common_name);

    const facts = appendTextElement(card, "div", "activity-facts", "");
    appendFact(facts, "Captured", displayDateTime(capture.observation_utc));
    appendFact(facts, "Total integration", integrationLabel(capture.total_integration_seconds));
    appendFact(facts, "Subframes", capture.subframe_count);
    appendFact(facts, "Sub-exposure", displayNumber(capture.sub_exposure_seconds, " sec"));
    appendFact(facts, "Gain", displayNumber(capture.gain));
    appendFact(facts, "Filter", friendlyFilterLabel(capture.filter_name));
    appendFact(
      facts,
      "Captured at",
      capture.location || "Location not recorded",
    );
    appendFact(facts, "Bortle class", bortleLabel(capture.bortle_class));
    appendFact(
      facts,
      "Capture quality",
      capture.quality_score === null ? "Not scored" : `${capture.quality_score}/100`,
    );
    appendImageButton(card, "View image", [capture]);
  });
};

let captureLocationMap;
let captureLocationMarkers;
let captureLocationMapInitialized = false;

const BORTLE_COLORS = {
  1: "#171717",
  2: "#555a60",
  3: "#2864ff",
  4: "#23d44f",
  5: "#e7dd28",
  6: "#ff9800",
  7: "#ff2217",
  8: "#f3f5f7",
  9: "#ffffff",
};

const BORTLE_NAMES = {
  1: "excellent dark sky",
  2: "average dark sky",
  3: "rural sky",
  4: "rural/suburban transition",
  5: "suburban",
  6: "bright suburban",
  7: "suburban/urban transition",
  8: "city sky",
  9: "inner city sky",
};

const renderCaptureLocations = (data) => {
  const container = byId("capture-location-map");
  const bortleMapKey = byId("bortle-map-key");
  bortleMapKey.replaceChildren();
  const recordedLocations = data.capture_locations || [];
  const locations = isMapOverlapDemo
    ? [
      ...recordedLocations,
      {
        location: "Prescott, AZ (simulation)",
        city_label: "Prescott, AZ (simulated)",
        latitude: 34.54,
        longitude: -112.4685,
        capture_count: 1,
        bortle_class: 4,
      },
    ]
    : recordedLocations;
  const demoNotice = byId("location-map-demo");
  demoNotice.hidden = !isMapOverlapDemo;
  setText(
    "location-map-summary",
    locations.length === 1 ? "1 location" : `${locations.length} locations`,
  );
  setText(
    "tracked-location-summary",
    locations.length === 1 ? "1 site" : `${locations.length} sites`,
  );
  [...new Set(
    locations
      .map((location) => location.bortle_class)
      .filter((bortleClass) => bortleClass !== null && bortleClass !== undefined),
  )]
    .sort((left, right) => left - right)
    .forEach((bortleClass) => {
      const keyItem = appendTextElement(bortleMapKey, "span", "bortle-map-key-item", "");
      const swatch = appendTextElement(keyItem, "span", "bortle-map-key-swatch", "");
      swatch.style.background = BORTLE_COLORS[bortleClass] || "#4fd4c5";
      appendTextElement(
        keyItem,
        "span",
        "",
        `Bortle ${bortleClass} · ${BORTLE_NAMES[bortleClass] || "unclassified"}`,
      );
    });

  if (!locations.length) {
    if (captureLocationMap) {
      captureLocationMap.remove();
      captureLocationMap = null;
      captureLocationMarkers = null;
      captureLocationMapInitialized = false;
    }
    container.replaceChildren();
    appendTextElement(container, "div", "empty-state", "No mapped capture locations are recorded yet.");
    return;
  }

  if (!window.L) {
    container.replaceChildren();
    appendTextElement(container, "div", "empty-state", "Interactive map controls are unavailable.");
    return;
  }
  if (!captureLocationMap) {
    container.replaceChildren();
    captureLocationMap = window.L.map(container, {
      scrollWheelZoom: true,
      worldCopyJump: true,
      minZoom: 2,
    });
    window.L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        maxZoom: 19,
        attribution: "© OpenStreetMap contributors",
      },
    ).addTo(captureLocationMap);
    captureLocationMarkers = window.L.featureGroup().addTo(captureLocationMap);
  } else {
    captureLocationMarkers.clearLayers();
  }

  locations.forEach((location, index) => {
    const bortleColor = BORTLE_COLORS[location.bortle_class] || "#4fd4c5";
    const captureMarker = window.L.circleMarker(
      [location.latitude, location.longitude],
      {
        radius: 11,
        color: "#efffff",
        weight: 3,
        fillColor: bortleColor,
        fillOpacity: 0.92,
      },
    ).addTo(captureLocationMarkers);
    captureMarker.bindTooltip(`${location.city_label}`, { direction: "top" });
    const popup = document.createElement("div");
    appendTextElement(popup, "strong", "", location.city_label);
    appendTextElement(
      popup,
      "div",
      "",
      `${location.capture_count} capture${location.capture_count === 1 ? "" : "s"} · ${location.bortle_class === null || location.bortle_class === undefined ? "Bortle not recorded" : `Bortle ${location.bortle_class}`}`,
    );
    captureMarker.bindPopup(popup);
  });
  if (!captureLocationMapInitialized) {
    captureLocationMap.fitBounds(captureLocationMarkers.getBounds(), {
      padding: [42, 42],
      maxZoom: 5,
    });
    captureLocationMapInitialized = true;
  }
};

const renderHistoryError = () => {
  setText("portfolio-summary", "Unavailable");
  setText("quality-summary", "Unavailable");
  setText("capture-summary", "Unavailable");
  ["target-portfolio", "quality-targets", "recent-captures", "capture-location-map", "bortle-map-key"].forEach((id) => {
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
    fetch(`/dashboard?include_all_history=${historyExpanded}`, { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`Dashboard endpoint returned ${response.status}.`);
      return response.json();
    }),
  ]);

  if (planResult.status === "fulfilled") {
    const data = isImmaculateDemo
      ? applyImmaculateDemo(
        planResult.value,
        dashboardResult.status === "fulfilled" ? dashboardResult.value : null,
      )
      : planResult.value;
    renderDecision(data);
    renderSchedule(data.schedule);
    renderConditions(data);
    renderNotes(data.schedule.notes, data.schedule.decision);
  } else {
    showPlanError(planResult.reason.message);
  }

  if (systemResult.status === "fulfilled") {
    renderSystem(systemResult.value);
  } else {
    setText("capture-library-status", "Capture-library status is unavailable.");
  }

  if (dashboardResult.status === "fulfilled") {
    renderPortfolio(dashboardResult.value);
    renderQualityByTarget(dashboardResult.value);
    await renderCaptureLocations(dashboardResult.value);
    renderRecentCaptures(dashboardResult.value);
  } else {
    renderHistoryError();
  }

  const refreshedAt = new Date();
  setText("page-refreshed", `Page refreshed ${refreshedAt.toLocaleTimeString()}`);
  const weatherFetchedAt = planResult.status === "fulfilled"
    ? displayDateTime(planResult.value.weather.fetched_at)
    : "unavailable";
  const historyGeneratedAt = dashboardResult.status === "fulfilled"
    ? displayDateTime(dashboardResult.value.generated_at)
    : "unavailable";
  setText(
    "data-updated",
    `Weather fetched ${weatherFetchedAt} · Capture history generated ${historyGeneratedAt}`,
  );
  refresh.disabled = false;
  refresh.textContent = refreshButtonLabel();
};

const toggleHistory = async () => {
  const button = byId("history-toggle");
  const nextExpanded = !historyExpanded;
  button.disabled = true;
  button.textContent = nextExpanded ? "Loading all history…" : "Showing recent history…";

  try {
    const response = await fetch(
      `/dashboard?include_all_history=${nextExpanded}`,
      { cache: "no-store" },
    );
    if (!response.ok) throw new Error(`Dashboard endpoint returned ${response.status}.`);
    const data = await response.json();
    historyExpanded = nextExpanded;
    renderRecentCaptures(data);
    button.textContent = historyExpanded ? "Show recent history" : "Show all history";
  } catch (error) {
    button.textContent = "Show all history";
    byId("load-error").textContent = error.message;
    byId("load-error").hidden = false;
  } finally {
    button.disabled = false;
  }
};

const runDashboardLoad = () => {
  loadDashboard().catch((error) => {
    showPlanError(error.message);
    const refresh = byId("refresh-button");
    refresh.disabled = false;
    refresh.textContent = refreshButtonLabel();
    setText("page-refreshed", "Page refresh failed");
  });
};

const imageDialog = byId("image-dialog");
const imageDialogImage = byId("image-dialog-image");

imageDialogImage.addEventListener("load", () => {
  imageDialogImage.hidden = false;
  byId("image-dialog-error").hidden = true;
});
imageDialogImage.addEventListener("error", () => {
  imageDialogImage.hidden = true;
  byId("image-dialog-error").hidden = false;
});
byId("image-dialog-close").addEventListener("click", () => {
  if (typeof imageDialog.close === "function") imageDialog.close();
  else imageDialog.removeAttribute("open");
});
byId("image-dialog-previous").addEventListener("click", () => {
  if (imageViewerIndex > 0) {
    imageViewerIndex -= 1;
    renderImageViewerItem();
  }
});
byId("image-dialog-next").addEventListener("click", () => {
  if (imageViewerIndex < imageViewerItems.length - 1) {
    imageViewerIndex += 1;
    renderImageViewerItem();
  }
});
const qualityInfoDialog = byId("quality-info-dialog");
byId("quality-info-close").addEventListener("click", () => {
  if (typeof qualityInfoDialog.close === "function") qualityInfoDialog.close();
  else qualityInfoDialog.removeAttribute("open");
});
imageDialog.addEventListener("close", () => {
  imageDialogImage.removeAttribute("src");
  imageViewerItems = [];
  imageViewerIndex = 0;
});

activateCurrentView();
byId("refresh-button").addEventListener("click", runDashboardLoad);
byId("history-toggle").addEventListener("click", () => {
  toggleHistory();
});
runDashboardLoad();
