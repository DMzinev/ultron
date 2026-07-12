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

    // Tab Navigation switching
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            tabBtns.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(targetTab).classList.add("active");
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
    }
});
