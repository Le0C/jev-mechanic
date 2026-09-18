"use strict";

const FLAG_THRESHOLD = 0.9;
const PROJECTION_SESSIONS = 1000;
const MOCK_PARAM = new URLSearchParams(location.search).get("mock");
const MOCK = MOCK_PARAM === "1" || MOCK_PARAM === "2";
const MOCK_VERSION = MOCK_PARAM === "2" ? 2 : 1;
const MOCK_STATUSES = ["asking", "confirm", "reask", "flagged", "diagnosed", "specialist"];
const MOCK_STATUSES_V2 = ["asking", "confirm", "reask", "flagged", "complete", "specialist"];
const V2_FAULT_THRESHOLD = 0.5;
const PREF_KEY = "jev-mechanic-start";
const MOCK_FIX = ["Measure the resting voltage.", "Charge the battery.", "Do a load test."];

const state = {
  view: null,
  mockBase: null,
  busy: false,
  renderedMermaid: null,
  renderedCurrent: null,
  openLedgerRows: new Set(),
  fixChecked: new Set(),
  chart: { scale: 1, x: 0, y: 0 },
  start: { version: 1, evidence: "report", cases: [], caseId: null },
};

const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value === true) node.setAttribute(key, "");
    else node.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function humanize(id) {
  if (!id) return "";
  const text = String(id).replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function pct(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return `${Math.round(value * 100)}%`;
}

function usd(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  if (value === 0) return "$0";
  if (Math.abs(value) >= 1) return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const decimals = Math.min(10, Math.max(2, -Math.floor(Math.log10(Math.abs(value))) + 2));
  return `$${value.toFixed(decimals)}`;
}

function tokens(value) {
  if (value === null || value === undefined) return "n/a";
  if (value >= 1e6) return `${(value / 1e6).toFixed(value >= 1e7 ? 1 : 2)}M`;
  return Math.round(value).toLocaleString("en-US");
}

function seconds(value) {
  if (value === null || value === undefined) return "n/a";
  if (value >= 3600) return `${(value / 3600).toFixed(1)} h`;
  if (value >= 60) return `${(value / 60).toFixed(1)} min`;
  return `${value.toFixed(2)} s`;
}

/* ---------- API ---------- */

async function api(method, path, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    throw new Error(`The server did not answer: ${error.message}`);
  }
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const message = payload && payload.error ? payload.error : `HTTP ${response.status}`;
    throw new Error(`${response.status}: ${message}`);
  }
  return payload;
}

