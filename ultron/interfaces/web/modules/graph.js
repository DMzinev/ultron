/**
 * Ultron Web SPA — Interactive Graph Topology Module
 * Campaign 10: Physics Loop, Viewport Pan/Zoom & Detail Drawer Sidebar
 */

import { APIClient } from './api.js';
import { UIManager } from './ui.js';
import { stateStore } from './state.js';

export class GraphView {
    constructor(svgId = "dependency-graph-full") {
        this.svgId = svgId;
        this.nodes = [];
        this.links = [];
        this.simRunning = false;
        this.animFrameId = null;
        this.scale = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.isPanning = false;
        this.panStartX = 0;
        this.panStartY = 0;
        this.chunkAnimFrameId = null;
        this.renderToken = 0;
        this.selectedNodeId = null;
    }

    selectNode(n) {
        if (!n) return;
        this.selectedNodeId = n.id;

        // Compute direct and transitive dependents (blast radius)
        const incoming = (this.links || []).filter(l => (l.target?.id || l.target) === n.id);
        const directDependents = new Set(incoming.map(l => l.source?.id || l.source).filter(Boolean));
        const transitiveDependents = new Set(typeof this.computeTransitiveDependents === 'function' ? this.computeTransitiveDependents(n.id) : []);

        this.nodes.forEach(node => {
            if (!node.element) return;
            const isSelected = node.id === n.id;
            const isDirect = directDependents.has(node.id);
            const isTransitive = transitiveDependents.has(node.id);

            const selBox = node.element.querySelector(".node-selected-box");
            if (selBox) selBox.classList.toggle("hidden", !isSelected);
            const box = node.element.querySelector(".node-box");
            if (box) {
                if (isSelected) {
                    box.setAttribute("stroke", "#38bdf8");
                    box.setAttribute("stroke-width", "3");
                    node.element.style.opacity = "1.0";
                    node.element.style.filter = "drop-shadow(0 0 10px rgba(56, 189, 248, 0.8))";
                } else if (isDirect) {
                    // Direct dependent: amber blast-radius halo
                    box.setAttribute("stroke", "#f59e0b");
                    box.setAttribute("stroke-width", "2.5");
                    node.element.style.opacity = "1.0";
                    node.element.style.filter = "drop-shadow(0 0 8px rgba(245, 158, 11, 0.7))";
                } else if (isTransitive) {
                    // Transitive dependent: red consequence warning
                    box.setAttribute("stroke", "#ef4444");
                    box.setAttribute("stroke-width", "2");
                    node.element.style.opacity = "0.9";
                    node.element.style.filter = "drop-shadow(0 0 6px rgba(239, 68, 68, 0.6))";
                } else {
                    // Unrelated node: dimmed by 75%
                    box.setAttribute("stroke", node.level === "HIGH" ? "#f43f5e" : (node.type === "file" ? "#38bdf8" : "#94a3b8"));
                    box.setAttribute("stroke-width", "1");
                    node.element.style.opacity = "0.25";
                    node.element.style.filter = "none";
                }
            }
        });

        // Highlight affected links
        (this.links || []).forEach(l => {
            if (!l.element) return;
            const src = l.source?.id || l.source;
            const tgt = l.target?.id || l.target;
            const isConnected = tgt === n.id || src === n.id || (transitiveDependents.has(src) && transitiveDependents.has(tgt));
            if (isConnected) {
                l.element.setAttribute("stroke", tgt === n.id ? "#f59e0b" : "#38bdf8");
                l.element.setAttribute("stroke-width", "2.5");
                l.element.style.opacity = "1.0";
            } else {
                l.element.style.opacity = "0.15";
            }
        });
    }

    clearSelection() {
        this.selectedNodeId = null;
        this.nodes.forEach(node => {
            if (!node.element) return;
            const selBox = node.element.querySelector(".node-selected-box");
            if (selBox) selBox.classList.add("hidden");
            const box = node.element.querySelector(".node-box");
            if (box) {
                box.setAttribute("stroke", node.level === "HIGH" ? "#f43f5e" : (node.type === "file" ? "#38bdf8" : "#94a3b8"));
                box.setAttribute("stroke-width", "1.5");
            }
            node.element.style.opacity = "1.0";
            node.element.style.filter = "none";
        });
        (this.links || []).forEach(l => {
            if (!l.element) return;
            l.element.setAttribute("stroke", "#64748b");
            l.element.setAttribute("stroke-width", "1");
            l.element.style.opacity = "0.5";
        });
    }

    focusNode(nodeId) {
        if (!nodeId) return;
        const normId = id => String(id || '').replace(/\\/g, '/');
        const targetId = normId(nodeId);
        const targetNode = this.nodes.find(n => n.id === targetId || n.id.endsWith('/' + targetId) || normId(n.label) === targetId);
        if (!targetNode) return;

        this.selectNode(targetNode);
        this.openNodeDrawer(targetNode);

        const svg = document.getElementById(this.svgId);
        const width = (svg ? svg.clientWidth : 0) || 800;
        const height = (svg ? svg.clientHeight : 0) || 500;

        this.scale = 1.2;
        this.panX = (width / 2) - (targetNode.x * this.scale);
        this.panY = (height / 2) - (targetNode.y * this.scale);
        if (typeof this.applyTransform === 'function') {
            this.applyTransform();
        }
    }

