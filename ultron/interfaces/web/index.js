/* Ultron — Unified Pre-Execution Intelligence Layer.
   Connects Repository Knowledge Models (RKM) to Modern Agentic Development:
   1. Architecture & Risk Dashboard
   2. Visual Topology Graph
   3. AI Agent Studio (Mission Envelopes & Contracts)
   4. Code Auditor & Safety Gates
*/

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
  pickerPath: "",
  activeView: "dashboard",
  // Graph state
  graphData: null,
  graphFilter: "all",
  graphGranularity: "file",
  graphExpanded: false,
  graphZoom: 1,
  graphPan: { x: 0, y: 0 },
  selectedNode: null,
  // Violations & Health
  violations: [],
  cycles: [],
  // Studio state
  studioFormat: "contract",
  // Auditor state
  auditorSource: "file",
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

function showToast(msg) {
  const t = $("toast");
  if (!t) return;
  t.textContent = msg;
  t.hidden = false;
  setTimeout(() => { t.hidden = true; }, 2600);
}

function splitPath(p) {
  const norm = String(p || "").replace(/\\/g, "/");
  const i = norm.lastIndexOf("/");
  return i === -1 ? { dir: "", base: norm } : { dir: norm.slice(0, i + 1), base: norm.slice(i + 1) };
}

/* ---------------- view navigation ---------------- */

function switchView(viewName) {
  state.activeView = viewName;
  document.querySelectorAll("#nav-tabs .nav-tab").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.view === viewName);
  });

  const views = ["view-dashboard", "view-graph", "view-studio", "view-auditor"];
  views.forEach((vid) => {
    const el = $(vid);
    if (!el) return;
    const isTarget = vid === `view-${viewName}`;
    el.hidden = !isTarget;
    if (isTarget) el.classList.add("is-active");
    else el.classList.remove("is-active");
  });

  if (viewName === "graph" && state.graphData) {
    requestAnimationFrame(() => renderTopologyGraph());
  }
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
  $("busy-text").textContent = "Analyzing repository AST & knowledge models…";
  show("busy-state");
  $("scan-btn").disabled = true;

  try {
    const [overviewData, healthData, graphData] = await Promise.all([
      api("/api/v1/overview", { repo }),
      api("/api/architecture-health", { repo }).catch(() => ({})),
      api("/api/dependency-graph", { repo, granularity: state.graphGranularity || "file" }).catch(() => ({}))
    ]);

    state.violations = healthData.violations || [];
    state.cycles = healthData.circular_dependencies || [];
    state.graphData = graphData.nodes ? graphData : null;

    render(overviewData, healthData);
  } catch (err) {
    $("error-text").textContent = err.message;
    show("error-state");
  } finally {
    $("scan-btn").disabled = false;
  }
}

