/* Ultron — Unified Pre-Execution Intelligence Layer.
   Connects Repository Knowledge Models (RKM) to Modern Agentic Development:
   1. Architecture & Risk Dashboard  (modules/dashboard.js, modules/violations.js, modules/detail.js)
   2. Visual Topology Graph          (modules/graph.js)
   3. AI Agent Studio                (modules/studio.js)
   4. Code Auditor & Safety Gates    (modules/auditor.js)
   Standardized 4-Layer Unidirectional ES Module Architecture (<400 lines per file).
*/

import { state as sharedState } from "./modules/state.js";
import { $, esc, normPath as helperNormPath, parseSeverity as helperParseSeverity, splitPath, api as helperApi, show, banner, showToast as helperShowToast } from "./modules/api.js";
import { updatePrimaryVerdict, renderSummary as renderSummaryModule, renderMemory, applyFilter, renderList, resetDetail, renderDashboard } from "./modules/dashboard.js";
import { renderViolations as renderViolationsModule, setupViolationsDelegation as setupViolationsDelegationModule, viewInGraph as viewInGraphModule, draftFixMission as draftFixMissionModule } from "./modules/violations.js";
import { selectFile as selectFileModule, renderWhy, loadCode, loadBrief, paintBrief, switchTab, copyBrief } from "./modules/detail.js";
import { renderTopologyGraph as renderTopologyGraphModule, openNodeInspector, graphSimulationNodes } from "./modules/graph.js";
import { compileAgentMission, copyStudioOutput, downloadStudioOutput } from "./modules/studio.js";
import { runCodeAudit as runCodeAuditModule } from "./modules/auditor.js";
import { openPicker as openPickerModule } from "./modules/picker.js";

/* ---------------- Shared State Facade ---------------- */

// Compatibility contract for test inspection: const state = { ...sharedState };
export const state = sharedState;

/* ---------------- Helper Facades (Backwards-Compatible Signatures) ---------------- */

export function normPath(p) { return helperNormPath(p); }
export function parseSeverity(s) { return helperParseSeverity(s); }
export async function api(path, body) { return helperApi(path, body); }
export function showToast(msg) { return helperShowToast(msg); }
export async function openPicker(startPath) { return openPickerModule(startPath); }

/* ---------------- View Navigation & Routing ---------------- */

export function switchView(viewName) {
  state.activeView = viewName;
  document.querySelectorAll("#nav-tabs .nav-tab").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.view === viewName);
  });
  ["view-dashboard", "view-graph", "view-studio", "view-auditor"].forEach((vid) => {
    const el = $(vid);
    if (!el) return;
    const isTarget = vid === `view-${viewName}`;
    el.hidden = !isTarget;
    el.classList.toggle("is-active", isTarget);
  });
  if (viewName === "graph" && state.graphData) {
    requestAnimationFrame(() => renderTopologyGraph());
  }
}

/* ---------------- Server Connection & Heartbeat ---------------- */

export async function pingServer() {
  const el = $("conn");
  try {
    await api("/api/v1/health");
    if (el) el.className = "conn is-ok";
    if ($("conn-text")) $("conn-text").textContent = "connected";
  } catch (_) {
    if (el) el.className = "conn is-down";
    if ($("conn-text")) $("conn-text").textContent = "offline";
  }
}

/* ---------------- Scanning & Job Orchestration ---------------- */

export async function scan() {
  const repoInput = $("repo-input");
  const repo = repoInput ? repoInput.value.trim() : "";
  if (!repo) {
    banner("Enter a repository path first.");
    if (repoInput) repoInput.focus();
    return;
  }
  state.repo = repo;
  banner("");
  if ($("busy-text")) $("busy-text").textContent = "Analyzing repository AST & knowledge models…";
  show("busy-state");
  if ($("scan-btn")) $("scan-btn").disabled = true;

  try {
    const [overviewData, healthData, graphData] = await Promise.all([
      api("/api/v1/overview", { repo }),
      api("/api/architecture-health", { repo }).catch(() => ({})),
      api("/api/dependency-graph", { repo, granularity: state.graphGranularity || "file" }).catch(() => ({})),
    ]);
    state.violations = healthData.violations || [];
    state.cycles = healthData.circular_dependencies || [];
    state.graphData = graphData && graphData.nodes ? graphData : null;
    render(overviewData, healthData);
  } catch (err) {
    if ($("error-text")) $("error-text").textContent = err.message;
    show("error-state");
  } finally {
    if ($("scan-btn")) $("scan-btn").disabled = false;
  }
}