    render(graphData) {
        const svg = document.getElementById(this.svgId);
        if (!svg) return;

        // Campaign 10 & v0.1.7: Clean up previous event listeners & animation frames
        this.destroy();
        this.renderToken++;
        const currentToken = this.renderToken;

        let rawNodes = graphData?.nodes || [];
        let rawLinks = graphData?.links || graphData?.edges || [];

        if (typeof rawNodes === 'object' && !Array.isArray(rawNodes)) {
            rawNodes = Object.values(rawNodes).map(n => ({
                id: n.id,
                label: n.file_path || n.id,
                type: (n.type || 'MODULE').toLowerCase(),
                facts: n.facts || {}
            }));
        }

        if (Array.isArray(rawLinks)) {
            rawLinks = rawLinks.map(l => ({
                source: l.source || l.source_id,
                target: l.target || l.target_id,
                type: l.type || 'DEPENDS_ON'
            }));
        }

        const emptyState = document.getElementById("graph-empty-state");
        if (!rawNodes || rawNodes.length === 0) {
            if (emptyState) emptyState.classList.remove("hidden");
            svg.innerHTML = '<defs><marker id="arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" opacity="0.5" /></marker></defs>';
            return;
        }
        if (emptyState) emptyState.classList.add("hidden");

        if (!graphData._isClustered) {
            this.originalGraphData = graphData;
        }

        // Auto-cluster graphs for larger repos (> 30 nodes) to guarantee 60fps and eliminate visual hairballs
        if (rawNodes.length > 30 && this.level !== "file" && !graphData._isClustered) {
            return this.renderHierarchical(graphData, "system");
        }

        const width = svg.clientWidth || 800;
        const height = svg.clientHeight || 500;

        svg.innerHTML = `
            <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" opacity="0.5" />
                </marker>
            </defs>
            <g id="viewport-transform">
                <g id="viewport-links"></g>
                <g id="viewport-nodes"></g>
            </g>
        `;

        const transformGroup = svg.querySelector("#viewport-transform");
        const linkGroup = svg.querySelector("#viewport-links");
        const nodeGroup = svg.querySelector("#viewport-nodes");

        this.applyTransform = () => {
            const transformGroup = svg.querySelector("#viewport-transform");
            if (transformGroup) {
                transformGroup.setAttribute("transform", `translate(${this.panX},${this.panY}) scale(${this.scale})`);
            }
        };
        this.applyTransform();

        // Viewport Zoom & Pan Handlers
        this.wheelHandler = (e) => {
            e.preventDefault();
            const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
            const newScale = Math.max(0.2, Math.min(4.0, this.scale * zoomFactor));
            const rect = svg.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            this.panX = mouseX - (mouseX - this.panX) * (newScale / this.scale);
            this.panY = mouseY - (mouseY - this.panY) * (newScale / this.scale);
            this.scale = newScale;
            this.applyTransform();
        };
        svg.addEventListener("wheel", this.wheelHandler, { passive: false });

        this.mouseDownHandler = (e) => {
            if (e.button === 0 && !e.target.closest('.graph-node-group')) {
                this.isPanning = true;
                this.panStartX = e.clientX - this.panX;
                this.panStartY = e.clientY - this.panY;
                svg.style.cursor = "grabbing";
            }
        };
        svg.addEventListener("mousedown", this.mouseDownHandler);

        this.clickHandler = (e) => {
            if (!e.target.closest('.graph-node-group')) {
                this.clearSelection();
            }
        };
        svg.addEventListener("click", this.clickHandler);

        this.mouseMoveHandler = (e) => {
            if (this.isPanning) {
                this.panX = e.clientX - this.panStartX;
                this.panY = e.clientY - this.panStartY;
                this.applyTransform();
            }
        };
        window.addEventListener("mousemove", this.mouseMoveHandler);

        this.mouseUpHandler = () => {
            if (this.isPanning) {
                this.isPanning = false;
                svg.style.cursor = "grab";
            }
            if (this.nodes) {
                this.nodes.forEach(n => { n.dragged = false; });
            }
        };
        window.addEventListener("mouseup", this.mouseUpHandler);

        // Process Nodes & Links with POSIX Path Normalizer
        const normId = id => String(id || '').replace(/\\/g, '/');

        // Structured Cache Key: repoId + snapId + modelHash + layoutMode + svgId
        const repoId = graphData?.repository_id || stateStore?.repository_id || stateStore?.repoPath || 'default_repo';
        const snapId = graphData?.snapshot_id || stateStore?.snapshot_id || 'default_snap';
        const modelHash = graphData?.model_hash || stateStore?.model_hash || 'default_hash';
        const layoutMode = this.level || (graphData?._isClustered ? 'cluster' : 'system');
        const svgId = this.svgId || 'dependency-graph-full';

        let cachedRelative = null;
        try {
            if (stateStore && typeof stateStore.getGraphLayout === 'function') {
                cachedRelative = stateStore.getGraphLayout(repoId, snapId, modelHash, layoutMode, svgId);
            }
            if (!cachedRelative && window._ULTRON_LAYOUT_CACHE) {
                const graphHash = (rawNodes || []).map(n => normId(n.id || n.label)).sort().join("|");
                cachedRelative = window._ULTRON_LAYOUT_CACHE[`ultron_layout_${graphHash}_${this.svgId}`];
            }
        } catch (_) {}

        this.isLayoutCached = !!cachedRelative;
        this.cacheContext = { repoId, snapId, modelHash, layoutMode, svgId };

        this.nodes = rawNodes.map(n => {
            const nid = normId(n.id);
            const relPos = cachedRelative && (cachedRelative[nid] || cachedRelative[n.id]);
            const px = (relPos && typeof relPos.rx === 'number') ? relPos.rx * width : (width / 2 + (Math.random() - 0.5) * 350);
            const py = (relPos && typeof relPos.ry === 'number') ? relPos.ry * height : (height / 2 + (Math.random() - 0.5) * 350);
            const rawLabel = String(n.label || n.id || '');
            const w = Math.min(280, Math.max(140, rawLabel.length * 7.5 + 24));
            const h = 42;
            return {
                ...n,
                id: nid,
                x: px,
                y: py,
                vx: 0,
                vy: 0,
                w: w,
                h: h,
                r: Math.max(w, h) / 2,
                visible: true
            };
        });

        // Save relative coordinates into layout cache if already known
        if (!this.isLayoutCached) {
            try {
                const relMap = {};
                this.nodes.forEach(n => {
                    relMap[n.id] = { rx: n.x / width, ry: n.y / height };
                });
                if (stateStore && typeof stateStore.setGraphLayout === 'function') {
                    stateStore.setGraphLayout(repoId, snapId, modelHash, layoutMode, svgId, relMap);
                }
            } catch (_) {}
        }

        // O(1) Map Link Lookup
        const nodeMap = new Map(this.nodes.map(n => [n.id, n]));
        let unresolvableCount = 0;

        this.links = rawLinks.map(l => {
            const srcId = normId(l.source);
            const tgtId = normId(l.target);
            const srcNode = nodeMap.get(srcId);
            const tgtNode = nodeMap.get(tgtId);
            if (!srcNode || !tgtNode) unresolvableCount++;
            return {
                ...l,
                source: srcId,
                target: tgtId,
                sourceNode: srcNode,
                targetNode: tgtNode,
                visible: true
            };
        }).filter(l => l.sourceNode && l.targetNode);

        if (unresolvableCount > 0) {
            console.debug(`[Ultron GraphView] Filtered out ${unresolvableCount} unresolvable link(s) for SVG ID: ${this.svgId}`);
        }

        // Chunked Asynchronous DOM Rendering (50 items per frame) to prevent UI thread freezing
        const CHUNK_SIZE = 50;
        let linkIdx = 0;
        let nodeIdx = 0;

        const renderChunks = () => {
            if (this.renderToken !== currentToken) return;

            // Render batch of links
            if (linkIdx < this.links.length) {
                const fragment = document.createDocumentFragment();
                const end = Math.min(linkIdx + CHUNK_SIZE, this.links.length);
                for (let i = linkIdx; i < end; i++) {
                    const l = this.links[i];
                    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                    line.setAttribute("class", `graph-link ${l.type}`);
                    if (l.type === "call") line.setAttribute("marker-end", "url(#arrow)");
                    line.setAttribute("x1", l.sourceNode.x);
                    line.setAttribute("y1", l.sourceNode.y);
                    line.setAttribute("x2", l.targetNode.x);
                    line.setAttribute("y2", l.targetNode.y);
                    l.element = line;
                    fragment.appendChild(line);
                }
                linkGroup.appendChild(fragment);
                linkIdx = end;
                this.chunkAnimFrameId = requestAnimationFrame(renderChunks);
                return;
            }

            // Render batch of nodes
            if (nodeIdx < this.nodes.length) {
                const fragment = document.createDocumentFragment();
                const end = Math.min(nodeIdx + CHUNK_SIZE, this.nodes.length);
                for (let i = nodeIdx; i < end; i++) {
                    const n = this.nodes[i];
                    const rawLabel = String(n.label || n.id || '');
                    const w = Math.min(280, Math.max(140, rawLabel.length * 7.5 + 24));
                    const h = 42;
                    n.w = w;
                    n.h = h;
                    n.r = Math.max(w, h) / 2;

                    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
                    g.setAttribute("class", "graph-node-group");
                    g.setAttribute("transform", `translate(${n.x},${n.y})`);

                    let color = "#94a3b8";
                    if (n.level === "HIGH") color = "#f43f5e";
                    else if (n.type === "file") color = "#38bdf8";
                    else if (n.type === "function") color = "#c084fc";

                    const selRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
                    selRect.setAttribute("class", "node-selected-box hidden");
                    selRect.setAttribute("x", -w / 2 - 4);
                    selRect.setAttribute("y", -h / 2 - 4);
                    selRect.setAttribute("width", w + 8);
                    selRect.setAttribute("height", h + 8);
                    selRect.setAttribute("rx", "8");
                    selRect.setAttribute("fill", "none");
                    selRect.setAttribute("stroke", "#38bdf8");
                    selRect.setAttribute("stroke-width", "1.5");
                    selRect.setAttribute("stroke-dasharray", "4,2");
                    g.appendChild(selRect);

                    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
                    rect.setAttribute("class", "node-box");
                    rect.setAttribute("x", -w / 2);
                    rect.setAttribute("y", -h / 2);
                    rect.setAttribute("width", w);
                    rect.setAttribute("height", h);
                    rect.setAttribute("rx", "6");
                    rect.setAttribute("fill", "rgba(15, 23, 42, 0.85)");
                    rect.setAttribute("stroke", color);
                    rect.setAttribute("stroke-width", "1.5");
                    rect.style.cursor = "pointer";
                    rect.style.transition = "stroke-width 0.15s, stroke 0.15s";
                    g.appendChild(rect);

                    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
                    title.textContent = `${n.id} (${n.complexity || 1} complexity, ${n.coupling || 0} callers)`;
                    g.appendChild(title);

                    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
                    text.setAttribute("class", "node-label");
                    text.setAttribute("x", "0");
                    text.setAttribute("y", "4");
                    text.setAttribute("fill", "#f8fafc");
                    text.setAttribute("font-size", "11px");
                    text.setAttribute("font-family", "JetBrains Mono, monospace");
                    text.setAttribute("text-anchor", "middle");
                    text.setAttribute("pointer-events", "none");
                    let displayLabel = rawLabel;
                    if (displayLabel.length > 24) {
                        displayLabel = displayLabel.substring(0, 10) + "..." + displayLabel.substring(displayLabel.length - 11);
                    }
                    text.textContent = displayLabel;
                    g.appendChild(text);

                    g.style.cursor = "pointer";
                    g.addEventListener("click", (e) => {
                        e.stopPropagation();
                        if (n.isCluster) {
                            this.drillDownCluster(n);
                            return;
                        }
                        this.selectNode(n);
                        this.openNodeDrawer(n);
                    });

                    rect.addEventListener("mouseenter", () => {
                        if (this.selectedNodeId !== n.id) {
                            rect.setAttribute("stroke-width", "2.5");
                            rect.setAttribute("fill", "rgba(30, 41, 59, 0.95)");
                        }
                    });
                    rect.addEventListener("mouseleave", () => {
                        if (this.selectedNodeId !== n.id) {
                            rect.setAttribute("stroke-width", "1.5");
                            rect.setAttribute("fill", "rgba(15, 23, 42, 0.85)");
                        }
                    });

                    rect.addEventListener("mousedown", (e) => {
                        n.dragged = true;
                    });

                    fragment.appendChild(g);
                    n.element = g;
                }
                nodeGroup.appendChild(fragment);
                nodeIdx = end;
                this.chunkAnimFrameId = requestAnimationFrame(renderChunks);
                return;
            }            // Finished DOM Chunking
            this.chunkAnimFrameId = null;
            if (this.isLayoutCached) {
                // Instantly apply pre-calculated coordinates without running simulation loop
                this.nodes.forEach(n => {
                    if (n.element) n.element.setAttribute("transform", `translate(${n.x},${n.y})`);
                });
                this.links.forEach(l => {
                    if (l.element && l.sourceNode && l.targetNode) {
                        const p1 = this.getBoxEdgeIntersection(l.sourceNode, l.targetNode);
                        const p2 = this.getBoxEdgeIntersection(l.targetNode, l.sourceNode);
                        l.element.setAttribute("x1", p1.x);
                        l.element.setAttribute("y1", p1.y);
                        l.element.setAttribute("x2", p2.x);
                        l.element.setAttribute("y2", p2.y);
                    }
                });
            } else {
                this.startPhysicsLoop(width, height);
            }
        };

        this.chunkAnimFrameId = requestAnimationFrame(renderChunks);
    }

