"use strict";

const byId = (id) => document.getElementById(id);

const authConfig = window.POLARIS_AUTH_CONFIG || { mode: "local" };
const usesHostedAuth = authConfig.mode === "supabase";
const EQ_MODE_PREFERENCE_KEY = "polaris.eqModeEnabled";
let supabaseClient = null;
let hostedSession = null;
let hostedObservatory = null;
let hostedProfile = null;
let hostedRecommendationRunId = null;
const invitationHash = new URLSearchParams(window.location.hash.slice(1));
const invitationQuery = new URLSearchParams(window.location.search);
let isInvitationFlow = (
  invitationHash.get("type") === "invite" || invitationQuery.get("type") === "invite"
);
let isPasswordRecoveryFlow = (
  invitationHash.get("type") === "recovery" || invitationQuery.get("type") === "recovery"
);

const readEqModePreference = () => {
  try {
    return window.localStorage.getItem(EQ_MODE_PREFERENCE_KEY) === "true";
  } catch {
    return false;
  }
};

const saveEqModePreference = (enabled) => {
  try {
    window.localStorage.setItem(EQ_MODE_PREFERENCE_KEY, String(enabled));
  } catch {
    // The dashboard still works when browser storage is unavailable.
  }
};

const applyEqModePreference = (enabled) => {
  byId("eq-mode-checkbox").checked = enabled;
  byId("hosted-eq-mode-checkbox").checked = enabled;
};

const rememberEqModePreference = (event) => {
  const enabled = event.target.checked;
  saveEqModePreference(enabled);
  applyEqModePreference(enabled);
};

// Keep the Tonight view useful when a catalog response is temporarily missing
// its optional reference-image metadata. The server remains the source of
// truth; this simply gives known targets a safe, official display fallback.
const TARGET_REFERENCE_IMAGE_FALLBACKS = {
  C20: {
    thumbnail_url: "https://cdn.esahubble.org/archives/images/thumb300y/heic0510a.jpg",
    source_url: "https://esahubble.org/images/heic0510a/",
    source_label: "ESA/Hubble",
    alt: "North America Nebula reference image from ESA/Hubble",
  },
};

const apiFetch = async (input, options = {}) => {
  const headers = new Headers(options.headers || {});
  if (hostedSession?.access_token) {
    headers.set("Authorization", `Bearer ${hostedSession.access_token}`);
  }
  return fetch(input, { ...options, headers });
};

const setAuthMessage = (message, targetId = "auth-message") => {
  setText(targetId, message, "");
};

const setHostedShell = (signedIn) => {
  byId("auth-gate").hidden = signedIn;
  byId("hosted-account-main").hidden = !signedIn;
  byId("main-content").hidden = signedIn;
  document.querySelector(".app-nav").hidden = signedIn;
  byId("simulation-banner").hidden = true;
  byId("account-control").hidden = !signedIn;
  byId("refresh-button").closest(".refresh-control").hidden = signedIn;
  byId("eq-mode-checkbox").closest(".tracking-mode-control").hidden = signedIn;
  document.querySelector(".readonly-badge").hidden = signedIn;
};

const showPasswordSetup = () => {
  setHostedShell(false);
  byId("sign-in-form").hidden = true;
  byId("accept-invite-form").hidden = false;
  const isRecovery = isPasswordRecoveryFlow;
  setText("auth-gate-title", isRecovery ? "Choose a new Polaris password" : "Choose your Polaris password");
  setAuthMessage(
    isRecovery
      ? "Use this only if you already created a Polaris password and asked to reset it."
      : "This private invitation lets you create your Polaris password for the first time.",
    "invite-message",
  );
};

const showSignIn = () => {
  byId("sign-in-form").hidden = false;
  byId("accept-invite-form").hidden = true;
  setText("auth-gate-title", "Sign in to Polaris");
};

const updateHostedAccountForm = (profile, observatory) => {
  byId("profile-display-name").value = profile?.display_name || "";
  byId("hosted-observatory-name").value = observatory?.name || "Home";
  byId("hosted-latitude").value = observatory?.latitude ?? "";
  byId("hosted-longitude").value = observatory?.longitude ?? "";
  byId("hosted-timezone").value = observatory?.timezone_name
    || Intl.DateTimeFormat().resolvedOptions().timeZone
    || "";
  byId("hosted-bortle").value = observatory?.bortle_class ?? "";
  byId("hosted-telescope-model").value = observatory?.telescope_model || "";
  byId("hosted-tracking-preference").value = observatory?.tracking_preference || "not_sure";
  byId("hosted-coordinates-approximate").checked = observatory
    ? Boolean(observatory.coordinates_are_approximate)
    : true;
};

const roundedApproximateCoordinate = (value) => Number(Number(value).toFixed(2));

const useDeviceLocation = () => {
  const button = byId("hosted-use-device-location");
  if (!navigator.geolocation) {
    setAuthMessage(
      "This browser cannot provide a location. Enter latitude and longitude manually below.",
      "hosted-location-message",
    );
    return;
  }

  button.disabled = true;
  setAuthMessage("Asking your browser for a general location…", "hosted-location-message");
  navigator.geolocation.getCurrentPosition(
    (position) => {
      byId("hosted-latitude").value = roundedApproximateCoordinate(position.coords.latitude);
      byId("hosted-longitude").value = roundedApproximateCoordinate(position.coords.longitude);
      byId("hosted-coordinates-approximate").checked = true;
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (timezone) byId("hosted-timezone").value = timezone;
      setAuthMessage(
        "Location added. Polaris will save only an approximate neighborhood-level location.",
        "hosted-location-message",
      );
      button.disabled = false;
    },
    (error) => {
      const message = error.code === error.PERMISSION_DENIED
        ? "Location permission was not allowed. Enter latitude and longitude manually below."
        : "Polaris could not get your location. Enter latitude and longitude manually below.";
      setAuthMessage(message, "hosted-location-message");
      button.disabled = false;
    },
    { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 },
  );
};

const showHostedAccountLoading = (message = "") => {
  byId("hosted-account-panel").hidden = true;
  byId("hosted-tonight-panel").hidden = true;
  byId("hosted-ready-panel").hidden = true;
  byId("hosted-account-loading").hidden = false;
  byId("hosted-account-retry").hidden = !message;
  setText(
    "hosted-account-loading-message",
    message,
    "Checking your saved observing home before building tonight's plan.",
  );
};

const showHostedAccountSetup = (message = "") => {
  byId("hosted-account-loading").hidden = true;
  byId("hosted-account-retry").hidden = true;
  byId("hosted-tonight-panel").hidden = true;
  byId("hosted-ready-panel").hidden = true;
  byId("hosted-account-panel").hidden = false;
  byId("hosted-account-cancel").hidden = !hostedObservatory;
  if (message) setAuthMessage(message, "hosted-account-message");
};

const showHostedReadyHandoff = () => {
  byId("hosted-account-loading").hidden = true;
  byId("hosted-account-retry").hidden = true;
  byId("hosted-account-panel").hidden = true;
  byId("hosted-tonight-panel").hidden = true;
  byId("hosted-ready-panel").hidden = false;
  setAuthMessage("", "hosted-account-message");
};

const showHostedTonight = () => {
  byId("hosted-account-loading").hidden = true;
  byId("hosted-account-retry").hidden = true;
  byId("hosted-account-panel").hidden = true;
  byId("hosted-ready-panel").hidden = true;
  byId("hosted-tonight-panel").hidden = false;
  setAuthMessage("", "hosted-account-message");
};

const resetHostedPlanDetails = () => {
  setText("hosted-tonight-date", "Building tonight's recommendation…");
  setText("hosted-target-label", "Primary target");
  setText("hosted-target-name", "—");
  setText("hosted-target-common-name", "");
  setText("hosted-target-reason", "Waiting for tonight's target.");
  setText("hosted-target-window", "—");
  setText("hosted-target-exposure", "—");
  setText("hosted-target-gain", "—");
  setText("hosted-target-filter", "—");
  setText("hosted-darkness-window", "—");
  setText("hosted-weather-summary", "—");
  renderSkyQuality(null);
  setText("hosted-weather-updated", "Weather time unavailable");
  const weatherDiagnostic = byId("hosted-weather-diagnostic");
  weatherDiagnostic.hidden = true;
  weatherDiagnostic.textContent = "";
  setText("hosted-moon-summary", "—");
  setText("hosted-moon-context", "Moon position unavailable");
  const notes = byId("hosted-plan-notes");
  notes.replaceChildren();
  notes.hidden = true;
  const scheduleList = byId("hosted-schedule-list");
  scheduleList.replaceChildren();
  appendTextElement(
    scheduleList,
    "div",
    "empty-state",
    "Building tonight's schedule…",
  );
  setText("hosted-schedule-count", "0 blocks");
  renderHostedReferenceImage(null);
};

const setHostedPlanLoading = () => {
  const card = byId("hosted-recommendation");
  card.className = "hosted-recommendation status-loading";
  setText("hosted-decision", "Checking conditions…");
  setText(
    "hosted-decision-message",
    "Comparing weather, darkness, Moon conditions, and target visibility.",
  );
  resetHostedPlanDetails();
  setText("hosted-plan-message", "Refreshing tonight's recommendation…");
  hostedRecommendationRunId = null;
  byId("hosted-feedback-panel").hidden = true;
  byId("hosted-feedback-yes").classList.remove("selected");
  byId("hosted-feedback-no").classList.remove("selected");
  byId("hosted-feedback-detail").hidden = true;
  byId("hosted-feedback-reason").value = "";
  setText("hosted-feedback-message", "");
};

const hostedPlanFailureMessage = (requestId = "") => {
  const requestNote = requestId
    ? ` If this keeps happening, send Doug request ID ${requestId}.`
    : "";
  return `Polaris could not build tonight's plan. Try Refresh tonight once more.${requestNote}`;
};

const renderHostedReferenceImage = (target) => {
  const link = byId("hosted-reference-image");
  const image = byId("hosted-reference-image-thumbnail");
  const label = byId("hosted-reference-image-label");
  const targetKey = String(target?.object || "")
    .replaceAll(/\s/g, "")
    .toUpperCase();
  const reference = target?.reference_image || TARGET_REFERENCE_IMAGE_FALLBACKS[targetKey];

  if (!reference?.thumbnail_url || !reference?.source_url) {
    link.hidden = true;
    image.removeAttribute("src");
    return;
  }

  link.href = reference.source_url;
  image.src = reference.thumbnail_url;
  image.alt = reference.alt || "Official target reference image";
  label.textContent = `Reference image · ${reference.source_label || "source"}`;
  image.onerror = () => {
    link.hidden = true;
  };
  link.hidden = false;
};

