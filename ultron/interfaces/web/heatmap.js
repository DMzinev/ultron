document.addEventListener("DOMContentLoaded", () => {
    // Elements
    const repoPathInput = document.getElementById("repo-path");
    const scanBtn = document.getElementById("scan-btn");
    const scanSpinner = document.getElementById("scan-spinner");
    const errorBanner = document.getElementById("error-banner");
    const errorMessage = document.getElementById("error-message");
    const closeErrorBtn = document.getElementById("close-error-btn");
    
    const treeContainer = document.getElementById("tree-container");
    const fileDetailPanel = document.getElementById("file-detail-panel");
    const fileDetailContent = document.getElementById("file-detail-content");
    const closeDetailBtn = document.getElementById("close-detail-btn");
    const tooltip = document.getElementById("tooltip");
    
    // Tab Elements
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    // Graph Elements
    const graphDetailPanel = document.getElementById("graph-detail-panel");
    const graphDetailContent = document.getElementById("graph-detail-content");
    const closeGraphDetailBtn = document.getElementById("close-graph-detail-btn");
    const graphLoading = document.getElementById("graph-loading");
    const graphError = document.getElementById("graph-error");
    const archGraphSvg = document.getElementById("arch-graph-svg");
    const graphRefreshBtn = document.getElementById("graph-refresh-btn");
    
    // Health Elements
    const healthProgressBar = document.getElementById("health-progress-bar");
    const healthScoreVal = document.getElementById("health-score-val");
    const statTotalFiles = document.getElementById("stat-total-files");
    const statHighFiles = document.getElementById("stat-high-files");
    const statMediumFiles = document.getElementById("stat-medium-files");
    const statLowFiles = document.getElementById("stat-low-files");
    const hotspotsTbody = document.getElementById("hotspots-tbody");
    const cyclesListContainer = document.getElementById("cycles-list-container");
    
    // Simulator Elements
    const contractsList = document.getElementById("contracts-list");
    const simulationContent = document.getElementById("simulation-content");

    // Controls
    const expandAllBtn = document.getElementById("expand-all-btn");
    const collapseAllBtn = document.getElementById("collapse-all-btn");

    // Global State
    let stats = { total: 0, high: 0, medium: 0, low: 0 };
    let globalScanData = null; // Stored from scan responses
    let fileRiskDetails = {};  // Map of filepath -> risk metrics

    // Auto-Initialize on page load
    autoInitialize();

    // Event Listeners
    scanBtn.addEventListener("click", () => triggerScan());
    repoPathInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") triggerScan();
    });
    closeErrorBtn.addEventListener("click", hideError);
    closeDetailBtn.addEventListener("click", closeFileDetail);
    expandAllBtn.addEventListener("click", () => toggleAll(true));
    collapseAllBtn.addEventListener("click", () => toggleAll(false));
    if (closeGraphDetailBtn) {
        closeGraphDetailBtn.addEventListener("click", () => {
            graphDetailPanel.classList.add("closed");
        });
    }
    if (graphRefreshBtn) {
        graphRefreshBtn.addEventListener("click", () => loadDependencyGraph());
    }

    // Tab Navigation switching
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            tabBtns.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(targetTab).classList.add("active");

            if (targetTab === "view-graph") {
                loadDependencyGraph();
            }
        });
    });

    // API Handlers
    async function autoInitialize() {
        try {
            const response = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            });
            if (response.ok) {
                const config = await response.json();
                if (config.success && config.default_repo) {
                    repoPathInput.value = config.default_repo;
                    performScan(config.default_repo);
                }
            }
        } catch (e) {
            console.warn("Unable to fetch default config", e);
        }
    }

    function triggerScan() {
        const repoPath = repoPathInput.value.trim();
        if (repoPath) {
            performScan(repoPath);
        }
    }

    async function performScan(repoPath) {
        hideError();
        showLoading(true);
        closeFileDetail();
        stats = { total: 0, high: 0, medium: 0, low: 0 };
        fileRiskDetails = {};
        updateStatsUI(0, 0, 0, 0);
        
        try {
            // 1. Fetch File Tree Heatmap
            const treeResponse = await fetch("/api/file-tree", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo: repoPath })
            });

            if (!treeResponse.ok) {
                throw new Error(await getErrorMessage(treeResponse));
            }

            const treeData = await treeResponse.json();
            if (treeData.success && treeData.tree) {
                renderTree(treeData.tree);
            } else {
                throw new Error(treeData.error || "Failed to scan codebase structure.");
            }

            // 2. Fetch Architecture Health & Simulator deltas
            const healthResponse = await fetch("/api/architecture-health", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo: repoPath })
            });

            if (!healthResponse.ok) {
                throw new Error(await getErrorMessage(healthResponse));
            }

            const healthData = await healthResponse.json();
            if (healthData.success) {
                globalScanData = healthData;
                renderHealthDashboard(healthData);
                renderSimulatorDashboard(healthData);
            } else {
                throw new Error(healthData.error || "Failed to retrieve architecture metrics.");
            }

        } catch (err) {
            showError(err.message);
            treeContainer.innerHTML = `
                <div class="empty-state">
                    <p style="color: #ef4444; font-weight: 600;">Error: ${err.message}</p>
                </div>
            `;
            renderHealthErrorState(err.message);
            renderSimulatorErrorState(err.message);
        } finally {
            showLoading(false);
        }
    }

    async function getErrorMessage(res) {
        try {
            const errData = await res.json();
            return errData.error || `Server returned status ${res.status}`;
        } catch (_) {
            try {
                const text = await res.text();
                return text.length < 200 ? text : `Server returned status ${res.status}`;
            } catch (__) {
                return `Server returned status ${res.status}`;
            }
        }
    }

    // Heatmap Tree Rendering
    function renderTree(treeData) {
        if (!treeData || treeData.length === 0) {
            treeContainer.innerHTML = `
                <div class="empty-state">
                    <p>Repository is empty or contains no supported files.</p>
                </div>
            `;
            return;
        }

        treeContainer.innerHTML = "";
        const rootList = document.createElement("div");
        rootList.className = "tree-root";
        
        treeData.forEach(node => {
            rootList.appendChild(createNodeElement(node));
        });
        
        treeContainer.appendChild(rootList);
    }

    function createNodeElement(node) {
        const nodeDiv = document.createElement("div");
        nodeDiv.className = "tree-node";
        
        const rowDiv = document.createElement("div");
        rowDiv.className = "tree-row";
        
        const arrowSpan = document.createElement("span");
        arrowSpan.className = "node-arrow";
        
        const iconSpan = document.createElement("span");
        iconSpan.className = "node-icon";

        if (node.type === "directory") {
            arrowSpan.textContent = "▶";
            arrowSpan.classList.add("expanded");
            iconSpan.textContent = "📁";
            rowDiv.appendChild(arrowSpan);
        } else {
            arrowSpan.style.visibility = "hidden";
            iconSpan.textContent = "📄";
            rowDiv.appendChild(arrowSpan);
            
            stats.total++;
            if (node.risk) {
                const lvl = (node.risk.level || "").toUpperCase();
                if (lvl === "HIGH") stats.high++;
                else if (lvl === "MEDIUM") stats.medium++;
                else stats.low++;
                
                // Map risk stats globally for Detail Panel lookups
                fileRiskDetails[node.path] = node.risk;
            }
        }

        rowDiv.appendChild(iconSpan);

        const nameSpan = document.createElement("span");
        nameSpan.className = "node-name";
        nameSpan.textContent = node.name;
        rowDiv.appendChild(nameSpan);

        if (node.risk) {
            const riskSpan = document.createElement("span");
            const lvl = (node.risk.level || "LOW").toLowerCase();
            riskSpan.className = `node-risk-chip level-${lvl}`;
            riskSpan.textContent = lvl;
            rowDiv.appendChild(riskSpan);
            
            // Tooltip events
            rowDiv.addEventListener("mouseenter", (e) => showTooltip(e, node.name, node.risk));
            rowDiv.addEventListener("mousemove", moveTooltip);
            rowDiv.addEventListener("mouseleave", hideTooltip);
        }

        nodeDiv.appendChild(rowDiv);

        if (node.type === "directory" && node.children) {
            const childrenContainer = document.createElement("div");
            childrenContainer.className = "children-container";
            childrenContainer.style.display = "block";
            
            node.children.forEach(child => {
                childrenContainer.appendChild(createNodeElement(child));
            });
            
            nodeDiv.appendChild(childrenContainer);
            
            rowDiv.addEventListener("click", (e) => {
                if (e.target.closest(".node-risk-chip")) return;
                
                const isExpanded = arrowSpan.classList.contains("expanded");
                if (isExpanded) {
                    arrowSpan.classList.remove("expanded");
                    arrowSpan.textContent = "▶";
                    childrenContainer.style.display = "none";
                } else {
                    arrowSpan.classList.add("expanded");
                    arrowSpan.textContent = "▼";
                    childrenContainer.style.display = "block";
                }
            });
        } else {
            // File click details overlay
            rowDiv.addEventListener("click", () => openFileDetail(node.path));
        }

        return nodeDiv;
    }

    // File Details Overlay Panel
    function openFileDetail(filepath) {
        const riskData = fileRiskDetails[filepath];
        if (!riskData) return;
        
        fileDetailPanel.classList.remove("closed");
        
        // Find hotspots metrics if available
        let complexity = "N/A";
        let coupling = "N/A";
        let fixes = "N/A";
        if (globalScanData && globalScanData.hotspots) {
            const hot = globalScanData.hotspots.find(h => h.file === filepath);
            if (hot) {
                complexity = hot.complexity;
                coupling = hot.coupling_debt;
                fixes = hot.bug_fix_count;
            }
        }

        // Calculate medians
        let repomedianComplexity = 0;
        let repomedianCoupling = 0;
        if (globalScanData && globalScanData.hotspots && globalScanData.hotspots.length > 0) {
            const complexities = globalScanData.hotspots.map(h => h.complexity).filter(c => typeof c === "number").sort((a,b)=>a-b);
            const couplings = globalScanData.hotspots.map(h => h.coupling_debt).filter(c => typeof c === "number").sort((a,b)=>a-b);
            if (complexities.length > 0) repomedianComplexity = complexities[Math.floor(complexities.length / 2)];
            if (couplings.length > 0) repomedianCoupling = couplings[Math.floor(couplings.length / 2)];
        }

        let whyHtml = '';
        if (riskData.level === "HIGH" || riskData.level === "MEDIUM") {
            whyHtml = `
                <div class="why-card" style="margin-top: 0.75rem; padding: 0.8rem; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 6px;">
                    <div style="font-weight: 700; color: #fca5a5; margin-bottom: 0.25rem; font-size: 0.8rem; display: flex; align-items: center; gap: 0.25rem;">
                        <span>⚠️</span> Why ${riskData.level}?
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary); line-height: 1.4;">
                        This module has a high risk tier because its metrics exceed repository norms:
                        <ul style="margin: 0.25rem 0 0 1rem; padding: 0;">
                            <li>Complexity: <strong>${complexity}</strong> (median: ${repomedianComplexity})</li>
                            <li>Coupling: <strong>${coupling}</strong> (median: ${repomedianCoupling})</li>
                            <li>Change Velocity: <strong>${fixes}</strong> bug-fix commit(s)</li>
                        </ul>
                    </div>
                </div>
            `;
        }

        // Find violation cards if any
        let violationsHtml = '<div class="empty-state-small" style="padding: 1rem 0;">No active architectural violations.</div>';
        if (globalScanData && globalScanData.violations) {
            const fileViolations = globalScanData.violations.filter(v => v.filepath === filepath);
            if (fileViolations.length > 0) {
                violationsHtml = fileViolations.map(v => `
                    <div class="sim-rec-item" style="border-left: 3px solid #ef4444;">
                        <div class="sim-rec-title" style="color: #fca5a5;">${v.principle}</div>
                        <div class="sim-rec-desc">${v.observation}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
                            <strong>Reason:</strong> ${v.reason}
                        </div>
                    </div>
                `).join("");
            }
        }
        
        fileDetailContent.innerHTML = `
            <div class="detail-file-title">${filepath}</div>
            
            <div class="stats-card" style="padding: 1rem; border-radius: 8px;">
                <div class="stat-row">
                    <span class="stat-label">Risk Level:</span>
                    <span class="stat-value text-${riskData.level.toLowerCase()}">${riskData.level}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Architectural Role:</span>
                    <span class="stat-value" style="color: #a78bfa; font-weight: 600;">${riskData.boundary_type || "Internal"}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Change Strategy:</span>
                    <span class="stat-value" style="color: #60a5fa; font-weight: 600;">${riskData.change_strategy_display || "Safe internal edits"}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Impact Score:</span>
                    <span class="stat-value">${riskData.impact_score.toFixed(2)}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Cyclomatic Complexity:</span>
                    <span class="stat-value">${complexity}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Coupling Debt:</span>
                    <span class="stat-value">${coupling}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Bug-Fix Commits:</span>
                    <span class="stat-value">${fixes}</span>
                </div>
            </div>
            
            ${whyHtml}
            
            <div class="sim-block-title" style="margin-top: 0.5rem;">Plain-English Summary</div>
            <div style="font-size: 0.85rem; line-height: 1.4; color: var(--text-secondary); background: rgba(255,255,255,0.02); padding: 0.8rem; border-radius: 6px; border: 1px solid var(--border-color);">
                ${riskData.summary}
            </div>

            <div class="sim-block-title" style="margin-top: 0.5rem;">Smell Warnings</div>
            <div class="sim-recs-list">
                ${violationsHtml}
            </div>
        `;
    }

    function closeFileDetail() {
        fileDetailPanel.classList.add("closed");
        fileDetailContent.innerHTML = '<div class="empty-state-small">Select a file in the tree to inspect details.</div>';
    }

    // Health Dashboard Rendering
    function renderHealthDashboard(data) {
        // Animate Radial Score Circle
        const score = Math.max(10, Math.min(100, data.health_score || 100));
        healthScoreVal.textContent = `${score}%`;
        
        const r = 90;
        const circ = 2 * Math.PI * r; // 565.48
        const offset = circ * (1 - score / 100);
        
        healthProgressBar.style.strokeDasharray = `${circ}`;
        healthProgressBar.style.strokeDashoffset = `${offset}`;
        
        // Dynamic score coloring
        if (score >= 80) {
            healthProgressBar.style.stroke = "var(--color-low)";
            healthScoreVal.style.color = "var(--color-low)";
        } else if (score >= 50) {
            healthProgressBar.style.stroke = "var(--color-medium)";
            healthScoreVal.style.color = "var(--color-medium)";
        } else {
            healthProgressBar.style.stroke = "var(--color-high)";
            healthScoreVal.style.color = "var(--color-high)";
        }

        // Stats summary
        updateStatsUI(stats.total, stats.high, stats.medium, stats.low);

        // Hotspots table
        if (data.hotspots && data.hotspots.length > 0) {
            hotspotsTbody.innerHTML = data.hotspots.map(h => `
                <tr data-file="${h.file}">
                    <td class="file-cell" title="${h.file}">${h.file}</td>
                    <td style="font-weight: 700;">${h.hotspot_score.toFixed(3)}</td>
                    <td>${h.complexity}</td>
                    <td>${h.coupling_debt}</td>
                    <td>${h.bug_fix_count}</td>
                </tr>
            `).join("");
            
            // Add click events to hotspot rows
            hotspotsTbody.querySelectorAll("tr").forEach(row => {
                row.addEventListener("click", () => {
                    const filepath = row.getAttribute("data-file");
                    // Switch to Heatmap tab
                    document.getElementById("tab-btn-heatmap").click();
                    openFileDetail(filepath);
                });
            });
        } else {
            hotspotsTbody.innerHTML = `<tr><td colspan="5" class="empty-table">No metrics available. Codebase is empty.</td></tr>`;
        }

        // Circular loops list
        if (data.circular_dependencies && data.circular_dependencies.length > 0) {
            cyclesListContainer.innerHTML = data.circular_dependencies.map(cycle => `
                <div class="cycle-item">
                    🔄 ${cycle.join(" &rarr; ")}
                </div>
            `).join("");
        } else {
            cyclesListContainer.innerHTML = `<div class="empty-state-small" style="color: var(--color-low);">No circular dependencies found. Codebase is clean!</div>`;
        }
    }

    // Simulator Dashboard Rendering
    function renderSimulatorDashboard(data) {
        if (!data.contracts || data.contracts.length === 0) {
            contractsList.innerHTML = `<div class="empty-state">No refactoring contracts available (zero design violations detected).</div>`;
            simulationContent.innerHTML = `<div class="empty-state-small">Select a refactoring contract to simulate projected deltas.</div>`;
            return;
        }

        contractsList.innerHTML = data.contracts.map((c, idx) => `
            <div class="contract-card" data-idx="${idx}">
                <div class="contract-header">
                    <span class="contract-file" title="${c.filepath}">${c.filepath}</span>
                    <span class="contract-violations-badge">${c.recommendations.length} smell${c.recommendations.length > 1 ? 's' : ''}</span>
                </div>
                <div class="contract-body">
                    Proposed: ${c.recommendations.map(r => r.refactoring).join(", ")}
                </div>
            </div>
        `).join("");

        // Click events on contracts
        const contractCards = contractsList.querySelectorAll(".contract-card");
        contractCards.forEach(card => {
            card.addEventListener("click", () => {
                contractCards.forEach(c => c.classList.remove("selected"));
                card.classList.add("selected");
                
                const idx = parseInt(card.getAttribute("data-idx"));
                renderSimulationDetail(data.contracts[idx]);
            });
        });
    }

    function renderSimulationDetail(contract) {
        const before = contract.before_snapshot;
        const after = contract.after_snapshot;

        // Calculate deltas
        const debtDelta = after.total_coupling_debt - before.total_coupling_debt;
        const cycleDelta = after.total_cycle_count - before.total_cycle_count;
        const violationDelta = after.total_violations - before.total_violations;
        const instDelta = after.avg_instability - before.avg_instability;
        const hsDelta = after.avg_hotspot_score - before.avg_hotspot_score;

        function formatDelta(val, dec = 0, lowerIsBetter = true) {
            if (val === 0) return `<span class="sim-metric-delta delta-neutral">0</span>`;
            const sign = val > 0 ? "+" : "";
            const isGood = lowerIsBetter ? val < 0 : val > 0;
            const cls = isGood ? "delta-good" : "text-high";
            return `<span class="sim-metric-delta ${cls}">${sign}${val.toFixed(dec)}</span>`;
        }

        simulationContent.innerHTML = `
            <div class="detail-file-title" style="font-size: 0.95rem; margin-bottom: 0.25rem;">${contract.filepath}</div>
            
            <div class="sim-block-title">Projected Metric Improvements</div>
            
            <div class="sim-metric-table">
                <div class="sim-metric-row">
                    <span class="sim-metric-name">Coupling Debt</span>
                    <span class="sim-metric-before">${before.total_coupling_debt.toFixed(1)}</span>
                    <span class="sim-metric-arrow">&rarr;</span>
                    <span class="sim-metric-after">${after.total_coupling_debt.toFixed(1)}</span>
                    ${formatDelta(debtDelta, 1, true)}
                </div>
                
                <div class="sim-metric-row">
                    <span class="sim-metric-name">Circular Loops</span>
                    <span class="sim-metric-before">${before.total_cycle_count}</span>
                    <span class="sim-metric-arrow">&rarr;</span>
                    <span class="sim-metric-after">${after.total_cycle_count}</span>
                    ${formatDelta(cycleDelta, 0, true)}
                </div>
                
                <div class="sim-metric-row">
                    <span class="sim-metric-name">Design Smells</span>
                    <span class="sim-metric-before">${before.total_violations}</span>
                    <span class="sim-metric-arrow">&rarr;</span>
                    <span class="sim-metric-after">${after.total_violations}</span>
                    ${formatDelta(violationDelta, 0, true)}
                </div>
                
                <div class="sim-metric-row">
                    <span class="sim-metric-name">Average Instability</span>
                    <span class="sim-metric-before">${before.avg_instability.toFixed(3)}</span>
                    <span class="sim-metric-arrow">&rarr;</span>
                    <span class="sim-metric-after">${after.avg_instability.toFixed(3)}</span>
                    ${formatDelta(instDelta, 3, true)}
                </div>
                
                <div class="sim-metric-row">
                    <span class="sim-metric-name">Average Hotspot Score</span>
                    <span class="sim-metric-before">${before.avg_hotspot_score.toFixed(4)}</span>
                    <span class="sim-metric-arrow">&rarr;</span>
                    <span class="sim-metric-after">${after.avg_hotspot_score.toFixed(4)}</span>
                    ${formatDelta(hsDelta, 4, true)}
                </div>
            </div>

            <div class="sim-block-title" style="margin-top: 0.75rem;">Refactoring Action Plan</div>
            <div class="sim-recs-list">
                ${contract.recommendations.map(r => `
                    <div class="sim-rec-item">
                        <div class="sim-rec-title">${r.principle} Refactor</div>
                        <div class="sim-rec-desc">${r.refactoring}</div>
                    </div>
                `).join("")}
            </div>
        `;
    }

    // Visual Error / Warning Fallbacks
    function renderHealthErrorState(msg) {
        healthScoreVal.textContent = "N/A";
        healthScoreVal.style.color = "var(--text-muted)";
        healthProgressBar.style.strokeDashoffset = "565.48";
        healthProgressBar.style.stroke = "var(--border-color)";
        
        hotspotsTbody.innerHTML = `<tr><td colspan="5" class="empty-table" style="color: #ef4444;">Error: ${msg}</td></tr>`;
        cyclesListContainer.innerHTML = `<div class="empty-state-small" style="color: #ef4444;">Failed to load dependencies.</div>`;
    }

    function renderSimulatorErrorState(msg) {
        contractsList.innerHTML = `<div class="empty-state" style="color: #ef4444;">Error: ${msg}</div>`;
        simulationContent.innerHTML = `<div class="empty-state-small" style="color: #ef4444;">Simulation unavailable due to errors.</div>`;
    }

    // Tooltip Position Helpers
    function showTooltip(e, name, riskData) {
        const boundaryHtml = (riskData.boundary_type && riskData.boundary_type !== "Internal")
            ? `<div style="font-size: 0.75rem; color: #a78bfa; margin-top: 0.2rem; font-weight: 600;">Role: ${riskData.boundary_type}</div>
               <div style="font-size: 0.75rem; color: #60a5fa; margin-top: 0.1rem;">Strategy: ${riskData.change_strategy_display || "Safe internal edits"}</div>`
            : "";
        tooltip.innerHTML = `
            <div class="tooltip-title">${name}</div>
            <div class="tooltip-metric">
                <span>Risk Level: <strong>${riskData.level}</strong></span>
                <span>Impact: <strong>${(riskData.impact_score || 0).toFixed(2)}</strong></span>
            </div>
            ${boundaryHtml}
            <div class="tooltip-desc">${riskData.summary || "No description available."}</div>
        `;
        tooltip.classList.remove("hidden");
        tooltip.style.display = "block";
        moveTooltip(e);
    }

    function moveTooltip(e) {
        const padding = 15;
        let x = e.pageX + padding;
        let y = e.pageY + padding;
        
        const tooltipWidth = tooltip.offsetWidth;
        const tooltipHeight = tooltip.offsetHeight;
        
        if (x + tooltipWidth > window.innerWidth + window.scrollX) {
            x = e.pageX - tooltipWidth - padding;
        }
        if (y + tooltipHeight > window.innerHeight + window.scrollY) {
            y = e.pageY - tooltipHeight - padding;
        }
        
        tooltip.style.left = `${x}px`;
        tooltip.style.top = `${y}px`;
    }

    function hideTooltip() {
        tooltip.classList.add("hidden");
        tooltip.style.display = "none";
    }

    // Toggle Folders
    function toggleAll(expand) {
        const containers = document.querySelectorAll(".children-container");
        const arrows = document.querySelectorAll(".node-arrow");
        
        containers.forEach(container => {
            container.style.display = expand ? "block" : "none";
        });
        
        arrows.forEach(arrow => {
            const row = arrow.closest(".tree-row");
            if (row && row.parentNode.querySelector(".children-container")) {
                if (expand) {
                    arrow.classList.add("expanded");
                    arrow.textContent = "▼";
                } else {
                    arrow.classList.remove("expanded");
                    arrow.textContent = "▶";
                }
            }
        });
    }

    // Utilities
    function showLoading(loading) {
        scanBtn.disabled = loading;
        scanSpinner.style.display = loading ? "inline-block" : "none";
    }

    function showError(msg) {
        errorMessage.textContent = msg;
        errorBanner.classList.remove("hidden");
    }

    function hideError() {
        errorBanner.classList.add("hidden");
        errorMessage.textContent = "";
    }

    function updateStatsUI(total, high, medium, low) {
        statTotalFiles.textContent = total;
        statHighFiles.textContent = high;
        statMediumFiles.textContent = medium;
        statLowFiles.textContent = low;

        const summaryBar = document.getElementById("summary-bar");
        const summaryTotal = document.getElementById("summary-total-files");
        const summaryHigh = document.getElementById("summary-high-files");
        const summaryPressure = document.getElementById("summary-arch-pressure");
        const summaryTopRole = document.getElementById("summary-top-role");

        if (summaryBar) {
            if (total > 0) {
                summaryBar.classList.remove("hidden");
                if (summaryTotal) summaryTotal.textContent = total;
                if (summaryHigh) summaryHigh.textContent = high;

                // Calculate architectural pressure
                let pressure = 0;
                if (globalScanData && globalScanData.hotspots && globalScanData.hotspots.length > 0) {
                    const couplings = globalScanData.hotspots.map(h => h.coupling_debt).filter(c => typeof c === "number").sort((a,b)=>a-b);
                    if (couplings.length > 0) {
                        const medianCoupling = couplings[Math.floor(couplings.length / 2)];
                        const aboveMedianCount = globalScanData.hotspots.filter(h => h.coupling_debt > medianCoupling).length;
                        pressure = Math.round((aboveMedianCount / globalScanData.hotspots.length) * 100);
                    }
                }
                if (summaryPressure) summaryPressure.textContent = `${pressure}%`;

                // Calculate primary risk focus role
                let topRole = "Internal";
                const roleScores = {};
                for (const filepath in fileRiskDetails) {
                    const riskData = fileRiskDetails[filepath];
                    if (riskData) {
                        const role = riskData.boundary_type || "Internal";
                        const score = riskData.impact_score || 0;
                        roleScores[role] = (roleScores[role] || 0) + score;
                    }
                }
                let maxScore = -1;
                for (const role in roleScores) {
                    if (roleScores[role] > maxScore) {
                        maxScore = roleScores[role];
                        topRole = role;
                    }
                }
                if (summaryTopRole) summaryTopRole.textContent = topRole;
            } else {
                summaryBar.classList.add("hidden");
            }
        }
    }

    // DEPENDENCY GRAPH RENDERING WITH VANILLA SVG
    let dragNode = null;
    let dragOffset = { x: 0, y: 0 };
    let panActive = false;
    let panStart = { x: 0, y: 0 };
    let viewBox = { x: 0, y: 0, w: 800, h: 600 };
    let zoomLevel = 1.0;

    async function loadDependencyGraph() {
        const repoPath = repoPathInput.value.trim();
        if (!repoPath) {
            if (graphError) {
                graphError.textContent = "Please enter a repository path first.";
                graphError.classList.remove("hidden");
            }
            return;
        }

        if (graphError) {
            graphError.classList.add("hidden");
            graphError.textContent = "";
        }
        if (graphLoading) {
            graphLoading.classList.remove("hidden");
        }
        
        // Clear previous SVG contents
        const svg = document.getElementById("arch-graph-svg");
        if (svg) {
            svg.innerHTML = "";
        }

        try {
            const response = await fetch("/api/dependency-graph", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo: repoPath })
            });

            if (!response.ok) {
                const errMsg = await getErrorMessage(response);
                throw new Error(errMsg);
            }

            const data = await response.json();
            if (graphLoading) {
                graphLoading.classList.add("hidden");
            }

            if (data.success) {
                renderDependencyGraph(data);
            } else {
                throw new Error(data.error || "Failed to load dependency graph.");
            }
        } catch (err) {
            if (graphLoading) {
                graphLoading.classList.add("hidden");
            }
            if (graphError) {
                graphError.textContent = `Error: ${err.message}`;
                graphError.classList.remove("hidden");
            }
        }
    }

    function renderDependencyGraph(data) {
        const svg = document.getElementById("arch-graph-svg");
        if (!svg) return;
        
        svg.innerHTML = "";

        const nodes = data.nodes || [];
        const links = data.links || [];
        
        const containerWidth = svg.clientWidth || 800;
        const containerHeight = svg.clientHeight || 600;
        viewBox = { x: 0, y: 0, w: containerWidth, h: containerHeight };
        updateSvgViewBox();

        // 1. Arrange nodes in a beautiful circular ring
        const centerX = containerWidth / 2;
        const centerY = containerHeight / 2;
        const radius = Math.min(containerWidth, containerHeight) * 0.35;
        
        nodes.forEach((node, i) => {
            const angle = (i / nodes.length) * 2 * Math.PI;
            node.x = centerX + radius * Math.cos(angle);
            node.y = centerY + radius * Math.sin(angle);
            node.label = node.label || node.id;
        });

        // Map node IDs to nodes
        const nodeMap = {};
        nodes.forEach(n => { nodeMap[n.id] = n; });

        // Resolve link references to node objects
        links.forEach(l => {
            l.sourceObj = typeof l.source === 'object' ? l.source : nodeMap[l.source];
            l.targetObj = typeof l.target === 'object' ? l.target : nodeMap[l.target];
        });

        // 2. SVG Markers for Arrowheads
        const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
        
        // Default marker
        const markerDefault = document.createElementNS("http://www.w3.org/2000/svg", "marker");
        markerDefault.setAttribute("id", "arrow-default");
        markerDefault.setAttribute("viewBox", "0 -5 10 10");
        markerDefault.setAttribute("refX", "22");
        markerDefault.setAttribute("refY", "0");
        markerDefault.setAttribute("markerWidth", "6");
        markerDefault.setAttribute("markerHeight", "6");
        markerDefault.setAttribute("orient", "auto");
        const pathDefault = document.createElementNS("http://www.w3.org/2000/svg", "path");
        pathDefault.setAttribute("d", "M0,-5L10,0L0,5");
        pathDefault.setAttribute("fill", "rgba(148, 163, 184, 0.25)");
        markerDefault.appendChild(pathDefault);
        defs.appendChild(markerDefault);

        // Active marker
        const markerActive = document.createElementNS("http://www.w3.org/2000/svg", "marker");
        markerActive.setAttribute("id", "arrow-active");
        markerActive.setAttribute("viewBox", "0 -5 10 10");
        markerActive.setAttribute("refX", "22");
        markerActive.setAttribute("refY", "0");
        markerActive.setAttribute("markerWidth", "6");
        markerActive.setAttribute("markerHeight", "6");
        markerActive.setAttribute("orient", "auto");
        const pathActive = document.createElementNS("http://www.w3.org/2000/svg", "path");
        pathActive.setAttribute("d", "M0,-5L10,0L0,5");
        pathActive.setAttribute("fill", "rgba(96, 165, 250, 0.9)");
        markerActive.appendChild(pathActive);
        defs.appendChild(markerActive);

        svg.appendChild(defs);

        // 3. Render Link lines
        const linksGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
        linksGroup.setAttribute("id", "links-group");
        links.forEach((l, idx) => {
            if (!l.sourceObj || !l.targetObj) return;
            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.setAttribute("class", "graph-link");
            line.setAttribute("id", `link-${idx}`);
            line.setAttribute("x1", l.sourceObj.x);
            line.setAttribute("y1", l.sourceObj.y);
            line.setAttribute("x2", l.targetObj.x);
            line.setAttribute("y2", l.targetObj.y);
            line.setAttribute("marker-end", "url(#arrow-default)");
            l.domElement = line;
            linksGroup.appendChild(line);
        });
        svg.appendChild(linksGroup);

        // 4. Render Node groups
        const nodesGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
        nodesGroup.setAttribute("id", "nodes-group");
        nodes.forEach(n => {
            const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
            group.setAttribute("class", "graph-node-group");
            group.setAttribute("id", `node-group-${n.id}`);

            // Circle
            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            const r = Math.max(8, 4 + Math.sqrt(n.complexity || 1) * 2);
            circle.setAttribute("r", r);
            circle.setAttribute("cx", n.x);
            circle.setAttribute("cy", n.y);
            circle.setAttribute("class", `graph-node level-${(n.level || "LOW").toLowerCase()}`);
            
            const lvl = (n.level || "LOW").toUpperCase();
            let fill = "var(--color-low, #10b981)";
            if (lvl === "HIGH") fill = "var(--color-high, #ef4444)";
            else if (lvl === "MEDIUM") fill = "var(--color-medium, #f59e0b)";
            circle.setAttribute("fill", fill);
            circle.setAttribute("stroke", "var(--border-color)");
            circle.setAttribute("stroke-width", "1px");

            // Text Label
            const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
            text.setAttribute("x", n.x + r + 4);
            text.setAttribute("y", n.y + 4);
            text.setAttribute("class", "graph-label");
            text.textContent = n.label;

            group.appendChild(circle);
            group.appendChild(text);
            
            n.domElement = group;
            n.circleElement = circle;
            n.textElement = text;

            // Events
            circle.addEventListener("click", (event) => {
                event.stopPropagation();
                
                // Clear previous active nodes & links
                document.querySelectorAll(".graph-node").forEach(c => c.classList.remove("active-node"));
                document.querySelectorAll(".graph-link").forEach(l => {
                    l.classList.remove("active-link");
                    l.setAttribute("marker-end", "url(#arrow-default)");
                });

                // Highlight clicked node
                circle.classList.add("active-node");

                // Highlight connected links
                links.forEach(l => {
                    if (l.sourceObj === n || l.targetObj === n) {
                        if (l.domElement) {
                            l.domElement.classList.add("active-link");
                            l.domElement.setAttribute("marker-end", "url(#arrow-active)");
                        }
                    }
                });

                openGraphFileDetail(n.id, n);
            });

            circle.addEventListener("mouseenter", (event) => {
                const mockRisk = {
                    level: n.level,
                    impact_score: n.impact_score,
                    boundary_type: n.role_display,
                    change_strategy_display: n.strategy_display,
                    summary: `Complexity: ${n.complexity}, Coupling: ${n.coupling}. Strategy: ${n.strategy_display}`
                };
                showTooltip(event, n.label, mockRisk);
            });

            circle.addEventListener("mousemove", moveTooltip);
            circle.addEventListener("mouseleave", hideTooltip);

            // Drag setup
            circle.addEventListener("mousedown", (event) => {
                event.stopPropagation();
                dragNode = n;
                const pt = svg.createSVGPoint();
                pt.x = event.clientX;
                pt.y = event.clientY;
                const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());
                dragOffset = { x: svgP.x - n.x, y: svgP.y - n.y };
            });

            nodesGroup.appendChild(group);
        });
        svg.appendChild(nodesGroup);

        // 5. Global SVG Events for Dragging, Panning & Zooming
        svg.addEventListener("mousedown", (event) => {
            if (dragNode) return;
            panActive = true;
            panStart = { x: event.clientX, y: event.clientY };
        });

        svg.addEventListener("mousemove", (event) => {
            if (dragNode) {
                // Drag Node
                const pt = svg.createSVGPoint();
                pt.x = event.clientX;
                pt.y = event.clientY;
                const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());
                
                dragNode.x = svgP.x - dragOffset.x;
                dragNode.y = svgP.y - dragOffset.y;

                // Update node DOM
                const r = parseFloat(dragNode.circleElement.getAttribute("r"));
                dragNode.circleElement.setAttribute("cx", dragNode.x);
                dragNode.circleElement.setAttribute("cy", dragNode.y);
                dragNode.textElement.setAttribute("x", dragNode.x + r + 4);
                dragNode.textElement.setAttribute("y", dragNode.y + 4);

                // Update links connected to node
                links.forEach(l => {
                    if (l.sourceObj === dragNode) {
                        l.domElement.setAttribute("x1", dragNode.x);
                        l.domElement.setAttribute("y1", dragNode.y);
                    }
                    if (l.targetObj === dragNode) {
                        l.domElement.setAttribute("x2", dragNode.x);
                        l.domElement.setAttribute("y2", dragNode.y);
                    }
                });
            } else if (panActive) {
                // Pan viewport
                const dx = (event.clientX - panStart.x) * zoomLevel;
                const dy = (event.clientY - panStart.y) * zoomLevel;
                viewBox.x -= dx;
                viewBox.y -= dy;
                panStart = { x: event.clientX, y: event.clientY };
                updateSvgViewBox();
            }
        });

        window.addEventListener("mouseup", () => {
            dragNode = null;
            panActive = false;
        });

        svg.addEventListener("wheel", (event) => {
            event.preventDefault();
            const zoomFactor = event.deltaY < 0 ? 0.9 : 1.1;
            zoomLevel *= zoomFactor;
            
            const pt = svg.createSVGPoint();
            pt.x = event.clientX;
            pt.y = event.clientY;
            const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());

            viewBox.w *= zoomFactor;
            viewBox.h *= zoomFactor;
            viewBox.x = svgP.x - (svgP.x - viewBox.x) * zoomFactor;
            viewBox.y = svgP.y - (svgP.y - viewBox.y) * zoomFactor;
            updateSvgViewBox();
        });

        svg.addEventListener("click", () => {
            document.querySelectorAll(".graph-node").forEach(c => c.classList.remove("active-node"));
            document.querySelectorAll(".graph-link").forEach(l => {
                l.classList.remove("active-link");
                l.setAttribute("marker-end", "url(#arrow-default)");
            });
            if (graphDetailPanel) {
                graphDetailPanel.classList.add("closed");
            }
        });
    }

    function updateSvgViewBox() {
        const svg = document.getElementById("arch-graph-svg");
        if (svg) {
            svg.setAttribute("viewBox", `${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`);
        }
    }

    function openGraphFileDetail(filepath, nodeData) {
        if (!nodeData || !graphDetailPanel || !graphDetailContent) return;
        graphDetailPanel.classList.remove("closed");
        
        let complexity = nodeData.complexity;
        let coupling = nodeData.coupling;
        let fixes = "0";
        if (globalScanData && globalScanData.hotspots) {
            const hot = globalScanData.hotspots.find(h => h.file === filepath);
            if (hot) {
                complexity = hot.complexity;
                coupling = hot.coupling_debt;
                fixes = hot.bug_fix_count;
            }
        }

        // Calculate medians
        let repomedianComplexity = 0;
        let repomedianCoupling = 0;
        if (globalScanData && globalScanData.hotspots && globalScanData.hotspots.length > 0) {
            const complexities = globalScanData.hotspots.map(h => h.complexity).filter(c => typeof c === "number").sort((a,b)=>a-b);
            const couplings = globalScanData.hotspots.map(h => h.coupling_debt).filter(c => typeof c === "number").sort((a,b)=>a-b);
            if (complexities.length > 0) repomedianComplexity = complexities[Math.floor(complexities.length / 2)];
            if (couplings.length > 0) repomedianCoupling = couplings[Math.floor(couplings.length / 2)];
        }

        let whyHtml = '';
        if (nodeData.level === "HIGH" || nodeData.level === "MEDIUM") {
            whyHtml = `
                <div class="why-card" style="margin-top: 0.75rem; padding: 0.8rem; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 6px;">
                    <div style="font-weight: 700; color: #fca5a5; margin-bottom: 0.25rem; font-size: 0.8rem; display: flex; align-items: center; gap: 0.25rem;">
                        <span>⚠️</span> Why ${nodeData.level}?
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary); line-height: 1.4;">
                        This module has a high risk tier because its metrics exceed repository norms:
                        <ul style="margin: 0.25rem 0 0 1rem; padding: 0;">
                            <li>Complexity: <strong>${complexity}</strong> (median: ${repomedianComplexity})</li>
                            <li>Coupling: <strong>${coupling}</strong> (median: ${repomedianCoupling})</li>
                            <li>Change Velocity: <strong>${fixes}</strong> bug-fix commit(s)</li>
                        </ul>
                    </div>
                </div>
            `;
        }

        let violationsHtml = '<div class="empty-state-small" style="padding: 1rem 0;">No active architectural violations.</div>';
        if (globalScanData && globalScanData.violations) {
            const fileViolations = globalScanData.violations.filter(v => v.filepath === filepath);
            if (fileViolations.length > 0) {
                violationsHtml = fileViolations.map(v => `
                    <div class="sim-rec-item" style="border-left: 3px solid #ef4444; margin-bottom: 0.5rem; padding: 0.5rem; background: rgba(255,255,255,0.01); border-radius: 4px;">
                        <div class="sim-rec-title" style="color: #fca5a5; font-size: 0.8rem; font-weight: 600;">${v.principle}</div>
                        <div class="sim-rec-desc" style="font-size: 0.75rem; color: var(--text-secondary);">${v.observation}</div>
                        <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 0.25rem;">
                            <strong>Reason:</strong> ${v.reason}
                        </div>
                    </div>
                `).join("");
            }
        }

        graphDetailContent.innerHTML = `
            <div class="detail-file-title" style="font-size: 1rem; font-weight: 700; word-break: break-all; margin-bottom: 0.75rem;">${filepath}</div>
            
            <div class="stats-card" style="padding: 1rem; border-radius: 8px; display: flex; flex-direction: column; gap: 0.5rem; background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); margin-bottom: 1rem;">
                <div class="stat-row" style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                    <span class="stat-label" style="color: var(--text-muted);">Risk Level:</span>
                    <span class="stat-value text-${nodeData.level.toLowerCase()}" style="font-weight: 700;">${nodeData.level}</span>
                </div>
                <div class="stat-row" style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                    <span class="stat-label" style="color: var(--text-muted);">Architectural Role:</span>
                    <span class="stat-value" style="color: #a78bfa; font-weight: 600;">${nodeData.role_display || "Internal"}</span>
                </div>
                <div class="stat-row" style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                    <span class="stat-label" style="color: var(--text-muted);">Change Strategy:</span>
                    <span class="stat-value" style="color: #60a5fa; font-weight: 600;">${nodeData.strategy_display || "Safe internal edits"}</span>
                </div>
                <div class="stat-row" style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                    <span class="stat-label" style="color: var(--text-muted);">Impact Score:</span>
                    <span class="stat-value">${(nodeData.impact_score || 0).toFixed(2)}</span>
                </div>
                <div class="stat-row" style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                    <span class="stat-label" style="color: var(--text-muted);">Complexity:</span>
                    <span class="stat-value">${complexity}</span>
                </div>
                <div class="stat-row" style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                    <span class="stat-label" style="color: var(--text-muted);">Coupling:</span>
                    <span class="stat-value">${coupling}</span>
                </div>
            </div>
            
            ${whyHtml}
            
            <div class="sim-block-title" style="margin-top: 1rem; font-weight: 700; font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.5rem;">Smell Warnings</div>
            <div class="sim-recs-list">
                ${violationsHtml}
            </div>
        `;
    }
});