    computeTransitiveDependents(nodeId) {
        const visited = new Set();
        const queue = [nodeId];
        while (queue.length > 0) {
            const curr = queue.shift();
            // incoming links (who imports/calls curr)
            const incoming = (this.links || []).filter(l => (l.target?.id || l.target) === curr);
            for (const link of incoming) {
                const src = link.source?.id || link.source;
                if (src && src !== nodeId && !visited.has(src)) {
                    visited.add(src);
                    queue.push(src);
                }
            }
        }
        return Array.from(visited);
    }

    computeTransitiveDependencies(nodeId) {
        const visited = new Set();
        const queue = [nodeId];
        while (queue.length > 0) {
            const curr = queue.shift();
            // outgoing links (who curr imports/calls)
            const outgoing = (this.links || []).filter(l => (l.source?.id || l.source) === curr);
            for (const link of outgoing) {
                const tgt = link.target?.id || link.target;
                if (tgt && tgt !== nodeId && !visited.has(tgt)) {
                    visited.add(tgt);
                    queue.push(tgt);
                }
            }
        }
        return Array.from(visited);
    }

    openNodeDrawer(n) {
        const drawer = document.getElementById("graph-detail-drawer") || document.getElementById("graph-node-drawer");
        if (!drawer) return;
        drawer.classList.remove("hidden");

        // Strict Edge Semantics (A -> B means A imports/depends on B)
        // Outgoing edges from n = direct dependencies of n (what n imports)
        // Incoming edges to n = direct dependents of n (who imports n)
        const incoming = (this.links || []).filter(l => (l.target?.id || l.target) === n.id);
        const outgoing = (this.links || []).filter(l => (l.source?.id || l.source) === n.id);
        const directDependentsCount = incoming.length;
        const directDependenciesCount = outgoing.length;
        const directDependentNames = incoming.map(l => l.source?.id || l.source).filter(Boolean);

        // Transitive downstream impact radius (who breaks if n changes)
        const transitiveDependents = this.computeTransitiveDependents(n.id);
        const transitiveImpactRadius = transitiveDependents.length;

        const impactScore = Number(n.impact_score) || 0;
        let changeImpactText = transitiveImpactRadius > 0
            ? `Changing this module is likely to affect ${transitiveImpactRadius} downstream component(s) (${directDependentsCount} direct).`
            : "Changing this module has localized impact with no detected downstream dependents.";

        let whatCouldBreakText = transitiveDependents.length > 0
            ? `${transitiveDependents.slice(0, 3).join(", ")}${transitiveDependents.length > 3 ? ` (+${transitiveDependents.length - 3} more)` : ""}`
            : "None (isolated leaf component)";

        const allCycles = this.detectCycles();
        const cycleInvolvement = allCycles.some(c => c.includes(n.id)) ? "Active circular loop" : "None";
        const evidenceText = `Dependencies: ${directDependenciesCount} · Dependents: ${directDependentsCount} · Transitive Blast Radius: ${transitiveImpactRadius} · Cycle: ${cycleInvolvement}`;

        UIManager.setElementText("drawer-node-label", n.label || n.id);
        UIManager.setElementText("drawer-node-type", n.type === "file" ? "📁 File Node" : "⚡ Function Node");
        UIManager.setElementText("drawer-impact-score", impactScore.toFixed(2));
        UIManager.setElementText("drawer-complexity", n.complexity || 1);
        UIManager.setElementText("drawer-coupling", n.coupling || 0);
        UIManager.setElementText("drawer-dependents-count", directDependentsCount);
        UIManager.setElementText("drawer-dependencies-count", directDependenciesCount);
        UIManager.setElementText("drawer-change-impact", changeImpactText);
        UIManager.setElementText("drawer-what-could-break", whatCouldBreakText);
        UIManager.setElementText("drawer-consequence-evidence", evidenceText);
        UIManager.setElementText("drawer-strategy", n.strategy_display || "Safe localized modifications");
        UIManager.setElementText("drawer-ai-content", "Click 'Explain with AI' for grounded architectural feedback.");

        // Check if node is part of a circular dependency cycle
        const cycleAlertBox = document.getElementById("drawer-cycle-alert-box");
        const cycleSeqEl = document.getElementById("drawer-cycle-sequence");
        const cycleRecEl = document.getElementById("drawer-cycle-recommendation");
        if (cycleAlertBox) {
            const relevantCycle = allCycles.find(c => c.includes(n.id));
            if (relevantCycle) {
                cycleAlertBox.classList.remove("hidden");
                if (cycleSeqEl) cycleSeqEl.textContent = relevantCycle.join(" -> ");
                if (cycleRecEl) cycleRecEl.textContent = `Break cycle by introducing interface or event bus between '${relevantCycle[0]}' and '${relevantCycle[1] || relevantCycle[0]}'.`;
            } else {
                cycleAlertBox.classList.add("hidden");
            }
        }

        const btnExplain = document.getElementById("btn-drawer-ai-critique") || document.getElementById("btn-drawer-ai-explain");
        if (btnExplain) {
            btnExplain.onclick = async () => {
                UIManager.setElementText("drawer-ai-content", "Querying Ultron AI critique...");
                try {
                    const res = await APIClient.post("/api/v1/ai/critique", {
                        file: n.file || n.id,
                        node_id: n.id,
                        complexity: n.complexity || 1,
                        coupling: n.coupling || 0,
                        impact_score: impactScore
                    });
                    if (res.success && res.data?.critique) {
                        UIManager.setElementText("drawer-ai-content", res.data.critique);
                    } else if (res.success && Array.isArray(res.data?.actionable_advice)) {
                        UIManager.setElementText("drawer-ai-content", res.data.actionable_advice.join("\n"));
                    } else {
                        const fallbackDetail = res.error ? ` (${res.error})` : "";
                        UIManager.setElementText("drawer-ai-content", `Offline Fallback${fallbackDetail}: High complexity (${n.complexity || 1}), Coupling (${n.coupling || 0}). Enforce Single Responsibility (SRP) and modular isolation.`);
                    }
                } catch (err) {
                    UIManager.setElementText("drawer-ai-content", `Offline Fallback: Complexity (${n.complexity || 1}), Coupling (${n.coupling || 0}). Enforce Single Responsibility (SRP).`);
                }
            };
        }

        const btnFocus = document.getElementById("btn-drawer-focus-node");
        if (btnFocus) {
            btnFocus.onclick = () => {
                this.focusNode(n.id);
                UIManager.showToast(`Focused node: ${n.label || n.id}`);
            };
        }

        const btnPushAgent = document.getElementById("btn-drawer-push-agent");
        if (btnPushAgent) {
            btnPushAgent.onclick = () => {
                const navAgent = document.getElementById("nav-prompt") || document.getElementById("nav-agent") || document.querySelector('[data-tab="prompt-tab"]') || document.querySelector('[data-tab="agent-tab"]');
                if (navAgent) navAgent.click();
                UIManager.showToast(`Switched to Agent Context for: ${n.label || n.id}`);
                const promptTarget = document.getElementById("prompt-target-file") || document.getElementById("prompt-files");
                if (promptTarget) {
                    promptTarget.value = n.file || n.id;
                }
                const promptIntent = document.getElementById("prompt-intent");
                if (promptIntent) {
                    promptIntent.value = `Focus on node: ${n.id} (${n.label || n.id}) - Strategy: ${n.strategy_display || "Local refactor"}`;
                    const btnHandoff = document.getElementById("btn-generate-prompt") || document.getElementById("btn-generate-handoff");
                    if (btnHandoff) btnHandoff.click();
                }
            };
        }

        const btnClose = drawer.querySelector(".btn-close") || document.getElementById("btn-close-drawer");
        if (btnClose) {
            btnClose.onclick = () => drawer.classList.add("hidden");
        }
    }