async function run(label, work) {
  if (state.busy) return;
  if (MOCK) {
    showError("Mock mode sends no requests. Use the Status menu to preview a different state.");
    return;
  }
  setBusy(true, label);
  hideError();
  try {
    await work();
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

function setBusy(busy, label) {
  state.busy = busy;
  document.body.classList.toggle("is-busy", busy);
  $("busy").hidden = !busy;
  if (label) $("busy-text").textContent = label;
  for (const button of document.querySelectorAll("#app button, #app input, #start button, #start textarea, #start input")) {
    if (button.closest(".chart-tools") || button.closest(".ledger-row") || button.closest(".fix-list")) continue;
    button.disabled = busy;
  }
}

function showError(text) {
  $("error-text").textContent = text;
  $("error").hidden = false;
}

function hideError() {
  $("error").hidden = true;
}

function setView(view) {
  state.view = view;
  if (!MOCK && view && view.id && location.hash !== `#${view.id}`) {
    history.replaceState(null, "", `#${view.id}`);
  }
  render();
}

function sessionPath(action) {
  return `/api/sessions/${encodeURIComponent(state.view.id)}${action ? `/${action}` : ""}`;
}

function sendAnswer(text) {
  const clean = text.trim();
  if (!clean) {
    showError("Type an answer first.");
    return;
  }
  run("Jev reads the answer", async () => setView(await api("POST", sessionPath("answer"), { text: clean })));
}

function choose(optionId) {
  run("Jev updates the case", async () => setView(await api("POST", sessionPath("choose"), { option: optionId })));
}

function accept() {
  run("Accept the diagnosis", async () => setView(await api("POST", sessionPath("accept"), {})));
}

function keepGoing() {
  run("Continue the flowchart", async () => setView(await api("POST", sessionPath("continue"), {})));
}

/* ---------- Start screen ---------- */

function showStart() {
  state.view = null;
  state.renderedMermaid = null;
  state.renderedCurrent = null;
  state.openLedgerRows.clear();
  state.fixChecked.clear();
  if (!MOCK) history.replaceState(null, "", location.pathname + location.search);
  $("app").hidden = true;
  $("start").hidden = false;
  $("new-session").hidden = true;
  $("status-badge").hidden = true;
  $("session-id").textContent = "";
  renderStartMode();
  if (!$("report-field").hidden) $("report-input").focus();
}

async function loadExamples() {
  const list = $("examples");
  list.replaceChildren(el("li", { class: "muted" }, "No examples yet."));
  if (MOCK) {
    list.replaceChildren(el("li", { class: "muted" }, "Mock mode loads no examples."));
    return;
  }
  try {
    const examples = await api("GET", "/api/examples");
    if (!examples.length) return;
    list.replaceChildren(
      ...examples.map((example) =>
        el(
          "li",
          {},
          el(
            "button",
            {
              class: "btn example",
              type: "button",
              onclick: () => {
                $("report-input").value = example.report;
                $("report-input").focus();
              },
            },
            el("span", { class: "example-title" }, example.title || example.id),
            el("span", { class: "example-report" }, example.report),
          ),
        ),
      ),
    );
  } catch (error) {
    list.replaceChildren(el("li", { class: "muted" }, `The examples did not load. ${error.message}`));
  }
}

function startSession(event) {
  event.preventDefault();
  const options = {
    extra_questions: $("opt-extra").checked,
    independent_lane: $("opt-independent").checked,
  };
  const start = state.start;
  let body;
  const report = $("report-input").value.trim();
  if (start.version === 2 && start.evidence === "case_file") {
    if (!start.caseId) {
      showError("Select a case first.");
      return;
    }
    body = { version: 2, mode: "case_file", case_id: start.caseId, ...options };
  } else if (!report) {
    showError("Type or select a customer report first.");
    return;
  } else if (start.version === 2) {
    body = { version: 2, mode: "report", report, ...options };
  } else {
    body = { report, ...options };
  }
  run(start.version === 2 ? "Jev reads the evidence" : "Jev reads the report", async () => {
    const view = await api("POST", "/api/sessions", body);
    state.chart = { scale: 1, x: 0, y: 0 };
    setView(view);
  });
}

/* ---------- Rendering ---------- */

function render() {
  const view = state.view;
  if (!view) return;
  renderFolds(view);
  renderCompare(view);
  $("start").hidden = true;
  $("app").hidden = false;
  $("new-session").hidden = false;
  $("session-id").textContent = view.id || "";
  const badge = $("status-badge");
  badge.hidden = false;
  badge.className = `badge badge-${view.status}`;
  badge.textContent = view.status;

  const v2 = isV2(view);
  for (const node of document.querySelectorAll(".v2-only")) node.hidden = !v2;
  $("report-panel").hidden = v2;
  $("evidence-panel").hidden = !v2;
  $("triage-wrap").hidden = v2;
  $("component-strip").hidden = !v2;
  $("flowchart-lane-title").textContent = v2 ? "Branch scores" : "Flowchart lane";
  $("independent-note").textContent = v2
    ? "Jev reads the whole case, with one Noul for each diagnosis. This lane does not change the loop."
    : "Jev reads the whole case in one question. This lane does not change the flowchart.";

  if (v2) {
    renderEvidence(view);
    renderComponents(view);
    renderSymptoms(view);
    renderFaults(view);
    renderFixPlan(view);
  } else {
    $("report").textContent = view.report || "";
    $("chart-title").textContent = "Flowchart";
  }
  renderLog(view);
  renderAnswer(view);
  renderChart(view);
  renderFlowchartLane(view);
  if (v2) renderIndependentV2(view);
  else renderIndependent(view);
  renderLedger(view);
  if (state.busy) setBusy(true);
}

function optionText(view, nodeId, optionId) {
  if (view.current && view.current.node_id === nodeId) {
    const match = (view.current.options || []).find((o) => o.id === optionId);
    if (match) return match.text;
  }
  return humanize(optionId);
}

function renderLog(view) {
  const steps = view.steps || [];
  const log = $("log");
  if (!steps.length) {
    log.replaceChildren(el("li", { class: "log-empty" }, "No answers yet."));
    return;
  }
  const items = [];
  let group = null;
  for (const step of steps) {
    if (isV2(view)) {
      const key = `${step.loop}:${step.component}`;
      if (key !== group) {
        group = key;
        items.push(
          el(
            "li",
            { class: "log-group" },
            el("span", { class: "chip" }, `Loop ${step.loop ?? "?"}`),
            el("span", {}, componentLabel(view, step.component)),
          ),
        );
      }
    }
    items.push(stepItem(view, step));
  }
  log.replaceChildren(...items);
  const last = log.lastElementChild;
  if (last && !MOCK) last.scrollIntoView({ block: "nearest" });
}

function stepItem(view, step) {
  const fromReport = step.source === "report";
  const probs = Object.entries(step.probabilities || {}).sort((a, b) => b[1] - a[1]);
  return el(
    "li",
    { class: `step${fromReport ? " step-report" : ""}` },
    el(
      "div",
      { class: "step-head" },
      el("span", {}, `Step ${step.step}`),
      fromReport
        ? el("span", { class: "chip chip-report" }, view.mode === "case_file" ? "from the case file" : "from the report") : el("span", { class: "chip" }, "mechanic"),
      step.outcome ? el("span", { class: `chip chip-${step.outcome}` }, step.outcome) : null,
    ),
    el("div", { class: "step-question" }, step.question || step.node_id),
    step.answer_text ? el("div", { class: "step-answer" }, `"${step.answer_text}"`) : null,
    el(
      "div",
      { class: "step-jev" },
      el("span", {}, "Jev: ", el("strong", {}, step.option ? optionText(view, step.node_id, step.option) : "no option")),
      el("span", { class: "conf", title: "Confidence of Jev" }, `confidence ${pct(step.confidence)}`),
    ),
    probs.length
      ? el(
          "details",
          { class: "probs" },
          el("summary", {}, "Probabilities"),
          el("ul", {}, probs.map(([id, p]) => el("li", {}, `${id}: ${p.toFixed(3)}`))),
        )
      : null,
  );
}

function answerForm(view, placeholder) {
  const input = el("input", { type: "text", id: "answer-input", placeholder, autocomplete: "off" });
  const form = el(
    "form",
    {
      class: "answer-row",
      onsubmit: (event) => {
        event.preventDefault();
        sendAnswer(input.value);
      },
    },
    input,
    el("button", { class: "btn btn-primary", type: "submit" }, "Send"),
  );
  const parts = [form];
  if (view.current && view.current.yes_no) {
    parts.push(
      el(
        "div",
        { class: "quick" },
        ["Yes", "No", "Not sure"].map((label) =>
          el("button", { class: "btn", type: "button", onclick: () => sendAnswer(label) }, label),
        ),
      ),
    );
  }
  return parts;
}

function renderAnswer(view) {
  const area = $("answer-area");
  const current = view.current;
  const parts = [];
  switch (view.status) {
    case "asking":
      parts.push(el("p", { class: "answer-question" }, current ? current.question : ""));
      parts.push(...answerForm(view, "Type the answer of the mechanic"));
      break;
    case "confirm":
      parts.push(el("p", { class: "answer-question" }, current ? current.question : ""));
      parts.push(el("p", { class: "answer-note message message-warn" }, "Jev is not sure. Select the option that matches the answer."));
      parts.push(
        el(
          "div",
          { class: "choices" },
          (view.confirm_options || []).map((option) =>
            el(
              "button",
              { class: "btn", type: "button", onclick: () => choose(option.id) },
              el("span", {}, option.text || humanize(option.id)),
              el("span", { class: "conf" }, pct(option.probability)),
            ),
          ),
        ),
      );
      break;
    case "reask":
      parts.push(el("p", { class: "answer-note message message-warn" }, "Jev could not map the answer to an option. Answer the question again."));
      parts.push(el("p", { class: "answer-question" }, current ? current.question : ""));
      if (current && current.options && current.options.length) {
        parts.push(el("ul", { class: "option-list" }, current.options.map((o) => el("li", {}, o.text))));
      }
      parts.push(...answerForm(view, "Type the answer again"));
      break;
    case "flagged":
      parts.push(
        el(
          "p",
          { class: "message message-warn" },
          view.flag
            ? `The ${isV2(view) ? "branch scores flag" : "flowchart lane flags"} ${view.flag.label} at ${pct(view.flag.score)}. Accept the diagnosis, or keep going with the next question.`
            : "A diagnosis passed 0.9. Accept it, or keep going.",
        ),
      );
      if (current) parts.push(el("p", { class: "answer-question muted" }, `Next question: ${current.question}`));
      parts.push(
        el(
          "div",
          { class: "flag-actions" },
          el("button", { class: "btn btn-good", type: "button", onclick: accept }, "Accept"),
          el("button", { class: "btn", type: "button", onclick: keepGoing }, "Keep going"),
        ),
      );
      break;
    case "diagnosed":
      parts.push(
        el(
          "p",
          { class: "message message-good" },
          view.diagnosis ? `Diagnosis: ${view.diagnosis.label}. Do the fix steps on the right.` : "The flowchart found a diagnosis.",
        ),
      );
      break;
    case "complete":
      parts.push(...completeMessage(view));
      break;
    case "specialist":
      parts.push(
        el(
          "p",
          { class: "message message-bad" },
          isV2(view)
            ? "Refer this car to a specialist. The loop found no fault."
            : "Refer this car to a specialist. The flowchart has no diagnosis for this case.",
        ),
      );
      if (isV2(view)) parts.push(...unexplainedMessage(view));
      break;
    default:
      parts.push(el("p", { class: "muted" }, `Status: ${view.status}`));
  }
  area.replaceChildren(...parts);
  const input = $("answer-input");
  if (input && !state.busy && !MOCK) input.focus();
}

function barRow({ label, score, top, threshold, title }) {
  const limit = threshold === true ? FLAG_THRESHOLD : threshold;
  const width = Math.max(0, Math.min(1, score || 0)) * 100;
  return el(
    "div",
    { class: `bar-row${top ? " top" : ""}`, title: title || `${label}: ${(score || 0).toFixed(3)}` },
    el("span", { class: "bar-label" }, label),
    el(
      "span",
      { class: "bar-track" },
      el("span", { class: "bar-fill", style: `width:${width.toFixed(1)}%` }),
      limit ? el("span", { class: "bar-threshold", style: `left:${limit * 100}%`, title: `${limit} limit` }) : null,
    ),
    el("span", { class: "bar-value" }, pct(score)),
  );
}

function renderBars(target, items, { threshold = false } = {}) {
  if (!items.length) {
    target.replaceChildren(el("p", { class: "bars-empty" }, "No scores yet."));
    return;
  }
  const best = Math.max(...items.map((i) => i.score || 0));
  target.replaceChildren(...items.map((item) => barRow({ ...item, top: (item.score || 0) === best && best > 0, threshold })));
}

function renderFlowchartLane(view) {
  if (isV2(view)) {
    const branch = [...(view.branch_scores || [])].sort((a, b) => b.score - a.score);
    renderBars($("scores"), branch.map((s) => ({ label: s.label || humanize(s.id), score: s.score })), { threshold: true });
    if (!branch.length) $("scores").replaceChildren(el("p", { class: "bars-empty" }, "No component is active."));
    $("diagnosis").replaceChildren();
    const holder = $("scores-wrap").parentElement;
    if (holder && holder.classList.contains("final-scores")) holder.replaceWith($("scores-wrap"));
    renderFlag(view);
    return;
  }
  const triage = view.triage || {};
  const triageItems = Object.entries(triage.probabilities || {})
    .sort((a, b) => b[1] - a[1])
    .map(([id, score]) => ({ label: id === "none" ? "None of these" : humanize(id), score }));
  renderBars($("triage"), triageItems);
  if (triage.confidence !== undefined && triage.confidence !== null) {
    $("triage").append(el("p", { class: "note" }, `Triage confidence ${pct(triage.confidence)}`));
  }

  const scores = [...(view.scores || [])].sort((a, b) => b.score - a.score);
  renderBars($("scores"), scores.map((s) => ({ label: s.label || humanize(s.id), score: s.score })), { threshold: true });

  const diagnosis = $("diagnosis");
  const scoresWrap = $("scores-wrap");
  if (view.status === "diagnosed" && view.diagnosis) {
    const d = view.diagnosis;
    diagnosis.replaceChildren(
      el(
        "div",
        { class: "diagnosis-card" },
        el("h3", {}, d.label || humanize(d.id)),
        d.description ? el("p", {}, d.description) : null,
        el("h4", { class: "sub-title" }, "Fix steps"),
        el(
          "ol",
          { class: "fix-list" },
          (d.fix || []).map((stepText, index) => {
            const key = `${d.id}:${index}`;
            const box = el("input", {
              type: "checkbox",
              checked: state.fixChecked.has(key),
              onchange: (event) => {
                if (event.target.checked) state.fixChecked.add(key);
                else state.fixChecked.delete(key);
              },
            });
            return el("li", {}, el("label", {}, box, el("span", {}, `${index + 1}. ${stepText}`)));
          }),
        ),
      ),
    );
    const details = el("details", { class: "final-scores" }, el("summary", {}, "Diagnosis scores"));
    scoresWrap.replaceWith(details);
    details.append(scoresWrap);
    scoresWrap.hidden = false;
  } else {
    diagnosis.replaceChildren();
    const holder = scoresWrap.parentElement;
    if (holder && holder.classList.contains("final-scores")) {
      holder.replaceWith(scoresWrap);
    }
  }

  renderFlag(view);
}

function renderFlag(view) {
  const flag = $("flag");
  if (view.flag && view.status !== "diagnosed" && view.status !== "complete") {
    const active = view.status === "flagged";
    flag.replaceChildren(
      el(
        "div",
        { class: `flag${active ? "" : " flag-quiet"}` },
        el("span", {}, "Flag: ", el("strong", {}, view.flag.label || humanize(view.flag.id)), ` at ${pct(view.flag.score)}`),
        active
          ? el(
              "div",
              { class: "flag-actions" },
              el("button", { class: "btn btn-good btn-small", type: "button", onclick: accept }, "Accept"),
              el("button", { class: "btn btn-small", type: "button", onclick: keepGoing }, "Keep going"),
            )
          : el("span", { class: "small" }, "The mechanic continues the flowchart."),
      ),
    );
  } else {
    flag.replaceChildren();
  }
}

function renderIndependent(view) {
  const lane = view.independent || { enabled: false, top: [], flag: null };
  const target = $("independent");
  const flag = $("independent-flag");
  if (!lane.enabled) {
    target.replaceChildren(el("p", { class: "bars-empty" }, "The independent lane is off for this session."));
    flag.replaceChildren();
    return;
  }
  const items = [...(lane.top || [])]
    .sort((a, b) => b.score - a.score)
    .map((s) => ({ label: s.label || (s.id === "none" ? "None of these" : humanize(s.id)), score: s.score }));
  renderBars(target, items, { threshold: true });
  flag.replaceChildren(
    lane.flag
      ? el(
          "div",
          { class: "flag" },
          el("span", {}, "Flag: ", el("strong", {}, lane.flag.label || humanize(lane.flag.id)), ` at ${pct(lane.flag.score)}`),
        )
      : el("p", { class: "note" }, `No diagnosis passed ${FLAG_THRESHOLD} in this lane.`),
  );
}

function ledgerDetail(row) {
  const parts = [];
  if (row.request !== undefined) {
    parts.push(el("h4", {}, "Request"), el("pre", {}, JSON.stringify(row.request, null, 2)));
  }
  const raw = row.raw !== undefined ? row.raw : row.answers !== undefined ? row.answers : row.response;
  if (raw !== undefined) {
    parts.push(el("h4", {}, "Raw answer"), el("pre", {}, JSON.stringify(raw, null, 2)));
  }
  if (!parts.length) {
    const fields = {};
    for (const [key, value] of Object.entries(row)) fields[key] = value;
    parts.push(el("h4", {}, "Row fields"), el("pre", {}, JSON.stringify(fields, null, 2)));
  }
  return el("div", { class: "ledger-detail" }, parts);
}

function renderLedger(view) {
  const ledger = view.ledger || { rows: [], totals: {} };
  const rows = ledger.rows || [];
  const head = el(
    "div",
    { class: "ledger-head" },
    el("span", {}, "Step"),
    el("span", {}, "Lane"),
    el("span", {}, "Kind"),
    el("span", { class: "num", title: "Input tokens" }, "In tok."),
    el("span", { class: "num" }, "Time"),
    el("span", { class: "num" }, "Jev cost"),
    el("span", { class: "num", title: "Opus 5 at the same input tokens" }, "Opus 5 cost"),
    el("span", {}),
  );
  const rowNodes = rows.map((row, index) => {
    const key = `${index}:${row.step}:${row.lane}:${row.kind}`;
    const details = el(
      "details",
      { class: "ledger-row", open: state.openLedgerRows.has(key) },
      el(
        "summary",
        { title: "Show the details of this request" },
        el("span", {}, row.step),
        el("span", { class: `lane-${row.lane}`, title: row.lane }, row.lane === "independent" ? "indep." : row.lane === "flowchart" ? "flow" : row.lane),
        el("span", {}, row.kind),
        el("span", { class: "num" }, tokens(row.input_tokens)),
        el("span", { class: "num" }, seconds(row.seconds)),
        el("span", { class: "num" }, usd(row.jev_cost)),
        el("span", { class: "num" }, usd(row.opus5_cost)),
      ),
    );
    details.addEventListener("toggle", () => {
      if (details.open) {
        state.openLedgerRows.add(key);
        if (!details.querySelector(".ledger-detail")) details.append(ledgerDetail(row));
      } else {
        state.openLedgerRows.delete(key);
      }
    });
    if (details.open) details.append(ledgerDetail(row));
    return details;
  });
  $("ledger").replaceChildren(
    el("div", { class: "ledger-grid" }, head, rowNodes.length ? rowNodes : el("p", { class: "bars-empty" }, "No requests yet.")),
  );

  const t = ledger.totals || {};
  const ratio = t.jev_cost > 0 ? t.opus5_cost / t.jev_cost : null;
  const stat = (label, value, sub) =>
    el("div", { class: "stat" }, el("div", { class: "stat-label" }, label), el("div", { class: "stat-value" }, value), sub ? el("div", { class: "stat-sub" }, sub) : null);
  const n = PROJECTION_SESSIONS;
  $("totals").replaceChildren(
    el("h3", { class: "sub-title" }, `Session totals (${t.requests ?? rows.length} requests)`),
    el(
      "div",
      { class: "totals" },
      stat("Tokens", tokens(t.input_tokens), `in, ${tokens(t.output_tokens)} out`),
      stat("Jev cost", usd(t.jev_cost)),
      stat("Opus 5 cost", usd(t.opus5_cost), "at the same input tokens"),
      stat("Ratio", ratio ? `${ratio.toFixed(0)}x` : "n/a", "Opus 5 / Jev"),
      stat("Compute time", seconds(t.compute_seconds ?? 0), "sum of all requests"),
      stat("Wait time", seconds(t.wait_seconds ?? 0), "longest request of each step"),
    ),
    el(
      "div",
      { class: "projection" },
      el("h3", {}, `Projection for ${n.toLocaleString("en-US")} sessions like this one`),
      el(
        "div",
        { class: "totals" },
        stat("Tokens", tokens((t.input_tokens || 0) * n), "input"),
        stat("Jev cost", usd((t.jev_cost || 0) * n)),
        stat("Opus 5 cost", usd((t.opus5_cost || 0) * n)),
        stat("Compute time", seconds((t.compute_seconds || 0) * n)),
      ),
    ),
    el(
      "p",
      { class: "note" },
      "The Opus 5 column multiplies the Jev input tokens by $5.00 for each million. It is a lower limit: it has no output tokens and no cache.",
    ),
  );
}

/* ---------- Start screen, version 2 ---------- */

function readPrefs() {
  try {
    return JSON.parse(localStorage.getItem(PREF_KEY) || "{}") || {};
  } catch {
    return {};
  }
}

function savePrefs() {
  try {
    localStorage.setItem(PREF_KEY, JSON.stringify({ version: state.start.version, evidence: state.start.evidence }));
  } catch {
    /* Storage is optional. */
  }
}

function setupStart() {
  const prefs = readPrefs();
  if (prefs.version === 2) state.start.version = 2;
  if (prefs.evidence === "case_file") state.start.evidence = "case_file";
  $(state.start.version === 2 ? "version-2" : "version-1").checked = true;
  $(state.start.evidence === "case_file" ? "evidence-case-file" : "evidence-report").checked = true;
  for (const input of document.querySelectorAll('input[name="version"]')) {
    input.addEventListener("change", () => {
      state.start.version = Number(input.value);
      savePrefs();
      renderStartMode();
    });
  }
  for (const input of document.querySelectorAll('input[name="evidence"]')) {
    input.addEventListener("change", () => {
      state.start.evidence = input.value;
      savePrefs();
      renderStartMode();
    });
  }
  renderStartMode();
}

function renderStartMode() {
  const { version, evidence } = state.start;
  const v2 = version === 2;
  const caseFile = v2 && evidence === "case_file";
  $("evidence-toggle").hidden = !v2;
  $("report-field").hidden = caseFile;
  $("case-picked").hidden = !caseFile;
  $("examples").hidden = v2;
  $("cases").hidden = !v2;
  $("examples-title").textContent = v2 ? "Cases" : "Examples";
  $("opt-independent-text").textContent = v2
    ? "Independent lane (Jev scores each diagnosis from the whole case)"
    : "Independent lane (Jev gives a diagnosis from the whole case)";
  $("start-intro").textContent = !v2
    ? "Type the report of the customer, or select an example. Jev reads the report, and the flowchart asks the questions that remain."
    : caseFile
      ? "Select a case. Jev reads the filtered case file and marks the symptoms. The app then walks one component at a time until each symptom has an explanation, for a maximum of three faults."
      : "Type a report, or select a case and edit its report. Jev marks the symptoms in the report. The app then walks one component at a time until each symptom has an explanation, for a maximum of three faults.";
  renderCases();
}

async function loadCases() {
  if (MOCK) return;
  try {
    state.start.cases = await api("GET", "/api/v2/cases");
    state.start.casesError = null;
  } catch (error) {
    state.start.cases = [];
    state.start.casesError = error.message;
  }
  renderCases();
}

function caseCounts(caseFile) {
  if (!caseFile) return "";
  const parts = [];
  const count = (key, one, many) => {
    const n = Array.isArray(caseFile[key]) ? caseFile[key].length : 0;
    if (n) parts.push(`${n} ${n === 1 ? one : many}`);
  };
  count("obd_codes", "code", "codes");
  count("service_history", "service line", "service lines");
  count("technician_notes", "note", "notes");
  return parts.join(", ");
}

function caseMeta(item) {
  const faults = (item.faults || []).length;
  return el(
    "span",
    { class: "case-meta" },
    faults ? el("span", { class: "chip chip-faults" }, `${faults} ${faults === 1 ? "fault" : "faults"}`) : null,
    (item.tags || []).map((tag) => el("span", { class: "chip" }, humanize(tag))),
    item.case_file ? el("span", { class: "muted small" }, caseCounts(item.case_file)) : null,
  );
}

function renderCases() {
  const list = $("cases");
  const { cases, casesError, evidence, caseId } = state.start;
  const caseFile = evidence === "case_file";
  if (MOCK) {
    list.replaceChildren(el("li", { class: "muted" }, "Mock mode loads no cases."));
  } else if (casesError) {
    list.replaceChildren(el("li", { class: "muted" }, `The cases did not load. ${casesError}`));
  } else if (!cases.length) {
    list.replaceChildren(el("li", { class: "muted" }, "No cases yet. The server reads them from data/v2/cases.json."));
  } else {
    list.replaceChildren(
      ...cases.map((item) =>
        el(
          "li",
          {},
          el(
            "button",
            {
              class: `btn example${caseFile && item.id === caseId ? " selected" : ""}`,
              type: "button",
              "aria-pressed": caseFile ? String(item.id === caseId) : null,
              onclick: () => {
                state.start.caseId = item.id;
                if (caseFile) {
                  renderCases();
                } else {
                  $("report-input").value = item.report || "";
                  $("report-input").focus();
                }
              },
            },
            el("span", { class: "example-title" }, item.title || item.id, item.date ? el("span", { class: "muted small" }, ` ${item.date}`) : null),
            el("span", { class: "example-report" }, item.report || ""),
            caseMeta(item),
          ),
        ),
      ),
    );
  }
  const picked = $("case-picked");
  const selected = cases.find((item) => item.id === caseId);
  picked.replaceChildren(
    selected
      ? el(
          "div",
          {},
          el("div", { class: "field-label" }, `Case: ${selected.title || selected.id}`),
          el("p", { class: "report small" }, selected.report || ""),
          caseMeta(selected),
        )
      : el("p", { class: "muted" }, "Select a case below. The session reads its report and its case file."),
  );
}

/* ---------- Version 2 view ---------- */

const CASE_SOURCES = [
  ["vehicle", "Vehicle"],
  ["obd_codes", "OBD codes"],
  ["freeze_frame", "Freeze frame"],
  ["service_history", "Service history"],
  ["technician_notes", "Technician notes"],
];

const COMPONENT_STATES = {
  open: { css: "pending", mark: "\u25CB", text: "pending" },
  pending: { css: "pending", mark: "\u25CB", text: "pending" },
  active: { css: "active", mark: "\u25CF", text: "active" },
  fault: { css: "done", mark: "\u2713", text: "done, fault found" },
  done: { css: "done", mark: "\u2713", text: "done" },
  no_fault: { css: "clear", mark: "\u2013", text: "done, no fault" },
};

const UNITS = { v: "V", c: "°C", kmh: "km/h", km: "km", pct: "%", kpa: "kPa", ms: "ms", s: "s", a: "A", bar: "bar", l: "L", mm: "mm" };

function isV2(view) {
  return Boolean(view && view.version === 2);
}

function componentLabel(view, id) {
  const match = (view.components || []).find((c) => c.id === id);
  return match ? match.label || humanize(id) : humanize(id);
}

function diagnosisLabel(view, id) {
  const lists = [view.faults, view.branch_scores, view.independent && view.independent.top, view.fix];
  for (const list of lists) {
    const match = (list || []).find((item) => item.id === id || item.diagnosis === id);
    if (match && match.label) return match.label;
  }
  return humanize(id);
}

function symptomLabel(view, id) {
  const match = (view.symptoms || []).find((s) => s.id === id);
  return match ? match.label || humanize(id) : humanize(id);
}

function fieldName(key) {
  const parts = String(key).split("_");
  const unit = parts.length > 1 ? UNITS[parts[parts.length - 1]] : null;
  if (unit) parts.pop();
  return { name: humanize(parts.join("_")), unit };
}

function formatValue(value, unit, key) {
  const text = typeof value === "number" && key !== "year" ? value.toLocaleString("en-US") : typeof value === "object" && value !== null ? JSON.stringify(value) : String(value);
  return unit ? `${text} ${unit}` : text;
}

function keyValues(object) {
  return el(
    "dl",
    { class: "kv" },
    Object.entries(object || {}).flatMap(([key, value]) => {
      const { name, unit } = fieldName(key);
      return [el("dt", {}, key === "vin" ? "VIN" : name), el("dd", {}, formatValue(value, unit, key))];
    }),
  );
}

function entryContent(source, entry) {
  if (entry === null || entry === undefined) return "";
  if (typeof entry !== "object") return String(entry);
  if (source === "obd_codes") {
    return [
      el("span", { class: "ev-code" }, entry.code || "?"),
      el("span", { class: "ev-text" }, entry.description || ""),
      entry.status ? el("span", { class: `chip chip-obd-${entry.status}` }, entry.status) : null,
      entry.mileage_km !== undefined ? el("span", { class: "ev-when" }, formatValue(entry.mileage_km, "km")) : null,
    ];
  }
  if (source === "service_history") {
    return [
      el("span", { class: "ev-when ev-date" }, entry.date || ""),
      el("span", { class: "ev-text" }, entry.work || ""),
      entry.mileage_km !== undefined ? el("span", { class: "ev-when" }, formatValue(entry.mileage_km, "km")) : null,
    ];
  }
  return el("span", { class: "ev-text" }, Object.entries(entry).map(([key, value]) => `${fieldName(key).name}: ${formatValue(value, fieldName(key).unit)}`).join(", "));
}

function sourceSection(source, title, kept, removed) {
  const rows = [];
  if (Array.isArray(kept)) {
    for (const entry of kept) rows.push(el("li", { class: `ev-row ev-${source}` }, entryContent(source, entry)));
  }
  for (const item of removed) {
    rows.push(
      el(
        "li",
        { class: `ev-row ev-${source} ev-removed`, title: `Code removed this entry before Jev read the case file: ${item.reason}` },
        entryContent(source, item.entry),
        el("span", { class: "ev-reason" }, `removed: ${item.reason}`),
      ),
    );
  }
  const keptCount = Array.isArray(kept) ? kept.length : null;
  const count =
    keptCount === null ? (removed.length ? `${removed.length} removed` : "") : `${keptCount} kept${removed.length ? `, ${removed.length} removed` : ""}`;
  const body = [];
  if (kept && !Array.isArray(kept) && typeof kept === "object") body.push(keyValues(kept));
  if (rows.length) body.push(el("ul", { class: "ev-list" }, rows));
  if (!body.length) body.push(el("p", { class: "muted small" }, "No entries."));
  return el(
    "section",
    { class: "ev-source" },
    el("h3", { class: "sub-title" }, title, count ? el("span", { class: "muted small" }, ` ${count}`) : null),
    body,
  );
}

function renderEvidence(view) {
  const evidence = view.evidence || {};
  const caseFile = evidence.case_file || null;
  const removed = evidence.removed || [];
  const parts = [
    el("h3", { class: "sub-title" }, "Customer report"),
    el("p", { class: "report" }, evidence.report || view.report || ""),
  ];
  if (view.mode !== "case_file" || !caseFile || !Object.keys(caseFile).length) {
    parts.push(el("p", { class: "note" }, "Jev reads the typed report only."));
  } else {
    for (const [source, title] of CASE_SOURCES) {
      const gone = removed.filter((item) => item.source === source);
      let kept = caseFile[source];
      if (Array.isArray(kept) && gone.length) {
        const removedKeys = new Set(gone.map((item) => JSON.stringify(item.entry)));
        kept = kept.filter((entry) => !removedKeys.has(JSON.stringify(entry)));
      }
      parts.push(sourceSection(source, title, kept, gone));
    }
    const known = new Set(CASE_SOURCES.map(([source]) => source));
    const other = removed.filter((item) => !known.has(item.source));
    if (other.length) parts.push(sourceSection("other", "Other removed entries", null, other));
    if (removed.length) {
      parts.push(el("p", { class: "note" }, `Code removed ${removed.length} irrelevant ${removed.length === 1 ? "entry" : "entries"} before Jev read the case file.`));
    }
  }
  $("evidence").replaceChildren(...parts);
}

function renderComponents(view) {
  const strip = $("component-strip");
  const components = view.components || [];
  const loop = view.loop || {};
  const active = components.find((c) => c.state === "active") || components.find((c) => c.id === loop.component);
  $("chart-title").textContent = active ? `Flowchart: ${active.label || humanize(active.id)}` : "Flowchart";
  strip.replaceChildren(
    el(
      "div",
      { class: "strip-head" },
      el("span", { class: "panel-title" }, "Components"),
      loop.index ? el("span", { class: "muted small" }, `loop ${loop.index}`) : null,
    ),
    components.length
      ? el(
          "ol",
          { class: "strip" },
          components.map((c) => {
            const look = COMPONENT_STATES[c.state] || COMPONENT_STATES.open;
            const score = c.score === null || c.score === undefined ? "n/a" : c.score.toFixed(2);
            return el(
              "li",
              {
                class: `comp comp-${look.css}`,
                title: `${c.label || humanize(c.id)}: ${look.text}, probability ${pct(c.probability)}, selection score ${score}`,
              },
              el("span", { class: "comp-mark", "aria-hidden": "true" }, look.mark),
              el("span", { class: "comp-label" }, c.label || humanize(c.id)),
              el("span", { class: "comp-prob" }, pct(c.probability)),
            );
          }),
        )
      : el("p", { class: "muted small" }, "No components yet."),
  );
}

function foldNote(details, text) {
  const summary = details.querySelector("summary");
  let note = summary.querySelector(".fold-note");
  if (!note) {
    note = el("span", { class: "fold-note" });
    summary.append(note);
  }
  note.textContent = text;
}

function symptomRow(view, symptom) {
  const width = Math.max(0, Math.min(1, symptom.probability || 0)) * 100;
  let status;
  if (!symptom.present) status = el("span", { class: "sym-status muted" }, "not present");
  else if (symptom.explained_by)
    status = el("span", { class: "sym-status sym-explained" }, "explained by ", el("strong", {}, diagnosisLabel(view, symptom.explained_by)));
  else {
    const ended = view.status === "complete" || view.status === "specialist";
    status = el("span", { class: "sym-status sym-open" }, ended ? "no explanation" : "no explanation yet");
  }
  return el(
    "li",
    { class: `sym${symptom.present ? " sym-present" : ""}` },
    el(
      "div",
      { class: "bar-row" },
      el("span", { class: "bar-label", title: symptom.label }, symptom.label || humanize(symptom.id)),
      el(
        "span",
        { class: "bar-track" },
        el("span", { class: "bar-fill", style: `width:${width.toFixed(1)}%` }),
        el("span", { class: "bar-threshold", style: "left:50%", title: "0.5 limit for present" }),
      ),
      el("span", { class: "bar-value" }, pct(symptom.probability)),
    ),
    status,
  );
}

function renderSymptoms(view) {
  const symptoms = [...(view.symptoms || [])].sort((a, b) => Number(b.present) - Number(a.present) || b.probability - a.probability);
  const present = symptoms.filter((s) => s.present);
  const absent = symptoms.filter((s) => !s.present);
  const explained = present.filter((s) => s.explained_by).length;
  foldNote($("symptoms-panel"), present.length ? `${explained} of ${present.length} explained` : "");
  const parts = [];
  if (!symptoms.length) parts.push(el("p", { class: "bars-empty" }, "No symptoms yet."));
  if (present.length) parts.push(el("ul", { class: "sym-list" }, present.map((s) => symptomRow(view, s))));
  else if (symptoms.length) parts.push(el("p", { class: "bars-empty" }, "Jev found no symptom above 0.5."));
  if (absent.length) {
    parts.push(
      el(
        "details",
        { class: "final-scores" },
        el("summary", {}, `${absent.length} symptoms not present`),
        el("ul", { class: "sym-list" }, absent.map((s) => symptomRow(view, s))),
      ),
    );
  }
  $("symptoms").replaceChildren(...parts);
}

function jumpTo(id) {
  const target = $(id);
  if (!target) return;
  target.scrollIntoView({ block: "nearest", behavior: "smooth" });
  target.classList.remove("pulse");
  void target.offsetWidth;
  target.classList.add("pulse");
}

function faultLink(view, id) {
  const found = (view.faults || []).some((f) => f.id === id);
  if (!found) return el("span", {}, diagnosisLabel(view, id));
  return el("button", { class: "link", type: "button", onclick: () => jumpTo(`fault-${id}`) }, diagnosisLabel(view, id));
}

function joinNodes(nodes) {
  const out = [];
  nodes.forEach((node, index) => {
    if (index) out.push(", ");
    out.push(node);
  });
  return out;
}

function renderFaults(view) {
  const faults = view.faults || [];
  foldNote($("faults-panel"), faults.length ? `${faults.length}` : "");
  if (!faults.length) {
    $("faults").replaceChildren(el("p", { class: "bars-empty" }, view.status === "specialist" ? "The loop found no fault." : "No fault found yet."));
    return;
  }
  $("faults").replaceChildren(
    el(
      "div",
      { class: "fault-cards" },
      faults.map((fault) => {
        const causes = faults.filter((other) => (other.caused_by_found || []).includes(fault.id)).map((other) => other.id);
        const causedBy = fault.caused_by_found || [];
        return el(
          "article",
          { class: `fault-card${causedBy.length ? "" : causes.length ? " fault-root" : ""}`, id: `fault-${fault.id}` },
          el(
            "div",
            { class: "fault-head" },
            el("h3", {}, fault.label || humanize(fault.id)),
            el("span", { class: "fault-score", title: "Branch score at the leaf" }, pct(fault.score)),
          ),
          el(
            "div",
            { class: "fault-meta" },
            el("span", { class: "chip" }, `Loop ${fault.loop ?? "?"}`),
            el("span", {}, componentLabel(view, fault.component)),
            !causedBy.length && causes.length ? el("span", { class: "chip chip-root" }, "root cause") : null,
          ),
          (fault.explains || []).length
            ? el("p", { class: "fault-line" }, el("span", { class: "muted" }, "Explains "), (fault.explains || []).map((id) => symptomLabel(view, id)).join(", "))
            : null,
          causedBy.length ? el("p", { class: "fault-line" }, el("span", { class: "muted" }, "Caused by "), joinNodes(causedBy.map((id) => faultLink(view, id)))) : null,
          causes.length ? el("p", { class: "fault-line" }, el("span", { class: "muted" }, "Causes "), joinNodes(causes.map((id) => faultLink(view, id)))) : null,
        );
      }),
    ),
  );
}

function renderFixPlan(view) {
  const fix = view.fix || [];
  const faults = view.faults || [];
  const effects = new Set(faults.flatMap((f) => (f.caused_by_found || []).length ? [f.id] : []));
  const causes = new Set(faults.flatMap((f) => f.caused_by_found || []));
  const total = fix.reduce((n, item) => n + (item.steps || []).length, 0);
  const done = fix.reduce((n, item) => n + (item.steps || []).filter((_, i) => state.fixChecked.has(`${item.diagnosis}:${i}`)).length, 0);
  foldNote($("fix-panel"), total ? `${done} of ${total} done` : "");
  if (!fix.length) {
    $("fix-plan").replaceChildren(el("p", { class: "bars-empty" }, "The fix plan starts when the loop finds a fault."));
    return;
  }
  let number = 0;
  const note = view.status === "complete" ? [] : [el("p", { class: "note" }, "The plan can change while the loop continues.")];
  $("fix-plan").replaceChildren(
    ...note,
    ...fix.map((item) =>
      el(
        "section",
        { class: "fix-group" },
        el(
          "h3",
          { class: "sub-title" },
          item.label || diagnosisLabel(view, item.diagnosis),
          causes.has(item.diagnosis) && !effects.has(item.diagnosis) ? el("span", { class: "chip chip-root" }, "root cause") : null,
        ),
        (item.steps || []).length
          ? el(
              "ol",
              { class: "fix-list" },
              item.steps.map((stepText, index) => {
                number += 1;
                const key = `${item.diagnosis}:${index}`;
                const box = el("input", {
                  type: "checkbox",
                  checked: state.fixChecked.has(key),
                  onchange: (event) => {
                    if (event.target.checked) state.fixChecked.add(key);
                    else state.fixChecked.delete(key);
                    renderFixPlan(view);
                  },
                });
                return el("li", {}, el("label", {}, box, el("span", {}, `${number}. ${stepText}`)));
              }),
            )
          : el("p", { class: "muted small" }, "An earlier fault in the plan has all the steps of this fault."),
      ),
    ),
  );
}

function listNames(names, max = 6) {
  if (names.length <= max) return names.join(", ");
  return `${names.slice(0, max).join(", ")} and ${names.length - max} more`;
}

function unexplainedMessage(view) {
  const open = view.unexplained || [];
  if (!open.length) return [];
  return [
    el(
      "p",
      { class: "message message-warn" },
      `${open.length} ${open.length === 1 ? "symptom has" : "symptoms have"} no explanation: ${listNames(open.map((s) => s.label || humanize(s.id)))}. Refer ${open.length === 1 ? "it" : "them"} to a specialist.`,
    ),
  ];
}

function completeMessage(view) {
  const faults = view.faults || [];
  const n = faults.length;
  const names = faults.map((f) => f.label || humanize(f.id)).join(", ");
  return [
    el("p", { class: "message message-good" }, `The case is complete. The loop found ${n} ${n === 1 ? "fault" : "faults"}: ${names}. Do the fix plan on the right, root cause first.`),
    ...unexplainedMessage(view),
  ];
}

function renderIndependentV2(view) {
  const lane = view.independent || { enabled: false, faults: [], top: [] };
  const target = $("independent");
  const flag = $("independent-flag");
  if (!lane.enabled) {
    target.replaceChildren(el("p", { class: "bars-empty" }, "The independent lane is off for this session."));
    flag.replaceChildren();
    return;
  }
  const faults = lane.faults || [];
  target.replaceChildren(
    el("h3", { class: "sub-title" }, `Faults above ${V2_FAULT_THRESHOLD}`),
    faults.length
      ? el("div", { class: "chips" }, faults.map((f) => el("span", { class: "chip chip-ind" }, `${f.label || humanize(f.id)} ${pct(f.score)}`)))
      : el("p", { class: "bars-empty" }, `No diagnosis passed ${V2_FAULT_THRESHOLD} in this lane.`),
    el("h3", { class: "sub-title" }, "Top eight"),
    el("div", { class: "bars" }),
  );
  const bars = target.lastElementChild;
  const items = [...(lane.top || [])].sort((a, b) => b.score - a.score).map((s) => ({ label: s.label || humanize(s.id), score: s.score }));
  renderBars(bars, items, { threshold: V2_FAULT_THRESHOLD });
  const loopIds = new Set((view.faults || []).map((f) => f.id));
  const laneIds = new Set(faults.map((f) => f.id));
  const same = loopIds.size === laneIds.size && [...loopIds].every((id) => laneIds.has(id));
  flag.replaceChildren(
    loopIds.size || laneIds.size
      ? el("p", { class: "note" }, same ? "This lane and the loop agree on the set of faults." : "This lane and the loop do not agree on the set of faults.")
      : null,
  );
}

function mockViewV2(status) {
  const base = state.mockBase;
  const view = structuredClone(base);
  view.status = status;
  view.confirm_options = [];
  view.flag = null;
  if (status === "confirm") {
    view.confirm_options = [
      { id: "external", text: "Yes, coolant comes out of the system", probability: 0.52 },
      { id: "no_leak", text: "No, the pressure holds", probability: 0.31 },
    ];
  }
  if (status === "flagged") {
    view.branch_scores = view.branch_scores.map((s, i) => ({ ...s, score: i === 0 ? 0.92 : s.score / 5 }));
    view.flag = { ...view.branch_scores[0] };
  }
  if (status === "complete" || status === "specialist") {
    view.current = null;
    view.components = view.components.map((c) => ({ ...c, state: c.state === "active" ? "no_fault" : c.state, score: null }));
    view.loop = { index: view.loop.index, component: null };
    view.branch_scores = [];
  }
  if (status === "specialist") {
    view.faults = [];
    view.fix = [];
    view.components = view.components.map((c) => ({ ...c, state: c.state === "open" ? c.state : "no_fault" }));
    view.symptoms = view.symptoms.map((s) => ({ ...s, explained_by: null }));
    view.unexplained = view.symptoms.filter((s) => s.present).map((s) => ({ id: s.id, label: s.label }));
  }
  return view;
}

/* ---------- Flowchart ---------- */

let mermaidReady = false;
let renderCount = 0;

function initMermaid() {
  if (!window.mermaid) return false;
  if (!mermaidReady) {
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: dark ? "dark" : "default",
      flowchart: { htmlLabels: true, useMaxWidth: false, wrappingWidth: 220, curve: "basis" },
    });
    mermaidReady = true;
  }
  return true;
}

