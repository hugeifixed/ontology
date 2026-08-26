function getRequestControl(element) {
  if (element?.matches?.("[data-loading-label]")) {
    return element;
  }
  return element?.querySelector?.("[data-loading-label]") || null;
}

const API_KEY_STORAGE_PREFIX = "governed-studio.api-key.";
const API_KEY_REUSE_FLAG = "governed-studio.reuse-api-key";
const composeProgressTimers = new WeakMap();

function stopComposeProgress(form) {
  const timer = composeProgressTimers.get(form);
  if (timer) {
    window.clearInterval(timer);
    composeProgressTimers.delete(form);
  }
  const panel = form?.querySelector("[data-compose-progress]");
  if (panel) {
    panel.hidden = true;
    panel.classList.add("hidden");
  }
}

function startComposeProgress(form) {
  const panel = form?.querySelector("[data-compose-progress]");
  const providerInput = form?.querySelector("select[name='provider']");
  if (!panel || !providerInput) return;

  stopComposeProgress(form);
  panel.hidden = false;
  panel.classList.remove("hidden");

  const title = panel.querySelector("[data-compose-progress-title]");
  const message = panel.querySelector("[data-compose-progress-message]");
  const elapsed = panel.querySelector("[data-compose-progress-elapsed]");
  const providerLabel =
    providerInput.options[providerInput.selectedIndex]?.textContent?.trim() ||
    "the selected route";
  const isDemo = providerInput.value === "demo";
  const startedAt = Date.now();
  let lastStage = -1;

  if (title) {
    title.textContent = isDemo
      ? "Building the proposal locally"
      : `Waiting for ${providerLabel}`;
  }

  const update = () => {
    const seconds = Math.floor((Date.now() - startedAt) / 1000);
    if (elapsed) elapsed.textContent = `Elapsed · ${seconds}s`;

    const stage = seconds < 3 ? 0 : seconds < 15 ? 1 : seconds < 30 ? 2 : 3;
    if (!message || stage === lastStage) return;
    lastStage = stage;
    if (isDemo) {
      message.textContent =
        "Validating the intent against approved catalog metadata. No external model call is being made.";
      return;
    }
    const stageMessages = [
      `Sending intent and approved catalog metadata to ${providerLabel}.`,
      `Waiting for a schema-constrained response from ${providerLabel}.`,
      `Still waiting for ${providerLabel}; provider response times can vary.`,
      "The request is still active. The server will stop it at the configured provider timeout.",
    ];
    message.textContent = stageMessages[stage];
  };

  update();
  composeProgressTimers.set(form, window.setInterval(update, 1000));
}

