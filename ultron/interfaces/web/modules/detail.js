/**
 * Ultron Web SPA — Pillar 1: File Detail Inspection Module
 * Layer 2 Feature Module: Why-it-scored, code viewer, context brief, tab switching.
 */

import { state } from "./state.js";
import { $, esc, normPath, parseSeverity, splitPath, api, showToast } from "./api.js";
import { reasonsFor, renderList } from "./dashboard.js";

export function selectFile(path, handlers = {}) {
  const targetNorm = normPath(path);
  let r = (state.risks || []).find((x) => {
    const p = normPath(x.file || x.file_path);
    return p === targetNorm || p.endsWith("/" + targetNorm) || targetNorm.endsWith("/" + p);
  });
  if (!r) {
    // Fallback: synthesize baseline entry so detail pane, code viewer, and active violations always open
    r = {
      file: targetNorm,
      file_path: targetNorm,
      level: "WATCH",
      complexity: 1,
      coupling: 0,
      impact_score: 1.0,
      callers: [],
      change_strategy_display: "Focus on resolving the architectural rule violation."
    };
  }
  state.selected = r;
  if (state.activeView !== "dashboard") {
    if (typeof handlers.onSwitchView === "function") handlers.onSwitchView("dashboard");
    else window.dispatchEvent(new CustomEvent("ultron:switch-view", { detail: { view: "dashboard" } }));
  }
  renderList();

  if ($("detail-title")) $("detail-title").textContent = splitPath(targetNorm).base;
  if ($("detail-placeholder")) $("detail-placeholder").hidden = true;
  if ($("detail-tabs")) $("detail-tabs").hidden = false;
  if ($("detail-actions")) $("detail-actions").hidden = false;
  renderWhy(r);
  switchTab(state.activeTab);

  const detailEl = document.querySelector(".pane-detail");
  if (detailEl && typeof detailEl.scrollIntoView === "function") {
    detailEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

export function renderWhy(r) {
  const cx = Number(r.complexity || 0);
  const cp = Number(r.coupling != null ? r.coupling : r.coupling_score || 0);
  const score = Number(r.impact_score || 0);
  const callers = r.callers || [];

  const guidance = r.change_strategy_display || r.mitigation ||
    (r.level === "HIGH"
      ? "Change this in small steps and re-run your tests after each one."
      : "Safe to edit directly.");

  const targetNorm = normPath(r.file || r.file_path);
  const fileViolations = (state.violations || []).filter((v) => {
    const vp = normPath(v.filepath || v.source_file || v.file);
    return vp && (vp === targetNorm || vp.endsWith("/" + targetNorm) || targetNorm.endsWith("/" + vp));
  });

  const tabWhy = $("tab-why");
  if (!tabWhy) return;

  tabWhy.innerHTML = `
    <div class="metrics">
      <div class="metric"><div class="metric-val">${score.toFixed(1)}</div><div class="metric-key">Risk score</div></div>
      <div class="metric"><div class="metric-val">${cx}</div><div class="metric-key">Complexity</div></div>
      <div class="metric"><div class="metric-val">${cp.toFixed(1)}</div><div class="metric-key">Coupling</div></div>
      <div class="metric"><div class="metric-val">${callers.length}</div><div class="metric-key">Used by</div></div>
    </div>

    ${fileViolations.length ? `
    <div class="why-block file-active-violations">
      <h3>Active Architectural Policy Violations (${fileViolations.length})</h3>
      <div class="mini-violations-list">
        ${fileViolations.map((v) => {
          const s = parseSeverity(v.severity);
          const sCls = s >= 3 ? "critical" : s >= 2 ? "warning" : "optimal";
          const pName = esc(v.principle || v.rule_name || v.rule_id || "Rule");
          const obs = esc(v.observation || v.reason || v.message || "");
          return `
            <div class="mini-violation-row">
              <div class="mini-v-info">
                <span class="badge-pill ${sCls}">Sev ${s}</span>
                <span><strong>${pName}</strong>: ${obs}</span>
              </div>
              <button class="btn btn-primary btn-sm btn-draft-file-fix" data-filepath="${esc(targetNorm)}" data-principle="${pName}">
                ⚡ Draft Fix
              </button>
            </div>
          `;
        }).join("")}
      </div>
    </div>` : ""}

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

export async function loadCode() {
  const path = state.selected && (state.selected.file || state.selected.file_path);
  if (!path) return;
  const view = $("code-view");
  if (!view) return;
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

export async function loadBrief() {
  const path = state.selected ? (state.selected.file || state.selected.file_path) : "";
  const key = `${state.repo}|${path}`;
  const view = $("brief-view");
  if (!view) return;
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

export function paintBrief(res) {
  const handoff = (res && res.handoff) || {};
  const text = state.briefTarget === "raw"
    ? ((res && res.canonical_brief && res.canonical_brief.raw_text) || JSON.stringify(res, null, 2))
    : (handoff[state.briefTarget] || "Not available.");
  if ($("brief-view")) $("brief-view").textContent = text;
}

export function switchTab(name) {
  state.activeTab = name;
  document.querySelectorAll("#detail-tabs .tab").forEach((b) => {
    b.classList.toggle("is-active", b.dataset.tab === name);
  });
  if ($("tab-why")) $("tab-why").hidden = name !== "why";
  if ($("tab-code")) $("tab-code").hidden = name !== "code";
  if ($("tab-brief")) $("tab-brief").hidden = name !== "brief";
  if (name === "code") loadCode();
  if (name === "brief") loadBrief();
}

export async function copyBrief() {
  const view = $("brief-view");
  const text = view ? view.textContent : "";
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
  if (btn) btn.textContent = "Copied";
  showToast("Agent briefing copied to clipboard");
  if (btn) setTimeout(() => { btn.textContent = "Copy"; }, 1400);
}