async function renderChart(view) {
  const canvas = $("chart-canvas");
  const text = view.mermaid || "";
  const current = view.current ? view.current.node_id : view.diagnosis ? view.diagnosis.id : view.status === "specialist" ? "specialist" : null;
  if (!text) {
    canvas.replaceChildren(el("p", { class: "chart-empty" }, "No flowchart in this view."));
    state.renderedMermaid = null;
    return;
  }
  if (!initMermaid()) {
    canvas.replaceChildren(el("p", { class: "chart-empty" }, "Mermaid did not load. The flowchart needs cdn.jsdelivr.net."));
    return;
  }
  if (text === state.renderedMermaid) {
    if (current !== state.renderedCurrent) {
      state.renderedCurrent = current;
      focusCurrent();
    }
    return;
  }
  const component = isV2(view) && view.loop ? view.loop.component : null;
  const firstRender = state.renderedMermaid === null || (component && component !== state.renderedComponent);
  state.renderedComponent = component || state.renderedComponent;
  state.renderedMermaid = text;
  state.renderedCurrent = current;
  try {
    renderCount += 1;
    const { svg } = await window.mermaid.render(`jev-chart-${renderCount}`, text);
    if (state.renderedMermaid !== text) return;
    canvas.innerHTML = svg;
    for (const shape of canvas.querySelectorAll("g.node:is(.leaf, .onpath, .current) > :is(rect, polygon, path, circle, ellipse)")) {
      shape.removeAttribute("style");
    }
    if (firstRender) fitChart();
    focusCurrent();
  } catch (error) {
    canvas.replaceChildren(el("pre", {}, `The flowchart did not render: ${error.message || error}`));
  }
}