async function saveScan() {
  const btn = $("save-btn");
  btn.disabled = true;
  btn.textContent = "Saving…";
  try {
    await api("/api/v1/analyze", { repo: state.repo });
    await waitForJob();
    const data = await api("/api/v1/overview", { repo: state.repo });
    render(data);
    showToast("Scan saved to Repository Knowledge Model");
  } catch (err) {
    banner(`Could not save scan: ${err.message}`);
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

/* ---------------- rendering dashboard ---------------- */

function render(data, healthData) {
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

  renderSummary(data, healthData);
  renderViolations();
  renderMemory(data.memory || {});
  applyFilter();
  resetDetail();
  show("results");

  // Pre-fill target in Agent Studio & Auditor
  if (state.risks.length > 0) {
    const topFile = state.risks[0].file || state.risks[0].file_path || "";
    if (!$("studio-target-file").value) $("studio-target-file").value = topFile;
    if (!$("auditor-file-input").value) $("auditor-file-input").value = topFile;
  }
}

function renderSummary(data, healthData) {
  const h = (healthData && healthData.health_score != null)
    ? { score: healthData.health_score, explanation: healthData.explanation }
    : (data.health || {});

  const el = $("health-score");
  const badge = $("health-badge");
  const score = h.score != null ? Math.round(h.score) : null;

  if (score == null) {
    el.textContent = "—";
    el.className = "score-num";
    badge.textContent = "Pending";
    badge.className = "badge-pill";
  } else {
    el.textContent = score;
    el.className = "score-num " + (score >= 70 ? "is-good" : score >= 40 ? "is-mid" : "is-bad");
    if (score >= 75) {
      badge.textContent = "Optimal";
      badge.className = "badge-pill optimal";
    } else if (score >= 45) {
      badge.textContent = "Watchlist";
      badge.className = "badge-pill warning";
    } else {
      badge.textContent = "Critical Risk";
      badge.className = "badge-pill critical";
    }
  }

  $("health-explain").textContent = h.explanation ||
    (score != null && score >= 70 ? "Architecture is balanced with well-contained modular boundaries." : "High coupling or complexity detected in critical modules.");

  const s = data.stats || {};
  $("count-high").textContent = s.high || 0;
  $("count-med").textContent = s.medium || 0;
  $("count-low").textContent = s.low || 0;
  $("count-files").textContent = s.total_files || 0;
  $("count-violations").textContent = state.violations.length;
  $("count-cycles").textContent = state.cycles.length;

  // Signal confidence basis chip
  const sigs = s.signals || {};
  const sigNames = Object.keys(sigs);
  const totalSigs = sigNames.length || 4;
  const activeSigs = sigNames.filter(k => sigs[k] && sigs[k].status === "active");
  const activeCount = activeSigs.length;
  const missingNames = sigNames.filter(k => sigs[k] && sigs[k].status !== "active");
  const confEl = $("count-confidence");
  const confChip = $("confidence-chip");
  if (confEl) confEl.textContent = `${activeCount} of ${totalSigs} signals`;
  if (confChip) {
    confChip.classList.toggle("is-full", activeCount === totalSigs);
    confChip.classList.toggle("is-partial", activeCount > 0 && activeCount < totalSigs);
    confChip.title = missingNames.length
      ? `Missing: ${missingNames.join(", ")} — ${missingNames.map(n => `${n} (${Math.round((sigs[n]?.weight || 0) * 100)}%)`).join(", ")}`
      : "All signals active";
  }
}

function renderViolations() {
  const list = $("violations-list");
  if (!list) return;

  if (state.violations.length === 0) {
    list.innerHTML = `<div class="pane-note">No architectural policy violations detected. Codebase complies with active constraints.</div>`;
    return;
  }

  list.innerHTML = state.violations.slice(0, 50).map((v) => {
    const sevClass = v.severity >= 3 ? "critical" : v.severity >= 2 ? "warning" : "optimal";
    return `<div class="violation-card">
      <div class="violation-top">
        <span class="violation-principle">${esc(v.principle || "Rule")}</span>
        <span class="badge-pill ${sevClass}">Sev ${esc(v.severity || 1)}</span>
      </div>
      <div class="violation-file">${esc(v.filepath || "")}</div>
      <div class="violation-obs">${esc(v.observation || v.reason || "")}</div>
      ${v.consequences ? `<div class="violation-conseq">Impact: ${esc(v.consequences)}</div>` : ""}
    </div>`;
  }).join("");
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
    : `<li class="mini-empty">Save a scan to track repeat offenders across runs.</li>`;

  const recs = mem.recommendations || [];
  $("rec-list").innerHTML = recs.length
    ? recs.map((r) => {
        const title = r.message || r.description || r.rule_id || "Suggestion";
        const sub = r.file_path ? splitPath(r.file_path).base : (r.rule_id || "");
        return `<li><div>${esc(title)}</div><div class="mini-sub">${esc(sub)}</div></li>`;
      }).join("")
    : `<li class="mini-empty">Save a scan to generate evolutionary suggestions.</li>`;
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
  $("detail-actions").hidden = true;
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
  $("detail-actions").hidden = false;
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
    </div>

    ${(() => {
      const fileSigs = r.signals || {};
      const names = Object.keys(fileSigs);
      const active = names.filter(k => fileSigs[k] && fileSigs[k].status === "active");
      const missing = names.filter(k => fileSigs[k] && fileSigs[k].status !== "active");
      const total = names.length || 4;
      const cls = active.length === total ? "optimal" : "warning";
      const missingStr = missing.length ? "; missing: " + missing.map(n => `${n} (${Math.round((fileSigs[n]?.weight || 0) * 100)}%)`).join(", ") : "";
      return `<div class="why-block confidence-basis">
        <h3>Confidence basis</h3>
        <span class="badge-pill ${cls}">${active.length} of ${total} signals (${active.join(", ")}${missingStr})</span>
      </div>`;
    })()}`;
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
    ? ((res.canonical_brief && res.canonical_brief.raw_text) || JSON.stringify(res, null, 2))
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
    try { document.execCommand("copy"); } catch (e) { /* fallback */ }
    document.body.removeChild(ta);
  }
  btn.textContent = "Copied";
  showToast("Agent briefing copied to clipboard");
  setTimeout(() => { btn.textContent = "Copy"; }, 1400);
}

/* ---------------- PILLAR 2: TOPOLOGY GRAPH ---------------- */

let graphSimulationNodes = [];

const PKG_PALETTE = [
  "#38bdf8", "#a78bfa", "#f472b6", "#fb923c",
  "#34d399", "#facc15", "#60a5fa", "#e879f9",
  "#4ade80", "#2dd4bf", "#818cf8", "#f87171"
];

function getPackageColor(pkg) {
  let hash = 0;
  for (let i = 0; i < pkg.length; i++) hash = (hash * 31 + pkg.charCodeAt(i)) >>> 0;
  return PKG_PALETTE[hash % PKG_PALETTE.length];
}

function renderTopologyGraph() {
  const svg = $("topology-svg");
  if (!svg) return;
  svg.innerHTML = "";

  if (!state.graphData || !state.graphData.nodes || state.graphData.nodes.length === 0) {
    if (state.risks && state.risks.length > 0) {
      state.graphData = {
        nodes: state.risks.map((r) => {
          const fid = (r.file || r.file_path || "").replace(/\\/g, "/");
          return {
            id: fid,
            label: splitPath(fid).base,
            type: "file",
            level: r.level || "LOW",
            role: r.architectural_role || r.boundary_type || "INTERNAL",
            complexity: r.complexity || 1,
            coupling: r.coupling != null ? r.coupling : (r.callers || []).length,
            impact_score: r.impact_score || 0,
            strategy_display: r.change_strategy_display || "",
            package: splitPath(fid).dir || "(root)",
            blast_radius: r.coupling != null ? r.coupling : (r.callers || []).length,
            in_cycle: false,
          };
        }),
        links: []
      };
      state.risks.forEach((r) => {
        const targetId = (r.file || r.file_path || "").replace(/\\/g, "/");
        (r.callers || []).forEach((c) => {
          state.graphData.links.push({
            source: String(c).replace(/\\/g, "/"),
            target: targetId,
            type: "import",
            in_cycle: false,
          });
        });
      });
    } else {
      return;
    }
  }

  const rawNodes = state.graphData.nodes || [];
  const rawLinks = state.graphData.links || [];

  let nodes = rawNodes;
  if (state.graphFilter === "high") {
    nodes = rawNodes.filter((n) => n.level === "HIGH");
  } else if (state.graphFilter === "core") {
    nodes = rawNodes.filter((n) => (n.role && n.role.toUpperCase() !== "INTERNAL") || n.level === "HIGH");
  }

  const totalFiltered = nodes.length;
  const isFileGranularity = (state.graphGranularity || "file") === "file";
  const expandBtn = $("graph-expand-toggle");

  // Progressive disclosure: cap at 80 files unless expanded
  if (isFileGranularity && totalFiltered > 80 && !state.graphExpanded) {
    nodes = [...nodes].sort((a, b) => (b.blast_radius || b.impact_score || 0) - (a.blast_radius || a.impact_score || 0)).slice(0, 80);
    if (expandBtn) {
      expandBtn.hidden = false;
      expandBtn.textContent = `Show All (${totalFiltered})`;
    }
  } else if (isFileGranularity && totalFiltered > 80 && state.graphExpanded) {
    if (expandBtn) {
      expandBtn.hidden = false;
      expandBtn.textContent = "Show Top 80";
    }
  } else {
    if (expandBtn) expandBtn.hidden = true;
  }

  // Update showing count label
  const countLabel = $("graph-count-label");
  if (countLabel) {
    if (isFileGranularity) {
      const distinctPkgs = new Set(nodes.map((n) => n.package || "(root)")).size;
      countLabel.textContent = `Showing ${nodes.length} of ${totalFiltered} files across ${distinctPkgs} packages`;
    } else {
      countLabel.textContent = `Showing ${nodes.length} of ${totalFiltered} symbols`;
    }
  }

  const width = svg.clientWidth || 800;
  const height = svg.clientHeight || 540;
  const cx = width / 2;
  const cy = height / 2;

  // Group nodes by package
  const packageGroups = new Map();
  nodes.forEach((n) => {
    const pkg = n.package || "(root)";
    if (!packageGroups.has(pkg)) packageGroups.set(pkg, []);
    packageGroups.get(pkg).push(n);
  });

  const pkgCount = packageGroups.size;
  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  g.setAttribute("id", "graph-viewport");
  g.setAttribute("transform", `translate(${state.graphPan.x}, ${state.graphPan.y}) scale(${state.graphZoom})`);
  svg.appendChild(g);

  graphSimulationNodes = [];

  if (isFileGranularity && pkgCount > 1) {
    const pkgRadius = Math.min(width, height) * 0.35;
    let pIdx = 0;
    packageGroups.forEach((members, pkg) => {
      const pAngle = (2 * Math.PI * pIdx) / pkgCount;
      const px = cx + pkgRadius * Math.cos(pAngle);
      const py = cy + pkgRadius * Math.sin(pAngle);
      const mCount = members.length;
      const clusterR = Math.min(110, Math.max(30, Math.sqrt(mCount) * 20));

      // Cluster boundary circle
      const cCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      cCircle.setAttribute("cx", px);
      cCircle.setAttribute("cy", py);
      cCircle.setAttribute("r", clusterR + 15);
      cCircle.setAttribute("class", "cluster-circle");
      g.appendChild(cCircle);

      // Cluster label
      const cLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
      cLabel.setAttribute("x", px);
      cLabel.setAttribute("y", py - clusterR - 4);
      cLabel.setAttribute("class", "cluster-label");
      cLabel.textContent = pkg;
      g.appendChild(cLabel);

      members.forEach((n, idx) => {
        const theta = mCount === 1 ? 0 : (2 * Math.PI * idx) / mCount;
        const dist = mCount === 1 ? 0 : clusterR * 0.72;
        const radius = Math.min(22, Math.max(8, Math.sqrt(n.blast_radius || n.coupling || 1) * 3 + 5));
        graphSimulationNodes.push({
          ...n,
          x: px + dist * Math.cos(theta),
          y: py + dist * Math.sin(theta),
          radius,
          packageColor: getPackageColor(pkg)
        });
      });
      pIdx++;
    });
  } else {
    // Single package or symbol layout
    const N = nodes.length;
    const R = Math.min(width, height) * 0.38;
    graphSimulationNodes = nodes.map((n, i) => {
      const theta = (2 * Math.PI * i) / (N || 1);
      const dist = n.level === "HIGH" ? R * 0.6 : R;
      const radius = Math.min(18, Math.max(7, Math.sqrt(n.complexity || 5) * 2.0));
      return {
        ...n,
        x: cx + dist * Math.cos(theta),
        y: cy + dist * Math.sin(theta),
        radius,
        packageColor: getPackageColor(n.package || "(root)")
      };
    });
  }

  const simMap = new Map();
  graphSimulationNodes.forEach((n) => simMap.set(n.id, n));

  const validLinks = rawLinks.filter((l) => {
    const sId = typeof l.source === "object" ? l.source.id : String(l.source).replace(/\\/g, "/");
    const tId = typeof l.target === "object" ? l.target.id : String(l.target).replace(/\\/g, "/");
    return simMap.has(sId) && simMap.has(tId);
  });

  validLinks.forEach((link) => {
    const sId = typeof link.source === "object" ? link.source.id : String(link.source).replace(/\\/g, "/");
    const tId = typeof link.target === "object" ? link.target.id : String(link.target).replace(/\\/g, "/");
    const src = simMap.get(sId);
    const tgt = simMap.get(tId);
    if (!src || !tgt) return;

    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", src.x);
    line.setAttribute("y1", src.y);
    line.setAttribute("x2", tgt.x);
    line.setAttribute("y2", tgt.y);
    const isCycle = !!link.in_cycle;
    line.setAttribute("class", isCycle ? "link cycle-link" : "link");
    if (isCycle) line.setAttribute("title", `Circular import cycle: ${src.label} ⇄ ${tgt.label}`);
    line.setAttribute("data-src", src.id);
    line.setAttribute("data-tgt", tgt.id);
    g.appendChild(line);
  });

  graphSimulationNodes.forEach((node) => {
    const color = node.level === "HIGH" ? "var(--high)" : node.level === "MEDIUM" ? "var(--med)" : "var(--low)";

    if (node.level === "HIGH" || node.in_cycle) {
      const glow = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      glow.setAttribute("cx", node.x);
      glow.setAttribute("cy", node.y);
      glow.setAttribute("r", node.radius + 6);
      glow.setAttribute("fill", "none");
      glow.setAttribute("stroke", node.in_cycle ? "#ef4444" : color);
      glow.setAttribute("class", "node-glow");
      g.appendChild(glow);
    }

    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", node.x);
    circle.setAttribute("cy", node.y);
    circle.setAttribute("r", node.radius);
    circle.setAttribute("fill", "#11141c");
    circle.setAttribute("stroke", node.in_cycle ? "#ef4444" : (node.packageColor || color));
    circle.setAttribute("stroke-width", node.in_cycle ? "3" : "2.5");
    circle.setAttribute("class", "node");
    circle.setAttribute("data-id", node.id);

    circle.addEventListener("click", (e) => {
      e.stopPropagation();
      openNodeInspector(node, validLinks);
    });

    circle.addEventListener("mouseenter", () => {
      g.querySelectorAll(".link").forEach((l) => {
        const isConn = l.getAttribute("data-src") === node.id || l.getAttribute("data-tgt") === node.id;
        l.classList.toggle("active", isConn);
      });
    });
    circle.addEventListener("mouseleave", () => {
      g.querySelectorAll(".link").forEach((l) => l.classList.remove("active"));
    });

    g.appendChild(circle);

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", node.x);
    text.setAttribute("y", node.y + node.radius + 12);
    text.setAttribute("class", "node-text");
    text.textContent = splitPath(node.id).base;
    g.appendChild(text);
  });

  setupGraphPanZoom(svg, g);
}

function setupGraphPanZoom(svg, g) {
  let isPanning = false;
  let startX = 0;
  let startY = 0;

  svg.onmousedown = (e) => {
    if (e.target.tagName === "circle") return;
    isPanning = true;
    startX = e.clientX - state.graphPan.x;
    startY = e.clientY - state.graphPan.y;
  };

  window.onmousemove = (e) => {
    if (!isPanning) return;
    state.graphPan.x = e.clientX - startX;
    state.graphPan.y = e.clientY - startY;
    g.setAttribute("transform", `translate(${state.graphPan.x}, ${state.graphPan.y}) scale(${state.graphZoom})`);
  };

  window.onmouseup = () => { isPanning = false; };

  svg.onwheel = (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    state.graphZoom = Math.min(3, Math.max(0.4, state.graphZoom * factor));
    g.setAttribute("transform", `translate(${state.graphPan.x}, ${state.graphPan.y}) scale(${state.graphZoom})`);
  };
}

function openNodeInspector(node, validLinks) {
  state.selectedNode = node;
  const ins = $("graph-inspector");
  ins.hidden = false;

  $("inspector-file").textContent = splitPath(node.id).base;
  $("inspector-file").title = node.id;

  const lvl = $("inspector-level");
  lvl.textContent = node.level;
  lvl.className = `badge lv-${node.level}`;

  $("inspector-role").textContent = node.role || "Internal";
  $("inspector-complexity").textContent = node.complexity || 0;
  $("inspector-coupling").textContent = node.coupling || 0;
  $("inspector-impact").textContent = Number(node.impact_score || 0).toFixed(1);
  $("inspector-strategy").textContent = node.strategy_display || "Local refactoring is safe; keep public interfaces unchanged.";

  const pkgEl = $("inspector-package");
  if (pkgEl) {
    pkgEl.textContent = node.package || "(root)";
    pkgEl.hidden = false;
  }
  const cycEl = $("inspector-cycle");
  if (cycEl) {
    cycEl.hidden = !node.in_cycle;
  }

  const deps = [];
  (validLinks || []).forEach((l) => {
    const sId = typeof l.source === "object" ? l.source.id : l.source;
    const tId = typeof l.target === "object" ? l.target.id : l.target;
    if (sId === node.id) deps.push(`Calls: ${splitPath(tId).base}`);
    else if (tId === node.id) deps.push(`Imported by: ${splitPath(sId).base}`);
  });

  $("inspector-dep-count").textContent = deps.length;
  $("inspector-dep-list").innerHTML = deps.length
    ? deps.slice(0, 10).map((d) => `<li>${esc(d)}</li>`).join("")
    : `<li class="mini-empty">No direct connections mapped in this view.</li>`;
}

/* ---------------- PILLAR 3: AGENT STUDIO ---------------- */

async function compileAgentMission() {
  const repo = state.repo || $("repo-input").value.trim() || ".";
  const targetFile = $("studio-target-file").value.trim();
  const intent = $("studio-intent").value.trim();
  const btn = $("studio-compile-btn");
  const output = $("studio-output");

  btn.disabled = true;
  btn.textContent = "Compiling grounded briefing…";
  output.textContent = "// Synthesizing AST boundaries, complexity limits, and verification requirements…";

  try {
    if (state.studioFormat === "contract") {
      const res = await api("/api/generate", { repo, intent: intent || "Implement requested changes with zero revision debt", target_files: targetFile ? [targetFile] : [] });
      output.textContent = res.prompt || JSON.stringify(res, null, 2);
      $("studio-output-title").textContent = "Ultron Pre-Execution Zero-Revision Contract";
    } else {
      const res = await api("/api/v1/context-brief", { repo, target_file: targetFile, intent });
      const handoff = res.handoff || {};
      const rendered = handoff[state.studioFormat] || JSON.stringify(res, null, 2);
      output.textContent = rendered;
      const titles = {
        claude: "Claude Code CLI Handoff",
        codex: "OpenAI Codex System Markdown Brief",
        antigravity: "Google Antigravity / Gemini Architectural Brief"
      };
      $("studio-output-title").textContent = titles[state.studioFormat] || "Agent Mission Package";
    }

    const lines = output.textContent.split("\n").length;
    const chars = output.textContent.length;
    $("studio-output-stats").textContent = `${lines} lines · ~${Math.round(chars / 4)} tokens · Grounded in AST`;
    showToast("Mission package compiled successfully");
  } catch (err) {
    output.textContent = `// Compilation failed: ${err.message}`;
    $("studio-output-stats").textContent = "Error";
    showToast(`Error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "Compile Agent Mission Package";
  }
}

async function copyStudioOutput() {
  const text = $("studio-output").textContent;
  try {
    await navigator.clipboard.writeText(text);
    showToast("Mission copied to clipboard!");
  } catch (_) {
    showToast("Please copy directly from the view.");
  }
}

function downloadStudioOutput() {
  const text = $("studio-output").textContent;
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `ultron-mission-${Date.now()}.md`;
  a.click();
  showToast("Saved mission file");
}

/* ---------------- PILLAR 4: CODE AUDITOR ---------------- */

async function runCodeAudit() {
  const repo = state.repo || $("repo-input").value.trim() || ".";
  const btn = $("auditor-run-btn");
  const shield = $("auditor-shield");
  const shieldIcon = $("auditor-shield-icon");
  const shieldText = $("auditor-shield-text");
  const verdictTitle = $("auditor-verdict-title");
  const verdictDesc = $("auditor-verdict-desc");
  const list = $("auditor-anomalies-list");

  btn.disabled = true;
  btn.textContent = "Auditing against rules & baseline…";
  shield.className = "auditor-shield";
  shieldIcon.textContent = "⋯";
  shieldText.textContent = "Checking";

  const typoThreshold = parseFloat($("auditor-slider-typo").value) / 100;

  const payload = {
    repo,
    typo_threshold: typoThreshold
  };

  const isSandbox = state.auditorSource === "sandbox";
  if (isSandbox) {
    payload.code = $("auditor-sandbox-code").value;
  } else {
    payload.target_file = $("auditor-file-input").value.trim();
  }

  try {
    const res = await api("/api/audit", payload);
    const anomalies = res.anomalies || [];

    const targetPath = payload.target_file || "";
    const fileViolations = state.violations.filter((v) => targetPath && v.filepath && v.filepath.includes(targetPath));

    const totalIssues = anomalies.length + fileViolations.length;

    if (totalIssues === 0) {
      shield.className = "auditor-shield clean";
      shieldIcon.textContent = "✓";
      shieldText.textContent = "Safe";
      verdictTitle.textContent = "Code Safety Gate Passed";
      verdictDesc.textContent = "No typo drift, signature mismatches, or architectural policy violations found.";
      list.innerHTML = `<div class="pane-note">All identifiers, signatures, and call sequences comply with baseline rules.</div>`;
    } else {
      shield.className = "auditor-shield anomaly";
      shieldIcon.textContent = "!";
      shieldText.textContent = "Alert";
      verdictTitle.textContent = `${totalIssues} Issue${totalIssues === 1 ? "" : "s"} Detected`;
      verdictDesc.textContent = "Anomalies or policy constraints require verification before merge.";

      const items = [];
      anomalies.forEach((a) => {
        const isTypo = a.type && a.type.toLowerCase().includes("typo");
        items.push(`<div class="anomaly-item ${isTypo ? "typo" : "markov"}">
          <div class="anomaly-title">${esc(a.type || "Code Anomaly")} in line ${esc(a.line || "?")}</div>
          <div class="anomaly-desc">${esc(a.description || a.message || "")}</div>
          ${a.suggestion ? `<div class="anomaly-fix">Suggested: ${esc(a.suggestion)}</div>` : ""}
        </div>`);
      });

      fileViolations.forEach((v) => {
        items.push(`<div class="anomaly-item markov">
          <div class="anomaly-title">Architectural Policy: ${esc(v.principle || "Rule")}</div>
          <div class="anomaly-desc">${esc(v.observation || v.reason || "")}</div>
          ${v.consequences ? `<div class="anomaly-fix">Consequence: ${esc(v.consequences)}</div>` : ""}
        </div>`);
      });

      list.innerHTML = items.join("");
    }
  } catch (err) {
    shield.className = "auditor-shield anomaly";
    shieldIcon.textContent = "✕";
    shieldText.textContent = "Error";
    verdictTitle.textContent = "Audit Failed";
    verdictDesc.textContent = err.message;
    list.innerHTML = `<div class="pane-note">${esc(err.message)}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Run Code Safety Audit";
  }
}

/* ---------------- folder picker ---------------- */

async function openPicker(startPath) {
  const box = $("picker");
  box.hidden = false;
  $("picker-list").innerHTML = `<li class="picker-note">Loading…</li>`;
  try {
    const q = startPath ? `?path=${encodeURIComponent(startPath)}` : "";
    const res = await api(`/api/list-dirs${q}`);
    state.pickerPath = res.path;
    $("picker-path").textContent = res.path;

    $("picker-drives").innerHTML = (res.drives || [])
      .map((d) => `<button class="chip-btn" data-path="${esc(d)}">${esc(d)}</button>`).join("");

    const rows = [];
    if (res.parent) rows.push(`<li class="picker-row" data-path="${esc(res.parent)}">↑ ..</li>`);
    for (const e of res.entries || []) {
      rows.push(`<li class="picker-row" data-path="${esc(e.path)}">${esc(e.name)}</li>`);
    }
    $("picker-list").innerHTML = rows.length ? rows.join("") : `<li class="picker-note">No subfolders here.</li>`;
  } catch (err) {
    $("picker-list").innerHTML = `<li class="picker-note">${esc(err.message)}</li>`;
  }
}

/* ---------------- wiring ---------------- */

function wire() {
  $("nav-tabs").addEventListener("click", (e) => {
    const btn = e.target.closest(".nav-tab");
    if (btn && btn.dataset.view) switchView(btn.dataset.view);
  });

  $("scan-btn").addEventListener("click", scan);
  $("empty-scan-btn").addEventListener("click", scan);
  $("retry-btn").addEventListener("click", scan);
  $("save-btn").addEventListener("click", saveScan);
  $("banner-dismiss").addEventListener("click", () => banner(""));
  $("filter-input").addEventListener("input", applyFilter);

  $("repo-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") scan();
  });

  $("browse-btn").addEventListener("click", () => openPicker($("repo-input").value.trim()));
  $("picker-close").addEventListener("click", () => { $("picker").hidden = true; });
  $("picker-use").addEventListener("click", () => {
    if (state.pickerPath) $("repo-input").value = state.pickerPath;
    $("picker").hidden = true;
  });

  $("picker-list").addEventListener("click", (e) => {
    const item = e.target.closest("[data-path]");
    if (item) openPicker(item.dataset.path);
  });

  $("picker-drives").addEventListener("click", (e) => {
    const item = e.target.closest("[data-path]");
    if (item) openPicker(item.dataset.path);
  });

  $("violations-chip").addEventListener("click", () => {
    const d = $("violations-drawer");
    d.hidden = !d.hidden;
  });
  $("close-violations").addEventListener("click", () => {
    $("violations-drawer").hidden = true;
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

  $("btn-jump-graph").addEventListener("click", () => {
    const p = state.selected ? (state.selected.file || state.selected.file_path) : "";
    switchView("graph");
    if (p) {
      setTimeout(() => {
        const simNode = graphSimulationNodes.find((n) => n.id === p);
        if (simNode) openNodeInspector(simNode);
      }, 100);
    }
  });

  $("btn-jump-studio").addEventListener("click", () => {
    const p = state.selected ? (state.selected.file || state.selected.file_path) : "";
    if (p) $("studio-target-file").value = p;
    switchView("studio");
  });

  $("btn-jump-auditor").addEventListener("click", () => {
    const p = state.selected ? (state.selected.file || state.selected.file_path) : "";
    if (p) {
      $("auditor-file-input").value = p;
      state.auditorSource = "file";
      $("auditor-file-group").hidden = false;
      $("auditor-sandbox-group").hidden = true;
      document.querySelectorAll("#auditor-source-seg .seg-btn").forEach((b) => {
        b.classList.toggle("is-active", b.dataset.source === "file");
      });
    }
    switchView("auditor");
  });

  document.querySelectorAll("[data-granularity]").forEach((b) => {
    b.addEventListener("click", async () => {
      document.querySelectorAll("[data-granularity]").forEach((x) => x.classList.remove("is-active"));
      b.classList.add("is-active");
      state.graphGranularity = b.dataset.granularity;
      state.graphExpanded = false;
      try {
        const graphData = await api("/api/dependency-graph", { repo: state.repo, granularity: state.graphGranularity });
        state.graphData = graphData.nodes ? graphData : null;
        renderTopologyGraph();
      } catch (err) {
        showToast("Failed to load " + state.graphGranularity + " graph: " + err.message);
      }
    });
  });

  const expandToggle = $("graph-expand-toggle");
  if (expandToggle) {
    expandToggle.addEventListener("click", () => {
      state.graphExpanded = !state.graphExpanded;
      renderTopologyGraph();
    });
  }

  document.querySelectorAll("[data-graph-filter]").forEach((b) => {
    b.addEventListener("click", () => {
      document.querySelectorAll("[data-graph-filter]").forEach((x) => x.classList.remove("is-active"));
      b.classList.add("is-active");
      state.graphFilter = b.dataset.graphFilter;
      renderTopologyGraph();
    });
  });

  $("graph-search-input").addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    const g = $("graph-viewport");
    if (!g) return;
    g.querySelectorAll(".node").forEach((circle) => {
      const id = circle.getAttribute("data-id") || "";
      const match = q && id.toLowerCase().includes(q);
      circle.setAttribute("stroke-width", match ? "6" : "2.5");
    });
  });

  $("graph-zoom-in").addEventListener("click", () => {
    state.graphZoom = Math.min(3, state.graphZoom * 1.25);
    const g = $("graph-viewport");
    if (g) g.setAttribute("transform", `translate(${state.graphPan.x}, ${state.graphPan.y}) scale(${state.graphZoom})`);
  });

  $("graph-zoom-out").addEventListener("click", () => {
    state.graphZoom = Math.max(0.4, state.graphZoom * 0.8);
    const g = $("graph-viewport");
    if (g) g.setAttribute("transform", `translate(${state.graphPan.x}, ${state.graphPan.y}) scale(${state.graphZoom})`);
  });

  $("graph-zoom-reset").addEventListener("click", () => {
    state.graphZoom = 1;
    state.graphPan = { x: 0, y: 0 };
    const g = $("graph-viewport");
    if (g) g.setAttribute("transform", "translate(0, 0) scale(1)");
  });

  $("inspector-close").addEventListener("click", () => {
    $("graph-inspector").hidden = true;
  });

  $("inspector-btn-dash").addEventListener("click", () => {
    if (state.selectedNode) {
      selectFile(state.selectedNode.id);
      switchView("dashboard");
    }
  });

  $("inspector-btn-studio").addEventListener("click", () => {
    if (state.selectedNode) {
      $("studio-target-file").value = state.selectedNode.id;
      switchView("studio");
    }
  });

  $("inspector-btn-audit").addEventListener("click", () => {
    if (state.selectedNode) {
      $("auditor-file-input").value = state.selectedNode.id;
      state.auditorSource = "file";
      $("auditor-file-group").hidden = false;
      $("auditor-sandbox-group").hidden = true;
      document.querySelectorAll("#auditor-source-seg .seg-btn").forEach((b) => {
        b.classList.toggle("is-active", b.dataset.source === "file");
      });
      switchView("auditor");
    }
  });

  $("studio-format-seg").addEventListener("click", (e) => {
    const f = e.target.dataset.format;
    if (!f) return;
    state.studioFormat = f;
    document.querySelectorAll("#studio-format-seg .seg-btn").forEach((b) => {
      b.classList.toggle("is-active", b.dataset.format === f);
    });
  });

  $("studio-compile-btn").addEventListener("click", compileAgentMission);
  $("studio-copy-btn").addEventListener("click", copyStudioOutput);
  $("studio-download-btn").addEventListener("click", downloadStudioOutput);

  $("auditor-source-seg").addEventListener("click", (e) => {
    const s = e.target.dataset.source;
    if (!s) return;
    state.auditorSource = s;
    document.querySelectorAll("#auditor-source-seg .seg-btn").forEach((b) => {
      b.classList.toggle("is-active", b.dataset.source === s);
    });
    $("auditor-file-group").hidden = s !== "file";
    $("auditor-sandbox-group").hidden = s !== "sandbox";
  });

  $("auditor-slider-typo").addEventListener("input", (e) => {
    $("auditor-val-typo").textContent = `${e.target.value}%`;
  });

  $("auditor-run-btn").addEventListener("click", runCodeAudit);
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
