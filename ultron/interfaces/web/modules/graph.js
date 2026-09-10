/**
 * Ultron Web SPA — Pillar 2: Topology Graph Module
 * Layer 2 Feature Module: Force-directed package clustering, pan/zoom, node inspector.
 */

import { state } from "./state.js";
import { $, esc, normPath, splitPath, showToast } from "./api.js";

export let graphSimulationNodes = [];

export function getGraphSimulationNodes() {
  return graphSimulationNodes;
}

export const PKG_PALETTE = [
  "#38bdf8", "#a78bfa", "#f472b6", "#fb923c",
  "#34d399", "#facc15", "#60a5fa", "#e879f9",
  "#4ade80", "#2dd4bf", "#818cf8", "#f87171"
];

export function getPackageColor(pkg) {
  let hash = 0;
  for (let i = 0; i < pkg.length; i++) hash = (hash * 31 + pkg.charCodeAt(i)) >>> 0;
  return PKG_PALETTE[hash % PKG_PALETTE.length];
}

export function renderTopologyGraph(handlers = {}) {
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
      const emptyState = $("graph-empty-state");
      if (emptyState) emptyState.hidden = false;
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

  const emptyState = $("graph-empty-state");
  if (nodes.length === 0) {
    if (emptyState) emptyState.hidden = false;
    const countLabel = $("graph-count-label");
    if (countLabel) countLabel.textContent = "Showing 0 files";
    return;
  } else {
    if (emptyState) emptyState.hidden = true;
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
      openNodeInspector(node, validLinks, handlers);
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

export function setupGraphPanZoom(svg, g) {
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

export function openNodeInspector(node, validLinks, handlers = {}) {
  state.selectedNode = node;
  const ins = $("graph-inspector");
  if (!ins) return;
  ins.hidden = false;

  if ($("inspector-file")) {
    $("inspector-file").textContent = splitPath(node.id).base;
    $("inspector-file").title = node.id;
  }

  const lvl = $("inspector-level");
  if (lvl) {
    lvl.textContent = node.level;
    lvl.className = `badge lv-${node.level}`;
  }

  if ($("inspector-role")) $("inspector-role").textContent = node.role || "Internal";
  if ($("inspector-complexity")) $("inspector-complexity").textContent = node.complexity || 0;
  if ($("inspector-coupling")) $("inspector-coupling").textContent = node.coupling || 0;
  if ($("inspector-impact")) $("inspector-impact").textContent = Number(node.impact_score || 0).toFixed(1);
  if ($("inspector-strategy")) $("inspector-strategy").textContent = node.strategy_display || "Local refactoring is safe; keep public interfaces unchanged.";

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

  if ($("inspector-dep-count")) $("inspector-dep-count").textContent = deps.length;
  if ($("inspector-dep-list")) {
    $("inspector-dep-list").innerHTML = deps.length
      ? deps.slice(0, 10).map((d) => `<li>${esc(d)}</li>`).join("")
      : `<li class="mini-empty">No direct connections mapped in this view.</li>`;
  }
}

export class GraphView {
  constructor(svgId = "topology-svg") {
    this.svgId = svgId;
  }
  render(graphData) {
    state.graphData = graphData;
    renderTopologyGraph();
  }
}