function applyTransform() {
  const { scale, x, y } = state.chart;
  $("chart-canvas").style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
}

function chartSize() {
  const svg = $("chart-canvas").querySelector("svg");
  if (!svg) return null;
  const box = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width ? svg.viewBox.baseVal : svg.getBBox();
  const width = parseFloat(svg.getAttribute("width")) || box.width;
  const height = parseFloat(svg.getAttribute("height")) || box.height;
  svg.setAttribute("width", width);
  svg.setAttribute("height", height);
  return { width, height };
}

function fitChart() {
  const size = chartSize();
  if (!size) return;
  const viewport = $("chart-viewport").getBoundingClientRect();
  const scale = Math.min(viewport.width / size.width, viewport.height / size.height, 1.2) * 0.95;
  state.chart.scale = Math.max(0.05, scale);
  state.chart.x = (viewport.width - size.width * state.chart.scale) / 2;
  state.chart.y = (viewport.height - size.height * state.chart.scale) / 2;
  applyTransform();
}

function currentNodeElement() {
  const canvas = $("chart-canvas");
  const byClass = canvas.querySelector("g.node.current");
  if (byClass) return byClass;
  const id = state.renderedCurrent;
  if (!id) return null;
  return canvas.querySelector(`g.node[id*="flowchart-${CSS.escape(id)}-"]`);
}

