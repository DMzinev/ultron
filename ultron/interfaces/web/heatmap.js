document.addEventListener("DOMContentLoaded", () => {
    // Elements
    const repoPathInput = document.getElementById("repo-path");
    const scanBtn = document.getElementById("scan-btn");
    const scanSpinner = document.getElementById("scan-spinner");
    const errorBanner = document.getElementById("error-banner");
    const errorMessage = document.getElementById("error-message");
    const closeErrorBtn = document.getElementById("close-error-btn");
    
    const treeContainer = document.getElementById("tree-container");
    const tooltip = document.getElementById("tooltip");
    
    const statTotalFiles = document.getElementById("stat-total-files");
    const statHighFiles = document.getElementById("stat-high-files");
    const statMediumFiles = document.getElementById("stat-medium-files");
    const statLowFiles = document.getElementById("stat-low-files");
    
    const expandAllBtn = document.getElementById("expand-all-btn");
    const collapseAllBtn = document.getElementById("collapse-all-btn");

    // Global Statistics Counter
    let stats = { total: 0, high: 0, medium: 0, low: 0 };

    // Fetch initial configuration on load
    autoInitialize();

    // Event Listeners
    scanBtn.addEventListener("click", () => {
        const repoPath = repoPathInput.value.trim();
        if (repoPath) {
            performScan(repoPath);
        }
    });

    repoPathInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            const repoPath = repoPathInput.value.trim();
            if (repoPath) {
                performScan(repoPath);
            }
        }
    });

    closeErrorBtn.addEventListener("click", hideError);
    
    expandAllBtn.addEventListener("click", () => toggleAll(true));
    collapseAllBtn.addEventListener("click", () => toggleAll(false));

    // Functions
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

    async function performScan(repoPath) {
        hideError();
        showLoading(true);
        stats = { total: 0, high: 0, medium: 0, low: 0 };
        updateStatsUI();
        
        try {
            const response = await fetch("/api/file-tree", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo: repoPath })
            });

            if (!response.ok) {
                let errMsg = `Server returned status ${response.status} ${response.statusText}`;
                try {
                    const errData = await response.json();
                    if (errData && errData.error) {
                        errMsg = errData.error;
                    }
                } catch (_) {
                    // Try getting raw text if JSON parsing fails
                    try {
                        const rawText = await response.text();
                        if (rawText && rawText.length < 500) {
                            errMsg = rawText;
                        }
                    } catch (__) {}
                }
                throw new Error(errMsg);
            }

            const data = await response.json();
            if (data.success && data.tree) {
                renderTree(data.tree);
                updateStatsUI();
            } else {
                throw new Error(data.error || "Failed to scan codebase structure.");
            }
        } catch (err) {
            showError(err.message);
            treeContainer.innerHTML = `
                <div class="empty-state">
                    <p style="color: #ef4444;">Error: ${err.message}</p>
                </div>
            `;
        } finally {
            showLoading(false);
        }
    }

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
        
        // Add indicator based on type
        const arrowSpan = document.createElement("span");
        arrowSpan.className = "node-arrow";
        
        const iconSpan = document.createElement("span");
        iconSpan.className = "node-icon";

        if (node.type === "directory") {
            arrowSpan.textContent = "▶";
            arrowSpan.classList.add("expanded"); // Default open
            iconSpan.textContent = "📁";
            rowDiv.appendChild(arrowSpan);
        } else {
            arrowSpan.style.visibility = "hidden";
            iconSpan.textContent = "📄";
            rowDiv.appendChild(arrowSpan);
            
            // Increment statistics counter for files
            stats.total++;
            if (node.risk) {
                const lvl = (node.risk.level || "").toUpperCase();
                if (lvl === "HIGH") stats.high++;
                else if (lvl === "MEDIUM") stats.medium++;
                else stats.low++;
            }
        }

        rowDiv.appendChild(iconSpan);

        const nameSpan = document.createElement("span");
        nameSpan.className = "node-name";
        nameSpan.textContent = node.name;
        rowDiv.appendChild(nameSpan);

        // Add Risk Level Badge/Chip
        if (node.risk) {
            const riskSpan = document.createElement("span");
            const lvl = (node.risk.level || "LOW").toLowerCase();
            riskSpan.className = `node-risk-chip level-${lvl}`;
            riskSpan.textContent = lvl;
            rowDiv.appendChild(riskSpan);
            
            // Set up custom tooltip listeners
            rowDiv.addEventListener("mouseenter", (e) => {
                showTooltip(e, node.name, node.risk);
            });
            rowDiv.addEventListener("mousemove", (e) => {
                moveTooltip(e);
            });
            rowDiv.addEventListener("mouseleave", () => {
                hideTooltip();
            });
        }

        nodeDiv.appendChild(rowDiv);

        if (node.type === "directory" && node.children) {
            const childrenContainer = document.createElement("div");
            childrenContainer.className = "children-container";
            childrenContainer.style.display = "block"; // Default expanded
            
            node.children.forEach(child => {
                childrenContainer.appendChild(createNodeElement(child));
            });
            
            nodeDiv.appendChild(childrenContainer);
            
            // Toggle Collapsible on Directory Click
            rowDiv.addEventListener("click", (e) => {
                // Prevent toggling if user hovers on file (handled separately by cursor)
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
        }

        return nodeDiv;
    }

    // Tooltip Helpers
    function showTooltip(e, name, riskData) {
        tooltip.innerHTML = `
            <div class="tooltip-title">${name}</div>
            <div class="tooltip-metric">
                <span>Risk Level: <strong>${riskData.level}</strong></span>
                <span>Impact: <strong>${(riskData.impact_score || 0).toFixed(2)}</strong></span>
            </div>
            <div class="tooltip-desc">${riskData.summary || "No description available."}</div>
        `;
        tooltip.classList.remove("hidden");
        tooltip.style.display = "block";
        moveTooltip(e);
    }

    function moveTooltip(e) {
        const padding = 15;
        // Keep tooltip from overflowing screen boundaries
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

    // Controls Helpers
    function toggleAll(expand) {
        const containers = document.querySelectorAll(".children-container");
        const arrows = document.querySelectorAll(".node-arrow");
        
        containers.forEach(container => {
            container.style.display = expand ? "block" : "none";
        });
        
        arrows.forEach(arrow => {
            const row = arrow.closest(".tree-row");
            // Only adjust folders, not files
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

    // Loading & Error States
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

    function updateStatsUI() {
        statTotalFiles.textContent = stats.total;
        statHighFiles.textContent = stats.high;
        statMediumFiles.textContent = stats.medium;
        statLowFiles.textContent = stats.low;
    }
});
