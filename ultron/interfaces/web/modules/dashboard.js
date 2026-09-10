/**
 * Ultron Web SPA — Pillar 1: Architecture & Risk Dashboard Module
 * Layer 2 Feature Module: Summary cards, verdict banner, file list & filter.
 */

import { state } from "./state.js";
import { $, esc, splitPath, banner, show } from "./api.js";

export function updatePrimaryVerdict() {
  const highCount = (state.risks || []).filter(r => (r.level || "").toUpperCase() === "HIGH").length;
  const titleEl = $("primary-verdict-title");
  const countEl = $("primary-risky-count");
  const descEl = $("primary-verdict-desc");
  if (countEl) countEl.textContent = highCount;
  if (titleEl) {
    if (highCount === 0) {
      titleEl.innerHTML = 'No files are risky to change right now — codebase is stable. <span id="primary-risky-count" hidden>0</span>';
    } else if (highCount === 1) {
      titleEl.innerHTML = 'This <span id="primary-risky-count">1</span> file is risky to change — here\'s why.';
    } else {
      titleEl.innerHTML = `These <span id="primary-risky-count">${highCount}</span> files are risky to change — here's why.`;
    }
  }
  if (descEl) {
    if (highCount === 0) {
      descEl.textContent = "Branch complexity and caller fan-out are balanced within normal operating thresholds across all analyzed modules.";
    } else {
      descEl.textContent = "High branch complexity combined with caller fan-out means changes to these files carry the widest blast radius across your repository.";
    }
  }
}

export function renderSummary(data, healthData) {
  const h = (healthData && healthData.health_score != null)
    ? { score: healthData.health_score, explanation: healthData.explanation }
    : ((data && data.health) || {});

  const el = $("health-score");
  const badge = $("health-badge");
  const score = h.score != null ? Math.round(h.score) : null;

  if (score == null) {
    if (el) { el.textContent = "—"; el.className = "score-num"; }
    if (badge) { badge.textContent = "Pending"; badge.className = "badge-pill"; }
  } else {
    if (el) {
      el.textContent = score;
      el.className = "score-num " + (score >= 70 ? "is-good" : score >= 40 ? "is-mid" : "is-bad");
    }
    if (badge) {
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
  }

  const healthExplain = $("health-explain");
  if (healthExplain) {
    healthExplain.textContent = h.explanation ||
      (score != null && score >= 70 ? "Architecture is balanced with well-contained modular boundaries." : "High coupling or complexity detected in critical modules.");
  }

  const s = (data && data.stats) || {};
  if ($("count-high")) $("count-high").textContent = s.high || 0;
  if ($("count-med")) $("count-med").textContent = s.medium || 0;
  if ($("count-low")) $("count-low").textContent = s.low || 0;
  if ($("count-files")) $("count-files").textContent = s.total_files || 0;
  if ($("count-violations")) $("count-violations").textContent = (state.violations || []).length;
  if ($("count-cycles")) $("count-cycles").textContent = (state.cycles || []).length;

  // Update primary verdict dynamic headline
  updatePrimaryVerdict();

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

export function renderMemory(mem) {
  const line = $("memory-line");
  if (!line) return;
  if (mem && mem.initialized && mem.latest_run) {
    const when = String(mem.latest_run.timestamp || "").replace("T", " ").slice(0, 16);
    line.textContent = `Last saved ${when}`;
  } else if (mem && mem.reason === "memory_unreadable") {
    line.textContent = "Saved data unreadable";
  } else {
    line.textContent = "Not saved yet";
  }

  const hot = $("hotspot-list");
  if (hot) {
    const hotspots = (mem && mem.hotspots) || [];
    hot.innerHTML = hotspots.length
      ? hotspots.map((h) => {
          const { base } = splitPath(h.file_path);
          return `<li><div>${esc(base)}</div>
            <div class="mini-sub">${h.change_count || 0} changes · ${h.violation_count || 0} issues</div></li>`;
        }).join("")
      : `<li class="mini-empty">Save a scan to track repeat offenders across runs.</li>`;
  }

  const recList = $("rec-list");
  if (recList) {
    const recs = (mem && mem.recommendations) || [];
    recList.innerHTML = recs.length
      ? recs.map((r) => {
          const title = r.message || r.description || r.rule_id || "Suggestion";
          const sub = r.file_path ? splitPath(r.file_path).base : (r.rule_id || "");
          return `<li><div>${esc(title)}</div><div class="mini-sub">${esc(sub)}</div></li>`;
        }).join("")
      : `<li class="mini-empty">Save a scan to generate evolutionary suggestions.</li>`;
  }
}

export function reasonsFor(r) {
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

export function applyFilter() {
  const input = $("filter-input");
  const q = input ? input.value.trim().toLowerCase() : "";
  state.filtered = q
    ? state.risks.filter((r) => String(r.file || r.file_path || "").toLowerCase().includes(q))
    : state.risks.slice();
  const filterQueryText = $("filter-query-text");
  if (filterQueryText && input) filterQueryText.textContent = input.value.trim();
  renderList();
}

export function renderList() {
  const list = $("risk-list");
  if (!list) return;
  const emptyEl = $("list-empty");
  if (emptyEl) emptyEl.hidden = (state.filtered || []).length > 0;

  list.innerHTML = (state.filtered || []).map((r, i) => {
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

export function resetDetail() {
  if ($("detail-title")) $("detail-title").textContent = "Select a file";
  if ($("detail-tabs")) $("detail-tabs").hidden = true;
  if ($("detail-actions")) $("detail-actions").hidden = true;
  if ($("detail-placeholder")) $("detail-placeholder").hidden = false;
  ["tab-why", "tab-code", "tab-brief"].forEach((id) => {
    const el = $(id);
    if (el) el.hidden = true;
  });
}

export function renderDashboard(data, healthData) {
  state.risks = data.risks || [];
  state.selected = null;
  state.briefCache.clear();
  state.fileCache.clear();

  if (data.repo && data.repo.path) {
    state.repo = data.repo.path;
    if ($("repo-input")) $("repo-input").value = data.repo.path;
  }

  if (data.state === "analysis_empty") {
    if ($("error-text")) $("error-text").textContent = data.message || "No Python files found here.";
    show("error-state");
    return;
  }

  if (data.intent && data.intent.matched === false && data.intent.message) {
    banner(data.intent.message);
  }

  renderSummary(data, healthData);
  renderMemory(data.memory || {});
  applyFilter();
  resetDetail();
  show("results");

  if (state.risks.length > 0) {
    const topFile = state.risks[0].file || state.risks[0].file_path || "";
    const studioTarget = $("studio-target-file");
    const auditorFile = $("auditor-file-input");
    if (studioTarget && !studioTarget.value) studioTarget.value = topFile;
    if (auditorFile && !auditorFile.value) auditorFile.value = topFile;
  }
}