function focusCurrent() {
  const node = currentNodeElement();
  if (!node) return;
  const size = chartSize();
  if (!size) return;
  const viewportBox = $("chart-viewport").getBoundingClientRect();
  if (state.chart.scale < 0.6) state.chart.scale = Math.min(0.9, Math.max(0.6, state.chart.scale));
  applyTransform();
  const nodeBox = node.getBoundingClientRect();
  const cx = nodeBox.left + nodeBox.width / 2 - viewportBox.left;
  const cy = nodeBox.top + nodeBox.height / 2 - viewportBox.top;
  state.chart.x += viewportBox.width / 2 - cx;
  state.chart.y += viewportBox.height / 2 - cy;
  applyTransform();
}

function zoomAt(factor, px, py) {
  const chart = state.chart;
  const next = Math.min(4, Math.max(0.05, chart.scale * factor));
  const ratio = next / chart.scale;
  chart.x = px - (px - chart.x) * ratio;
  chart.y = py - (py - chart.y) * ratio;
  chart.scale = next;
  applyTransform();
}

function setupPanZoom() {
  const viewport = $("chart-viewport");
  let drag = null;
  viewport.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const box = viewport.getBoundingClientRect();
      const factor = Math.exp(-event.deltaY * (event.ctrlKey ? 0.01 : 0.0015));
      zoomAt(factor, event.clientX - box.left, event.clientY - box.top);
    },
    { passive: false },
  );
  viewport.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    drag = { id: event.pointerId, x: event.clientX, y: event.clientY, ox: state.chart.x, oy: state.chart.y };
    viewport.setPointerCapture(event.pointerId);
    viewport.classList.add("dragging");
  });
  viewport.addEventListener("pointermove", (event) => {
    if (!drag || drag.id !== event.pointerId) return;
    state.chart.x = drag.ox + event.clientX - drag.x;
    state.chart.y = drag.oy + event.clientY - drag.y;
    applyTransform();
  });
  const end = (event) => {
    if (!drag || drag.id !== event.pointerId) return;
    drag = null;
    viewport.classList.remove("dragging");
  };
  viewport.addEventListener("pointerup", end);
  viewport.addEventListener("pointercancel", end);
  const centerZoom = (factor) => {
    const box = viewport.getBoundingClientRect();
    zoomAt(factor, box.width / 2, box.height / 2);
  };
  $("zoom-in").addEventListener("click", () => centerZoom(1.25));
  $("zoom-out").addEventListener("click", () => centerZoom(0.8));
  $("zoom-fit").addEventListener("click", fitChart);
  $("zoom-current").addEventListener("click", focusCurrent);
}