const renderLegacyReferenceImage = (target) => {
  const link = byId("target-reference-image");
  const image = byId("target-reference-image-thumbnail");
  const label = byId("target-reference-image-label");
  const targetKey = String(target?.object || "")
    .replaceAll(/\s/g, "")
    .toUpperCase();
  const reference = target?.reference_image || TARGET_REFERENCE_IMAGE_FALLBACKS[targetKey];

  if (!reference?.thumbnail_url || !reference?.source_url) {
    link.hidden = true;
    image.removeAttribute("src");
    return;
  }

  link.href = reference.source_url;
  image.src = reference.thumbnail_url;
  image.alt = reference.alt || "Official target reference image";
  label.textContent = `Reference image · ${reference.source_label || "source"}`;
  image.onerror = () => {
    link.hidden = true;
  };
  link.hidden = false;
};

const skyQualityStars = (score) => {
  if (score === null || score === undefined) return 0;
  if (score >= 90) return 5;
  if (score >= 75) return 4;
  if (score >= 60) return 3;
  if (score >= 40) return 2;
  return 1;
};

const renderSkyQuality = (rating) => {
  const container = byId("hosted-sky-quality");
  container.replaceChildren();
  if (!rating || rating.quality === "Unavailable") {
    container.textContent = "Sky quality unavailable";
    return;
  }

  const stars = skyQualityStars(rating.score);
  const text = appendTextElement(
    container,
    "span",
    "sky-quality-stars",
    "★".repeat(stars) + "☆".repeat(5 - stars),
  );
  text.setAttribute("aria-label", `${stars} of 5 stars`);
  appendTextElement(container, "span", "", ` ${rating.quality}`);
  const button = appendTextElement(container, "button", "quality-info-button", "i");
  button.type = "button";
  button.setAttribute("aria-label", "About this sky-quality rating");
  button.addEventListener("click", () => {
    const details = (rating.deductions || [])
      .map((deduction) => `${deduction.label}: −${displayMeasuredNumber(deduction.points)} points`)
      .join(" · ");
    openInfoDialog(
      "Sky quality",
      `${rating.quality} — ${stars} of 5 stars`,
      "A planning estimate based on cloud cover, humidity, wind, Moon brightness, and the Moon's distance from the selected target. It is not a score of your photographs.",
      `Current details: ${rating.score}/100${details ? ` · ${details}` : ""}`,
    );
  });
};

const renderHostedSchedule = (schedule) => {
  const container = byId("hosted-schedule-list");
  const blocks = schedule?.blocks || [];
  container.replaceChildren();
  setText(
    "hosted-schedule-count",
    `${blocks.length} block${blocks.length === 1 ? "" : "s"}`,
  );

  if (!blocks.length) {
    const emptyScheduleMessage = schedule?.decision === "Do Not Image"
      ? "No imaging is scheduled while conditions are unsuitable."
      : schedule?.decision === "Plan unavailable"
        ? "Tonight's schedule could not be refreshed yet. Try again in a moment."
        : "No target met the visibility and minimum-time requirements.";
    appendTextElement(
      container,
      "div",
      "empty-state",
      emptyScheduleMessage,
    );
    return;
  }

  blocks.forEach((block) => {
    const card = appendTextElement(container, "article", "hosted-schedule-block", "");
    const time = appendTextElement(card, "div", "hosted-schedule-time", "");
    appendTextElement(time, "strong", "", shortTime(block.start));
    appendTextElement(time, "span", "", `to ${shortTime(block.end)}`);

    const body = appendTextElement(card, "div", "hosted-schedule-body", "");
    const identity = appendTextElement(body, "div", "hosted-schedule-identity", "");
    const runLabel = block.total_runs > 1
      ? ` · Run ${block.run_number} of ${block.total_runs}`
      : "";
    appendTextElement(
      identity,
      "strong",
      "",
      `${block.object || "Unknown target"}${runLabel}`,
    );
    appendTextElement(identity, "span", "", block.common_name || "");
    if (block.reason) appendTextElement(body, "p", "", block.reason);

    const settings = appendTextElement(body, "div", "hosted-schedule-settings", "");
    equipmentChips(block).forEach((chip) => {
      const element = appendTextElement(settings, "span", "", chip.label);
      if (chip.title) element.title = chip.title;
      if (chip.filterValue) appendFilterInfoButton(element, chip.filterValue);
    });
    appendSettingsInfoButton(settings, block);
  });
};

const displayedTargetSettings = (target, schedule) => {
  const settings = { ...(target?.recommended_settings || {}) };
  const firstScheduledBlock = (schedule?.blocks || []).find(
    (block) => block.object === target?.object,
  );
  if (!firstScheduledBlock) return settings;

  return {
    ...settings,
    exposure_seconds:
      firstScheduledBlock.recommended_sub_exposure_seconds
      ?? settings.exposure_seconds,
    gain: firstScheduledBlock.recommended_gain ?? settings.gain,
    filter_name:
      firstScheduledBlock.recommended_filter ?? settings.filter_name,
  };
};

const renderHostedTonight = (data) => {
  const schedule = data.schedule || {};
  const decision = schedule.decision || "Conditions Unknown";
  const statusClass = `status-${decision.toLowerCase().replaceAll(" ", "-")}`;
  byId("hosted-recommendation").className = `hosted-recommendation ${statusClass}`;
  setText("hosted-tonight-observatory", data.observatory?.name, "your observatory");
  setText("observatory-name", data.observatory?.name, "Your observatory");
  setText("hosted-tonight-date", `Plan for ${displayDate(data.date)}`);
  setText("hosted-decision", decision);
  setText(
    "hosted-decision-message",
    decision === "Use Caution"
      ? "Conditions are usable, but one or more factors need attention before imaging."
      : data.message,
    "Recommendation available.",
  );

  const target = data.recommended_target || data.backup_target;
  setText(
    "hosted-target-label",
    data.recommended_target ? "Primary target" : "Fallback if conditions improve",
  );
  if (target) {
    const settings = displayedTargetSettings(target, schedule);
    setText("hosted-target-name", target.object, "Unknown target");
    setText("hosted-target-common-name", target.common_name, "");
    setText("hosted-target-reason", target.reason, "Planner recommendation available.");
    setText(
      "hosted-target-window",
      targetWindowLabel(target.recommended_start, target.recommended_end),
    );
    setText(
      "hosted-target-exposure",
      displayNumber(settings.exposure_seconds, " sec"),
    );
    setText("hosted-target-gain", displayNumber(settings.gain));
    renderFilterValue("hosted-target-filter", settings.filter_name);
    renderHostedReferenceImage(target);
  } else {
    setText("hosted-target-name", "No target");
    setText("hosted-target-common-name", "");
    setText("hosted-target-reason", "No target currently meets the planner requirements.");
    setText("hosted-target-window", "No usable window");
    setText("hosted-target-exposure", null);
    setText("hosted-target-gain", null);
    setText("hosted-target-filter", null);
    renderHostedReferenceImage(null);
  }

  const darkness = data.darkness || {};
  const weather = data.weather || {};
  const moon = data.moon || {};
  setText(
    "hosted-darkness-window",
    `${shortTime(darkness.astronomical_darkness_start)}–${shortTime(
      darkness.astronomical_darkness_end,
    )}`,
  );
  renderSkyQuality(data.night_rating);
  setText(
    "hosted-weather-summary",
    `${displayNumber(
      weather.planned_cloud_cover_percent ?? weather.cloud_cover_percent,
      "% clouds",
    )} · ${displayNumber(
      weather.planned_wind_speed_mph ?? weather.wind_speed_mph,
      " mph wind",
    )}`,
  );
  setText(
    "hosted-weather-updated",
    weather.planned_temperature_at
      ? `Forecast for ${displayDateTime(weather.planned_temperature_at)}`
      : weather.observed_at
      ? `Observed ${displayDateTime(weather.observed_at)}`
      : "Weather time unavailable",
  );
  const weatherDiagnostic = byId("hosted-weather-diagnostic");
  const weatherUnavailable =
    weather.status && weather.status.toLowerCase().includes("unavailable");
  weatherDiagnostic.hidden = !weatherUnavailable;
  weatherDiagnostic.textContent = weatherUnavailable
    ? weather.status
    : "";
  setText(
    "hosted-moon-summary",
    `${moon.phase_name || "Moon"} · ${displayNumber(
      moon.illumination_percent,
      "% illuminated",
    )}`,
  );
  setText(
    "hosted-moon-context",
    moon.above_horizon
      ? moon.next_moonset
        ? `Above horizon now · sets ${shortTime(moon.next_moonset)}`
        : "Above horizon now"
      : moon.next_moonrise
        ? `Below horizon now · rises ${shortTime(moon.next_moonrise)}`
        : "Below horizon now",
  );

  const notes = byId("hosted-plan-notes");
  notes.replaceChildren();
  const visibleNotes = (schedule.notes || []).filter(
    (note) =>
      note &&
      note !== data.message &&
      !note.toLowerCase().startsWith("use caution:") &&
      note !== "Review live conditions before starting any scheduled block.",
  );
  notes.hidden = decision === "Proceed" || visibleNotes.length === 0;
  renderAdvisoryNotes(notes, visibleNotes);
  renderHostedSchedule(schedule);
  hostedRecommendationRunId = data.recommendation_run_id || null;
  byId("hosted-feedback-panel").hidden = !hostedRecommendationRunId;
  setText(
    "hosted-plan-message",
    `Plan refreshed ${new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}.`,
  );
  const weatherTimestamp =
    weather.planned_temperature_at || weather.observed_at || weather.fetched_at;
  setText(
    "data-updated",
    weatherTimestamp
      ? `Weather data ${displayDateTime(weatherTimestamp)}`
      : "Weather data time unavailable",
  );
};

const loadHostedTonight = async () => {
  const refresh = byId("hosted-refresh-button");
  refresh.disabled = true;
  refresh.textContent = "Refreshing…";
  setHostedPlanLoading();
  showHostedTonight();

  try {
    const eqEnabled = byId("hosted-eq-mode-checkbox").checked;
    const response = await apiFetch(
      `/tonight?equatorial_mode_enabled=${eqEnabled}`,
      {
        method: "POST",
        cache: "no-store",
      },
    );
    if (response.status === 409) {
      showHostedAccountSetup("Add an observing home before building tonight's plan.");
      return;
    }
    if (!response.ok) {
      throw new Error(hostedPlanFailureMessage(response.headers.get("X-Request-ID") || ""));
    }
    renderHostedTonight(await response.json());
  } catch (error) {
    byId("hosted-recommendation").className = "hosted-recommendation status-error";
    setText("hosted-decision", "Plan unavailable");
    setText("hosted-decision-message", error.message);
    setText("hosted-target-reason", "Your observing home is still saved. This is a planning refresh problem, not a telescope-control action.");
    renderHostedSchedule({ decision: "Plan unavailable", blocks: [] });
    setText("hosted-plan-message", "Try Refresh tonight again. If it fails twice, send Doug the request ID and a screenshot.");
  } finally {
    refresh.disabled = false;
    refresh.textContent = "Refresh tonight";
  }
};