    startPhysicsLoop(width, height) {
        this.simRunning = true;
        const numNodes = this.nodes.length;
        if (numNodes === 0) return;

        const kRepulsion = Math.max(2500, Math.min(numNodes * 80, 10000));
        let alpha = 1.0;
        let iteration = 0;
        const MAX_ITERATIONS = 30;

        const step = () => {
            if (!this.simRunning) return;
            iteration++;
            alpha *= 0.90;

            if (alpha < 0.005 || iteration >= MAX_ITERATIONS) {
                // Auto-freeze simulation at equilibrium to guarantee 0% background CPU and butter-smooth 60fps
                this.simRunning = false;
                if (this.animFrameId) cancelAnimationFrame(this.animFrameId);

                // Save equilibrium layout to stateStore
                try {
                    if (this.cacheContext && stateStore && typeof stateStore.setGraphLayout === 'function') {
                        const relMap = {};
                        this.nodes.forEach(n => {
                            relMap[n.id] = { rx: n.x / width, ry: n.y / height };
                        });
                        const { repoId, snapId, modelHash, layoutMode, svgId } = this.cacheContext;
                        stateStore.setGraphLayout(repoId, snapId, modelHash, layoutMode, svgId, relMap);
                    }
                } catch (_) {}
                return;
            }

            for (let i = 0; i < numNodes; i++) {
                for (let j = i + 1; j < numNodes; j++) {
                    const n1 = this.nodes[i];
                    const n2 = this.nodes[j];
                    let dx = n2.x - n1.x;
                    let dy = n2.y - n1.y;
                    let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                    let minDist = n1.r + n2.r + 35;

                    if (dist < minDist) {
                        let force = ((minDist - dist) / dist) * 0.4 * alpha;
                        let fx = dx * force;
                        let fy = dy * force;
                        if (!n1.dragged) { n1.vx -= fx; n1.vy -= fy; }
                        if (!n2.dragged) { n2.vx += fx; n2.vy += fy; }
                    }

                    let force = (kRepulsion / (dist * dist)) * alpha;
                    let fx = (dx / dist) * force;
                    let fy = (dy / dist) * force;
                    if (!n1.dragged) { n1.vx -= fx * 0.05; n1.vy -= fy * 0.05; }
                    if (!n2.dragged) { n2.vx += fx * 0.05; n2.vy += fy * 0.05; }
                }
            }

            this.links.forEach(l => {
                let dx = l.targetNode.x - l.sourceNode.x;
                let dy = l.targetNode.y - l.sourceNode.y;
                let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                let force = (dist - 100) * 0.03 * alpha;
                let fx = (dx / dist) * force;
                let fy = (dy / dist) * force;
                if (!l.sourceNode.dragged) { l.sourceNode.vx += fx; l.sourceNode.vy += fy; }
                if (!l.targetNode.dragged) { l.targetNode.vx -= fx; l.targetNode.vy -= fy; }
            });

            this.nodes.forEach(n => {
                if (!n.dragged) {
                    n.vx *= 0.85;
                    n.vy *= 0.85;
                    n.x += n.vx;
                    n.y += n.vy;
                }
                if (n.element) {
                    n.element.setAttribute("transform", `translate(${n.x},${n.y})`);
                }
            });

            this.links.forEach(l => {
                if (l.element && l.sourceNode && l.targetNode) {
                    const p1 = this.getBoxEdgeIntersection(l.sourceNode, l.targetNode);
                    const p2 = this.getBoxEdgeIntersection(l.targetNode, l.sourceNode);
                    l.element.setAttribute("x1", p1.x);
                    l.element.setAttribute("y1", p1.y);
                    l.element.setAttribute("x2", p2.x);
                    l.element.setAttribute("y2", p2.y);
                }
            });

            this.animFrameId = requestAnimationFrame(step);
        };

        step();
    }