/* ---------- Mock mode ---------- */

function mockView(status) {
  const view = structuredClone(state.mockBase);
  view.status = status;
  view.confirm_options = [];
  if (status === "confirm") {
    view.confirm_options = [
      { id: "yes", text: "Yes, the headlights go dim", probability: 0.64 },
      { id: "no", text: "No, the headlights stay bright", probability: 0.21 },
    ];
  }
  if (status === "asking" || status === "confirm" || status === "reask") view.flag = null;
  if (status === "diagnosed") {
    const flag = state.mockBase.flag || { id: "flat_battery", label: "Flat battery" };
    view.current = null;
    view.flag = null;
    view.diagnosis = {
      id: flag.id,
      label: flag.label,
      description: "The battery has too little charge to turn the starter",
      fix: MOCK_FIX,
    };
  }
  if (status === "specialist") {
    view.current = null;
    view.flag = null;
    view.diagnosis = null;
  }
  return view;
}

async function startMock() {
  $("mock-badge").hidden = false;
  const select = $("mock-status");
  $("mock-status-wrap").hidden = false;
  const file = MOCK_VERSION === 2 ? "mock-view-v2.json" : "mock-view.json";
  try {
    const response = await fetch(file);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.mockBase = await response.json();
  } catch (error) {
    showError(`${file} did not load: ${error.message}`);
    return;
  }
  const statuses = MOCK_VERSION === 2 ? MOCK_STATUSES_V2 : MOCK_STATUSES;
  const make = MOCK_VERSION === 2 ? mockViewV2 : mockView;
  select.replaceChildren(...statuses.map((s) => el("option", { value: s, selected: s === state.mockBase.status }, s)));
  select.addEventListener("change", () => setView(make(select.value)));
  setView(make(state.mockBase.status));
}