export async function saveScan() {
  const btn = $("save-btn");
  if (btn) { btn.disabled = true; btn.textContent = "Saving…"; }
  try {
    await api("/api/v1/analyze", { repo: state.repo });
    await waitForJob();
    const data = await api("/api/v1/overview", { repo: state.repo });
    render(data);
    showToast("Scan saved to Repository Knowledge Model");
  } catch (err) {
    banner(`Could not save scan: ${err.message}`);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "Save this scan"; }
  }
}

export async function waitForJob() {
  for (let i = 0; i < 300; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    const p = await api("/api/v1/progress");
    if (p.status === "success") return;
    if (p.status === "failed") throw new Error(p.error || "Analysis failed");
    if (p.status === "cancelled") throw new Error("Analysis was cancelled");
  }
  throw new Error("Analysis timed out");
}

/* ---------------- Pillar Lifecycle Facades ---------------- */

export function render(data, healthData) {
  renderDashboard(data, healthData);
  renderViolations();
}

export function renderSummary(data, healthData) {
  return renderSummaryModule(data, healthData);
}

export function renderViolations() {
  return renderViolationsModule();
}

export function setupViolationsDelegation() {
  return setupViolationsDelegationModule({
    onSelectFile: (path) => selectFile(path),
    onViewInGraph: (path) => viewInGraph(path),
    onDraftFix: (path, vidx) => draftFixMission(path, vidx),
  });
}

export function viewInGraph(path) {
  return viewInGraphModule(path, {
    onSwitchView: (v) => switchView(v),
    onOpenNodeInspector: (node, links) => openNodeInspector(node, links),
    findGraphNode: (norm) => graphSimulationNodes.find((n) => {
      const nid = normPath(n.id);
      return nid === norm || nid.endsWith("/" + norm) || norm.endsWith("/" + nid);
    }),
  });
}

export function draftFixMission(path, vidx, principleOverride) {
  return draftFixMissionModule(path, vidx, principleOverride, {
    onSwitchView: (v) => switchView(v),
    onCompileMission: () => compileAgentMission(),
  });
}

export function selectFile(path) {
  return selectFileModule(path, {
    onSwitchView: (v) => switchView(v),
  });
}

export function renderTopologyGraph() {
  return renderTopologyGraphModule({
    onSwitchView: (v) => switchView(v),
    onSelectFile: (p) => selectFile(p),
  });
}

export async function runCodeAudit() {
  // Dispatches code safety audit via /api/audit endpoint
  try {
    const res = await runCodeAuditModule();
    if (!res.success) {
      showToast("Audit Incomplete: " + (res.error || "Unknown audit failure"));
    }
    return res;
  } catch (err) {
    showToast("Audit Incomplete: " + (err.message || "Unknown error"));
    throw err;
  }
}

/* ---------------- Keyboard Navigation ---------------- */

export function setupKeyboardShortcuts() {
  window.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const active = document.activeElement;
    const isEditing = active && (["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName) || active.isContentEditable);
    if (e.key === "Escape") {
      if (isEditing) { active.blur(); return; }
      for (const id of ["violations-drawer", "graph-inspector", "picker"]) {
        const el = $(id);
        if (el && !el.hidden) { el.hidden = true; return; }
      }
      if (state.selected) { state.selected = null; renderList(); resetDetail(); }
      return;
    }
    if (isEditing) return;
    const viewMap = { "1": "dashboard", "2": "graph", "3": "studio", "4": "auditor" };
    if (viewMap[e.key]) { e.preventDefault(); switchView(viewMap[e.key]); }
    else if (e.key === "/" && state.activeView === "dashboard") {
      const input = $("filter-input");
      if (input) { e.preventDefault(); input.focus(); input.select(); }
    }
  });
}

/* ---------------- Event Delegation & Wireup ---------------- */

