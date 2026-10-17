"use strict";

const queryInput = document.querySelector("#query");
const runButton = document.querySelector("#run");
const resetButton = document.querySelector("#reset");
const globalStatus = document.querySelector("#global-status");
const presetsElement = document.querySelector("#presets");
const explanation = document.querySelector("#explanation");
let examples = [];
let csrfToken = "";
let busy = false;

async function api(path, payload, token) {
  const options = { credentials: "same-origin", cache: "no-store" };
  if (payload !== undefined) {
    options.method = "POST";
    options.headers = { "Content-Type": "application/json" };
    if (token) options.headers["X-CSRF-Token"] = token;
    options.body = JSON.stringify(payload);
  }
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message || "The local request failed.");
  return data;
}

function setStatus(message, error = false) {
  globalStatus.textContent = message;
  globalStatus.classList.toggle("error", error);
}

function setBusy(value) {
  busy = value;
  runButton.disabled = value;
  resetButton.disabled = value || !csrfToken;
  queryInput.disabled = value;
  for (const button of presetsElement.querySelectorAll("button")) button.disabled = value;
}

function renderPanel(mode, data) {
  const panel = document.querySelector(`#${mode}-panel`);
  const status = panel.querySelector(".panel-status");
  status.textContent = data.error ? data.error.message : `${data.rows.length} record(s) returned`;
  status.classList.toggle("error", Boolean(data.error));
  panel.querySelector(".sql").textContent = data.sql;
  if (mode === "fixed") {
    panel.querySelector(".parameters").textContent = JSON.stringify(data.parameters, null, 2);
  }
  const body = panel.querySelector("tbody");
  body.replaceChildren();
  for (const record of data.rows) {
    const row = document.createElement("tr");
    const internal = record.source === "internal";
    row.classList.toggle("internal", internal);
    const values = [record.id, record.name, record.description,
      internal ? "SYNTHETIC INTERNAL" : "Public catalogue"];
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = String(value);
      row.append(cell);
    }
    body.append(row);
  }
  panel.querySelector(".empty-message").hidden = data.rows.length !== 0 || Boolean(data.error);
}

function renderFailure(mode) {
  const panel = document.querySelector(`#${mode}-panel`);
  const status = panel.querySelector(".panel-status");
  status.textContent = "Request failed. Check that the local server is running, then retry.";
  status.classList.add("error");
  panel.querySelector("tbody").replaceChildren();
  panel.querySelector(".sql").textContent = "Query unavailable because the request failed.";
  panel.querySelector(".empty-message").hidden = true;
  if (mode === "fixed") panel.querySelector(".parameters").textContent = "Unavailable";
}

async function compare() {
  if (busy) return;
  const query = queryInput.value;
  setBusy(true);
  setStatus("Running both queries against the local synthetic database…");
  for (const button of presetsElement.querySelectorAll("button")) {
    button.setAttribute("aria-pressed", String(button.dataset.query === query));
  }
  const modes = ["vulnerable", "fixed"];
  const results = await Promise.allSettled(modes.map(mode => api(`/api/search/${mode}`, { query })));
  let failed = false;
  results.forEach((result, index) => {
    if (result.status === "fulfilled") renderPanel(modes[index], result.value);
    else { renderFailure(modes[index]); failed = true; }
  });
  if (failed) {
    setStatus("A local request failed. Restart the server or retry.", true);
    explanation.textContent = "The comparison is incomplete. Retry to compare both results.";
  } else {
    const example = examples.find(item => item.query === query);
    const vulnerable = results[0].value;
    if (example) explanation.textContent = example.explanation;
    else if (vulnerable.error) explanation.textContent = "The interpolated query changed SQL syntax and failed. The fixed query binds the whole search pattern as data, including quotes.";
    else if (vulnerable.rows.some(row => row.source === "internal")) explanation.textContent = "The unsafe query read synthetic internal records. The fixed template searches only product names and keeps the input separate from SQL code.";
    else explanation.textContent = "The fixed query keeps the SQL structure constant and supplies the search pattern separately. Ordinary input can return the same results; LIKE wildcards still apply.";
    setStatus("Comparison complete · All records are synthetic.");
  }
  setBusy(false);
}

document.querySelector("#search-form").addEventListener("submit", event => {
  event.preventDefault();
  compare();
});

resetButton.addEventListener("click", async () => {
  if (busy || !window.confirm("Reset the dedicated synthetic demo database to its original fixtures?")) return;
  setBusy(true);
  try {
    await api("/api/reset", {}, csrfToken);
    queryInput.value = "backpack";
    setBusy(false);
    await compare();
    setStatus("Demo data reset to the original fixtures. Comparison refreshed.");
  } catch {
    setStatus("Reset failed. Reload the page to refresh its local reset token, then retry.", true);
    setBusy(false);
  }
});

async function initialize() {
  setBusy(true);
  try {
    const [presets, config] = await Promise.all([api("/api/examples"), api("/api/config")]);
    examples = presets;
    csrfToken = config.csrf_token;
    for (const example of examples) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = example.label;
      button.title = example.explanation;
      button.dataset.query = example.query;
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", () => { queryInput.value = example.query; compare(); });
      presetsElement.append(button);
    }
    setBusy(false);
    await compare();
  } catch {
    setStatus("Could not load the local lab. Check the server, then reload this page.", true);
    setBusy(false);
  }
}

initialize();