const saveHostedPlanFeedback = async (useful, reason = null) => {
  if (!hostedRecommendationRunId) return;

  const yesButton = byId("hosted-feedback-yes");
  const noButton = byId("hosted-feedback-no");
  const saveNoteButton = byId("hosted-feedback-save-note");
  yesButton.disabled = true;
  noButton.disabled = true;
  saveNoteButton.disabled = true;
  setText("hosted-feedback-message", "Saving your response…");

  try {
    const response = await apiFetch(
      `/recommendations/${hostedRecommendationRunId}/feedback`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ useful, reason }),
      },
    );
    if (!response.ok) {
      throw new Error("Polaris could not save your response. Please try again.");
    }
    yesButton.classList.toggle("selected", useful);
    noButton.classList.toggle("selected", !useful);
    setText(
      "hosted-feedback-message",
      reason ? "Thank you—your note was saved." : "Thank you—your response was saved.",
    );
  } catch (error) {
    setText("hosted-feedback-message", error.message);
  } finally {
    yesButton.disabled = false;
    noButton.disabled = false;
    saveNoteButton.disabled = false;
  }
};

const loadHostedAccount = async () => {
  const profileResponse = await apiFetch("/profile", { cache: "no-store" });
  let profile = null;
  if (profileResponse.status === 404) {
    setText("hosted-account-state", "Setup needed");
    setText(
      "hosted-account-intro",
      "Add your name and one observing location. You can use an approximate location if you prefer not to save your exact address.",
    );
  } else if (!profileResponse.ok) {
    throw new Error("Polaris could not load your account. Please sign out and try again.");
  } else {
    profile = await profileResponse.json();
  }

  const observatoryResponse = await apiFetch("/observatories", { cache: "no-store" });
  if (!observatoryResponse.ok) {
    throw new Error("Polaris could not load your observing location. Please try again.");
  }
  const observatories = await observatoryResponse.json();
  hostedObservatory = observatories[0] || null;
  hostedProfile = profile;
  updateHostedAccountForm(profile, hostedObservatory);
  setText(
    "observatory-name",
    hostedObservatory?.name,
    hostedObservatory ? "Your observatory" : "Setup required",
  );

  if (profile && hostedObservatory) {
    setText("hosted-account-state", "Observing home saved");
    setText(
      "hosted-account-intro",
      "Update the location Polaris uses for your nightly recommendations.",
    );
    await loadHostedTonight();
  } else {
    showHostedAccountSetup();
  }
};

const saveHostedAccount = async (event) => {
  event.preventDefault();
  const submit = event.currentTarget.querySelector("button[type='submit']");
  submit.disabled = true;
  setAuthMessage("Saving your observing home…", "hosted-account-message");

  try {
    const isFirstObservingHome = !hostedObservatory;
    const profileResponse = await apiFetch("/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        display_name: byId("profile-display-name").value.trim(),
        onboarding_state: "observatory",
      }),
    });
    if (!profileResponse.ok) {
      throw new Error("Polaris could not save your profile. Please try again.");
    }

    const useApproximateLocation = byId("hosted-coordinates-approximate").checked;
    const latitude = Number(byId("hosted-latitude").value);
    const longitude = Number(byId("hosted-longitude").value);
    const observatoryPayload = {
      name: byId("hosted-observatory-name").value.trim(),
      latitude: useApproximateLocation ? roundedApproximateCoordinate(latitude) : latitude,
      longitude: useApproximateLocation ? roundedApproximateCoordinate(longitude) : longitude,
      timezone_name: byId("hosted-timezone").value.trim(),
      bortle_class: byId("hosted-bortle").value
        ? Number(byId("hosted-bortle").value)
        : null,
      coordinates_are_approximate: useApproximateLocation,
      telescope_model: byId("hosted-telescope-model").value || null,
      tracking_preference: byId("hosted-tracking-preference").value,
    };
    const observatoryResponse = await apiFetch(
      hostedObservatory ? `/observatories/${hostedObservatory.id}` : "/observatories",
      {
        method: hostedObservatory ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(observatoryPayload),
      },
    );
    if (!observatoryResponse.ok) {
      throw new Error("Polaris could not save your observing location. Check the values and try again.");
    }
    hostedObservatory = await observatoryResponse.json();
    hostedProfile = await profileResponse.json();
    setText("hosted-account-state", "Observing home saved");
    setText(
      "hosted-account-intro",
      "Update the location Polaris uses for your nightly recommendations.",
    );
    if (isFirstObservingHome) {
      showHostedReadyHandoff();
    } else {
      setAuthMessage("Saved. Building tonight's plan…", "hosted-account-message");
      await loadHostedTonight();
    }
  } catch (error) {
    setAuthMessage(error.message, "hosted-account-message");
  } finally {
    submit.disabled = false;
  }
};

const handleHostedSession = async (session) => {
  hostedSession = session;
  if (!session) {
    setHostedShell(false);
    showSignIn();
    setAuthMessage("");
    return;
  }
  if (isInvitationFlow || isPasswordRecoveryFlow) {
    showPasswordSetup();
    return;
  }
  setHostedShell(true);
  showHostedAccountLoading();
  setText("account-email", session.user?.email || "Signed in");
  try {
    await loadHostedAccount();
  } catch (error) {
    showHostedAccountLoading(error.message);
  }
};

const retryHostedAccountLoad = async () => {
  if (!hostedSession) return;
  showHostedAccountLoading();
  try {
    await loadHostedAccount();
  } catch (error) {
    showHostedAccountLoading(error.message);
  }
};

const initializeHostedAuth = async () => {
  if (!authConfig.supabaseUrl || !authConfig.supabasePublishableKey) {
    setHostedShell(false);
    setAuthMessage("Polaris sign-in is not configured yet. Please contact the operator.");
    return;
  }
  if (!window.supabase?.createClient) {
    setHostedShell(false);
    setAuthMessage("Polaris could not load secure sign-in. Please refresh the page.");
    return;
  }

  supabaseClient = window.supabase.createClient(
    authConfig.supabaseUrl,
    authConfig.supabasePublishableKey,
  );
  // Register immediately: Supabase emits PASSWORD_RECOVERY while it restores
  // the session embedded in a password-reset link.
  supabaseClient.auth.onAuthStateChange((event, session) => {
    hostedSession = session;
    if (event === "PASSWORD_RECOVERY") {
      isPasswordRecoveryFlow = true;
      void handleHostedSession(session);
      return;
    }
    if (!session) void handleHostedSession(null);
  });

  // The browser client detects both implicit and PKCE recovery links during
  // initialization. Do not exchange a code here: doing so races that built-in
  // handling and consumes the link before the recovery event can reach the UI.
  const { data, error } = await supabaseClient.auth.getSession();
  if (error) {
    setAuthMessage("Polaris could not complete the secure invitation link. Please request a new invitation.");
  }
  await handleHostedSession(data?.session || null);
};

const signIn = async (event) => {
  event.preventDefault();
  const submit = event.currentTarget.querySelector("button[type='submit']");
  submit.disabled = true;
  setAuthMessage("Signing in…");
  try {
    const { data, error } = await supabaseClient.auth.signInWithPassword({
      email: byId("sign-in-email").value.trim(),
      password: byId("sign-in-password").value,
    });
    if (error || !data.session) {
      throw new Error("Email or password was not accepted. Please try again.");
    }
    byId("sign-in-password").value = "";
    await handleHostedSession(data.session);
  } catch (error) {
    setAuthMessage(error.message);
  } finally {
    submit.disabled = false;
  }
};

