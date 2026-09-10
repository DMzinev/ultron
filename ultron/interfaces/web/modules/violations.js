/**
 * Ultron Web SPA — Pillar 1: Violations Drawer Module
 * Layer 2 Feature Module: Architectural policy violations grouping, delegation, and fix drafting.
 */

import { state } from "./state.js";
import { $, esc, normPath, parseSeverity, splitPath, showToast } from "./api.js";

export function renderViolations() {
  const list = $("violations-list");
  if (!list) return;

  setupViolationsDelegation();

  if (!state.violations || state.violations.length === 0) {
    list.innerHTML = `<div class="pane-note">No architectural policy violations detected. Codebase complies with active constraints.</div>`;
    return;
  }

  // Enrich each violation with target path, numerical severity, and blast radius from state.risks
  const enriched = state.violations.map((v, idx) => {
    const rawPath = v.filepath || v.source_file || v.file || "";
    const targetPath = normPath(rawPath);
    const sevNum = parseSeverity(v.severity);
    const risk = state.risks.find((r) => {
      const rf = normPath(r.file || r.file_path);
      return rf === targetPath || rf.endsWith("/" + targetPath) || targetPath.endsWith("/" + rf);
    });
    const br = Number(risk?.impact_score != null ? risk.impact_score : (risk?.coupling != null ? risk.coupling : 1.0));
    const safeBlastRadius = Number.isFinite(br) && br > 0 ? Math.max(1.0, br) : 1.0;
    const priority = sevNum * safeBlastRadius;
    const principle = String(v.principle || v.rule_name || v.rule_id || "Architectural Policy").trim();
    return {
      raw: v,
      idx,
      targetPath,
      sevNum,
      safeBlastRadius,
      priority,
      principle,
      observation: v.observation || v.reason || v.message || "",
      consequences: v.consequences || v.remediation || ""
    };
  });

  // Group by principle
  const groupsMap = new Map();
  enriched.forEach((item) => {
    if (!groupsMap.has(item.principle)) {
      groupsMap.set(item.principle, []);
    }
    groupsMap.get(item.principle).push(item);
  });

  // Sort items within each group, and calculate group metrics
  const groups = Array.from(groupsMap.entries()).map(([principle, items]) => {
    items.sort((a, b) =>
      b.priority - a.priority ||
      b.sevNum - a.sevNum ||
      a.targetPath.localeCompare(b.targetPath) ||
      a.idx - b.idx
    );

    const maxPriority = Math.max(...items.map((it) => it.priority));
    const maxSev = Math.max(...items.map((it) => it.sevNum));
    const maxBlast = Math.max(...items.map((it) => it.safeBlastRadius));
    return {
      principle,
      items,
      totalCount: items.length,
      maxPriority,
      maxSev,
      maxBlast
    };
  });

  // Sort groups by maxPriority descending, then maxSev descending, then count, then principle
  groups.sort((a, b) =>
    b.maxPriority - a.maxPriority ||
    b.maxSev - a.maxSev ||
    b.totalCount - a.totalCount ||
    a.principle.localeCompare(b.principle)
  );

  // Render grouped HTML
  list.innerHTML = groups.map((g) => {
    const groupSevClass = g.maxSev >= 3 ? "critical" : g.maxSev >= 2 ? "warning" : "optimal";
    const groupSevLabel = g.maxSev >= 3 ? "Critical" : g.maxSev >= 2 ? "Warning" : "Advisory";

    return `
      <div class="violation-group">
        <div class="violation-group-header">
          <div class="violation-group-title">
            <span class="violation-group-principle">${esc(g.principle)}</span>
            <span class="badge-pill">${g.totalCount} ${g.totalCount === 1 ? "violation" : "violations"}</span>
          </div>
          <span class="badge-pill ${groupSevClass}">Top Sev ${g.maxSev} (${groupSevLabel}) · Max Blast ${g.maxBlast.toFixed(1)}</span>
        </div>
        <div class="violation-group-items">
          ${g.items.map((item) => {
            const sevClass = item.sevNum >= 3 ? "critical" : item.sevNum >= 2 ? "warning" : "optimal";
            const sevLabel = item.sevNum >= 3 ? "Critical" : item.sevNum >= 2 ? "Warning" : "Advisory";
            return `
              <div class="violation-card" data-filepath="${esc(item.targetPath)}" data-vidx="${item.idx}" tabindex="0" role="button" aria-label="View violation in ${esc(item.targetPath)}">
                <div class="violation-top">
                  <span class="violation-principle">${esc(item.principle)}</span>
                  <div class="violation-badges">
                    <span class="badge-pill ${sevClass}">Sev ${item.sevNum} (${sevLabel})</span>
                    <span class="badge-pill" title="Blast radius based on dependency callers and complexity">Blast ${item.safeBlastRadius.toFixed(1)}</span>
                  </div>
                </div>
                <div class="violation-file">📁 ${esc(item.targetPath || "Unspecified file")}</div>
                <div class="violation-obs">${esc(item.observation)}</div>
                ${item.consequences ? `<div class="violation-conseq">Impact: ${esc(item.consequences)}</div>` : ""}
                <div class="violation-actions">
                  <button class="btn btn-ghost btn-sm" data-action="inspect" data-filepath="${esc(item.targetPath)}" title="Open file detail in dashboard">
                    Inspect File →
                  </button>
                  <button class="btn btn-ghost btn-sm" data-action="graph" data-filepath="${esc(item.targetPath)}" title="Locate in topology graph">
                    View in Graph
                  </button>
                  <button class="btn btn-primary btn-sm" data-action="draft-fix" data-filepath="${esc(item.targetPath)}" data-vidx="${item.idx}" title="Pre-fill Agent Studio fix mission">
                    ⚡ Draft Fix Mission
                  </button>
                </div>
              </div>
            `;
          }).join("")}
        </div>
      </div>
    `;
  }).join("");
}

