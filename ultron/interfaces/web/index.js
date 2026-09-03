/* Ultron — single-screen dashboard.
   One question: what is risky to change here, and what do I tell my agent? */

const $ = (id) => document.getElementById(id);

const state = {
  repo: "",
  risks: [],
  filtered: [],
  selected: null,
  briefCache: new Map(),
  fileCache: new Map(),
  activeTab: "why",
  briefTarget: "claude",
};

/* ---------------- helpers ---------------- */

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

async function api(path, body) {
  const opts = body === undefined
    ? { method: "GET" }
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch (_) { /* non-JSON body */ }
  if (!res.ok) {
    const msg = (data && (data.message || data.error)) || `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data || {};
}

function show(view) {
  ["empty-state", "busy-state", "results", "error-state"].forEach((id) => {
    $(id).hidden = id !== view;
  });
}

function banner(text) {
  if (!text) { $("banner").hidden = true; return; }
  $("banner-text").textContent = text;
  $("banner").hidden = false;
}

function splitPath(p) {
  const norm = String(p || "").replace(/\\/g, "/");
  const i = norm.lastIndexOf("/");
  return i === -1 ? { dir: "", base: norm } : { dir: norm.slice(0, i + 1), base: norm.slice(i + 1) };
}

/* ---------------- connection ---------------- */

async function pingServer() {
  const el = $("conn");
  try {
    await api("/api/v1/health");
    el.className = "conn is-ok";
    $("conn-text").textContent = "connected";
  } catch (_) {
    el.className = "conn is-down";
    $("conn-text").textContent = "offline";
  }
}

/* ---------------- scanning ---------------- */

async function scan() {
  const repo = $("repo-input").value.trim();
  if (!repo) {
    banner("Enter a repository path first.");
    $("repo-input").focus();
    return;
  }

  state.repo = repo;
  banner("");
  $("busy-text").textContent = "Reading the repository…";
  show("busy-state");
  $("scan-btn").disabled = true;

  try {
    const data = await api("/api/v1/overview", { repo });
    render(data);
  } catch (err) {
    $("error-text").textContent = err.message;
    show("error-state");
  } finally {
    $("scan-btn").disabled = false;
  }
}

/* Persist the scan so trends, repeat offenders and suggestions become available.
   The old UI never called this, so those panels could never fill. */
async function saveScan() {
  const btn = $("save-btn");
  btn.disabled = true;
  btn.textContent = "Saving…";
  try {
    await api("/api/v1/analyze", { repo: state.repo });
    await waitForJob();
    const data = await api("/api/v1/overview", { repo: state.repo });
    render(data);
    banner("");
  } catch (err) {
    banner(`Could not save the scan: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "Save this scan";
  }
}

async function waitForJob() {
  for (let i = 0; i < 300; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    const p = await api("/api/v1/progress");
    if (p.status === "success") return;
    if (p.status === "failed") throw new Error(p.error || "Analysis failed");
    if (p.status === "cancelled") throw new Error("Analysis was cancelled");
  }
  throw new Error("Analysis timed out");
}

/* ---------------- rendering ---------------- */

function render(data) {
  state.risks = data.risks || [];
  state.selected = null;
  state.briefCache.clear();
  state.fileCache.clear();

  if (data.repo && data.repo.path) {
    state.repo = data.repo.path;
    $("repo-input").value = data.repo.path;
  }

  if (data.state === "analysis_empty") {
    $("error-text").textContent = data.message || "No Python files found here.";
    show("error-state");
    return;
  }

  if (data.intent && data.intent.matched === false && data.intent.message) {
    banner(data.intent.message);
  }

  renderSummary(data);
  renderMemory(data.memory || {});
  applyFilter();
  resetDetail();
  show("results");
}

function renderSummary(data) {
  const h = data.health || {};
  const el = $("health-score");
  if (h.score == null) {
    el.textContent = "—";
    el.className = "score-num";
  } else {
    el.textContent = Math.round(h.score);
    el.className = "score-num " + (h.score >= 70 ? "is-good" : h.score >= 40 ? "is-mid" : "is-bad");
  }
  $("health-explain").textContent = h.explanation || "";

  const s = data.stats || {};
  $("count-high").textContent = s.high || 0;
  $("count-med").textContent = s.medium || 0;
  $("count-low").textContent = s.low || 0;
  $("count-files").textContent = s.total_files || 0;
}