    getBoxEdgeIntersection(node, target) {
        if (!node || !target) return { x: 0, y: 0 };
        const hw = (node.w || 140) / 2;
        const hh = (node.h || 42) / 2;
        const dx = target.x - node.x;
        const dy = target.y - node.y;
        if (Math.abs(dx) < 1e-6 && Math.abs(dy) < 1e-6) {
            return { x: node.x, y: node.y };
        }
        const absDx = Math.abs(dx);
        const absDy = Math.abs(dy);
        let scale = 1;
        if (absDx * hh > absDy * hw) {
            scale = hw / (absDx || 1e-6);
        } else {
            scale = hh / (absDy || 1e-6);
        }
        return {
            x: node.x + dx * scale,
            y: node.y + dy * scale
        };
    }

    zoomIn() {
        this.scale = Math.min(4.0, this.scale * 1.25);
        if (typeof this.applyTransform === 'function') this.applyTransform();
    }

    zoomOut() {
        this.scale = Math.max(0.2, this.scale * 0.8);
        if (typeof this.applyTransform === 'function') this.applyTransform();
    }

    resetView() {
        this.scale = 1.0;
        this.panX = 0;
        this.panY = 0;
        if (typeof this.applyTransform === 'function') this.applyTransform();
    }

    fitToScreen() {
        if (!this.nodes || this.nodes.length === 0) return;
        const svg = document.getElementById(this.svgId);
        const width = (svg ? svg.clientWidth : 0) || 800;
        const height = (svg ? svg.clientHeight : 0) || 500;

        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        const visibleNodes = this.nodes.filter(n => !n.element || (n.element.style.display !== "none" && n.element.style.opacity !== "0.15"));
        const targetNodes = visibleNodes.length > 0 ? visibleNodes : this.nodes;
        targetNodes.forEach(n => {
            const hw = (n.w || 140) / 2;
            const hh = (n.h || 42) / 2;
            if (n.x - hw < minX) minX = n.x - hw;
            if (n.x + hw > maxX) maxX = n.x + hw;
            if (n.y - hh < minY) minY = n.y - hh;
            if (n.y + hh > maxY) maxY = n.y + hh;
        });
        const graphWidth = (maxX - minX) || 1;
        const graphHeight = (maxY - minY) || 1;
        const padding = 60;
        const scaleX = (width - padding * 2) / graphWidth;
        const scaleY = (height - padding * 2) / graphHeight;
        this.scale = Math.max(0.2, Math.min(2.0, Math.min(scaleX, scaleY)));
        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;
        this.panX = (width / 2) - (centerX * this.scale);
        this.panY = (height / 2) - (centerY * this.scale);
        if (typeof this.applyTransform === 'function') {
            this.applyTransform();
        }
    }