export function setupViolationsDelegation(handlers = {}) {
  const list = $("violations-list");
  if (!list || list._delegated) return;
  list._delegated = true;

  list.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-action]");
    const card = e.target.closest(".violation-card");
    if (btn) {
      e.stopPropagation();
      const action = btn.dataset.action;
      const fpath = btn.dataset.filepath;
      const vidx = parseInt(btn.dataset.vidx, 10);
      if (action === "inspect") {
        if (typeof handlers.onSelectFile === "function") handlers.onSelectFile(fpath);
        else window.dispatchEvent(new CustomEvent("ultron:select-file", { detail: { path: fpath } }));
      } else if (action === "graph") {
        viewInGraph(fpath, handlers);
      } else if (action === "draft-fix") {
        draftFixMission(fpath, vidx, null, handlers);
      }
      return;
    }
    if (card) {
      const fpath = card.dataset.filepath;
      if (fpath) {
        if (typeof handlers.onSelectFile === "function") handlers.onSelectFile(fpath);
        else window.dispatchEvent(new CustomEvent("ultron:select-file", { detail: { path: fpath } }));
      }
    }
  });

  list.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      const card = e.target.closest(".violation-card");
      if (card && card.dataset.filepath) {
        e.preventDefault();
        const fpath = card.dataset.filepath;
        if (typeof handlers.onSelectFile === "function") handlers.onSelectFile(fpath);
        else window.dispatchEvent(new CustomEvent("ultron:select-file", { detail: { path: fpath } }));
      }
    }
  });
}

export function viewInGraph(path, handlers = {}) {
  const norm = normPath(path);
  if (typeof handlers.onSwitchView === "function") handlers.onSwitchView("graph");
  else window.dispatchEvent(new CustomEvent("ultron:switch-view", { detail: { view: "graph" } }));

  setTimeout(() => {
    let node = null;
    if (typeof handlers.findGraphNode === "function") {
      node = handlers.findGraphNode(norm);
    }
    if (!node && state.graphData && state.graphData.nodes) {
      node = state.graphData.nodes.find((n) => {
        const nid = normPath(n.id);
        return nid === norm || nid.endsWith("/" + norm) || norm.endsWith("/" + nid);
      });
    }
    if (node) {
      if (typeof handlers.onOpenNodeInspector === "function") {
        handlers.onOpenNodeInspector(node, state.graphData ? state.graphData.links : []);
      } else {
        window.dispatchEvent(new CustomEvent("ultron:inspect-node", { detail: { node } }));
      }
      showToast(`Highlighted ${splitPath(node.id).base} in graph`);
    } else {
      showToast(`Node for ${splitPath(norm).base} not in current graph view`);
    }
  }, 120);
}

export function draftFixMission(path, vidx, principleOverride, handlers = {}) {
  const norm = normPath(path);
  const v = (vidx != null && state.violations && state.violations[vidx]) ? state.violations[vidx] : null;
  const targetFile = norm || (v && normPath(v.filepath || v.source_file)) || "";
  const targetInput = $("studio-target-file");
  if (targetInput) targetInput.value = targetFile;

  const principle = principleOverride || (v ? (v.principle || v.rule_name || v.rule_id || "Architectural Rule") : "Architectural Policy");
  const sevNum = v ? parseSeverity(v.severity) : 2;
  const sevLabel = sevNum >= 3 ? "Critical" : sevNum >= 2 ? "Warning" : "Advisory";
  const observation = v ? (v.observation || v.reason || v.message || "Constraint threshold exceeded") : "Policy violation detected";
  const consequences = v && v.consequences ? v.consequences : (v && v.remediation ? v.remediation : "");

  const intent = [
    `Fix architectural violation in ${targetFile}:`,
    `- Principle: ${principle}`,
    `- Severity: ${sevLabel} (Severity Rank ${sevNum})`,
    `- Observation: ${observation}`,
    consequences ? `- Impact & Consequences: ${consequences}` : "",
    `- Refactoring Objective: Refactor ${targetFile} to strictly resolve the ${principle} violation while preserving downstream caller contracts and bounded blast radius.`
  ].filter(Boolean).join("\n");

  const intentInput = $("studio-intent");
  if (intentInput) intentInput.value = intent;

  if (typeof handlers.onSwitchView === "function") handlers.onSwitchView("studio");
  else window.dispatchEvent(new CustomEvent("ultron:switch-view", { detail: { view: "studio" } }));

  if (typeof handlers.onCompileMission === "function") {
    handlers.onCompileMission();
  } else {
    window.dispatchEvent(new CustomEvent("ultron:compile-mission"));
  }
  showToast("Fix mission drafted in Agent Studio");
}
