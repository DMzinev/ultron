/**
 * Ultron Web SPA — Interactive Graph Topology Module
 * Campaign 10: Physics Loop, Viewport Pan/Zoom & Detail Drawer Sidebar
 */

import { APIClient } from './api.js';
import { UIManager } from './ui.js';

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
    }

    render(graphData) {
        const svg = document.getElementById(this.svgId);
        if (!svg) return;

        // Campaign 10: Clean up previous event listeners & animation frame to prevent leaks
        this.destroy();

        const emptyState = document.getElementById("graph-empty-state");
        if (!graphData || !Array.isArray(graphData.nodes) || graphData.nodes.length === 0) {
            if (emptyState) emptyState.classList.remove("hidden");
            svg.innerHTML = '<defs><marker id="arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" opacity="0.5" /></marker></defs>';
            return;
        }
        if (emptyState) emptyState.classList.add("hidden");

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

        const applyTransform = () => {
            if (transformGroup) {
                transformGroup.setAttribute("transform", `translate(${this.panX},${this.panY}) scale(${this.scale})`);
            }
        };
        applyTransform();

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
            applyTransform();
        };
        svg.addEventListener("wheel", this.wheelHandler, { passive: false });

        this.mouseDownHandler = (e) => {
            if (e.target === svg || e.target === transformGroup || e.target.tagName === 'g') {
                this.isPanning = true;
                this.panStartX = e.clientX - this.panX;
                this.panStartY = e.clientY - this.panY;
                svg.style.cursor = "grabbing";
            }
        };
        svg.addEventListener("mousedown", this.mouseDownHandler);

        this.mouseMoveHandler = (e) => {
            if (this.isPanning) {
                this.panX = e.clientX - this.panStartX;
                this.panY = e.clientY - this.panStartY;
                applyTransform();
            }
        };
        window.addEventListener("mousemove", this.mouseMoveHandler);

        this.mouseUpHandler = () => {
            if (this.isPanning) {
                this.isPanning = false;
                svg.style.cursor = "grab";
            }
        };
        window.addEventListener("mouseup", this.mouseUpHandler);

        // Process Nodes & Links
        this.nodes = graphData.nodes.map(n => ({
            ...n,
            x: width / 2 + (Math.random() - 0.5) * 350,
            y: height / 2 + (Math.random() - 0.5) * 350,
            vx: 0,
            vy: 0,
            r: n.type === "file" ? 10 : 7,
            visible: true
        }));

        this.links = graphData.links.map(l => ({
            ...l,
            sourceNode: this.nodes.find(n => n.id === l.source),
            targetNode: this.nodes.find(n => n.id === l.target),
            visible: true
        })).filter(l => l.sourceNode && l.targetNode);

        // Render Lines
        this.links.forEach(l => {
            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.setAttribute("class", `graph-link ${l.type}`);
            if (l.type === "call") line.setAttribute("marker-end", "url(#arrow)");
            l.element = line;
            linkGroup.appendChild(line);
        });

        // Render Nodes
        this.nodes.forEach(n => {
            const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
            g.setAttribute("class", "graph-node-group");

            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("class", "node-circle");

            let color = "#94a3b8";
            if (n.level === "HIGH") color = "#f43f5e";
            else if (n.type === "file") color = "#38bdf8";
            else if (n.type === "function") color = "#c084fc";

            circle.setAttribute("fill", color);
            circle.setAttribute("r", n.r);
            circle.setAttribute("stroke", "rgba(0,0,0,0.6)");
            if (n.level === "HIGH") circle.setAttribute("filter", "drop-shadow(0 0 6px #f43f5e)");

            const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
            text.setAttribute("class", "node-label");
            text.setAttribute("dy", n.r + 12);
            text.setAttribute("fill", "#e2e8f0");
            text.setAttribute("font-size", "11px");
            text.setAttribute("text-anchor", "middle");
            text.setAttribute("pointer-events", "none");
            text.textContent = n.label || n.id;

            g.appendChild(circle);
            g.appendChild(text);

            n.element = g;

            // Click node to open Detail Drawer Sidebar
            circle.addEventListener("click", (e) => {
                e.stopPropagation();
                this.openNodeDrawer(n);
            });

            // Drag behavior
            circle.addEventListener("mousedown", (e) => {
                e.stopPropagation();
                n.dragged = true;
                svg.style.cursor = "grabbing";
            });

            nodeGroup.appendChild(g);
        });

        this.startPhysicsLoop(width, height);
    }

    openNodeDrawer(n) {
        const drawer = document.getElementById("graph-detail-drawer");
        if (!drawer) return;

        UIManager.setElementText("drawer-node-label", n.label || n.id);
        UIManager.setElementText("drawer-node-type", n.type === "file" ? "📁 File Node" : "⚡ Function Node");
        UIManager.setElementText("drawer-impact-score", (n.impact_score || 0).toFixed(2));
        UIManager.setElementText("drawer-complexity", n.complexity || 1);
        UIManager.setElementText("drawer-coupling", n.coupling || 0);
        UIManager.setElementText("drawer-strategy", n.strategy_display || "Safe localized modifications");
        UIManager.setElementText("drawer-ai-content", "Click 'Explain with AI' for grounded architectural feedback.");

        drawer.classList.remove("hidden");

        const btnAI = document.getElementById("btn-drawer-ai-critique");
        if (btnAI) {
            btnAI.onclick = async () => {
                UIManager.setButtonLoading(btnAI, true, "Analyzing with Local AI...");
                UIManager.setElementText("drawer-ai-content", "Querying Local AI Engine...");

                const res = await APIClient.post("/api/v1/ai/critique", {
                    file: n.id,
                    complexity: n.complexity || 1,
                    coupling: n.coupling || 0,
                    impact_score: n.impact_score || 0
                });

                UIManager.setButtonLoading(btnAI, false);

                if (res.success && res.data) {
                    UIManager.setElementText("drawer-ai-content", res.data.critique || res.data.error || "Critique generated successfully.");
                } else {
                    UIManager.setElementText("drawer-ai-content", `Offline Fallback: High complexity (${n.complexity || 1}). Enforce Single Responsibility (SRP).`);
                }
            };
        }

        const btnClose = document.getElementById("btn-close-drawer");
        if (btnClose) {
            btnClose.onclick = () => drawer.classList.add("hidden");
        }
    }

    startPhysicsLoop(width, height) {
        this.simRunning = true;
        const numNodes = this.nodes.length;
        const kRepulsion = Math.max(2500, numNodes * 90);

        const step = () => {
            if (!this.simRunning) return;

            for (let i = 0; i < numNodes; i++) {
                for (let j = i + 1; j < numNodes; j++) {
                    const n1 = this.nodes[i];
                    const n2 = this.nodes[j];
                    let dx = n2.x - n1.x;
                    let dy = n2.y - n1.y;
                    let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                    let minDist = n1.r + n2.r + 35;

                    if (dist < minDist) {
                        let force = (minDist - dist) / dist * 0.4;
                        let fx = dx * force;
                        let fy = dy * force;
                        if (!n1.dragged) { n1.vx -= fx; n1.vy -= fy; }
                        if (!n2.dragged) { n2.vx += fx; n2.vy += fy; }
                    }

                    let force = (kRepulsion / (dist * dist));
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
                let force = (dist - 100) * 0.03;
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
                if (l.element) {
                    l.element.setAttribute("x1", l.sourceNode.x);
                    l.element.setAttribute("y1", l.sourceNode.y);
                    l.element.setAttribute("x2", l.targetNode.x);
                    l.element.setAttribute("y2", l.targetNode.y);
                }
            });

            this.animFrameId = requestAnimationFrame(step);
        };

        step();
    }

    destroy() {
        this.simRunning = false;
        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }

        const svg = document.getElementById(this.svgId);
        if (svg) {
            if (this.wheelHandler) svg.removeEventListener("wheel", this.wheelHandler);
            if (this.mouseDownHandler) svg.removeEventListener("mousedown", this.mouseDownHandler);
        }
        if (this.mouseMoveHandler) window.removeEventListener("mousemove", this.mouseMoveHandler);
        if (this.mouseUpHandler) window.removeEventListener("mouseup", this.mouseUpHandler);
    }
}