/* ---------- Boot ---------- */

async function boot() {
  $("error-close").addEventListener("click", hideError);
  $("start-form").addEventListener("submit", startSession);
  setupStart();
  $("new-session").addEventListener("click", () => {
    hideError();
    showStart();
  });
  setupPanZoom();
  loadExamples();
  loadCases();
  if (MOCK) {
    await startMock();
    return;
  }
  const id = location.hash.slice(1);
  if (id) {
    try {
      setView(await api("GET", `/api/sessions/${encodeURIComponent(id)}`));
      return;
    } catch {
      history.replaceState(null, "", location.pathname + location.search);
    }
  }
  showStart();
}

boot();

// The flowchart lane starts collapsed. Open it when the user must act on it:
// a flag to accept, or the fix steps of a diagnosis.
function renderFolds(view) {
  const lane = $("flowchart-lane");
  const summary = lane.querySelector("summary");
  if (isV2(view)) {
    if (view.status === "flagged" && state.foldStatus !== view.status) lane.open = true;
    state.foldStatus = view.status;
    const topBranch = [...(view.branch_scores || [])].sort((a, b) => b.score - a.score)[0];
    foldNote(lane, topBranch ? `${topBranch.label || humanize(topBranch.id)} ${pct(topBranch.score)}` : "");
    return;
  }
  const needsAction = view.status === "flagged" || view.status === "diagnosed";
  if (needsAction && state.foldStatus !== view.status) lane.open = true;
  state.foldStatus = view.status;
  let note = summary.querySelector(".fold-note");
  if (!note) {
    note = document.createElement("span");
    note.className = "fold-note";
    summary.appendChild(note);
  }
  const top = (view.scores || [])[0];
  note.textContent = view.diagnosis
    ? view.diagnosis.label
    : top ? `${top.label} ${Math.round(top.score * 100)}%` : "";
}