const requestPasswordReset = async () => {
  const email = byId("sign-in-email").value.trim();
  if (!email) {
    setAuthMessage("Enter your email address first, then choose Forgot password.");
    return;
  }

  const button = byId("forgot-password-button");
  button.disabled = true;
  setAuthMessage("Sending a secure reset link…");
  try {
    const { error } = await supabaseClient.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}${window.location.pathname}`,
    });
    if (error) {
      throw new Error(error.message || "Polaris could not send a reset link. Please try again later.");
    }
    setAuthMessage("Check your email for the reset link. If this is your first visit, use Doug's original invitation link instead.");
  } catch (error) {
    setAuthMessage(error.message);
  } finally {
    button.disabled = false;
  }
};

const acceptInvitation = async (event) => {
  event.preventDefault();
  const password = byId("invite-password").value;
  const confirmation = byId("invite-password-confirmation").value;
  if (password !== confirmation) {
    setAuthMessage("The two passwords do not match.", "invite-message");
    return;
  }

  const submit = event.currentTarget.querySelector("button[type='submit']");
  submit.disabled = true;
  setAuthMessage("Saving your password…", "invite-message");
  try {
    const { error } = await supabaseClient.auth.updateUser({ password });
    if (error) {
      throw new Error(error.message || "Polaris could not save that password. Please try again.");
    }
    byId("invite-password").value = "";
    byId("invite-password-confirmation").value = "";
    isInvitationFlow = false;
    isPasswordRecoveryFlow = false;
    window.history.replaceState({}, document.title, window.location.pathname);
    await handleHostedSession(hostedSession);
  } catch (error) {
    setAuthMessage(error.message, "invite-message");
  } finally {
    submit.disabled = false;
  }
};

const signOut = async () => {
  if (supabaseClient) await supabaseClient.auth.signOut();
  hostedObservatory = null;
  hostedProfile = null;
  await handleHostedSession(null);
};

const VIEW_PATHS = {
  "/operator": "tonight",
  "/operator/portfolio": "portfolio",
  "/operator/quality": "quality",
  "/operator/history": "history",
  "/operator/locations": "locations",
  "/operator/data": "data",
};

const VIEW_TITLES = {
  tonight: "Night Operations",
  portfolio: "Portfolio",
  quality: "Quality by Target",
  history: "History",
  locations: "Locations",
  data: "Data Status",
};

const currentPath = window.location.pathname.replace(/\/$/, "") || "/operator";
const activeView = VIEW_PATHS[currentPath] || "tonight";
const demoMode = new URLSearchParams(window.location.search).get("demo");
const isImmaculateDemo = activeView === "tonight" && demoMode === "immaculate";
const isMapOverlapDemo = activeView === "history" && demoMode === "map-overlap";
let historyExpanded = false;
let portfolioSearch = "";
let portfolioFilter = "all";
let qualitySearch = "";
let qualityFilter = "all";
let latestDashboardData = null;
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

const displayFractionPercent = (value) => {
  if (value === null || value === undefined) return "—";
  const percent = Number(value) * 100;
  if (!Number.isFinite(percent)) return value;
  const digits = Math.abs(percent) < 0.01 ? 4 : 2;
  return `${percent.toFixed(digits).replace(/\.?0+$/, "")}%`;
};

const filterDetails = (value) => {
  if (!value) return { name: "Not recorded", description: "" };
  const filters = {
    "duo-band": {
      name: "Duo-Band",
      description:
        "Passes the hydrogen-alpha and oxygen-III wavelengths emitted by many nebulae. It blocks much of the surrounding skyglow, making glowing gas easier to capture.",
    },
    astro: {
      name: "Astro",
      description:
        "A general-purpose deep-sky filter that keeps a broad range of visible light for galaxies, clusters, and other natural-color targets.",
    },
    vis: {
      name: "VIS",
      description:
        "A visible-light filter intended for natural-color imaging while limiting wavelengths outside the normal visible range.",
    },
    uhc: {
      name: "UHC",
      description:
        "A contrast-enhancing nebula filter that passes selected emission wavelengths while reducing common sources of light pollution.",
    },
    clear: {
      name: "Clear",
      description:
        "A clear optical window with no intentional light-filtering effect, allowing the camera to use its full available wavelength range.",
    },
    none: {
      name: "No filter",
      description:
        "No imaging filter is selected, so the camera receives the full available light from the telescope.",
    },
  };
  return filters[value.trim().toLowerCase()] || { name: value, description: "" };
};

const friendlyFilterLabel = (value) => filterDetails(value).name;

const openInfoDialog = (eyebrow, title, body, range = "") => {
  setText("quality-info-eyebrow", eyebrow);
  setText("quality-info-title", title);
  setText("quality-info-body", body);
  setText("quality-info-range", range);
  byId("quality-info-range").hidden = !range;
  const dialog = byId("quality-info-dialog");
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
};

const termDetails = {
  "astronomical-darkness": {
    eyebrow: "Tonight term",
    title: "Astronomical darkness",
    body:
      "The part of the night when the Sun is far enough below the horizon that the sky is as dark as it gets naturally. Polaris uses this window for deep-sky imaging plans.",
  },
  "sub-exposure": {
    eyebrow: "Tonight setting",
    title: "Sub-exposure",
    body:
      "How long each individual camera frame should collect light. Polaris keeps this conservative for smart telescopes unless the target, tracking mode, and prior results support a longer frame.",
  },
  gain: {
    eyebrow: "Tonight setting",
    title: "Gain",
    body:
      "A camera sensitivity setting. Higher gain makes the signal brighter faster, but bright areas can clip sooner and noise can become more visible.",
  },
  filter: {
    eyebrow: "Tonight setting",
    title: "Filter",
    body:
      "The optical filter Polaris recommends for the target and sky. Filters can help isolate nebula light, reduce some skyglow, or keep a natural-color view depending on the target.",
  },
  bortle: {
    eyebrow: "Setup term",
    title: "Bortle class",
    body:
      "A 1 to 9 estimate of sky brightness at your observing location. Lower numbers are darker skies. If you do not know it, leave it as Not known yet.",
  },
};

const openTermInfo = (termKey) => {
  const term = termDetails[termKey];
  if (!term) return;
  openInfoDialog(term.eyebrow, term.title, term.body);
};

const openFilterInfo = (value) => {
  const filter = filterDetails(value);
  if (!filter.description) return;
  openInfoDialog("Imaging filter", filter.name, filter.description);
};

const appendFilterInfoButton = (parent, value) => {
  const filter = filterDetails(value);
  if (!filter.description) return;
  const button = appendTextElement(parent, "button", "quality-info-button", "i");
  button.type = "button";
  button.setAttribute("aria-label", `About the ${filter.name} filter`);
  button.addEventListener("click", () => openFilterInfo(value));
};

const appendSettingsInfoButton = (parent, block) => {
  const reasons = block.settings_reasons || [];
  if (!reasons.length) return;

  const button = appendTextElement(
    parent,
    "button",
    "settings-rationale-button",
    "Why these settings?",
  );
  button.type = "button";
  button.setAttribute(
    "aria-label",
    `Why these settings were recommended for ${block.object}`,
  );
  button.addEventListener("click", () => {
    const confidence = block.settings_confidence
      || "Beginner-safe starting point";
    openInfoDialog(
      "Tonight's imaging recipe",
      `${block.object}: ${confidence}`,
      reasons.join(" "),
      "Polaris keeps a setting from your capture history unless the target, Moon, light pollution, or planned weather creates a clear reason to change it.",
    );
  });
};

const renderFilterValue = (id, value) => {
  const container = byId(id);
  container.replaceChildren();
  appendTextElement(container, "span", "", friendlyFilterLabel(value));
  appendFilterInfoButton(container, value);
};

const qualityInterpretation = (score) => {
  if (score === null || score === undefined) return "Not scored";
  if (score >= 85) return "Strong result";
  if (score >= 70) return "Acceptable result";
  return "Review recommended";
};

const targetMatchesSearch = (target, search) => {
  const haystack = `${target.object || ""} ${target.common_name || ""}`.toLowerCase();
  return haystack.includes(search.trim().toLowerCase());
};

const targetNeedsSpecializedScoring = (target) => target.quality_captures.some(
  (capture) =>
    capture.components?.scoring_version === "2.0" &&
    capture.components?.confidence === "unsupported",
);

const targetMatchesGroup = (target, group) => {
  if (group === "all") return true;
  const objectName = (target.object || "").trim().toUpperCase();
  const objectType = (target.profile?.object_type || "").toLowerCase();
  const isLunar = objectName === "MOON" || objectType.includes("lunar");
  const isSolarSystem = [
    "SUN", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO",
  ].includes(objectName) || /(^|\s)planet(\s|$)/.test(objectType);
  const isNebula = objectType.includes("nebula");
  const isGalaxy = objectType.includes("galaxy");
  const isCluster = objectType.includes("cluster");
  const isMessier = /^M\d+$/.test(objectName);

  if (group === "messier") return isMessier;
  if (group === "nebula") return isNebula;
  if (group === "galaxy") return isGalaxy;
  if (group === "cluster") return isCluster;
  if (group === "solar-system") return isSolarSystem;
  if (group === "lunar") return isLunar;
  if (group === "other") {
    return !isMessier && !isNebula && !isGalaxy && !isCluster && !isSolarSystem && !isLunar;
  }
  return true;
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
  const parsed = new Date(
    /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T12:00:00` : value,
  );
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

    const filterName = candidateSettings.filter_name || "the selected filter";
    const targetName = candidate.common_name || candidate.object;
    const filterReason = filterName === "Duo-Band"
      ? (
        `Use Duo-Band for ${targetName}. It keeps the red hydrogen and `
        + "blue-green oxygen light found in glowing nebulae while blocking "
        + "much of the Moon and nearby light."
      )
      : filterName === "Astro"
        ? (
          `Use the Astro filter for ${targetName}. It collects a wider range `
          + "of light and keeps more natural star color."
        )
        : (
          `Use ${filterName} because it is the filter currently saved for `
          + `${targetName}.`
        );

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
      settings_confidence: "Simulation preview",
      settings_reasons: [
        filterReason,
        `Use ${exposureSeconds}-second exposures because the preview has clear skies and gentle wind.`,
        (
          "Gain does not collect more light; it controls how strongly the camera "
          + "turns the captured signal into pixel brightness. Raising gain makes "
          + "faint detail show more strongly, but bright stars reach pure white "
          + "sooner—losing detail—and noise becomes more visible. Lowering gain "
          + "preserves more detail in bright stars, but faint detail looks weaker "
          + `in each frame. Keep gain at ${candidateSettings.gain ?? "the saved value"} for this target.`
        ),
      ],
      settings_adjustments: [],
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
    planned_cloud_cover_percent: 0,
    planned_humidity_percent: 20,
    planned_wind_speed_mph: 1,
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
let imageViewerVariant = "original";

const pointsLabel = (points) => `${points > 0 ? "+" : ""}${points} pts`;

const qualityAnalysisSummary = (components) => {
  if (!components) return "This image has not been broken down into individual quality measurements yet.";
  if (components.scoring_version === "2.0") {
    return [
      `Sharpness: ${displayMeasuredNumber(components.median_fwhm)} px FWHM (${pointsLabel(components.sharpness_points)} / 30)`,
      `Star roundness: ${displayMeasuredNumber(components.median_roundness)} (${pointsLabel(components.roundness_points)} / 25)`,
      `Star signal-to-noise: ${displayMeasuredNumber(components.median_star_snr)} (${pointsLabel(components.signal_points)} / 20)`,
      `Background gradient: ${displayFractionPercent(components.background_gradient)} (${pointsLabel(components.uniformity_points)} / 15)`,
      `Clipped pixels: ${displayFractionPercent(components.clipped_pixel_fraction)} (${pointsLabel(components.clipping_points)} / 10)`,
      `Detected stars: ${displayNumber(components.stars_detected)} (diagnostic only)`,
    ].join(" · ");
  }
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

  if (imageViewerVariant === "processed" && !item.processed_preview_url) {
    imageViewerVariant = "original";
  }
  const displayingProcessed = imageViewerVariant === "processed";
  const imageUrl = displayingProcessed
    ? item.processed_preview_url
    : item.preview_url;

  const image = byId("image-dialog-image");
  const error = byId("image-dialog-error");
  image.hidden = true;
  error.hidden = true;
  image.removeAttribute("src");
  image.alt = `${item.object || "Capture"}${
    item.common_name ? ` — ${item.common_name}` : ""
  } preview`;
  image.src = imageUrl;

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

  const original = byId("image-dialog-original");
  const processed = byId("image-dialog-processed");
  original.hidden = !item.preview_url;
  processed.hidden = !item.processed_preview_url;
  original.disabled = !displayingProcessed;
  processed.disabled = displayingProcessed;
  setText(
    "image-dialog-variant-note",
    displayingProcessed
      ? "Processed presentation image — excluded from quality scoring and integration totals."
      : "Original scientific preview — used for capture review and quality scoring.",
  );

  const previous = byId("image-dialog-previous");
  const next = byId("image-dialog-next");
  previous.hidden = imageViewerItems.length <= 1;
  next.hidden = imageViewerItems.length <= 1;
  previous.disabled = imageViewerIndex === 0;
  next.disabled = imageViewerIndex === imageViewerItems.length - 1;
};