function renderMemory(mem) {
  const line = $("memory-line");
  if (mem.initialized && mem.latest_run) {
    const when = String(mem.latest_run.timestamp || "").replace("T", " ").slice(0, 16);
    line.textContent = `Last saved ${when}`;
  } else if (mem.reason === "memory_unreadable") {
    line.textContent = "Saved data unreadable";
  } else {
    line.textContent = "Not saved yet";
  }

  const hot = $("hotspot-list");
  const hotspots = mem.hotspots || [];
  hot.innerHTML = hotspots.length
    ? hotspots.map((h) => {
        const { base } = splitPath(h.file_path);
        return `<li><div>${esc(base)}</div>
          <div class="mini-sub">${h.change_count || 0} changes · ${h.violation_count || 0} issues</div></li>`;
      }).join("")
    : `<li class="mini-empty">Save a scan to start tracking this.</li>`;

  const recs = mem.recommendations || [];
  $("rec-list").innerHTML = recs.length
    ? recs.map((r) => {
        const title = r.message || r.description || r.rule_id || "Suggestion";
        const sub = r.file_path ? splitPath(r.file_path).base : (r.rule_id || "");
        return `<li><div>${esc(title)}</div><div class="mini-sub">${esc(sub)}</div></li>`;
      }).join("")
    : `<li class="mini-empty">Save a scan to get suggestions.</li>`;
}

function reasonsFor(r) {
  const out = [];
  const cx = Number(r.complexity || 0);
  const cp = Number(r.coupling != null ? r.coupling : r.coupling_score || 0);
  const callers = (r.callers || []).length;
  if (cx > 10) out.push(`Complex control flow (McCabe ${cx})`);
  if (cp > 5) out.push(`Tightly coupled (score ${cp.toFixed(1)})`);
  if (callers > 0) out.push(`${callers} file${callers === 1 ? "" : "s"} import it`);
  if (!out.length) out.push("Small and self-contained");
  return out;
}

function applyFilter() {
  const q = $("filter-input").value.trim().toLowerCase();
  state.filtered = q
    ? state.risks.filter((r) => String(r.file || r.file_path || "").toLowerCase().includes(q))
    : state.risks.slice();
  renderList();
}

function renderList() {
  const list = $("risk-list");
  $("list-empty").hidden = state.filtered.length > 0;

  list.innerHTML = state.filtered.map((r, i) => {
    const path = r.file || r.file_path || "";
    const { dir, base } = splitPath(path);
    const level = r.level || "LOW";
    const active = state.selected && (state.selected.file || state.selected.file_path) === path;
    return `<li class="risk-item${active ? " is-active" : ""}" data-path="${esc(path)}">
      <span class="risk-rank">${i + 1}</span>
      <span class="risk-body">
        <span class="risk-name"><span class="risk-dir">${esc(dir)}</span>${esc(base)}</span>
        <span class="risk-reason">${esc(reasonsFor(r)[0])}</span>
      </span>
      <span class="risk-level lv-${esc(level)}">${esc(level)}</span>
    </li>`;
  }).join("");
}

function resetDetail() {
  $("detail-title").textContent = "Select a file";
  $("detail-tabs").hidden = true;
  $("detail-placeholder").hidden = false;
  ["tab-why", "tab-code", "tab-brief"].forEach((id) => { $(id).hidden = true; });
}

function selectFile(path) {
  const r = state.risks.find((x) => (x.file || x.file_path) === path);
  if (!r) return;
  state.selected = r;
  renderList();

  $("detail-title").textContent = splitPath(path).base;
  $("detail-placeholder").hidden = true;
  $("detail-tabs").hidden = false;
  renderWhy(r);
  switchTab(state.activeTab);
}

function renderWhy(r) {
  const cx = Number(r.complexity || 0);
  const cp = Number(r.coupling != null ? r.coupling : r.coupling_score || 0);
  const score = Number(r.impact_score || 0);
  const callers = r.callers || [];

  const guidance = r.change_strategy_display || r.mitigation ||
    (r.level === "HIGH"
      ? "Change this in small steps and re-run your tests after each one."
      : "Safe to edit directly.");

  $("tab-why").innerHTML = `
    <div class="metrics">
      <div class="metric"><div class="metric-val">${score.toFixed(1)}</div><div class="metric-key">Risk score</div></div>
      <div class="metric"><div class="metric-val">${cx}</div><div class="metric-key">Complexity</div></div>
      <div class="metric"><div class="metric-val">${cp.toFixed(1)}</div><div class="metric-key">Coupling</div></div>
      <div class="metric"><div class="metric-val">${callers.length}</div><div class="metric-key">Used by</div></div>
    </div>

    <div class="why-block">
      <h3>Why it scored this way</h3>
      <ul>${reasonsFor(r).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
    </div>

    <div class="why-block">
      <h3>How to change it</h3>
      <div class="guidance">${esc(guidance)}</div>
    </div>

    ${callers.length ? `<div class="why-block">
      <h3>Files that depend on it</h3>
      <ul>${callers.slice(0, 12).map((c) => `<li>${esc(splitPath(c).base)}</li>`).join("")}
      ${callers.length > 12 ? `<li>…and ${callers.length - 12} more</li>` : ""}</ul>
    </div>` : ""}

    <div class="why-block">
      <h3>Role</h3>
      <p>${esc(r.boundary_type || r.architectural_role || "Internal")}</p>
    </div>`;
}