// Opus 5 prices from the Claude API reference, 2026-09-18. The time model is an
// assumption, because this app has no Opus 5 measurement. Each request gets one time
// to the first token, then a fixed output speed, with thinking off.
const OPUS5 = { inPerMtok: 5.0, outPerMtok: 25.0, firstTokenS: 1.5, outTokensPerS: 50 };

// The header compares this session with the same requests sent to Opus 5.
// Opus 5 reads the same input and writes the same answers, so the token counts match.
function renderCompare(view) {
  const box = $("compare");
  const rows = (view.ledger && view.ledger.rows) || [];
  if (!rows.length) { box.hidden = true; return; }
  let tokIn = 0, tokOut = 0, jevCost = 0, jevTime = 0, opusCost = 0, opusTime = 0;
  for (const r of rows) {
    tokIn += r.input_tokens;
    tokOut += r.output_tokens;
    jevCost += r.jev_cost;
    jevTime += r.seconds;
    opusCost += (r.input_tokens * OPUS5.inPerMtok + r.output_tokens * OPUS5.outPerMtok) / 1e6;
    opusTime += OPUS5.firstTokenS + r.output_tokens / OPUS5.outTokensPerS;
  }
  const tokens = (tokIn + tokOut).toLocaleString("en-US");
  const money = (v) => v < 0.01 ? `$${v.toFixed(5)}` : `$${v.toFixed(3)}`;
  const secs = (v) => v < 60 ? `${v.toFixed(1)} s` : `${(v / 60).toFixed(1)} min`;
  const ratio = (a, b) => `${(a / b).toFixed(a / b < 10 ? 1 : 0)}x`;
  box.hidden = false;
  box.innerHTML = "";
  const timeNote = `Opus 5 time is an estimate: ${OPUS5.firstTokenS} s to the first token for each request, ` +
    `then ${OPUS5.outTokensPerS} output tokens a second, with thinking off. Jev time is measured.`;
  const badge = (label, jev, opus, factor, title) => {
    const b = document.createElement("span");
    b.className = "cmp-badge";
    b.title = title;
    b.innerHTML = `<span class="cmp-label"></span><span class="cmp-jev"></span>` +
      `<span class="cmp-vs">/</span><span class="cmp-opus"></span><span class="cmp-factor"></span>`;
    b.querySelector(".cmp-label").textContent = label;
    b.querySelector(".cmp-jev").textContent = `Jev ${jev}`;
    b.querySelector(".cmp-opus").textContent = `Opus 5 ${opus}`;
    b.querySelector(".cmp-factor").textContent = factor;
    box.appendChild(b);
  };
  badge("Tokens", tokens, tokens, "same",
    `${tokIn.toLocaleString("en-US")} in, ${tokOut.toLocaleString("en-US")} out. Opus 5 gets the same prompt and writes the same answers.`);
  badge("Cost", money(jevCost), money(opusCost), `${ratio(opusCost, jevCost)}`,
    `Jev: input tokens only, output is free. Opus 5: $${OPUS5.inPerMtok} in and $${OPUS5.outPerMtok} out for each million tokens.`);
  badge("Time", secs(jevTime), `~${secs(opusTime)}`, `~${ratio(opusTime, jevTime)}`, timeNote);
}