const openImageViewer = (items, startIndex = 0, preferredVariant = "original") => {
  imageViewerItems = items.filter((item) => item.preview_url);
  if (!imageViewerItems.length) return;
  imageViewerIndex = Math.max(0, Math.min(startIndex, imageViewerItems.length - 1));
  imageViewerVariant = (
    preferredVariant === "processed"
    && imageViewerItems[imageViewerIndex].processed_preview_url
  ) ? "processed" : "original";
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
    body: "This is the number of star-like points Polaris can identify. It helps establish whether enough stars were available for reliable measurements, but it depends strongly on the target and field of view.",
    range: "Quality v2 awards no points for raw star count. At least 25 usable stellar measurements are required for a deep-sky score; 50 or more provides high confidence.",
  },
  sharpness: {
    title: "Sharpness (FWHM)",
    body: "FWHM measures the width of a typical detected star in pixels. Smaller values mean the star image is tighter and usually indicate better focus and steadier atmospheric seeing.",
    range: "The point range comes from the named equipment profile. For the DWARF mini starter profile, 1.8 px or lower earns 30 points and 2.5 px or higher earns 0.",
  },
  roundness: {
    title: "Star roundness",
    body: "Roundness measures how stretched the detected stars are. Values nearer zero represent rounder stars; larger values can indicate tracking, alignment, focus, or optical issues.",
    range: "0.08 or lower earns 25 points. Credit decreases gradually to 0 points at 0.35.",
  },
  signal: {
    title: "Star signal-to-noise",
    body: "This compares a typical detected star peak with the robust background noise. Higher values mean stellar signal stands out more clearly from the background.",
    range: "50 or higher earns 20 points. Credit decreases gradually to 0 points at 5.",
  },
  uniformity: {
    title: "Background uniformity",
    body: "Polaris compares sigma-clipped background tiles across the image. A smaller gradient means the background is more even after bright outliers are rejected.",
    range: "A 5% gradient or lower earns 15 points. Credit decreases gradually to 0 points at 60%.",
  },
  clipping: {
    title: "Highlight protection",
    body: "This measures the fraction of pixels pinned at the image maximum. Too many clipped pixels can erase detail in bright stars or target cores.",
    range: "0.01% or less earns 10 points. Credit decreases gradually to 0 points at 1%.",
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
  openInfoDialog("Quality component", info.title, info.body, info.range);
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

const appendQualityDiagnostic = (parent, label, value, note, infoKey = null) => {
  const component = appendTextElement(parent, "div", "quality-component", "");
  const labelElement = appendTextElement(component, "span", "", label);
  if (infoKey) {
    const button = appendTextElement(labelElement, "button", "quality-info-button", "i");
    button.type = "button";
    button.setAttribute("aria-label", `About ${label}`);
    button.addEventListener("click", () => openQualityInfo(infoKey));
  }
  appendTextElement(component, "strong", "", value);
  appendTextElement(component, "small", "", note);
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
  setText(
    "decision-message",
    decision === "Use Caution"
      ? "Conditions are usable, but one or more factors need attention before imaging."
      : data.message,
  );

  const recommended = data.recommended_target;
  const target = recommended || data.backup_target;
  const plannedTemperature = data.weather?.planned_temperature_f;
  const targetForecast = byId("target-forecast");
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
    renderLegacyReferenceImage(null);
    targetForecast.hidden = true;
    return;
  }

  setText("target-name", target.object);
  setText("target-common-name", target.common_name, "");
  setText("target-reason", target.reason, "Planner recommendation available.");
  renderLegacyReferenceImage(target);
  if (plannedTemperature === null || plannedTemperature === undefined) {
    targetForecast.hidden = true;
  } else {
    targetForecast.hidden = false;
    setText(
      "target-forecast",
      `Forecast at planned start: ${displayNumber(plannedTemperature, "°F")}`,
    );
  }
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

  const settings = displayedTargetSettings(target, schedule);
  setText("target-exposure", displayNumber(settings.exposure_seconds, " sec"));
  setText("target-gain", displayNumber(settings.gain));
  renderFilterValue("target-filter", settings.filter_name);
};