function safeSessionGet(key) {
  try {
    return window.sessionStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function safeSessionSet(key, value) {
  try {
    window.sessionStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

function safeSessionRemove(key) {
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // Storage can be unavailable under restrictive browser privacy settings.
  }
}

function apiKeyControls(form) {
  return {
    keyInput: form?.querySelector("input[name='api_key']"),
    providerInput: form?.querySelector("select[name='provider']"),
    reuseInput: form?.querySelector("[data-reuse-api-key]"),
    status: form?.querySelector("[data-key-storage-status]"),
  };
}

function storageKeyFor(provider) {
  return `${API_KEY_STORAGE_PREFIX}${provider}`;
}

function updateProviderRouteStatus(provider) {
  const route = document.querySelector(`[data-provider-route="${provider}"]`);
  if (!route) return;

  const form = document.querySelector("[data-api-key-form]");
  const controls = apiKeyControls(form);
  const hasTabKey =
    safeSessionGet(API_KEY_REUSE_FLAG) === "true" &&
    Boolean(safeSessionGet(storageKeyFor(provider)));
  const hasRequestKey =
    controls.providerInput?.value === provider &&
    Boolean(controls.keyInput?.value.trim());
  const hasEnvironmentKey = route.dataset.environmentKey === "true";
  const status = route.querySelector("[data-provider-route-status]");
  const indicator = route.querySelector("[data-provider-route-indicator]");

  let label = "No key configured";
  let indicatorClass = "status-neutral";
  if (hasTabKey) {
    label = "Tab key ready";
    indicatorClass = "status-success";
  } else if (hasRequestKey) {
    label = "Request key entered";
    indicatorClass = "status-info";
  } else if (hasEnvironmentKey) {
    label = "Environment key available";
    indicatorClass = "status-success";
  }

  if (status) status.textContent = label;
  if (indicator) {
    indicator.classList.remove(
      "status-neutral",
      "status-info",
      "status-success",
      "status-warning",
      "status-error",
    );
    indicator.classList.add(indicatorClass);
  }
}

function updateProviderRouteStatuses() {
  updateProviderRouteStatus("gemini");
  updateProviderRouteStatus("anthropic");
}

function restoreTabKey(form) {
  const { keyInput, providerInput, reuseInput, status } = apiKeyControls(form);
  if (!keyInput || !providerInput || !reuseInput) return;

  const reuseEnabled = safeSessionGet(API_KEY_REUSE_FLAG) === "true";
  reuseInput.checked = reuseEnabled;
  if (!reuseEnabled || providerInput.value === "demo") {
    keyInput.value = "";
    if (status) status.textContent = "";
    updateProviderRouteStatuses();
    return;
  }

  const storedKey = safeSessionGet(storageKeyFor(providerInput.value));
  keyInput.value = storedKey;
  if (status) {
    const providerLabel = providerInput.value === "gemini" ? "Gemini" : "Anthropic";
    status.textContent = storedKey
      ? `${providerLabel} key ready in this tab.`
      : `No ${providerLabel} key is stored in this tab.`;
  }
  updateProviderRouteStatuses();
}

function forgetTabKeys(form) {
  safeSessionRemove(API_KEY_REUSE_FLAG);
  safeSessionRemove(storageKeyFor("gemini"));
  safeSessionRemove(storageKeyFor("anthropic"));
  const { keyInput, status } = apiKeyControls(form);
  if (keyInput) keyInput.value = "";
  if (status) status.textContent = "The tab-stored keys were removed.";
  updateProviderRouteStatuses();
}

function preserveTabKey(form) {
  const { keyInput, providerInput, reuseInput, status } = apiKeyControls(form);
  if (!keyInput || !providerInput || !reuseInput || !reuseInput.checked) return;
  if (providerInput.value === "demo" || !keyInput.value) return;

  const stored =
    safeSessionSet(API_KEY_REUSE_FLAG, "true") &&
    safeSessionSet(storageKeyFor(providerInput.value), keyInput.value);
  if (status) {
    status.textContent = stored
      ? "Key saved only for this browser tab."
      : "This browser blocked tab storage; the key will remain request-only.";
  }
  updateProviderRouteStatuses();
}

document.addEventListener("htmx:beforeRequest", (event) => {
  const target = event.detail.target;
  if (target) {
    target.setAttribute("aria-busy", "true");
    if (target.id) {
      event.detail.elt.dataset.requestTargetId = target.id;
    }
  }
  const composeFeedback = event.detail.elt.querySelector?.("[data-compose-feedback]");
  composeFeedback?.replaceChildren();
  if (event.detail.elt.matches?.("[data-api-key-form]")) {
    startComposeProgress(event.detail.elt);
  }
  const keyInput = event.detail.elt.querySelector?.("input[name='api_key']");
  if (keyInput) {
    preserveTabKey(event.detail.elt);
    keyInput.setAttribute("aria-busy", "true");
  }

  const requestControl = getRequestControl(event.detail.elt);
  if (requestControl) {
    requestControl.dataset.idleLabel = requestControl.getAttribute("aria-label") || "";
    requestControl.setAttribute("aria-label", requestControl.dataset.loadingLabel);
    requestControl.setAttribute("aria-busy", "true");
  }
});

document.addEventListener("htmx:afterRequest", (event) => {
  const target = event.detail.target;
  const originalTargetId = event.detail.elt.dataset.requestTargetId;
  if (originalTargetId) {
    document.getElementById(originalTargetId)?.setAttribute("aria-busy", "false");
    delete event.detail.elt.dataset.requestTargetId;
  }
  const keyInput = event.detail.elt.querySelector?.("input[name='api_key']");
  if (keyInput) {
    const { reuseInput } = apiKeyControls(event.detail.elt);
    if (reuseInput?.checked) {
      restoreTabKey(event.detail.elt);
    } else {
      keyInput.value = "";
    }
    keyInput.removeAttribute("aria-busy");
  }
  if (event.detail.elt.matches?.("[data-api-key-form]")) {
    stopComposeProgress(event.detail.elt);
  }

  const requestControl = getRequestControl(event.detail.elt);
  if (requestControl) {
    if (requestControl.dataset.idleLabel) {
      requestControl.setAttribute("aria-label", requestControl.dataset.idleLabel);
    }
    delete requestControl.dataset.idleLabel;
    requestControl.removeAttribute("aria-busy");
  }

  if (!event.detail.successful) {
    target?.setAttribute("aria-busy", "false");
    const announcer = document.getElementById("studio-announcer");
    if (announcer) {
      announcer.textContent = "The request could not be completed.";
    }
  }
});

["htmx:sendError", "htmx:timeout", "htmx:abort"].forEach((eventName) => {
  document.addEventListener(eventName, (event) => {
    const form = event.detail.elt?.matches?.("[data-api-key-form]")
      ? event.detail.elt
      : event.detail.elt?.closest?.("[data-api-key-form]");
    if (form) stopComposeProgress(form);
  });
});

document.addEventListener("change", (event) => {
  const form = event.target.closest?.("[data-api-key-form]");
  if (!form) return;
  if (event.target.matches("[data-reuse-api-key]")) {
    if (event.target.checked) {
      safeSessionSet(API_KEY_REUSE_FLAG, "true");
      preserveTabKey(form);
    } else {
      forgetTabKeys(form);
    }
  }
  if (event.target.matches("select[name='provider']")) {
    restoreTabKey(form);
  }
  updateProviderRouteStatuses();
});

document.addEventListener("input", (event) => {
  if (!event.target.matches("[data-api-key-form] input[name='api_key']")) return;
  updateProviderRouteStatuses();
});

document.addEventListener("click", (event) => {
  const example = event.target.closest?.("[data-discovery-example]");
  if (example) {
    const input = document.getElementById("id_discovery_intent");
    if (input) {
      input.value = example.dataset.discoveryExample;
      input.focus();
    }
    return;
  }

  const useIntent = event.target.closest?.("[data-use-discovery-intent]");
  if (useIntent) {
    const result = useIntent.closest("article");
    const source = result?.querySelector("[data-discovered-intent]");
    const proposalIntent = document.getElementById("id_intent");
    if (source && proposalIntent) {
      proposalIntent.value = source.value;
      proposalIntent.scrollIntoView({ behavior: "smooth", block: "center" });
      window.setTimeout(() => proposalIntent.focus(), 180);
    }
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("[data-api-key-form]");
  if (form) restoreTabKey(form);
  updateProviderRouteStatuses();
});

document.addEventListener("htmx:afterSettle", (event) => {
  const target = event.detail.target;
  target?.setAttribute("aria-busy", "false");

  const result = target?.matches?.("[data-result-focus]")
    ? target
    : target?.querySelector?.("[data-result-focus]");
  result?.focus();

  const announcer = document.getElementById("studio-announcer");
  if (announcer) {
    announcer.textContent = result?.dataset.announcement || "Content updated.";
  }
});