    filterNodes(query) {
        const q = (query || "").trim().toLowerCase();
        const matchingNodeIds = new Set();
        let matchCount = 0;

        this.nodes.forEach(n => {
            if (!n.element) return;
            const labelText = (n.label || n.id || "").toLowerCase();
            const matches = !q || labelText.includes(q);
            n.element.style.opacity = matches ? "1" : "0.15";
            if (matches) {
                matchingNodeIds.add(n.id);
                matchCount++;
            }
        });

        this.links.forEach(l => {
            if (!l.element) return;
            const srcId = typeof l.source === 'object' ? l.source.id : l.source;
            const tgtId = typeof l.target === 'object' ? l.target.id : l.target;
            const matches = !q || (matchingNodeIds.has(srcId) && matchingNodeIds.has(tgtId));
            l.element.style.opacity = matches ? "0.6" : "0.08";
        });

        const emptyEl = document.getElementById("graph-empty-state");
        if (emptyEl) {
            emptyEl.classList.toggle("hidden", matchCount > 0 || this.nodes.length === 0);
        }
        return matchCount;
    }

    filterByRiskThreshold(minScore = 0.0) {
        const threshold = Number(minScore) || 0.0;
        const visibleNodeIds = new Set();
        let visibleCount = 0;

        this.nodes.forEach(n => {
            if (!n.element) return;
            const score = Number(n.impact_score) || Number(n.facts?.impact_score) || 0;
            const matches = score >= threshold;
            n.element.style.display = matches ? "" : "none";
            if (matches) {
                visibleNodeIds.add(n.id);
                visibleCount++;
            }
        });

        this.links.forEach(l => {
            if (!l.element) return;
            const srcId = typeof l.source === 'object' ? l.source.id : l.source;
            const tgtId = typeof l.target === 'object' ? l.target.id : l.target;
            const matches = visibleNodeIds.has(srcId) && visibleNodeIds.has(tgtId);
            l.element.style.display = matches ? "" : "none";
        });

        const emptyEl = document.getElementById("graph-empty-state");
        if (emptyEl) {
            emptyEl.classList.toggle("hidden", visibleCount > 0 || this.nodes.length === 0);
        }
        return visibleCount;
    }

    filterByRiskTier(tier = "all") {
        let t = (tier || "all").trim().toUpperCase();
        if (t === "MED") t = "MEDIUM";
        const matchingNodeIds = new Set();
        let matchCount = 0;

        this.nodes.forEach(n => {
            if (!n.element) return;
            let nodeTier = (n.level || n.risk_tier || n.facts?.risk_tier || "LOW").toUpperCase();
            if (nodeTier === "MED") nodeTier = "MEDIUM";
            const matches = t === "ALL" || nodeTier === t;
            n.element.style.opacity = matches ? "1" : "0.15";
            if (matches) {
                matchingNodeIds.add(n.id);
                matchCount++;
            }
        });

        this.links.forEach(l => {
            if (!l.element) return;
            const srcId = typeof l.source === 'object' ? l.source.id : l.source;
            const tgtId = typeof l.target === 'object' ? l.target.id : l.target;
            const matches = t === "ALL" || (matchingNodeIds.has(srcId) && matchingNodeIds.has(tgtId));
            l.element.style.opacity = matches ? "0.6" : "0.08";
        });

        const emptyEl = document.getElementById("graph-empty-state");
        if (emptyEl) {
            emptyEl.classList.toggle("hidden", matchCount > 0 || this.nodes.length === 0);
        }
        return matchCount;
    }

    filterByType(nodeType = "all") {
        const targetType = (nodeType || "all").trim().toLowerCase();
        const matchingNodeIds = new Set();
        let matchCount = 0;

        this.nodes.forEach(n => {
            if (!n.element) return;
            const actualType = (n.type || n.kind || (n.id.endsWith(".py") ? "file" : "module")).toLowerCase();
            const matches = targetType === "all" || actualType === targetType || (targetType === "file" && n.id.includes("."));
            n.element.style.opacity = matches ? "1" : "0.15";
            if (matches) {
                matchingNodeIds.add(n.id);
                matchCount++;
            }
        });

        this.links.forEach(l => {
            if (!l.element) return;
            const srcId = typeof l.source === 'object' ? l.source.id : l.source;
            const tgtId = typeof l.target === 'object' ? l.target.id : l.target;
            const matches = targetType === "all" || (matchingNodeIds.has(srcId) && matchingNodeIds.has(tgtId));
            l.element.style.opacity = matches ? "0.6" : "0.08";
        });

        const emptyEl = document.getElementById("graph-empty-state");
        if (emptyEl) {
            emptyEl.classList.toggle("hidden", matchCount > 0 || this.nodes.length === 0);
        }
        return matchCount;
    }