const equipmentChips = (block) => {
  const chips = [];
  if (block.recommended_sub_exposure_seconds !== null) {
    chips.push({ label: `${block.recommended_sub_exposure_seconds} sec subs` });
  }
  if (block.recommended_gain !== null) {
    chips.push({ label: `Gain ${block.recommended_gain}` });
  }
  if (block.recommended_filter) {
    chips.push({
      label: friendlyFilterLabel(block.recommended_filter),
      filterValue: block.recommended_filter,
    });
  }
  if (block.planned_subframes !== null) {
    const subframeRuns = block.subframe_runs || [];
    if (subframeRuns.length > 1) {
      chips.push({
        label: `${block.planned_subframes} frames: ${subframeRuns.join(" + ")}`,
        title: `DWARF accepts up to 999 frames per run: ${subframeRuns.join(" + ")}.`,
      });
    } else {
      chips.push({ label: `${block.planned_subframes} frames` });
    }
  }
  chips.push({ label: `${block.imaging_minutes} min imaging` });
  if (block.setup_minutes) chips.push({ label: `${block.setup_minutes} min setup` });
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
    appendTargetIdentity(
      heading,
      block.total_runs > 1
        ? `${block.object} · Run ${block.run_number} of ${block.total_runs}`
        : block.object,
      block.common_name,
    );
    appendTextElement(heading, "span", "", durationLabel(block.duration_minutes));

    if (block.reason) {
      appendTextElement(card, "p", "schedule-reason", block.reason);
    }

    const chips = appendTextElement(card, "div", "equipment-row", "");
    equipmentChips(block).forEach((chip) => {
      const element = appendTextElement(chips, "span", "equipment-chip", chip.label);
      if (chip.title) element.title = chip.title;
      if (chip.filterValue) appendFilterInfoButton(element, chip.filterValue);
    });
    appendSettingsInfoButton(chips, block);

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
  setText(
    "night-rating",
    data.night_rating
      ? `${data.night_rating.quality} (${data.night_rating.score}/100)`
      : "Unavailable",
  );
  const ratingDeductions = data.night_rating?.deductions || [];
  setText(
    "weather-status",
    ratingDeductions.length
      ? ratingDeductions
          .map(
            (deduction) =>
              `${deduction.label}: −${displayMeasuredNumber(deduction.points)} points`,
          )
          .join(" · ")
      : data.night_rating?.quality === "Unavailable"
        ? "Weather measurements unavailable"
        : "No sky-quality deductions",
  );
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
  const moonPosition = moon.above_horizon ? "Above horizon now" : "Below horizon now";
  const nextMoonEvent = moon.above_horizon
    ? moon.next_moonset
      ? ` · sets ${shortTime(moon.next_moonset)}`
      : ""
    : moon.next_moonrise
      ? ` · rises ${shortTime(moon.next_moonrise)}`
      : "";
  const moonImpact = target?.moon_warning
    ? target.moon_warning.replace(/^(None|Minimal) — /, "")
    : "Target impact is unavailable.";
  setText(
    "moon-context",
    `${moonPosition}${nextMoonEvent}. During the target window: ${moonImpact}`,
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
  list.replaceChildren();
  const visibleNotes = (notes || []).filter(
    (note) =>
      note &&
      !note.toLowerCase().startsWith("use caution:") &&
      note !== "Review live conditions before starting any scheduled block.",
  );
  list.hidden = decision === "Proceed" || visibleNotes.length === 0;

  if (list.hidden) return;

  renderAdvisoryNotes(list, visibleNotes);
};

const renderAdvisoryNotes = (list, notes) => {
  const itemsByCategory = new Map();
  const capitalizeBullet = (value) =>
    value ? `${value.charAt(0).toUpperCase()}${value.slice(1)}` : value;

  notes.forEach((note) => {
    const guidanceMatch = note.match(/^(.+?) guidance:\s*(.+)$/i);
    if (guidanceMatch) {
      const category = guidanceMatch[1].trim().toLowerCase();
      const parent = itemsByCategory.get(category);
      if (!parent) {
        appendTextElement(list, "li", "", note);
        return;
      }

      const guidance = document.createElement("ul");
      guidance.className = "advisory-note-guidance";
      guidanceMatch[2]
        .split(";")
        .map((action) => action.trim())
        .filter(Boolean)
        .forEach((action) =>
          appendTextElement(guidance, "li", "", capitalizeBullet(action)),
        );
      parent.appendChild(guidance);
      return;
    }

    const categoryMatch = note.match(/^(.+?):\s*(.+)$/);
    const item = document.createElement("li");
    if (categoryMatch) {
      const category = categoryMatch[1].trim();
      const label = appendTextElement(item, "strong", "advisory-note-label", `${category}: `);
      label.setAttribute("aria-label", `${category} advisory`);
      item.appendChild(document.createTextNode(capitalizeBullet(categoryMatch[2])));
      itemsByCategory.set(category.toLowerCase(), item);
    } else {
      item.textContent = capitalizeBullet(note);
    }
    list.appendChild(item);
  });
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
  const targets = data.targets.filter((target) => {
    if (!targetMatchesSearch(target, portfolioSearch)) return false;
    return targetMatchesGroup(target, portfolioFilter);
  });
  setText(
    "portfolio-summary",
    `${targets.length} of ${data.metrics.targets} targets · ${data.metrics.total_integration_hours} hours`,
  );

  if (!targets.length) {
    appendTextElement(
      container,
      "div",
      "empty-state",
      data.targets.length
        ? "No targets match this search or filter."
        : "No captured targets yet.",
    );
    return;
  }

  targets.forEach((target) => {
    const card = appendTextElement(container, "article", "target-card", "");
    const top = appendTextElement(card, "div", "target-card-top", "");
    const presentationImage = (
      target.presentation_preview_image
      || target.preview_image
    );
    const portfolioPreviewUrl = (
      presentationImage?.display_preview_url
      || target.preview_url
    );
    if (portfolioPreviewUrl) {
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
      preview.src = portfolioPreviewUrl;
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
        if (presentationImage) openImageViewer([presentationImage], 0, "processed");
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
      `Imaging aim: ${(target.goal_options || []).find((option) => option.tier === target.goal_tier)?.label || "Detailed"} · ${target.goal_hours} hr`,
    );
    const goalDetails = document.createElement("details");
    goalDetails.className = "target-goal-details";
    const goalSummary = document.createElement("summary");
    goalSummary.textContent = "Why this goal?";
    goalDetails.appendChild(goalSummary);
    appendTextElement(goalDetails, "p", "target-goal-explanation", target.integration_goal_note);
    card.appendChild(goalDetails);
    if ((target.goal_options || []).length) {
      appendTextElement(
        card,
        "p",
        "target-goal-options",
        `Aim guide: ${target.goal_options.map((option) => `${option.label} ${option.hours} hr`).join(" · ")}`,
      );
    }

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

  const analyzedTargets = [...data.targets]
    .filter((target) => target.quality_captures.length)
    .sort((left, right) => left.object.localeCompare(right.object));
  const scoredTargetCount = analyzedTargets.filter(
    (target) => target.average_quality !== null,
  ).length;
  const alternateModelCount = analyzedTargets.length - scoredTargetCount;
  const targets = analyzedTargets.filter((target) => {
    if (!targetMatchesSearch(target, qualitySearch)) return false;
    return targetMatchesGroup(target, qualityFilter);
  });

  setText(
    "quality-summary",
    `${scoredTargetCount} scored target${scoredTargetCount === 1 ? "" : "s"}${
      alternateModelCount
        ? ` · ${alternateModelCount} planetary/lunar target${
            alternateModelCount === 1 ? "" : "s"
          } awaiting specialized scoring`
        : ""
    } · showing ${targets.length} of ${analyzedTargets.length}`,
  );

  if (!targets.length) {
    appendTextElement(
      container,
      "div",
      "empty-state",
      analyzedTargets.length
        ? "No targets match this search or filter."
        : "No targets have quality scores yet.",
    );
    return;
  }

  targets.forEach((target) => {
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
    const needsSpecializedModel = targetNeedsSpecializedScoring(target);
    if (needsSpecializedModel) {
      appendTextElement(
        heading,
        "span",
        "quality-sample",
        "Planetary/lunar scoring is not available yet",
      );
    } else if (target.scored_capture_count < target.capture_count) {
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
    appendTextElement(
      averageFact,
      "dd",
      "",
      target.average_quality === null ? "Not scored" : `${target.average_quality}/100`,
    );
    const bestFact = appendTextElement(facts, "div", "", "");
    appendTextElement(bestFact, "dt", "", "Best score");
    appendTextElement(
      bestFact,
      "dd",
      "",
      target.best_quality === null ? "Not scored" : `${target.best_quality}/100`,
    );
    const latestFact = appendTextElement(facts, "div", "", "");
    appendTextElement(latestFact, "dt", "", "Latest capture");
    appendTextElement(latestFact, "dd", "", displayDate(target.latest_capture));

    if (target.average_quality !== null) {
      const scoreBar = document.createElement("progress");
      scoreBar.className = "quality-score-bar";
      scoreBar.max = 100;
      scoreBar.value = target.average_quality;
      scoreBar.setAttribute(
        "aria-label",
        `${target.object} average quality ${target.average_quality} out of 100`,
      );
      card.appendChild(scoreBar);
    }

    const breakdown = document.createElement("details");
    breakdown.className = "quality-breakdown";
    const summary = appendTextElement(
      breakdown,
      "summary",
      "",
      `Analysis details for ${target.quality_captures.length} capture${
        target.quality_captures.length === 1 ? "" : "s"
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
        capture.quality_score === null
          ? "Not scored"
          : `${capture.quality_score}/100`,
      );

      const components = capture.components;
      const componentGrid = appendTextElement(
        captureRow,
        "div",
        "quality-component-grid",
        "",
      );
      if (
        components.scoring_version === "2.0"
        && components.confidence === "unsupported"
      ) {
        appendQualityDiagnostic(
          componentGrid,
          "Scoring model",
          "Planetary model required",
          "Deep-sky Quality v2 does not score this capture",
        );
        appendQualityDiagnostic(
          componentGrid,
          "Stars detected",
          displayNumber(components.stars_detected),
          `${displayNumber(components.star_sample_count)} used · diagnostic only`,
          "stars",
        );
      } else if (components.scoring_version === "2.0") {
        appendQualityDiagnostic(
          componentGrid,
          "Scoring model",
          "Quality v2",
          `${components.profile_label} · ${components.confidence} confidence`,
        );
        appendQualityComponent(
          componentGrid,
          "Sharpness",
          `${displayMeasuredNumber(components.median_fwhm)} px FWHM`,
          components.sharpness_points,
          30,
          "sharpness",
        );
        appendQualityComponent(
          componentGrid,
          "Star roundness",
          displayMeasuredNumber(components.median_roundness),
          components.roundness_points,
          25,
          "roundness",
        );
        appendQualityComponent(
          componentGrid,
          "Star signal-to-noise",
          displayMeasuredNumber(components.median_star_snr),
          components.signal_points,
          20,
          "signal",
        );
        appendQualityComponent(
          componentGrid,
          "Background gradient",
          displayFractionPercent(components.background_gradient),
          components.uniformity_points,
          15,
          "uniformity",
        );
        appendQualityComponent(
          componentGrid,
          "Clipped pixels",
          displayFractionPercent(components.clipped_pixel_fraction),
          components.clipping_points,
          10,
          "clipping",
        );
        appendQualityDiagnostic(
          componentGrid,
          "Stars detected",
          displayNumber(components.stars_detected),
          `${displayNumber(components.star_sample_count)} used · diagnostic only`,
          "stars",
        );
      } else {
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
      }
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

let candidateSiteMap;
let candidateSiteLayers;
let candidateSiteOrigin = null;
let savedCandidateSites = [];
let candidateSiteSort = "newest";
let visitedSiteSort = "recent";
let selectedCandidateSiteIds = [];

const milesToMeters = (miles) => miles * 1609.344;

const CANDIDATE_VEHICLE_LABELS = {
  standard_vehicle: "Standard vehicle",
  high_clearance: "High-clearance recommended",
  four_wheel_drive: "4x4 required",
};

const CANDIDATE_PROPERTY_ACCESS_LABELS = {
  public_property: "Public property",
  private_permission: "Private · permission required",
  restricted: "Restricted access",
};

const CANDIDATE_READINESS_CHECKS = [
  { key: "parking_setup_confirmed", label: "Parking / setup confirmed" },
  { key: "horizon_confirmed", label: "Horizon reviewed" },
  { key: "access_confirmed", label: "Access / permission confirmed" },
  { key: "amenities_confirmed", label: "Facilities / cell plan confirmed" },
];

const candidateVehicleLabel = (value) => CANDIDATE_VEHICLE_LABELS[value] || value;
const candidatePropertyAccessLabel = (value) => CANDIDATE_PROPERTY_ACCESS_LABELS[value] || value;

const appendCandidateSiteDetail = (details, label, value) => {
  if (!value) return;
  const item = appendTextElement(details, "div", "candidate-site-detail", "");
  appendTextElement(item, "dt", "", label);
  appendTextElement(item, "dd", "", value);
};

const appendCandidateSiteOption = (select, value, label, selectedValue) => {
  const option = appendTextElement(select, "option", "", label);
  option.value = value;
  option.selected = value === (selectedValue || "");
};

const candidateReadinessCount = (site) => CANDIDATE_READINESS_CHECKS.filter(
  ({ key }) => site[key],
).length;

const candidateDirectionsUrl = (site) => (
  `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${site.latitude},${site.longitude}`)}`
);

const appendDirectionsIcon = (container) => {
  const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  icon.classList.add("candidate-site-directions-icon");
  icon.setAttribute("viewBox", "0 0 24 24");
  icon.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M12 2.8a6.2 6.2 0 0 0-6.2 6.2c0 4.65 6.2 12.2 6.2 12.2S18.2 13.65 18.2 9A6.2 6.2 0 0 0 12 2.8Zm0 8.6A2.4 2.4 0 1 1 12 6.6a2.4 2.4 0 0 1 0 4.8Z");
  icon.appendChild(path);
  container.appendChild(icon);
};

const candidateSiteDistanceLabel = (site) => {
  if (!candidateSiteOrigin || !window.L) return "Distance unavailable";
  const miles = window.L.latLng(
    candidateSiteOrigin.latitude,
    candidateSiteOrigin.longitude,
  ).distanceTo([site.latitude, site.longitude]) / 1609.344;
  return miles < 10 ? `${miles.toFixed(1)} mi away` : `${Math.round(miles)} mi away`;
};

const candidateSiteDistanceMiles = (site) => {
  if (!candidateSiteOrigin || !window.L) return Number.POSITIVE_INFINITY;
  return window.L.latLng(
    candidateSiteOrigin.latitude,
    candidateSiteOrigin.longitude,
  ).distanceTo([site.latitude, site.longitude]) / 1609.344;
};

const sortedCandidateSites = () => [...savedCandidateSites].sort((left, right) => {
  if (candidateSiteSort === "distance") {
    return candidateSiteDistanceMiles(left) - candidateSiteDistanceMiles(right);
  }
  if (candidateSiteSort === "bortle_distance") {
    const bortleDifference = (left.bortle_class ?? 10) - (right.bortle_class ?? 10);
    return bortleDifference || candidateSiteDistanceMiles(left) - candidateSiteDistanceMiles(right);
  }
  return new Date(right.created_at) - new Date(left.created_at);
});

const sortedVisitedSites = () => savedCandidateSites
  .filter((site) => site.visited_at)
  .sort((left, right) => {
    if (visitedSiteSort === "rating") {
      const ratingDifference = (right.star_rating || 0) - (left.star_rating || 0);
      if (ratingDifference) return ratingDifference;
    }
    return new Date(right.visited_at) - new Date(left.visited_at);
  });

const starRatingLabel = (rating) => (
  rating ? `${"★".repeat(rating)}${"☆".repeat(5 - rating)} ${rating}/5` : "Not rated"
);

const appendStarRating = (card, site) => {
  if (!site.visited_at) return;
  const rating = document.createElement("div");
  rating.className = "candidate-site-rating";
  const label = appendTextElement(rating, "span", "", "Your rating");
  label.id = `candidate-site-rating-label-${site.id}`;
  const controls = document.createElement("span");
  controls.className = "candidate-site-rating-controls";
  controls.setAttribute("role", "group");
  controls.setAttribute("aria-labelledby", label.id);
  for (let value = 1; value <= 5; value += 1) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = value <= (site.star_rating || 0) ? "selected" : "";
    button.textContent = "★";
    button.setAttribute("aria-label", `Rate ${value} out of 5 stars`);
    button.setAttribute("aria-pressed", String(site.star_rating === value));
    button.addEventListener("click", () => updateCandidateSite(site.id, { star_rating: value }));
    controls.appendChild(button);
  }
  appendTextElement(rating, "strong", "", starRatingLabel(site.star_rating));
  rating.appendChild(controls);
  card.appendChild(rating);
};

const renderCandidateSiteComparison = (candidateSites) => {
  const comparison = byId("candidate-site-comparison");
  const grid = byId("candidate-site-comparison-grid");
  selectedCandidateSiteIds = selectedCandidateSiteIds.filter((siteId) => (
    candidateSites.some((site) => site.id === siteId)
  ));
  const sites = selectedCandidateSiteIds
    .map((siteId) => candidateSites.find((site) => site.id === siteId))
    .filter(Boolean);
  comparison.hidden = sites.length < 2;
  grid.replaceChildren();
  if (sites.length < 2) return;
  sites.forEach((site) => {
    const card = appendTextElement(grid, "article", "candidate-site-comparison-card", "");
    appendTextElement(card, "strong", "", site.name);
    const details = appendTextElement(card, "dl", "candidate-site-comparison-details", "");
    appendCandidateSiteDetail(details, "Distance", candidateSiteDistanceLabel(site));
    appendCandidateSiteDetail(
      details,
      "Bortle",
      site.bortle_class === null || site.bortle_class === undefined
        ? "Not recorded"
        : `Bortle ${site.bortle_class}`,
    );
    appendCandidateSiteDetail(details, "Hours", site.access_hours || "Not recorded");
    appendCandidateSiteDetail(
      details,
      "Vehicle",
      candidateVehicleLabel(site.vehicle_requirement) || "Not recorded",
    );
    appendCandidateSiteDetail(
      details,
      "Property",
      candidatePropertyAccessLabel(site.property_access) || "Not recorded",
    );
    appendCandidateSiteDetail(
      details,
      "Readiness",
      `${candidateReadinessCount(site)} / ${CANDIDATE_READINESS_CHECKS.length} confirmed`,
    );
  });
};

const toggleCandidateSiteComparison = (siteId) => {
  if (selectedCandidateSiteIds.includes(siteId)) {
    selectedCandidateSiteIds = selectedCandidateSiteIds.filter((id) => id !== siteId);
  } else if (selectedCandidateSiteIds.length < 3) {
    selectedCandidateSiteIds = [...selectedCandidateSiteIds, siteId];
  }
  renderSavedSiteLists();
};

const setCandidateCoordinates = (latitude, longitude) => {
  byId("candidate-site-latitude").value = Number(latitude).toFixed(5);
  byId("candidate-site-longitude").value = Number(longitude).toFixed(5);
};

const updateCandidateResearchLinks = () => {
  const lightPollutionLink = byId("candidate-light-pollution-link");
  if (!lightPollutionLink || !candidateSiteOrigin) return;
  const latitude = Number(candidateSiteOrigin.latitude).toFixed(1);
  const longitude = Number(candidateSiteOrigin.longitude).toFixed(1);
  lightPollutionLink.href = `https://lightpollutionmap.app/?lat=${latitude}&lng=${longitude}&zoom=8`;
};

const renderCandidateSiteList = ({
  listId,
  sites,
  includeComparison = false,
  emptyMessage,
}) => {
  const list = byId(listId);
  list.replaceChildren();
  if (includeComparison) renderCandidateSiteComparison(sites);
  if (!sites.length) {
    appendTextElement(
      list,
      "div",
      "empty-state",
      emptyMessage,
    );
    return;
  }
  sites.forEach((site) => {
    const card = appendTextElement(list, "article", "candidate-site-card", "");
    const heading = appendTextElement(card, "div", "candidate-site-card-heading", "");
    appendTextElement(heading, "strong", "", site.name);
    const badges = appendTextElement(heading, "span", "candidate-site-badges", "");
    appendTextElement(
      badges,
      "span",
      site.visited_at ? "candidate-site-visited" : "candidate-site-pending",
      site.visited_at ? "Visited" : "Candidate",
    );
    appendTextElement(
      badges,
      "span",
      "",
      site.bortle_class === null || site.bortle_class === undefined
        ? "Bortle not recorded"
        : `Bortle ${site.bortle_class}`,
    );
    appendTextElement(card, "p", "", candidateSiteDistanceLabel(site));
    appendTextElement(
      card,
      "p",
      "candidate-site-coordinates",
      `${Number(site.latitude).toFixed(4)}, ${Number(site.longitude).toFixed(4)}`,
    );
    appendStarRating(card, site);
    if (site.access_hours || site.vehicle_requirement || site.property_access) {
      const detailsList = appendTextElement(card, "dl", "candidate-site-details", "");
      appendCandidateSiteDetail(detailsList, "Hours", site.access_hours);
      appendCandidateSiteDetail(
        detailsList,
        "Vehicle",
        candidateVehicleLabel(site.vehicle_requirement),
      );
      appendCandidateSiteDetail(
        detailsList,
        "Property",
        candidatePropertyAccessLabel(site.property_access),
      );
    }
    const readinessCount = candidateReadinessCount(site);
    if (readinessCount) {
      appendTextElement(
        card,
        "p",
        "candidate-site-readiness-summary",
        `Site readiness: ${readinessCount} / ${CANDIDATE_READINESS_CHECKS.length} confirmed`,
      );
    }
    if (site.notes) appendTextElement(card, "p", "candidate-site-notes", site.notes);
    const actions = appendTextElement(card, "div", "candidate-site-actions", "");
    if (site.source_url) {
      const link = appendTextElement(actions, "a", "candidate-site-link-button candidate-site-reference", "Open reference");
      link.href = site.source_url;
      link.target = "_blank";
      link.rel = "noreferrer";
    }
    const directions = document.createElement("a");
    directions.className = "candidate-site-link-button candidate-site-directions";
    appendDirectionsIcon(directions);
    appendTextElement(directions, "span", "", "Get directions");
    directions.href = candidateDirectionsUrl(site);
    directions.target = "_blank";
    directions.rel = "noreferrer";
    actions.appendChild(directions);
    const visited = appendTextElement(
      actions,
      "button",
      "candidate-site-visit-toggle",
      site.visited_at ? "Mark as candidate" : "Mark visited",
    );
    visited.type = "button";
    visited.addEventListener("click", () => updateCandidateSite(site.id, {
      visited: !site.visited_at,
    }));
    if (includeComparison) {
      const isSelectedForComparison = selectedCandidateSiteIds.includes(site.id);
      const compare = appendTextElement(
        actions,
        "button",
        isSelectedForComparison ? "candidate-site-compare selected" : "candidate-site-compare",
        isSelectedForComparison ? "Selected for comparison" : "Compare",
      );
      compare.type = "button";
      compare.disabled = !isSelectedForComparison && selectedCandidateSiteIds.length >= 3;
      compare.addEventListener("click", () => toggleCandidateSiteComparison(site.id));
    }
    const details = document.createElement("details");
    details.className = "candidate-site-editor";
    const summary = document.createElement("summary");
    summary.textContent = "Update site details";
    details.appendChild(summary);
    const form = document.createElement("form");
    const hoursLabel = document.createElement("label");
    hoursLabel.textContent = "Access hours";
    const hours = document.createElement("input");
    hours.maxLength = 250;
    hours.value = site.access_hours || "";
    hoursLabel.appendChild(hours);
    form.appendChild(hoursLabel);
    const editorGrid = document.createElement("div");
    editorGrid.className = "candidate-coordinate-grid";
    const vehicleLabel = document.createElement("label");
    vehicleLabel.textContent = "Vehicle access";
    const vehicle = document.createElement("select");
    appendCandidateSiteOption(vehicle, "", "Not known yet", site.vehicle_requirement);
    Object.entries(CANDIDATE_VEHICLE_LABELS).forEach(([value, labelText]) => {
      appendCandidateSiteOption(vehicle, value, labelText, site.vehicle_requirement);
    });
    vehicleLabel.appendChild(vehicle);
    editorGrid.appendChild(vehicleLabel);
    const propertyLabel = document.createElement("label");
    propertyLabel.textContent = "Property access";
    const property = document.createElement("select");
    appendCandidateSiteOption(property, "", "Not known yet", site.property_access);
    Object.entries(CANDIDATE_PROPERTY_ACCESS_LABELS).forEach(([value, labelText]) => {
      appendCandidateSiteOption(property, value, labelText, site.property_access);
    });
    propertyLabel.appendChild(property);
    editorGrid.appendChild(propertyLabel);
    form.appendChild(editorGrid);
    const readiness = document.createElement("fieldset");
    readiness.className = "candidate-site-readiness";
    const readinessLegend = document.createElement("legend");
    readinessLegend.textContent = "Site readiness";
    readiness.appendChild(readinessLegend);
    const readinessInputs = {};
    CANDIDATE_READINESS_CHECKS.forEach(({ key, label: labelText }) => {
      const readinessLabel = document.createElement("label");
      const readinessInput = document.createElement("input");
      readinessInput.type = "checkbox";
      readinessInput.checked = Boolean(site[key]);
      readinessLabel.appendChild(readinessInput);
      readinessLabel.append(` ${labelText}`);
      readinessInputs[key] = readinessInput;
      readiness.appendChild(readinessLabel);
    });
    form.appendChild(readiness);
    const label = document.createElement("label");
    label.textContent = "Field notes";
    const notes = document.createElement("textarea");
    notes.rows = 4;
    notes.maxLength = 1000;
    notes.value = site.notes || "";
    label.appendChild(notes);
    form.appendChild(label);
    const save = appendTextElement(form, "button", "candidate-site-note-save", "Save notes");
    save.type = "submit";
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      updateCandidateSite(site.id, {
        access_hours: hours.value.trim() || null,
        vehicle_requirement: vehicle.value || null,
        property_access: property.value || null,
        ...Object.fromEntries(
          CANDIDATE_READINESS_CHECKS.map(({ key }) => [key, readinessInputs[key].checked]),
        ),
        notes: notes.value.trim(),
      });
    });
    details.appendChild(form);
    card.appendChild(details);
    const remove = appendTextElement(card, "button", "candidate-site-remove", "Remove");
    remove.type = "button";
    remove.addEventListener("click", () => removeCandidateSite(site.id));
  });
};

const renderSavedSiteLists = () => {
  const candidates = sortedCandidateSites().filter((site) => !site.visited_at);
  const visited = sortedVisitedSites();
  setText(
    "candidate-site-summary",
    candidates.length === 1 ? "1 candidate" : `${candidates.length} candidates`,
  );
  setText(
    "visited-site-summary",
    visited.length === 1 ? "1 visited site" : `${visited.length} visited sites`,
  );
  renderCandidateSiteList({
    listId: "candidate-site-list",
    sites: candidates,
    includeComparison: true,
    emptyMessage: "No candidate sites saved yet. Click the map or enter coordinates to add one.",
  });
  renderCandidateSiteList({
    listId: "visited-site-list",
    sites: visited,
    emptyMessage: "No visited sites yet. Mark a candidate as visited after you have observed there.",
  });
};

const renderCandidateSiteMapKey = () => {
  const key = byId("candidate-site-map-key");
  key.replaceChildren();
  const items = [];
  [...new Set(
    savedCandidateSites
      .map((site) => site.bortle_class)
      .filter((bortleClass) => bortleClass !== null && bortleClass !== undefined),
  )]
    .sort((left, right) => left - right)
    .forEach((bortleClass) => {
      items.push({
        color: BORTLE_COLORS[bortleClass] || "#4fd4c5",
        label: `Bortle ${bortleClass}`,
      });
    });
  items.forEach((item) => {
    const keyItem = appendTextElement(key, "span", "candidate-site-map-key-item", "");
    const swatch = appendTextElement(keyItem, "span", "candidate-site-map-key-swatch", "");
    swatch.style.background = item.color;
    appendTextElement(keyItem, "span", "", item.label);
  });
};

const renderCandidateSiteMap = () => {
  const container = byId("candidate-site-map");
  if (!candidateSiteOrigin) return;
  if (!window.L) {
    container.replaceChildren();
    appendTextElement(container, "div", "empty-state", "Interactive map controls are unavailable.");
    return;
  }
  if (!candidateSiteMap) {
    container.replaceChildren();
    candidateSiteMap = window.L.map(container, {
      scrollWheelZoom: true,
      worldCopyJump: true,
      minZoom: 2,
    }).setView([candidateSiteOrigin.latitude, candidateSiteOrigin.longitude], 7);
    window.L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      { maxZoom: 19, attribution: "© OpenStreetMap contributors" },
    ).addTo(candidateSiteMap);
    candidateSiteLayers = window.L.featureGroup().addTo(candidateSiteMap);
    candidateSiteMap.on("click", (event) => {
      setCandidateCoordinates(event.latlng.lat, event.latlng.lng);
      setText("candidate-site-status", "Map point selected. Add a name, then save the site.");
    });
  } else {
    candidateSiteLayers.clearLayers();
    candidateSiteMap.invalidateSize();
  }

  const origin = [candidateSiteOrigin.latitude, candidateSiteOrigin.longitude];
  window.L.circleMarker(origin, {
    radius: 8,
    color: "#efffff",
    weight: 2,
    fillColor: "#4fd4c5",
    fillOpacity: 1,
  }).addTo(candidateSiteLayers).bindPopup("Your planning origin");
  [25, 50, 100].forEach((miles) => {
    window.L.circle(origin, {
      radius: milesToMeters(miles),
      color: "#d58cff",
      weight: 3,
      opacity: 0.92,
      fill: false,
      interactive: false,
    }).addTo(candidateSiteLayers);
  });
  savedCandidateSites.forEach((site) => {
    const marker = window.L.circleMarker([site.latitude, site.longitude], {
      radius: 10,
      color: "#efffff",
      weight: 2,
      fillColor: BORTLE_COLORS[site.bortle_class] || "#4fd4c5",
      fillOpacity: 0.94,
    }).addTo(candidateSiteLayers);
    const popup = document.createElement("div");
    appendTextElement(popup, "strong", "", site.name);
    appendTextElement(popup, "div", "", candidateSiteDistanceLabel(site));
    appendTextElement(
      popup,
      "div",
      "",
      site.bortle_class === null || site.bortle_class === undefined
        ? "Bortle not recorded"
        : bortleLabel(site.bortle_class),
    );
    appendTextElement(popup, "div", "", site.visited_at ? "Visited site" : "Candidate site");
    marker.bindPopup(popup);
  });
};

const renderCandidateSites = (origin, sites) => {
  candidateSiteOrigin = origin;
  savedCandidateSites = sites;
  updateCandidateResearchLinks();
  renderCandidateSiteMap();
  renderSavedSiteLists();
  renderCandidateSiteMapKey();
};

const loadCandidateSites = async (origin) => {
  const response = await apiFetch("/candidate-sites", { cache: "no-store" });
  if (!response.ok) throw new Error(`Candidate sites endpoint returned ${response.status}.`);
  renderCandidateSites(origin, await response.json());
};

const updateCandidateSite = async (siteId, payload) => {
  try {
    const response = await apiFetch(`/candidate-sites/${siteId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("The site could not be updated. Please try again.");
    const updatedSite = await response.json();
    savedCandidateSites = savedCandidateSites.map((site) => (
      site.id === siteId ? updatedSite : site
    ));
    renderCandidateSiteMap();
    renderSavedSiteLists();
    renderCandidateSiteMapKey();
    setText("candidate-site-status", "Potential site updated.");
  } catch (error) {
    setText("candidate-site-status", error.message);
  }
};

const removeCandidateSite = async (siteId) => {
  if (!window.confirm("Remove this saved potential site?")) return;
  const response = await apiFetch(`/candidate-sites/${siteId}`, { method: "DELETE" });
  if (!response.ok) {
    setText("candidate-site-status", "The site could not be removed. Please try again.");
    return;
  }
  savedCandidateSites = savedCandidateSites.filter((site) => site.id !== siteId);
  selectedCandidateSiteIds = selectedCandidateSiteIds.filter((id) => id !== siteId);
  renderCandidateSiteMap();
  renderSavedSiteLists();
  renderCandidateSiteMapKey();
  setText("candidate-site-status", "Potential site removed.");
};

const saveCandidateSite = async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const bortleValue = byId("candidate-site-bortle").value;
  const payload = {
    name: byId("candidate-site-name").value.trim(),
    latitude: Number(byId("candidate-site-latitude").value),
    longitude: Number(byId("candidate-site-longitude").value),
    bortle_class: bortleValue ? Number(bortleValue) : null,
    access_hours: byId("candidate-site-hours").value.trim() || null,
    vehicle_requirement: byId("candidate-site-vehicle").value || null,
    property_access: byId("candidate-site-property").value || null,
    parking_setup_confirmed: byId("candidate-site-parking").checked,
    horizon_confirmed: byId("candidate-site-horizon").checked,
    access_confirmed: byId("candidate-site-access").checked,
    amenities_confirmed: byId("candidate-site-amenities").checked,
    notes: byId("candidate-site-notes").value.trim(),
    source_url: byId("candidate-site-source").value.trim() || null,
  };
  const submit = form.querySelector("button[type='submit']");
  submit.disabled = true;
  setText("candidate-site-status", "Saving potential site…");
  try {
    const response = await apiFetch("/candidate-sites", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("The site could not be saved. Check the coordinates and try again.");
    savedCandidateSites = [await response.json(), ...savedCandidateSites];
    form.reset();
    renderCandidateSiteMap();
    renderSavedSiteLists();
    renderCandidateSiteMapKey();
    setText("candidate-site-status", "Potential site saved.");
  } catch (error) {
    setText("candidate-site-status", error.message);
  } finally {
    submit.disabled = false;
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

  const eqEnabled = byId("eq-mode-checkbox").checked;
  const [planResult, systemResult, dashboardResult] = await Promise.allSettled([
    apiFetch(`/tonight?equatorial_mode_enabled=${eqEnabled}`, { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`Tonight endpoint returned ${response.status}.`);
      return response.json();
    }),
    apiFetch("/system", { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`System endpoint returned ${response.status}.`);
      return response.json();
    }),
    apiFetch(`/dashboard?include_all_history=${historyExpanded}`, { cache: "no-store" }).then((response) => {
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
    try {
      await loadCandidateSites(data.observatory);
    } catch (error) {
      setText("candidate-site-summary", "Unavailable");
      setText("visited-site-summary", "Unavailable");
      const list = byId("candidate-site-list");
      list.replaceChildren();
      appendTextElement(list, "div", "empty-state", error.message);
      const visitedList = byId("visited-site-list");
      visitedList.replaceChildren();
      appendTextElement(visitedList, "div", "empty-state", error.message);
    }
  } else {
    showPlanError(planResult.reason.message);
    setText("candidate-site-summary", "Unavailable");
    setText("visited-site-summary", "Unavailable");
  }

  if (systemResult.status === "fulfilled") {
    renderSystem(systemResult.value);
  } else {
    setText("capture-library-status", "Capture-library status is unavailable.");
  }

  if (dashboardResult.status === "fulfilled") {
    latestDashboardData = dashboardResult.value;
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
  button.textContent = nextExpanded ? "Loading all captures…" : "Showing fewer captures…";

  try {
    const response = await apiFetch(
      `/dashboard?include_all_history=${nextExpanded}`,
      { cache: "no-store" },
    );
    if (!response.ok) throw new Error(`Dashboard endpoint returned ${response.status}.`);
    const data = await response.json();
    historyExpanded = nextExpanded;
    latestDashboardData = data;
    renderRecentCaptures(data);
    button.textContent = historyExpanded ? "Show fewer captures" : "View all captures";
  } catch (error) {
    button.textContent = "View all captures";
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
byId("image-dialog-original").addEventListener("click", () => {
  imageViewerVariant = "original";
  renderImageViewerItem();
});
byId("image-dialog-processed").addEventListener("click", () => {
  if (imageViewerItems[imageViewerIndex]?.processed_preview_url) {
    imageViewerVariant = "processed";
    renderImageViewerItem();
  }
});
const qualityInfoDialog = byId("quality-info-dialog");
byId("quality-info-close").addEventListener("click", () => {
  if (typeof qualityInfoDialog.close === "function") qualityInfoDialog.close();
  else qualityInfoDialog.removeAttribute("open");
});
document.querySelectorAll("[data-term-info]").forEach((button) => {
  button.addEventListener("click", () => openTermInfo(button.dataset.termInfo));
});
imageDialog.addEventListener("close", () => {
  imageDialogImage.removeAttribute("src");
  imageViewerItems = [];
  imageViewerIndex = 0;
});

activateCurrentView();
applyEqModePreference(readEqModePreference());
byId("eq-mode-checkbox").addEventListener("change", rememberEqModePreference);
byId("hosted-eq-mode-checkbox").addEventListener("change", rememberEqModePreference);
byId("refresh-button").addEventListener("click", runDashboardLoad);
byId("history-toggle").addEventListener("click", () => {
  toggleHistory();
});
byId("portfolio-search").addEventListener("input", (event) => {
  portfolioSearch = event.target.value;
  if (latestDashboardData) renderPortfolio(latestDashboardData);
});
byId("portfolio-filter").addEventListener("change", (event) => {
  portfolioFilter = event.target.value;
  if (latestDashboardData) renderPortfolio(latestDashboardData);
});
byId("quality-search").addEventListener("input", (event) => {
  qualitySearch = event.target.value;
  if (latestDashboardData) renderQualityByTarget(latestDashboardData);
});
byId("quality-filter").addEventListener("change", (event) => {
  qualityFilter = event.target.value;
  if (latestDashboardData) renderQualityByTarget(latestDashboardData);
});
byId("candidate-site-form").addEventListener("submit", saveCandidateSite);
byId("candidate-site-sort").addEventListener("change", (event) => {
  candidateSiteSort = event.target.value;
  renderSavedSiteLists();
});
byId("visited-site-sort").addEventListener("change", (event) => {
  visitedSiteSort = event.target.value;
  renderSavedSiteLists();
});
byId("candidate-site-comparison-clear").addEventListener("click", () => {
  selectedCandidateSiteIds = [];
  renderSavedSiteLists();
});
byId("sign-in-form").addEventListener("submit", signIn);
byId("forgot-password-button").addEventListener("click", requestPasswordReset);
byId("accept-invite-form").addEventListener("submit", acceptInvitation);
byId("sign-out-button").addEventListener("click", signOut);
byId("hosted-account-retry").addEventListener("click", retryHostedAccountLoad);
byId("hosted-account-form").addEventListener("submit", saveHostedAccount);
byId("hosted-use-device-location").addEventListener("click", useDeviceLocation);
byId("hosted-refresh-button").addEventListener("click", loadHostedTonight);
byId("hosted-feedback-yes").addEventListener("click", () => {
  byId("hosted-feedback-detail").hidden = true;
  byId("hosted-feedback-reason").value = "";
  saveHostedPlanFeedback(true);
});
byId("hosted-feedback-no").addEventListener("click", () => {
  saveHostedPlanFeedback(false);
  byId("hosted-feedback-detail").hidden = false;
});
byId("hosted-feedback-save-note").addEventListener("click", () => {
  const reason = byId("hosted-feedback-reason").value.trim();
  if (!reason) {
    setText("hosted-feedback-message", "Add a short note first, or leave this optional field blank.");
    return;
  }
  saveHostedPlanFeedback(false, reason);
});
byId("hosted-edit-home-button").addEventListener("click", () => {
  updateHostedAccountForm(hostedProfile, hostedObservatory);
  showHostedAccountSetup();
});
byId("hosted-account-cancel").addEventListener("click", showHostedTonight);
byId("hosted-ready-continue").addEventListener("click", loadHostedTonight);
byId("hosted-ready-edit-home").addEventListener("click", () => {
  updateHostedAccountForm(hostedProfile, hostedObservatory);
  showHostedAccountSetup();
});

const bootApplication = async () => {
  if (usesHostedAuth) {
    await initializeHostedAuth();
    return;
  }
  runDashboardLoad();
};

bootApplication();