async function loadCode() {
  const path = state.selected && (state.selected.file || state.selected.file_path);
  if (!path) return;
  const view = $("code-view");
  if (state.fileCache.has(path)) { view.textContent = state.fileCache.get(path); return; }
  view.textContent = "Loading…";
  try {
    const res = await api("/api/get-file", { repo: state.repo, file: path });
    const content = res.content || "";
    state.fileCache.set(path, content);
    view.textContent = content;
  } catch (err) {
    view.textContent = `Could not read this file: ${err.message}`;
  }
}

async function loadBrief() {
  const path = state.selected ? (state.selected.file || state.selected.file_path) : "";
  const key = `${state.repo}|${path}`;
  const view = $("brief-view");
  if (state.briefCache.has(key)) { paintBrief(state.briefCache.get(key)); return; }
  view.textContent = "Building the briefing…";
  try {
    const res = await api("/api/v1/context-brief", { repo: state.repo, target_file: path });
    state.briefCache.set(key, res);
    paintBrief(res);
  } catch (err) {
    view.textContent = `Could not build a briefing: ${err.message}`;
  }
}

function paintBrief(res) {
  const handoff = res.handoff || {};
  const text = state.briefTarget === "raw"
    ? ((res.canonical_brief && res.canonical_brief.raw_text) || "No briefing text available.")
    : (handoff[state.briefTarget] || "Not available.");
  $("brief-view").textContent = text;
}

function switchTab(name) {
  state.activeTab = name;
  document.querySelectorAll("#detail-tabs .tab").forEach((b) => {
    b.classList.toggle("is-active", b.dataset.tab === name);
  });
  $("tab-why").hidden = name !== "why";
  $("tab-code").hidden = name !== "code";
  $("tab-brief").hidden = name !== "brief";
  if (name === "code") loadCode();
  if (name === "brief") loadBrief();
}

async function copyBrief() {
  const text = $("brief-view").textContent;
  const btn = $("copy-brief");
  try {
    await navigator.clipboard.writeText(text);
  } catch (_) {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) { /* clipboard unavailable */ }
    document.body.removeChild(ta);
  }
  btn.textContent = "Copied";
  setTimeout(() => { btn.textContent = "Copy"; }, 1400);
}

/* ---------------- wiring ---------------- */

function wire() {
  $("scan-btn").addEventListener("click", scan);
  $("empty-scan-btn").addEventListener("click", scan);
  $("retry-btn").addEventListener("click", scan);
  $("save-btn").addEventListener("click", saveScan);
  $("banner-dismiss").addEventListener("click", () => banner(""));
  $("filter-input").addEventListener("input", applyFilter);

  $("repo-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") scan();
  });

  $("browse-btn").addEventListener("click", async () => {
    try {
      const res = await api("/api/browse-folder", { initial_dir: $("repo-input").value.trim() });
      if (res.path) $("repo-input").value = res.path;
      else if (res.folder) $("repo-input").value = res.folder;
    } catch (err) {
      banner(`Folder picker unavailable: ${err.message}. Type the path instead.`);
    }
  });

  $("risk-list").addEventListener("click", (e) => {
    const item = e.target.closest(".risk-item");
    if (item) selectFile(item.dataset.path);
  });

  $("detail-tabs").addEventListener("click", (e) => {
    if (e.target.dataset.tab) switchTab(e.target.dataset.tab);
  });

  $("brief-target").addEventListener("click", (e) => {
    const t = e.target.dataset.target;
    if (!t) return;
    state.briefTarget = t;
    document.querySelectorAll("#brief-target .seg-btn").forEach((b) => {
      b.classList.toggle("is-active", b.dataset.target === t);
    });
    const key = `${state.repo}|${state.selected ? (state.selected.file || state.selected.file_path) : ""}`;
    if (state.briefCache.has(key)) paintBrief(state.briefCache.get(key));
  });

  $("copy-brief").addEventListener("click", copyBrief);
}

async function init() {
  wire();
  pingServer();
  setInterval(pingServer, 20000);
  try {
    const res = await api("/api/get-repo-root");
    if (res.repo_root) $("repo-input").value = res.repo_root;
  } catch (_) { /* server may not be up yet */ }
}

document.addEventListener("DOMContentLoaded", init);