    highlightBlastRadius(nodeId) {
        if (!nodeId) return null;
        const normId = id => String(id || '').replace(/\\/g, '/');
        const target = normId(nodeId);

        // Compute upstream (inbound callers) and downstream (outbound dependents)
        const upstream = new Set();
        const downstream = new Set();

        const inboundMap = new Map();
        const outboundMap = new Map();

        this.links.forEach(l => {
            const src = normId(typeof l.source === 'object' ? l.source.id : l.source);
            const tgt = normId(typeof l.target === 'object' ? l.target.id : l.target);
            if (!src || !tgt) return;

            if (!outboundMap.has(src)) outboundMap.set(src, []);
            outboundMap.get(src).push(tgt);

            if (!inboundMap.has(tgt)) inboundMap.set(tgt, []);
            inboundMap.get(tgt).push(src);
        });

        // Downstream BFS (outbound from target)
        const qDown = [target];
        const visitedDown = new Set([target]);
        while (qDown.length > 0) {
            const curr = qDown.shift();
            const neighbors = outboundMap.get(curr) || [];
            neighbors.forEach(nxt => {
                if (!visitedDown.has(nxt)) {
                    visitedDown.add(nxt);
                    downstream.add(nxt);
                    qDown.push(nxt);
                }
            });
        }

        // Upstream BFS (inbound to target)
        const qUp = [target];
        const visitedUp = new Set([target]);
        while (qUp.length > 0) {
            const curr = qUp.shift();
            const neighbors = inboundMap.get(curr) || [];
            neighbors.forEach(nxt => {
                if (!visitedUp.has(nxt)) {
                    visitedUp.add(nxt);
                    upstream.add(nxt);
                    qUp.push(nxt);
                }
            });
        }

        // Apply visual styling to nodes
        this.nodes.forEach(n => {
            if (!n.element) return;
            const nid = normId(n.id);
            const box = n.element.querySelector('.node-box');
            if (!box) return;

            if (nid === target) {
                n.element.style.opacity = '1.0';
                box.setAttribute('stroke', '#38bdf8');
                box.setAttribute('stroke-width', '3');
            } else if (downstream.has(nid)) {
                n.element.style.opacity = '1.0';
                box.setAttribute('stroke', '#f59e0b');
                box.setAttribute('stroke-width', '2.5');
            } else if (upstream.has(nid)) {
                n.element.style.opacity = '1.0';
                box.setAttribute('stroke', '#38bdf8');
                box.setAttribute('stroke-width', '2.5');
            } else {
                n.element.style.opacity = '0.15';
            }
        });

        // Apply styling to links
        this.links.forEach(l => {
            if (!l.element) return;
            const src = normId(typeof l.source === 'object' ? l.source.id : l.source);
            const tgt = normId(typeof l.target === 'object' ? l.target.id : l.target);

            const isDownstreamEdge = (src === target || downstream.has(src)) && downstream.has(tgt);
            const isUpstreamEdge = (tgt === target || upstream.has(tgt)) && upstream.has(src);

            if (isDownstreamEdge) {
                l.element.style.opacity = '1.0';
                l.element.setAttribute('stroke', '#f59e0b');
                l.element.setAttribute('stroke-width', '2.5');
            } else if (isUpstreamEdge) {
                l.element.style.opacity = '1.0';
                l.element.setAttribute('stroke', '#38bdf8');
                l.element.setAttribute('stroke-width', '2.5');
            } else {
                l.element.style.opacity = '0.1';
            }
        });

        const totalImpactSet = new Set([...upstream, ...downstream]);

        return {
            targetId: target,
            upstreamCount: upstream.size,
            downstreamCount: downstream.size,
            totalImpact: totalImpactSet.size
        };
    }

    clearBlastRadius() {
        this.nodes.forEach(n => {
            if (!n.element) return;
            n.element.style.opacity = '1.0';
            const isSelected = n.id === this.selectedNodeId;
            const selBox = n.element.querySelector('.node-selected-box');
            if (selBox) selBox.classList.toggle('hidden', !isSelected);
            const box = n.element.querySelector('.node-box');
            if (box) {
                box.setAttribute('stroke', isSelected ? '#38bdf8' : (n.level === 'HIGH' ? '#f43f5e' : (n.type === 'file' ? '#38bdf8' : '#94a3b8')));
                box.setAttribute('stroke-width', isSelected ? '2.5' : '1.5');
            }
        });

        this.links.forEach(l => {
            if (!l.element) return;
            l.element.style.opacity = '0.6';
            l.element.setAttribute('stroke', '#475569');
            l.element.setAttribute('stroke-width', '1.5');
        });
    }

    detectCycles() {
        const adj = new Map();
        this.nodes.forEach(n => adj.set(n.id, new Set()));
        this.links.forEach(l => {
            const srcId = (l.source && l.source.id) || l.source;
            const tgtId = (l.target && l.target.id) || l.target;
            if (adj.has(srcId) && adj.has(tgtId)) {
                adj.get(srcId).add(tgtId);
            }
        });

        const discovered = [];
        const visitedInPath = new Set();

        const dfs = (current, start, path) => {
            const neighbors = Array.from(adj.get(current) || []);
            for (const neighbor of neighbors) {
                if (neighbor === start) {
                    discovered.push([...path, start]);
                } else if (!visitedInPath.has(neighbor) && neighbor >= start) {
                    visitedInPath.add(neighbor);
                    path.push(neighbor);
                    dfs(neighbor, start, path);
                    path.pop();
                    visitedInPath.delete(neighbor);
                }
            }
        };

        const allNodeIds = Array.from(adj.keys()).sort();
        allNodeIds.forEach(startNode => {
            visitedInPath.add(startNode);
            dfs(startNode, startNode, [startNode]);
            visitedInPath.delete(startNode);
        });

        return discovered;
    }

    highlightCycles(cycles) {
        if (!Array.isArray(cycles) || cycles.length === 0) {
            cycles = this.detectCycles();
        }

        const cyclicNodeIds = new Set();
        const cyclicEdgeKeys = new Set();

        cycles.forEach(c => {
            for (let i = 0; i < c.length; i++) {
                cyclicNodeIds.add(c[i]);
                if (i < c.length - 1) {
                    cyclicEdgeKeys.add(`${c[i]}->${c[i+1]}`);
                }
            }
        });

        if (cyclicNodeIds.size === 0) {
            return { cycleCount: 0, nodeCount: 0, cycles: [] };
        }

        // Highlight nodes
        this.nodes.forEach(n => {
            if (!n.element) return;
            const box = n.element.querySelector('.node-box');
            if (cyclicNodeIds.has(n.id)) {
                n.element.style.opacity = '1.0';
                if (box) {
                    box.setAttribute('stroke', '#ec4899');
                    box.setAttribute('stroke-width', '3');
                }
            } else {
                n.element.style.opacity = '0.15';
            }
        });

        // Highlight edges
        this.links.forEach(l => {
            if (!l.element) return;
            const srcId = (l.source && l.source.id) || l.source;
            const tgtId = (l.target && l.target.id) || l.target;
            const key = `${srcId}->${tgtId}`;

            if (cyclicEdgeKeys.has(key)) {
                l.element.style.opacity = '1.0';
                l.element.setAttribute('stroke', '#ec4899');
                l.element.setAttribute('stroke-width', '3');
            } else {
                l.element.style.opacity = '0.1';
            }
        });

        return {
            cycleCount: cycles.length,
            nodeCount: cyclicNodeIds.size,
            cycles: cycles
        };
    }