export function wire() {
  setupKeyboardShortcuts();

  $("nav-tabs")?.addEventListener("click", (e) => {
    const btn = e.target.closest(".nav-tab");
    if (btn && btn.dataset.view) switchView(btn.dataset.view);
  });

  [
    ["scan-btn", "click", scan],
    ["empty-scan-btn", "click", scan],
    ["retry-btn", "click", scan],
    ["save-btn", "click", saveScan],
    ["banner-dismiss", "click", () => banner("")],
    ["filter-input", "input", applyFilter],
    ["clear-filter-btn", "click", () => { const el = $("filter-input"); if (el) { el.value = ""; applyFilter(); el.focus(); } }],
    ["repo-input", "keydown", (e) => { if (e.key === "Enter") scan(); }],
    ["browse-btn", "click", () => openPicker($("repo-input")?.value?.trim() || "")],
    ["picker-close", "click", () => { if ($("picker")) $("picker").hidden = true; }],
    ["picker-use", "click", () => { if (state.pickerPath) $("repo-input").value = state.pickerPath; if ($("picker")) $("picker").hidden = true; }],
    ["violations-chip", "click", () => { const d = $("violations-drawer"); if (d && !(d.hidden = !d.hidden)) renderViolations(); }],
    ["close-violations", "click", () => { if ($("violations-drawer")) $("violations-drawer").hidden = true; }],
    ["copy-brief", "click", copyBrief],
    ["graph-expand-toggle", "click", () => { state.graphExpanded = !state.graphExpanded; renderTopologyGraph(); }],
    ["inspector-close", "click", () => { if ($("graph-inspector")) $("graph-inspector").hidden = true; }],
    ["studio-compile-btn", "click", compileAgentMission],
    ["studio-copy-btn", "click", copyStudioOutput],
    ["studio-download-btn", "click", downloadStudioOutput],
    ["auditor-run-btn", "click", runCodeAudit],
  ].forEach(([id, evt, fn]) => $(id)?.addEventListener(evt, fn));

  $("graph-reload-btn")?.addEventListener("click", async () => {
    try {
      const graphData = await api("/api/dependency-graph", { repo: state.repo, granularity: state.graphGranularity });
      state.graphData = graphData.nodes ? graphData : null;
      renderTopologyGraph();
    } catch (err) { showToast("Failed to reload graph: " + err.message); }
  });

  const handlePickerClick = (e) => {
    const item = e.target.closest("[data-path]");
    if (item) openPicker(item.dataset.path);
  };
  $("picker-list")?.addEventListener("click", handlePickerClick);
  $("picker-drives")?.addEventListener("click", handlePickerClick);

  setupViolationsDelegation();

  $("tab-why")?.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-draft-file-fix");
    if (btn) { e.stopPropagation(); draftFixMission(btn.dataset.filepath, null, btn.dataset.principle); }
  });

  $("risk-list")?.addEventListener("click", (e) => {
    const item = e.target.closest(".risk-item");
    if (item) selectFile(item.dataset.path);
  });

  $("detail-tabs")?.addEventListener("click", (e) => { if (e.target.dataset.tab) switchTab(e.target.dataset.tab); });

  const bindSeg = (id, key, cb) => {
    $(id)?.addEventListener("click", (e) => {
      const v = e.target.dataset[key];
      if (!v) return;
      document.querySelectorAll(`#${id} .seg-btn`).forEach((b) => b.classList.toggle("is-active", b.dataset[key] === v));
      cb(v);
    });
  };
  bindSeg("brief-target", "target", (t) => {
    state.briefTarget = t;
    const key = `${state.repo}|${state.selected ? (state.selected.file || state.selected.file_path) : ""}`;
    if (state.briefCache.has(key)) paintBrief(state.briefCache.get(key));
  });
  bindSeg("studio-format-seg", "format", (f) => { state.studioFormat = f; });
  bindSeg("auditor-source-seg", "source", (s) => {
    state.auditorSource = s;
    if ($("auditor-file-group")) $("auditor-file-group").hidden = s !== "file";
    if ($("auditor-sandbox-group")) $("auditor-sandbox-group").hidden = s !== "sandbox";
  });

  const jumpFrom = (view, getP, cb) => {
    const p = getP();
    if (p && cb) cb(p);
    if (p || !getP) switchView(view);
  };
  const selFile = () => state.selected ? (state.selected.file || state.selected.file_path) : "";
  const insFile = () => state.selectedNode ? state.selectedNode.id : "";
  const syncAuditorFile = (p) => {
    if ($("auditor-file-input")) $("auditor-file-input").value = p;
    state.auditorSource = "file";
    if ($("auditor-file-group")) $("auditor-file-group").hidden = false;
    if ($("auditor-sandbox-group")) $("auditor-sandbox-group").hidden = true;
    document.querySelectorAll("#auditor-source-seg .seg-btn").forEach((b) => b.classList.toggle("is-active", b.dataset.source === "file"));
  };

  $("btn-jump-graph")?.addEventListener("click", () => jumpFrom("graph", selFile, (p) => {
    setTimeout(() => { const n = graphSimulationNodes.find((x) => x.id === p); if (n) openNodeInspector(n); }, 100);
  }));
  $("btn-jump-studio")?.addEventListener("click", () => jumpFrom("studio", selFile, (p) => {
    if ($("studio-target-file")) $("studio-target-file").value = p;
  }));
  $("btn-jump-auditor")?.addEventListener("click", () => jumpFrom("auditor", selFile, syncAuditorFile));

  $("inspector-btn-dash")?.addEventListener("click", () => jumpFrom("dashboard", insFile, (id) => selectFile(id)));
  $("inspector-btn-studio")?.addEventListener("click", () => jumpFrom("studio", insFile, (id) => {
    if ($("studio-target-file")) $("studio-target-file").value = id;
  }));
  $("inspector-btn-audit")?.addEventListener("click", () => jumpFrom("auditor", insFile, syncAuditorFile));

  const bindGroup = (sel, dataKey, cb) => {
    document.querySelectorAll(sel).forEach((b) => {
      b.addEventListener("click", () => {
        document.querySelectorAll(sel).forEach((x) => x.classList.remove("is-active"));
        b.classList.add("is-active");
        cb(b.dataset[dataKey]);
      });
    });
  };
  bindGroup("[data-granularity]", "granularity", async (gran) => {
    state.graphGranularity = gran;
    state.graphExpanded = false;
    try {
      const data = await api("/api/dependency-graph", { repo: state.repo, granularity: gran });
      state.graphData = data.nodes ? data : null;
      renderTopologyGraph();
    } catch (err) { showToast("Failed to load " + gran + " graph: " + err.message); }
  });
  bindGroup("[data-graph-filter]", "graphFilter", (filt) => {
    state.graphFilter = filt;
    renderTopologyGraph();
  });

  $("graph-search-input")?.addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    const g = $("graph-viewport");
    if (!g) return;
    g.querySelectorAll(".node").forEach((circle) => {
      const id = circle.getAttribute("data-id") || "";
      circle.setAttribute("stroke-width", q && id.toLowerCase().includes(q) ? "6" : "2.5");
    });
  });

  [["graph-zoom-in", 1.25, false], ["graph-zoom-out", 0.8, false], ["graph-zoom-reset", 1, true]].forEach(([id, f, r]) => {
    $(id)?.addEventListener("click", () => {
      state.graphZoom = r ? 1 : Math.min(3, Math.max(0.4, state.graphZoom * f));
      if (r) state.graphPan = { x: 0, y: 0 };
      $("graph-viewport")?.setAttribute("transform", `translate(${state.graphPan.x}, ${state.graphPan.y}) scale(${state.graphZoom})`);
    });
  });

  $("auditor-slider-typo")?.addEventListener("input", (e) => {
    if ($("auditor-val-typo")) $("auditor-val-typo").textContent = `${e.target.value}%`;
  });
}

/* ---------------- Lifecycle Initialization ---------------- */

export async function init() {
  wire();
  pingServer();
  setInterval(pingServer, 20000);
  try {
    const res = await api("/api/get-repo-root");
    if (res.repo_root && $("repo-input")) $("repo-input").value = res.repo_root;
  } catch (_) {
    /* server may not be running yet */
  }
}

document.addEventListener("DOMContentLoaded", init);