    setLevel(level, rawGraphData) {
        this.level = level || "system";
        const data = rawGraphData || this.currentRawGraph;
        if (data) {
            this.renderHierarchical(data, this.level);
        }
    }

    renderHierarchical(graphData, level = "system") {
        if (!graphData) return;
        this.currentRawGraph = graphData;
        this.level = level;

        if (level === "file") {
            return this.render(graphData);
        }

        // Client-side fast cluster transformation for System / Module view
        const rawNodes = graphData.nodes || [];
        const rawLinks = graphData.links || graphData.edges || [];
        const depth = level === "system" ? 1 : 2;

        const clusters = new Map();
        const nodeToCluster = new Map();

        let commonPrefix = null;
        const normalizedPaths = rawNodes.map(n => String(n.id || n.file || "").replace(/\\/g, '/').replace(/^(\.\/|[a-zA-Z]:\/)/, '').replace(/^\/+/, '')).filter(p => p.includes('/'));
        if (normalizedPaths.length > 0) {
            const firstParts = normalizedPaths[0].split('/');
            if (firstParts.length > 1) {
                const cand = firstParts[0];
                if (normalizedPaths.every(p => p.startsWith(cand + '/'))) {
                    commonPrefix = cand;
                }
            }
        }

        const extractDomain = (path) => {
            let p = String(path || "").replace(/\\/g, '/').replace(/^(\.\/|[a-zA-Z]:\/)/, '').replace(/^\/+/, '');
            if (commonPrefix && p.startsWith(commonPrefix + '/')) {
                p = p.slice(commonPrefix.length + 1);
            }
            const parts = p.split('/').filter(Boolean);
            if (parts.length <= 1) return "(root)";
            let effectiveParts = parts;
            if (["src", "lib", "app", "pkg", "packages"].includes(parts[0].toLowerCase()) && parts.length > 2) {
                effectiveParts = parts.slice(1);
            }
            if (effectiveParts.length <= 1) return "(root)";
            return depth === 1 ? effectiveParts[0] : effectiveParts.slice(0, Math.min(depth, effectiveParts.length - 1)).join('/');
        };

        rawNodes.forEach(n => {
            const id = String(n.id || n.file || "unknown");
            const domain = extractDomain(id);
            nodeToCluster.set(id, domain);

            if (!clusters.has(domain)) {
                clusters.set(domain, {
                    id: domain,
                    label: domain.toUpperCase(),
                    files: [],
                    totalComplexity: 0,
                    highRiskCount: 0
                });
            }
            const c = clusters.get(domain);
            c.files.push(id);
            const comp = Number(n.complexity || n.cyclomatic_complexity || 1);
            c.totalComplexity += comp;
            if (n.level === "HIGH") c.highRiskCount++;
        });

        const clusterNodes = Array.from(clusters.values()).map(c => {
            const fCount = c.files.length;
            const avgComp = Math.round(c.totalComplexity / Math.max(1, fCount));
            const cLevel = c.highRiskCount > 0 ? "HIGH" : (avgComp >= 8 ? "MED" : "LOW");
            return {
                id: c.id,
                label: `${c.label} (${fCount})`,
                file_count: fCount,
                files: c.files,
                complexity: avgComp,
                level: cLevel,
                isCluster: true
            };
        });

        const edgeMap = new Map();
        rawLinks.forEach(link => {
            const src = String(link.source?.id || link.source || "");
            const tgt = String(link.target?.id || link.target || "");
            const weight = Number(link.weight || link.coupling || 1);

            const cSrc = nodeToCluster.get(src) || extractDomain(src);
            const cTgt = nodeToCluster.get(tgt) || extractDomain(tgt);

            if (cSrc !== cTgt && cSrc && cTgt) {
                const edgeKey = `${cSrc}--->${cTgt}`;
                if (!edgeMap.has(edgeKey)) {
                    edgeMap.set(edgeKey, {
                        source: cSrc,
                        target: cTgt,
                        weight: 0
                    });
                }
                edgeMap.get(edgeKey).weight += weight;
            }
        });

        const clusteredGraph = {
            _isClustered: true,
            nodes: clusterNodes,
            links: Array.from(edgeMap.values())
        };

        this.render(clusteredGraph);
    }

    drillDownCluster(clusterNode) {
        if (!this.originalGraphData || !clusterNode.files) return;
        const fileSet = new Set(clusterNode.files);
        const subNodes = (this.originalGraphData.nodes || []).filter(node => fileSet.has(node.id || node.file));
        const subLinks = (this.originalGraphData.links || this.originalGraphData.edges || []).filter(link => {
            const s = String(link.source?.id || link.source || "");
            const t = String(link.target?.id || link.target || "");
            return fileSet.has(s) && fileSet.has(t);
        });

        const subGraph = {
            _isClustered: true,
            _isDrillDown: true,
            _parentCluster: clusterNode.id,
            nodes: subNodes,
            links: subLinks
        };
        this.render(subGraph);
    }

    resetToDomains() {
        if (this.originalGraphData) {
            this.renderHierarchical(this.originalGraphData, "system");
        }
    }

    destroy() {
        this.simRunning = false;
        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }
        if (this.chunkAnimFrameId) {
            cancelAnimationFrame(this.chunkAnimFrameId);
            this.chunkAnimFrameId = null;
        }

        const svg = document.getElementById(this.svgId);
        if (svg) {
            if (this.wheelHandler) svg.removeEventListener("wheel", this.wheelHandler);
            if (this.mouseDownHandler) svg.removeEventListener("mousedown", this.mouseDownHandler);
            if (this.clickHandler) svg.removeEventListener("click", this.clickHandler);
        }
        if (this.mouseMoveHandler) window.removeEventListener("mousemove", this.mouseMoveHandler);
        if (this.mouseUpHandler) window.removeEventListener("mouseup", this.mouseUpHandler);
    }
}
