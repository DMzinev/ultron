document.addEventListener("DOMContentLoaded", () => {
    // -------------------------------------------------------------
    // Tab Navigation Logic
    // -------------------------------------------------------------
    const navButtons = document.querySelectorAll(".nav-btn");
    const tabs = document.querySelectorAll(".tab-content");

    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            navButtons.forEach(b => b.classList.remove("active"));
            tabs.forEach(t => t.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(targetTab).classList.add("active");
        });
    });

    // -------------------------------------------------------------
    // Switch Mode Toggle (Creator vs Engineer)
    // -------------------------------------------------------------
    const modeToggle = document.getElementById("mode-toggle");
    const labelCreator = document.getElementById("label-creator");
    const labelEngineer = document.getElementById("label-engineer");

    function applyMode() {
        if (modeToggle.checked) {
            // Engineer Mode active
            document.body.className = "mode-engineer";
            labelEngineer.classList.add("active");
            labelCreator.classList.remove("active");
        } else {
            // Creator Mode active
            document.body.className = "mode-creator";
            labelCreator.classList.add("active");
            labelEngineer.classList.remove("active");
        }
        
        // Re-render dashboard if data exists
        if (codebaseData) {
            renderDashboard(codebaseData);
        }
    }

    modeToggle.addEventListener("change", applyMode);
    applyMode(); // run once on boot

    // -------------------------------------------------------------
    // Sliders UI logic
    // -------------------------------------------------------------
    const sliderTypo = document.getElementById("slider-typo");
    const valTypo = document.getElementById("val-typo");
    sliderTypo.addEventListener("input", (e) => {
        valTypo.textContent = `${e.target.value}%`;
    });

    const sliderProb = document.getElementById("slider-prob");
    const valProb = document.getElementById("val-prob");
    sliderProb.addEventListener("input", (e) => {
        valProb.textContent = `${(e.target.value / 100).toFixed(1)}%`;
    });

    // -------------------------------------------------------------
    // Toast UI logic
    // -------------------------------------------------------------
    const toast = document.getElementById("toast");
    function showToast(message) {
        toast.textContent = message;
        toast.classList.remove("hidden");
        setTimeout(() => {
            toast.classList.add("hidden");
        }, 2500);
    }

    // -------------------------------------------------------------
    // API Server Handlers
    // -------------------------------------------------------------
    const repoInput = document.getElementById("global-repo");
    const loadRepoBtn = document.getElementById("btn-load-repo");
    
    // Core State
    let codebaseData = null;

    loadRepoBtn.addEventListener("click", async () => {
        const repo = repoInput.value.trim();
        if (!repo) {
            alert("Please specify a valid repository path.");
            return;
        }

        loadRepoBtn.disabled = true;
        loadRepoBtn.querySelector("span").textContent = "Connecting...";

        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo })
            });
            const data = await response.json();
            
            if (data.error) {
                alert(`Error: ${data.error}`);
            } else {
                codebaseData = data;
                renderDashboard(data);
                loadFileTree(); // Load visual directory tree
                showToast("Project modules connected!");
            }
        } catch (err) {
            console.error(err);
            alert(`Failed to connect to API server: ${err.message}`);
        } finally {
            loadRepoBtn.disabled = false;
            loadRepoBtn.querySelector("span").textContent = "Connect Project";
        }
    });

    function jsonStringify(obj) {
        return JSON.stringify(obj);
    }

    function renderDashboard(data) {
        // Update stats counters
        document.getElementById("stat-total-files").textContent = data.stats.total_files;
        document.getElementById("stat-total-defs").textContent = data.stats.total_definitions;
        
        const highRiskCount = data.risks.filter(r => r.level === "HIGH").length;
        const highRiskEl = document.getElementById("stat-high-risks");
        highRiskEl.textContent = highRiskCount;
        if (highRiskCount > 0) {
            highRiskEl.classList.add("risk-alert");
        } else {
            highRiskEl.classList.remove("risk-alert");
        }

        // Draw Interactive SVG Graph
        renderSVGGraph(data.risks);

        // Render Engineer Mode Table
        renderRiskTable(data.risks);

        // Render Creator Mode Heatmap
        renderHeatmapGrid(data.risks);

        // Load Verification Report stats
        loadVerificationReport();
    }

    // 1. Draw SVG Topology Graph
    function renderSVGGraph(risks) {
        const svg = document.getElementById("dependency-graph");
        svg.innerHTML = "";
        
        const N = risks.length;
        if (N === 0) return;

        const width = svg.clientWidth || 600;
        const height = 320;
        svg.setAttribute("height", height);

        const cx = width / 2;
        const cy = height / 2;
        const R = Math.min(width, height) * 0.35;

        // Map layout nodes coordinates
        const nodeMap = {};
        risks.forEach((risk, i) => {
            const theta = (2 * Math.PI * i) / N;
            const x = cx + R * Math.cos(theta);
            const y = cy + R * Math.sin(theta);
            nodeMap[risk.file] = { x, y, risk };
        });

        // Collect all connection links (Callers -> Target)
        // Draw links first so they appear behind nodes
        risks.forEach(target => {
            if (target.callers && target.callers.length > 0) {
                target.callers.forEach(caller => {
                    // Try to find if caller is in our scanned files
                    const sourceNode = nodeMap[caller];
                    const targetNode = nodeMap[target.file];
                    
                    if (sourceNode && targetNode) {
                        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                        line.setAttribute("x1", sourceNode.x);
                        line.setAttribute("y1", sourceNode.y);
                        line.setAttribute("x2", targetNode.x);
                        line.setAttribute("y2", targetNode.y);
                        line.setAttribute("class", "link");
                        svg.appendChild(line);
                    }
                });
            }
        });

        // Draw node circles
        Object.keys(nodeMap).forEach(key => {
            const item = nodeMap[key];
            const colorMap = {
                "LOW": "var(--risk-low)",
                "MEDIUM": "var(--risk-med)",
                "HIGH": "var(--risk-high)"
            };
            const color = colorMap[item.risk.level];

            // Glow circle for High Risk zones
            if (item.risk.level === "HIGH") {
                const glowCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                glowCircle.setAttribute("cx", item.x);
                glowCircle.setAttribute("cy", item.y);
                glowCircle.setAttribute("r", 12);
                glowCircle.setAttribute("fill", "none");
                glowCircle.setAttribute("stroke", color);
                glowCircle.setAttribute("class", "node-glow");
                svg.appendChild(glowCircle);
            }

            // Central circle node
            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("cx", item.x);
            circle.setAttribute("cy", item.y);
            circle.setAttribute("r", 10);
            circle.setAttribute("fill", "rgba(13,15,23,0.95)");
            circle.setAttribute("stroke", color);
            circle.setAttribute("stroke-width", "3");
            circle.setAttribute("class", "node");
            
            // Interaction: select as audit target on click
            circle.addEventListener("click", () => {
                document.getElementById("audit-file").value = `${repoInput.value.trim()}/${item.risk.file}`;
                document.getElementById("prompt-files").value = item.risk.file;
                showToast(`Target set to ${item.risk.file}`);
            });
            svg.appendChild(circle);

            // Node text label
            const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
            text.setAttribute("x", item.x);
            text.setAttribute("y", item.y);
            text.setAttribute("dy", "28");
            text.setAttribute("class", "node-text");
            // get only filename basename
            const parts = item.risk.file.split('/');
            text.textContent = parts[parts.length - 1];
            svg.appendChild(text);
        });
    }

    // 2. Render Risk datagrid (Engineer Mode)
    function renderRiskTable(risks) {
        const tbody = document.getElementById("file-risk-tbody");
        tbody.innerHTML = "";

        if (risks.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="table-empty">No modules found.</td></tr>`;
            return;
        }

        risks.forEach(risk => {
            const tr = document.createElement("tr");
            
            const tdFile = document.createElement("td");
            tdFile.className = "file-name";
            tdFile.textContent = risk.file;
            tr.appendChild(tdFile);

            const tdComp = document.createElement("td");
            tdComp.textContent = risk.complexity;
            tr.appendChild(tdComp);

            const tdCoup = document.createElement("td");
            tdCoup.textContent = risk.coupling;
            tr.appendChild(tdCoup);

            const tdScore = document.createElement("td");
            tdScore.style.fontFamily = "var(--font-mono)";
            tdScore.textContent = risk.impact_score.toFixed(2);
            tr.appendChild(tdScore);

            const tdBadge = document.createElement("td");
            const badge = document.createElement("span");
            badge.className = `badge ${risk.level.toLowerCase()}`;
            badge.textContent = risk.level;
            tdBadge.appendChild(badge);
            tr.appendChild(tdBadge);

            // Render Confidence
            const tdConfidence = document.createElement("td");
            const confVal = risk.confidence !== undefined ? risk.confidence : 1.0;
            const confPct = Math.round(confVal * 100);
            const confSpan = document.createElement("span");
            confSpan.className = "confidence-val";
            if (confPct >= 80) {
                confSpan.classList.add("high");
            } else if (confPct >= 50) {
                confSpan.classList.add("medium");
            } else {
                confSpan.classList.add("low");
            }
            confSpan.textContent = `${confPct}%`;
            tdConfidence.appendChild(confSpan);
            tr.appendChild(tdConfidence);

            const tdActions = document.createElement("td");
            const btnTarget = document.createElement("button");
            btnTarget.className = "action-link";
            btnTarget.textContent = "Target";
            btnTarget.addEventListener("click", () => {
                document.getElementById("prompt-files").value = risk.file;
                document.getElementById("nav-prompt").click();
            });
            tdActions.appendChild(btnTarget);

            const btnAudit = document.createElement("button");
            btnAudit.className = "action-link";
            btnAudit.textContent = "Audit";
            btnAudit.addEventListener("click", () => {
                document.getElementById("audit-file").value = `${repoInput.value.trim()}/${risk.file}`;
                document.getElementById("nav-auditor").click();
            });
            tdActions.appendChild(btnAudit);

            // Thumbs Up / Down feedback buttons
            const btnAccurate = document.createElement("button");
            btnAccurate.className = "action-link btn-feedback";
            btnAccurate.innerHTML = "👍";
            btnAccurate.title = "Mark this risk score as Accurate";
            btnAccurate.style.marginRight = "6px";
            btnAccurate.style.transition = "all 0.2s ease";
            btnAccurate.addEventListener("click", async () => {
                await logFeedback(risk.file, true, btnAccurate);
            });
            tdActions.appendChild(btnAccurate);

            const btnInaccurate = document.createElement("button");
            btnInaccurate.className = "action-link btn-feedback";
            btnInaccurate.innerHTML = "👎";
            btnInaccurate.title = "Mark this risk score as Inaccurate (False Positive)";
            btnInaccurate.style.transition = "all 0.2s ease";
            btnInaccurate.addEventListener("click", async () => {
                await logFeedback(risk.file, false, btnInaccurate);
            });
            tdActions.appendChild(btnInaccurate);

            tr.appendChild(tdActions);
            tbody.appendChild(tr);
        });
    }

    async function logFeedback(file, accurate, btn) {
        const repo = repoInput.value.trim();
        try {
            const response = await fetch("/api/log-risk-feedback", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo, file, accurate })
            });
            const data = await response.json();
            if (data.success) {
                btn.style.opacity = "1.0";
                btn.style.transform = "scale(1.2)";
                const row = btn.closest("tr");
                const feedbackBtns = row.querySelectorAll(".btn-feedback");
                feedbackBtns.forEach(b => {
                    if (b !== btn) {
                        b.style.opacity = "0.4";
                        b.style.transform = "none";
                    }
                });
                
                // Trigger re-analysis to immediately scale thresholds
                const btnAnalyze = document.getElementById("btn-analyze-repo");
                if (btnAnalyze) {
                    btnAnalyze.click();
                }
            }
        } catch (err) {
            console.error("Error logging feedback:", err);
        }
    }

    async function loadVerificationReport() {
        const repo = repoInput.value.trim();
        if (!repo) return;
        try {
            const response = await fetch("/api/report", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo })
            });
            const data = await response.json();
            if (data.success) {
                const ratePct = Math.round(data.pledges.success_rate * 100);
                document.getElementById("report-pledge-rate").textContent = `${ratePct}%`;
                document.getElementById("report-mean-error").textContent = data.calibration.mean_error.toFixed(4);
                document.getElementById("report-pledge-counts").textContent = `${data.pledges.active} / ${data.pledges.total}`;
                
                const tbody = document.getElementById("report-calibration-tbody");
                tbody.innerHTML = "";
                if (data.calibration.points.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="3" class="table-empty">No calibration samples.</td></tr>`;
                } else {
                    data.calibration.points.forEach(pt => {
                        const tr = document.createElement("tr");
                        tr.innerHTML = `
                            <td>${pt.bin}</td>
                            <td>${pt.count}</td>
                            <td>${Math.round(pt.actual_rate * 100)}%</td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            }
        } catch (err) {
            console.error("Error loading verification report:", err);
        }
    }

    // 3. Render Heatmap grid (Creator Mode)
    function renderHeatmapGrid(risks) {
        const grid = document.getElementById("creator-heatmap-grid");
        grid.innerHTML = "";

        if (risks.length === 0) {
            grid.innerHTML = `<div class="table-empty">No modules found.</div>`;
            return;
        }

        risks.forEach(risk => {
            const card = document.createElement("div");
            card.className = `heatmap-card ${risk.level.toLowerCase()} glass`;

            const nameParts = risk.file.split('/');
            const baseName = nameParts[nameParts.length - 1];

            const title = document.createElement("span");
            title.className = "heatmap-title";
            title.textContent = baseName;
            card.appendChild(title);

            const desc = document.createElement("span");
            desc.className = "heatmap-desc";
            if (risk.level === "LOW") {
                desc.textContent = "Safe Zone. Easy and safe to change. Modifications won't affect other parts of the app.";
            } else if (risk.level === "MEDIUM") {
                desc.textContent = "Shared Utility. Changing this might impact adjacent pages. Be careful with connection formats.";
            } else {
                desc.textContent = "Core System. Critical boundary. Avoid modifying this directory unless absolutely necessary.";
            }
            card.appendChild(desc);

            const badge = document.createElement("span");
            badge.className = `badge ${risk.level.toLowerCase()} heatmap-badge`;
            badge.textContent = risk.level === "LOW" ? "Safe" : risk.level === "MEDIUM" ? "Moderate" : "Danger Zone";
            card.appendChild(badge);

            grid.appendChild(card);
        });
    }

    // -------------------------------------------------------------
    // Prompt Compiler logic
    // -------------------------------------------------------------
    const generatePromptBtn = document.getElementById("btn-generate-prompt");
    const copyPromptBtn = document.getElementById("btn-copy-prompt");
    const promptOutputBox = document.getElementById("prompt-output-box");

    generatePromptBtn.addEventListener("click", async () => {
        const repo = repoInput.value.trim();
        const intent = document.getElementById("prompt-intent").value.trim();
        const files = document.getElementById("prompt-files").value.trim();

        if (!repo) {
            alert("Please connect your project folder first.");
            return;
        }
        if (!intent) {
            alert("Write down your vision description first.");
            return;
        }

        generatePromptBtn.disabled = true;
        generatePromptBtn.querySelector("span").textContent = "Compiling...";

        try {
            const response = await fetch("/api/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo, intent, files })
            });
            const data = await response.json();
            
            if (data.error) {
                alert(`Error: ${data.error}`);
            } else {
                promptOutputBox.textContent = data.prompt;
                showToast("Instructions compiled!");
            }
        } catch (err) {
            console.error(err);
            alert(`API Error: ${err.message}`);
        } finally {
            generatePromptBtn.disabled = false;
            generatePromptBtn.querySelector("span").textContent = modeToggle.checked ? "Compile AI Instruction Prompt" : "Generate AI Instructions";
        }
    });

    copyPromptBtn.addEventListener("click", () => {
        const text = promptOutputBox.textContent;
        if (!text || text.startsWith("Generated instructions")) return;
        
        navigator.clipboard.writeText(text).then(() => {
            showToast("Copied to clipboard!");
        }).catch(err => {
            alert("Failed to copy: " + err);
        });
    });

    // -------------------------------------------------------------
    // Auditor / Health Shield Logic
    // -------------------------------------------------------------
    const runAuditBtn = document.getElementById("btn-run-audit");
    const anomalyReportsArea = document.getElementById("anomaly-reports");
    const auditStatusEl = document.getElementById("audit-status");
    const healthShield = document.getElementById("health-shield");
    const shieldText = document.getElementById("shield-text");
    const sandboxEditor = document.getElementById("sandbox-editor");

    runAuditBtn.addEventListener("click", async () => {
        const repo = repoInput.value.trim();
        const target_file = document.getElementById("audit-file").value.trim();
        const typo_threshold = sliderTypo.value / 100;
        const prob_threshold = sliderProb.value / 100;
        const sandbox_code = sandboxEditor.value.trim();

        if (!repo) {
            alert("Please connect your project first.");
            return;
        }

        // Must specify target file OR paste sandbox code
        if (!sandbox_code && !target_file) {
            alert("Select a target file to verify or paste code inside the Sandbox Editor.");
            return;
        }

        runAuditBtn.disabled = true;
        runAuditBtn.querySelector("span").textContent = "Auditing...";
        auditStatusEl.textContent = "Auditing...";
        auditStatusEl.className = "report-status";

        // Reset shield state
        healthShield.className = "health-shield";
        shieldText.textContent = "checking";

        try {
            const payload = {
                repo,
                typo_threshold,
                prob_threshold
            };
            if (sandbox_code) {
                payload.code = sandbox_code;
            } else {
                payload.target_file = target_file;
            }

            const response = await fetch("/api/audit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify(payload)
            });
            const data = await response.json();
            
            if (data.error) {
                alert(`Error: ${data.error}`);
                auditStatusEl.textContent = "Error";
                shieldText.textContent = "error";
            } else {
                renderAuditReport(data.anomalies);
            }
        } catch (err) {
            console.error(err);
            alert(`API Error: ${err.message}`);
            auditStatusEl.textContent = "Error";
            shieldText.textContent = "error";
        } finally {
            runAuditBtn.disabled = false;
            runAuditBtn.querySelector("span").textContent = modeToggle.checked ? "Run Anomaly Audit" : "Run Safety Check";
        }
    });

    function renderAuditReport(anomalies) {
        anomalyReportsArea.innerHTML = "";

        const isCreator = !modeToggle.checked;

        if (anomalies.length === 0) {
            auditStatusEl.textContent = isCreator ? "Safe" : "Clean";
            auditStatusEl.className = "report-status clean";
            
            // Set Shield visual state to Green/Clean
            healthShield.className = "health-shield clean";
            shieldText.textContent = "Safe";

            anomalyReportsArea.innerHTML = `
                <div class="report-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="var(--risk-low)" stroke-width="2.5" style="width:48px;height:48px;padding:4px;">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    <h3 style="color:var(--risk-low);font-weight:700;">Code Safety Passed</h3>
                    <p>${isCreator ? "This code aligns perfectly with your system's baseline. It is safe to use!" : "All checked variables, signatures, and call sequences conform to baseline patterns."}</p>
                </div>
            `;
            return;
        }

        auditStatusEl.textContent = `${anomalies.length} Issue(s)`;
        auditStatusEl.className = "report-status anomaly";

        // Set Shield visual state to Red/Alert
        healthShield.className = "health-shield anomaly";
        shieldText.textContent = "Alert";

        anomalies.forEach(anom => {
            const card = document.createElement("div");
            const isTypo = anom.type.includes("Spelling");
            card.className = `anomaly-card ${isTypo ? "typo" : "markov"}`;

            const iconBox = document.createElement("div");
            iconBox.className = "anomaly-icon-box";
            iconBox.innerHTML = isTypo ? `
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                    <path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4z"></path>
                </svg>
            ` : `
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 4 23 10 17 10"></polyline>
                    <polyline points="1 20 1 14 7 14"></polyline>
                    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                </svg>
            `;
            card.appendChild(iconBox);

            const details = document.createElement("div");
            details.className = "anomaly-details";

            const meta = document.createElement("div");
            meta.className = "anomaly-meta";
            
            const typeText = document.createElement("span");
            typeText.className = "anom-type";
            typeText.style.color = isTypo ? "var(--risk-high)" : "var(--neon-purple)";
            
            if (isCreator) {
                typeText.textContent = isTypo ? "Typo Alert" : "Execution Sequence Alert";
            } else {
                typeText.textContent = anom.type;
            }
            meta.appendChild(typeText);

            if (!isCreator && anom.line > 0) {
                const lineText = document.createElement("span");
                lineText.className = "anom-line";
                lineText.textContent = `Line ${anom.line}`;
                meta.appendChild(lineText);
            }
            details.appendChild(meta);

            const text = document.createElement("div");
            text.className = "anom-text";
            
            // Format details in a user-friendly way if in Creator Mode
            if (isCreator) {
                if (isTypo) {
                    // friendly spelling typo format
                    text.textContent = anom.details.replace(
                        "Called identifier", "We detected an unknown word"
                    ).replace(
                        "is not defined in codebase. Did you mean", "which is not in your codebase. We think you meant"
                    );
                } else {
                    // friendly markov sequence format
                    text.textContent = anom.details.replace(
                        "Transition", "The call sequence"
                    ).replace(
                        "has 0.00% occurrence probability in baseline codebase (at or below threshold 0.00%). Highly improbable execution path.",
                        "does not match normal flows. You are calling these components out-of-order."
                    );
                }
            } else {
                text.textContent = anom.details;
            }
            
            details.appendChild(text);
            card.appendChild(details);
            anomalyReportsArea.appendChild(card);
        });
    }

    // -------------------------------------------------------------
    // IDE Workspace & File Explorer System Controllers (v1.4)
    // -------------------------------------------------------------
    const activeFileNameEl = document.getElementById("editor-active-file");
    const unsavedBadgeEl = document.getElementById("editor-unsaved-badge");
    const saveFileBtn = document.getElementById("btn-save-file");
    const lineGutter = document.getElementById("editor-gutter");
    
    let activeFileRelativePath = null;
    let originalFileContent = "";

    async function loadFileTree() {
        const repo = repoInput.value.trim();
        const treeContainer = document.getElementById("file-explorer-tree");
        treeContainer.innerHTML = "<div class='table-empty'>Loading directory structure...</div>";
        
        try {
            const response = await fetch("/api/file-tree", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo })
            });
            const data = await response.json();
            if (data.error) {
                treeContainer.innerHTML = `<div class='table-empty'>Error: ${data.error}</div>`;
            } else {
                treeContainer.innerHTML = "";
                const treeDom = renderTreeNode(data.tree);
                treeContainer.appendChild(treeDom);
            }
        } catch (err) {
            console.error(err);
            treeContainer.innerHTML = "<div class='table-empty'>Failed to load file explorer.</div>";
        }
    }

    function renderTreeNode(nodes) {
        const wrapper = document.createElement("div");
        wrapper.className = "tree-folder-children";
        
        nodes.forEach(node => {
            const nodeEl = document.createElement("div");
            nodeEl.className = "tree-node";
            
            if (node.type === "directory") {
                const folderEl = document.createElement("div");
                folderEl.className = "tree-folder";
                
                const titleEl = document.createElement("div");
                titleEl.className = "tree-folder-title";
                titleEl.innerHTML = `
                    <span class="tree-folder-chevron">▼</span>
                    <span class="tree-folder-icon">📁</span>
                    <span class="tree-folder-name">${node.name}</span>
                `;
                
                titleEl.addEventListener("click", (e) => {
                    e.stopPropagation();
                    folderEl.classList.toggle("collapsed");
                });
                
                folderEl.appendChild(titleEl);
                
                const childrenDom = renderTreeNode(node.children);
                folderEl.appendChild(childrenDom);
                nodeEl.appendChild(folderEl);
            } else {
                const fileEl = document.createElement("div");
                fileEl.className = "tree-file-node";
                fileEl.innerHTML = `
                    <span class="tree-file-icon">📄</span>
                    <span class="tree-file-name">${node.name}</span>
                `;
                
                fileEl.addEventListener("click", (e) => {
                    e.stopPropagation();
                    document.querySelectorAll(".tree-file-node").forEach(n => n.classList.remove("active"));
                    fileEl.classList.add("active");
                    selectFileInWorkspace(node.path);
                });
                nodeEl.appendChild(fileEl);
            }
            wrapper.appendChild(nodeEl);
        });
        return wrapper;
    }

    async function selectFileInWorkspace(filepath) {
        const repo = repoInput.value.trim();
        activeFileRelativePath = filepath;
        activeFileNameEl.textContent = filepath;
        unsavedBadgeEl.classList.add("hidden");
        
        sandboxEditor.value = "# Loading file content...";
        updateLineNumbers();
        
        // Auto-select files in config
        document.getElementById("audit-file").value = `${repo}/${filepath}`;
        document.getElementById("prompt-files").value = filepath;
        
        try {
            const response = await fetch("/api/get-file", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo, file: filepath })
            });
            const data = await response.json();
            if (data.error) {
                sandboxEditor.value = `# Error loading file: ${data.error}`;
            } else {
                sandboxEditor.value = data.content;
                originalFileContent = data.content;
                
                saveFileBtn.classList.remove("disabled");
                saveFileBtn.removeAttribute("disabled");
            }
            updateLineNumbers();
        } catch (err) {
            sandboxEditor.value = `# Failed to load file: ${err.message}`;
            updateLineNumbers();
        }
    }

    function updateLineNumbers() {
        const lines = sandboxEditor.value.split('\n');
        const numLines = lines.length;
        lineGutter.innerHTML = "";
        for (let i = 1; i <= numLines; i++) {
            const span = document.createElement("span");
            span.textContent = i;
            lineGutter.appendChild(span);
        }
    }

    sandboxEditor.addEventListener("input", () => {
        updateLineNumbers();
        if (activeFileRelativePath) {
            if (sandboxEditor.value !== originalFileContent) {
                unsavedBadgeEl.classList.remove("hidden");
            } else {
                unsavedBadgeEl.classList.add("hidden");
            }
        }
    });

    sandboxEditor.addEventListener("scroll", () => {
        lineGutter.scrollTop = sandboxEditor.scrollTop;
    });

    saveFileBtn.addEventListener("click", async () => {
        if (!activeFileRelativePath) return;
        const repo = repoInput.value.trim();
        const content = sandboxEditor.value;
        
        saveFileBtn.disabled = true;
        saveFileBtn.classList.add("disabled");
        saveFileBtn.querySelector("span").textContent = "Saving...";
        
        try {
            const response = await fetch("/api/save-file", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo, file: activeFileRelativePath, content })
            });
            const data = await response.json();
            if (data.error) {
                alert(`Save failed: ${data.error}`);
            } else {
                originalFileContent = content;
                unsavedBadgeEl.classList.add("hidden");
                showToast("File saved to workspace!");
                
                // Re-scans metrics automatically to keep IDE view up to date
                const resp = await fetch("/api/analyze", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: jsonStringify({ repo })
                });
                const scanData = await resp.json();
                if (!scanData.error) {
                    codebaseData = scanData;
                    renderDashboard(scanData);
                }
            }
        } catch (err) {
            alert(`Error saving file: ${err.message}`);
        } finally {
            saveFileBtn.disabled = false;
            saveFileBtn.classList.remove("disabled");
            saveFileBtn.querySelector("span").textContent = "Save Changes";
        }
    });

    const runTestsBtn = document.getElementById("btn-run-tests");
    const terminalLog = document.getElementById("terminal-log");

    runTestsBtn.addEventListener("click", async () => {
        const repo = repoInput.value.trim();
        if (!repo) {
            alert("Connect a repository first.");
            return;
        }
        
        runTestsBtn.disabled = true;
        runTestsBtn.classList.add("disabled");
        runTestsBtn.querySelector("span").textContent = "Running...";
        terminalLog.textContent = "Executing unittest suite...\n$ python -m unittest discover\n\n";
        terminalLog.scrollTop = terminalLog.scrollHeight;
        
        try {
            const response = await fetch("/api/run-tests", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo })
            });
            const data = await response.json();
            if (data.error) {
                terminalLog.textContent += `[Execution Failed]\nError: ${data.error}`;
            } else {
                terminalLog.textContent += data.output;
                terminalLog.textContent += `\n\n[Suite Completed with exit code ${data.exit_code}]`;
                
                // Self-calibration of predicted failing test cases
                const outputStr = data.output || "";
                const failedTests = [...outputStr.matchAll(/(?:FAIL|ERROR): (\w+)/g)].map(m => m[1]);
                
                const predictionItems = document.querySelectorAll(".prediction-item");
                predictionItems.forEach(item => {
                    const testName = item.querySelector(".prediction-name").textContent;
                    // Test name format is test_name
                    if (failedTests.includes(testName)) {
                        item.classList.add("failed");
                        item.classList.remove("success");
                        logSessionEvent("prediction_hit", { test: testName });
                    } else {
                        item.classList.add("success");
                        item.classList.remove("failed");
                        logSessionEvent("prediction_miss", { test: testName });
                    }
                });
                
                logSessionEvent("test_run", { exit_code: data.exit_code, failures: failedTests.length });
                loadVerificationReport();
            }
            terminalLog.scrollTop = terminalLog.scrollHeight;
        } catch (err) {
            terminalLog.textContent += `[Network Error]\nFailed to connect: ${err.message}`;
            terminalLog.scrollTop = terminalLog.scrollHeight;
        } finally {
            runTestsBtn.disabled = false;
            runTestsBtn.classList.remove("disabled");
            runTestsBtn.querySelector("span").textContent = "Run Project Tests";
        }
    });

    // -------------------------------------------------------------
    // Diff-Aware Risk and Test Prediction Logic
    // -------------------------------------------------------------
    let diffTimeout = null;
    sandboxEditor.addEventListener("input", () => {
        // Toggle unsaved badge
        unsavedBadgeEl.classList.remove("hidden");
        
        clearTimeout(diffTimeout);
        diffTimeout = setTimeout(runChangeAnalysis, 800);
    });

    async function runChangeAnalysis() {
        const repo = repoInput.value.trim();
        const content = sandboxEditor.value;
        if (!repo || !activeFileRelativePath || content === originalFileContent) {
            document.getElementById("editor-diff-badge").classList.add("hidden");
            document.getElementById("prediction-list").innerHTML = '<div class="prediction-empty" style="opacity: 0.5; text-align: center; padding: 20px 0;">Make edits in the editor to predict failures.</div>';
            document.getElementById("prediction-status").textContent = "No predictions";
            return;
        }

        try {
            // 1. Fetch Diff Risk Delta
            const resRisk = await fetch("/api/diff-risk", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo, file: activeFileRelativePath, old_code: originalFileContent, new_code: content })
            });
            const dataRisk = await resRisk.json();

            const changedFunctions = [];
            if (dataRisk.success && dataRisk.diff_risk) {
                const dr = dataRisk.diff_risk;
                const badge = document.getElementById("editor-diff-badge");
                const score = dr.delta_score;
                const confPct = Math.round((dr.confidence !== undefined ? dr.confidence : 1.0) * 100);
                badge.textContent = `ΔI: ${score >= 0 ? "+" : ""}${score.toFixed(2)} (Conf: ${confPct}%)`;
                badge.classList.remove("hidden");

                dr.changes.forEach(c => {
                    changedFunctions.push(c.name);
                });
            }

            // 2. Fetch Test Impact Predictions
            const resPredict = await fetch("/api/predict-impact", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo, changed_files: [activeFileRelativePath], changed_functions: changedFunctions })
            });
            const dataPredict = await resPredict.json();

            const predList = document.getElementById("prediction-list");
            const predStatus = document.getElementById("prediction-status");

            if (dataPredict.success && dataPredict.predictions.length > 0) {
                predStatus.textContent = `${dataPredict.predictions.length} tests at risk`;
                predStatus.className = "report-status warning";

                predList.innerHTML = dataPredict.predictions.map(p => `
                    <div class="prediction-item">
                        <span class="prediction-name">${p.test_name}</span>
                        <span class="prediction-reason">${p.reason}</span>
                    </div>
                `).join("");
            } else {
                predStatus.textContent = "All tests safe";
                predStatus.className = "report-status success";
                predList.innerHTML = '<div class="prediction-empty" style="opacity: 0.8; text-align: center; color: var(--risk-low); padding: 20px 0;">✔ No test regressions predicted.</div>';
            }
        } catch (err) {
            console.error("Error during change analysis:", err);
        }
    }

    // -------------------------------------------------------------
    // Repository Dependency Graph Explorer (Force-Directed layout)
    // -------------------------------------------------------------
    let nodes = [];
    let links = [];
    let simRunning = false;
    const navGraph = document.getElementById("nav-graph");

    if (navGraph) {
        navGraph.addEventListener("click", () => {
            loadDependencyGraph();
        });
    }

    async function loadDependencyGraph() {
        const repo = repoInput.value.trim();
        if (!repo) return;
        try {
            const res = await fetch("/api/dependency-graph", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo })
            });
            const data = await res.json();
            if (data.success) {
                renderFullGraph(data.graph);
            }
        } catch (err) {
            console.error("Failed to load dependency graph:", err);
        }
    }

    function renderFullGraph(graph) {
        const svg = document.getElementById("dependency-graph-full");
        if (!svg) return;
        
        // Reset SVG but keep defs
        svg.innerHTML = `
            <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#9aa0a6" />
                </marker>
            </defs>
        `;

        const width = svg.clientWidth || 800;
        const height = svg.clientHeight || 500;

        nodes = graph.nodes.map(n => ({
            ...n,
            x: width / 2 + (Math.random() - 0.5) * 300,
            y: height / 2 + (Math.random() - 0.5) * 300,
            vx: 0,
            vy: 0
        }));

        links = graph.links.map(l => ({
            ...l,
            sourceNode: nodes.find(n => n.id === l.source),
            targetNode: nodes.find(n => n.id === l.target)
        })).filter(l => l.sourceNode && l.targetNode);

        // Render Links
        const linkGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
        links.forEach(l => {
            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.setAttribute("class", `graph-link ${l.type}`);
            if (l.type === "call") {
                line.setAttribute("marker-end", "url(#arrow)");
            }
            l.element = line;
            linkGroup.appendChild(line);
        });
        svg.appendChild(linkGroup);

        // Render Nodes
        const nodeGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
        nodes.forEach(n => {
            const g = document.createElementNS("http://www.w3.org/2000/svg", "g");

            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("class", "node-circle");

            let color = "var(--text-secondary)";
            let r = 6;
            if (n.type === "file") {
                color = "var(--neon-cyan)";
                r = 10;
            } else if (n.type === "function") {
                color = "var(--neon-purple)";
                r = 7;
            }

            circle.setAttribute("fill", color);
            circle.setAttribute("r", r);
            circle.setAttribute("stroke", "rgba(0,0,0,0.6)");

            const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
            text.setAttribute("class", "node-label");
            text.setAttribute("dy", r + 12);
            text.textContent = n.label;

            g.appendChild(circle);
            g.appendChild(text);

            n.element = g;
            n.circle = circle;

            circle.addEventListener("mousedown", (e) => {
                e.preventDefault();
                n.dragged = true;
                svg.style.cursor = "grabbing";
            });

            nodeGroup.appendChild(g);
        });
        svg.appendChild(nodeGroup);

        svg.addEventListener("mousemove", (e) => {
            const rect = svg.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            nodes.forEach(n => {
                if (n.dragged) {
                    n.x = mouseX;
                    n.y = mouseY;
                    n.vx = 0;
                    n.vy = 0;
                }
            });
        });

        window.addEventListener("mouseup", () => {
            nodes.forEach(n => {
                n.dragged = false;
            });
            svg.style.cursor = "grab";
        });

        if (!simRunning) {
            simRunning = true;
            runPhysicsLoop();
        }
    }

    function runPhysicsLoop() {
        const svg = document.getElementById("dependency-graph-full");
        if (!svg) {
            simRunning = false;
            return;
        }

        const width = svg.clientWidth || 800;
        const height = svg.clientHeight || 500;
        const centerX = width / 2;
        const centerY = height / 2;

        const kForce = 0.04;
        const kRepulsion = 1800;
        const kGravity = 0.015;
        const damping = 0.88;
        const desiredDistance = 70;

        // Repulsion
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                const n1 = nodes[i];
                const n2 = nodes[j];
                const dx = n2.x - n1.x;
                const dy = n2.y - n1.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1.0;
                if (dist < 250) {
                    const force = kRepulsion / (dist * dist);
                    const fx = (dx / dist) * force;
                    const fy = (dy / dist) * force;
                    if (!n1.dragged) {
                        n1.vx -= fx;
                        n1.vy -= fy;
                    }
                    if (!n2.dragged) {
                        n2.vx += fx;
                        n2.vy += fy;
                    }
                }
            }
        }

        // Attraction
        links.forEach(l => {
            const n1 = l.sourceNode;
            const n2 = l.targetNode;
            const dx = n2.x - n1.x;
            const dy = n2.y - n1.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1.0;
            const diff = dist - desiredDistance;
            const force = kForce * diff;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            if (!n1.dragged) {
                n1.vx += fx;
                n1.vy += fy;
            }
            if (!n2.dragged) {
                n2.vx -= fx;
                n2.vy -= fy;
            }
        });

        // Update positions
        nodes.forEach(n => {
            if (!n.dragged) {
                const dx = centerX - n.x;
                const dy = centerY - n.y;
                n.vx += dx * kGravity;
                n.vy += dy * kGravity;

                n.x += n.vx;
                n.y += n.vy;

                n.vx *= damping;
                n.vy *= damping;

                n.x = Math.max(15, Math.min(width - 15, n.x));
                n.y = Math.max(15, Math.min(height - 15, n.y));
            }

            if (n.element) {
                n.element.setAttribute("transform", `translate(${n.x}, ${n.y})`);
            }
        });

        links.forEach(l => {
            if (l.element) {
                l.element.setAttribute("x1", l.sourceNode.x);
                l.element.setAttribute("y1", l.sourceNode.y);
                l.element.setAttribute("x2", l.targetNode.x);
                l.element.setAttribute("y2", l.targetNode.y);
            }
        });

        requestAnimationFrame(runPhysicsLoop);
    }

    const btnRefreshGraph = document.getElementById("btn-refresh-graph");
    if (btnRefreshGraph) {
        btnRefreshGraph.addEventListener("click", loadDependencyGraph);
    }

    // -------------------------------------------------------------
    // Empirical Human Study Session Logger Telemetry
    // -------------------------------------------------------------
    let sessionActive = false;
    let sessionStartTime = null;
    let sessionTimerId = null;
    let sessionLogs = null;

    const btnStartSession = document.getElementById("btn-start-session");
    const btnStopSession = document.getElementById("btn-stop-session");
    const sessionTimerEl = document.getElementById("session-timer");

    function logSessionEvent(type, metadata = {}) {
        if (!sessionActive) return;
        sessionLogs.events.push({
            timestamp: new Date().toISOString(),
            type,
            ...metadata
        });
        if (type === "save") sessionLogs.saves++;
        if (type === "audit") sessionLogs.audits++;
        if (type === "test_run") sessionLogs.test_runs++;
        if (type === "prediction_hit") sessionLogs.prediction_hits++;
        if (type === "prediction_miss") sessionLogs.prediction_misses++;
    }

    if (btnStartSession) {
        btnStartSession.addEventListener("click", () => {
            sessionActive = true;
            sessionStartTime = new Date();
            sessionLogs = {
                saves: 0,
                audits: 0,
                test_runs: 0,
                prediction_hits: 0,
                prediction_misses: 0,
                events: []
            };

            btnStartSession.classList.add("hidden");
            btnStopSession.classList.remove("hidden");
            sessionTimerEl.classList.remove("hidden");
            sessionTimerEl.classList.add("session-timer-pulse");

            let elapsed = 0;
            sessionTimerId = setInterval(() => {
                elapsed++;
                const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
                const secs = String(elapsed % 60).padStart(2, '0');
                sessionTimerEl.textContent = `${mins}:${secs}`;
            }, 1000);

            showToast("Study Session started! Telemetry active.");
            logSessionEvent("session_start");
        });
    }

    if (btnStopSession) {
        btnStopSession.addEventListener("click", async () => {
            sessionActive = false;
            clearInterval(sessionTimerId);
            sessionTimerEl.classList.add("hidden");
            sessionTimerEl.classList.remove("session-timer-pulse");
            btnStopSession.classList.add("hidden");
            btnStartSession.classList.remove("hidden");

            const elapsedSecs = Math.floor((new Date() - sessionStartTime) / 1000);
            sessionLogs.elapsed_seconds = elapsedSecs;
            logSessionEvent("session_stop");

            // Save session to server
            const repo = repoInput.value.trim();
            if (repo) {
                try {
                    const res = await fetch("/api/save-session", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: jsonStringify({ repo, session_data: sessionLogs })
                    });
                    const data = await res.json();
                    if (data.success) {
                        showToast(`Session logs saved: ${data.filename}`);
                    }
                } catch (err) {
                    console.error("Failed to save session logs:", err);
                }
            }

            // Export as download
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(sessionLogs, null, 2));
            const downloadAnchor = document.createElement('a');
            downloadAnchor.setAttribute("href", dataStr);
            downloadAnchor.setAttribute("download", `ultron_session_${new Date().getTime()}.json`);
            document.body.appendChild(downloadAnchor);
            downloadAnchor.click();
            downloadAnchor.remove();
        });
    }

    // Hook existing UI clicks to log telemetry
    // Intercept clicks
    saveFileBtn.addEventListener("click", () => {
        logSessionEvent("save", { file: activeFileRelativePath });
    });

    const auditBtn = document.getElementById("btn-run-audit");
    auditBtn.addEventListener("click", () => {
        logSessionEvent("audit", { file: activeFileRelativePath });
    });

    // -------------------------------------------------------------
    // Auto-Calibration logic
    // -------------------------------------------------------------
    const btnCalibrate = document.getElementById("btn-calibrate");
    const calibrationResults = document.getElementById("calibration-results");

    if (btnCalibrate) {
        btnCalibrate.addEventListener("click", async () => {
            const repo = repoInput.value.trim();
            if (!repo) {
                alert("Please connect a project first.");
                return;
            }

            btnCalibrate.disabled = true;
            btnCalibrate.querySelector("span").textContent = "Calibrating...";
            calibrationResults.style.display = "none";

            try {
                const response = await fetch("/api/calibrate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: jsonStringify({ repo })
                });
                const data = await response.json();

                if (data.error) {
                    alert(`Calibration error: ${data.error}`);
                } else if (data.success) {
                    // Update Typo Similarity slider
                    const typoVal = Math.round(data.optimal_typo_threshold * 100);
                    sliderTypo.value = typoVal;
                    valTypo.textContent = `${typoVal}%`;

                    // Update Transition Prob slider
                    const probVal = Math.round(data.optimal_prob_threshold * 100);
                    sliderProb.value = probVal;
                    valProb.textContent = `${(probVal / 100).toFixed(1)}%`;

                    // Build Sweep History HTML table
                    let tableHTML = `
                        <div style="font-weight:700; color:var(--neon-cyan); margin-bottom:6px;">Sweep Results (Max F1: ${data.max_f1.toFixed(2)})</div>
                        <table>
                            <thead>
                                <tr>
                                    <th>T_typo</th>
                                    <th>Precision</th>
                                    <th>Recall</th>
                                    <th>F1 Score</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;

                    data.sweep_history.forEach(item => {
                        const isOptimal = Math.abs(item.typo_threshold - data.optimal_typo_threshold) < 0.001;
                        tableHTML += `
                            <tr class="${isOptimal ? 'optimal' : ''}">
                                <td>${item.typo_threshold.toFixed(2)}</td>
                                <td>${item.precision.toFixed(2)}</td>
                                <td>${item.recall.toFixed(2)}</td>
                                <td>${item.f1_score.toFixed(2)}</td>
                            </tr>
                        `;
                    });

                    tableHTML += `
                            </tbody>
                        </table>
                    `;
                    calibrationResults.innerHTML = tableHTML;
                    calibrationResults.style.display = "block";
                    showToast("Thresholds calibrated!");
                    
                    if (sessionActive) {
                        logSessionEvent("calibrate", { optimal_typo: data.optimal_typo_threshold, optimal_prob: data.optimal_prob_threshold });
                    }
                }
            } catch (err) {
                console.error("Calibration request failed:", err);
                alert(`API Error: ${err.message}`);
            } finally {
                btnCalibrate.disabled = false;
                btnCalibrate.querySelector("span").textContent = "Calibrate Thresholds";
            }
        });
    }

    // -------------------------------------------------------------
    // Demo Playground Quick Start handler (v1.7)
    // -------------------------------------------------------------
    const loadPlaygroundBtn = document.getElementById("btn-load-playground");
    if (loadPlaygroundBtn) {
        loadPlaygroundBtn.addEventListener("click", async () => {
            loadPlaygroundBtn.disabled = true;
            loadPlaygroundBtn.querySelector("span").textContent = "Creating...";

            try {
                const response = await fetch("/api/playground", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" }
                });
                const data = await response.json();

                if (data.error) {
                    alert(`Playground creation failed: ${data.error}`);
                } else if (data.success) {
                    // Automatically fill the repo input and connect
                    repoInput.value = data.path;
                    loadRepoBtn.click();
                    showToast("Playground Connected!");
                }
            } catch (err) {
                console.error("Playground request failed:", err);
                alert(`API Error: ${err.message}`);
            } finally {
                loadPlaygroundBtn.disabled = false;
                loadPlaygroundBtn.querySelector("span").textContent = "Demo Playground";
            }
        });
    }

    // -------------------------------------------------------------
    // Onboarding Tour Modal Logic (v1.7)
    // -------------------------------------------------------------
    const tourModal = document.getElementById("tour-modal");
    const openTourBtn = document.getElementById("btn-open-tour");
    const closeTourBtn = document.getElementById("btn-close-tour");
    const prevSlideBtn = document.getElementById("btn-prev-slide");
    const nextSlideBtn = document.getElementById("btn-next-slide");
    const slides = document.querySelectorAll(".tour-slide");
    const dots = document.querySelectorAll(".tour-dot");

    let currentSlide = 0;

    function showSlide(index) {
        currentSlide = index;
        slides.forEach((slide, i) => {
            slide.classList.toggle("active", i === index);
        });
        dots.forEach((dot, i) => {
            dot.classList.toggle("active", i === index);
            dot.style.background = i === index ? "var(--neon-cyan)" : "rgba(255,255,255,0.2)";
        });

        prevSlideBtn.disabled = index === 0;
        prevSlideBtn.classList.toggle("disabled", index === 0);
        
        if (index === slides.length - 1) {
            nextSlideBtn.querySelector("span").textContent = "Get Started";
        } else {
            nextSlideBtn.querySelector("span").textContent = "Next";
        }
    }

    if (openTourBtn && tourModal) {
        openTourBtn.addEventListener("click", () => {
            tourModal.classList.remove("hidden");
            showSlide(0);
        });
        
        // Show automatically for first-time visitors who don't have a repo loaded yet
        setTimeout(() => {
            if (!codebaseData && tourModal.classList.contains("hidden")) {
                tourModal.classList.remove("hidden");
                showSlide(0);
            }
        }, 1200);
    }

    if (closeTourBtn && tourModal) {
        closeTourBtn.addEventListener("click", () => {
            tourModal.classList.add("hidden");
        });
    }

    if (prevSlideBtn) {
        prevSlideBtn.addEventListener("click", () => {
            if (currentSlide > 0) showSlide(currentSlide - 1);
        });
    }

    if (nextSlideBtn) {
        nextSlideBtn.addEventListener("click", () => {
            if (currentSlide < slides.length - 1) {
                showSlide(currentSlide + 1);
            } else {
                tourModal.classList.add("hidden");
            }
        });
    }

    dots.forEach((dot, index) => {
        dot.addEventListener("click", () => showSlide(index));
    });

    // -------------------------------------------------------------
    // Real-Time Thoughts-to-Creation Analyzer (v1.7)
    // -------------------------------------------------------------
    const promptIntentInput = document.getElementById("prompt-intent");
    const creatorRiskAssistant = document.getElementById("creator-risk-assistant");
    const creatorAssistantText = document.getElementById("creator-assistant-text");

    if (promptIntentInput && creatorRiskAssistant && creatorAssistantText) {
        promptIntentInput.addEventListener("input", () => {
            const val = promptIntentInput.value.trim().toLowerCase();
            if (val.length < 8) {
                creatorRiskAssistant.style.display = "none";
                return;
            }

            creatorRiskAssistant.style.display = "block";
            
            if (!codebaseData) {
                creatorAssistantText.innerHTML = `⚠️ <span style="color:var(--risk-med);">No project connected.</span> Connect a repository or click "Demo Playground" above to analyze potential risks.`;
                return;
            }

            // Simple semantic keyword matching
            const matchedFiles = [];
            const keywords = val.split(/\s+/).filter(w => w.length > 3);
            
            codebaseData.risks.forEach(item => {
                const parts = item.file.toLowerCase().split('/');
                const baseName = parts[parts.length - 1];
                
                // Match keywords against filename or callers
                const hasKeyword = keywords.some(kw => 
                    baseName.includes(kw) || 
                    item.file.toLowerCase().includes(kw)
                );
                
                if (hasKeyword) {
                    matchedFiles.push(item);
                }
            });

            if (matchedFiles.length > 0) {
                let textHTML = `<span style="color:var(--neon-cyan); font-weight:700;">Intent Analysis Output:</span><br/>`;
                textHTML += `Your description suggests modifications to: <br/>`;
                
                matchedFiles.forEach(file => {
                    const levelColor = file.level === "HIGH" ? "var(--risk-high)" : file.level === "MEDIUM" ? "var(--risk-med)" : "var(--risk-low)";
                    textHTML += `* <strong style="color:var(--text-primary);">${file.file}</strong> (<span style="color:${levelColor}; font-weight:700;">${file.level} Risk</span>)<br/>`;
                    textHTML += `  - <em>Risk advice: ${file.mitigation}</em><br/>`;
                });
                
                // Auto-fill Target files input box to ease user thoughts-to-creation transition
                const targetFiles = matchedFiles.map(f => f.file).join(", ");
                document.getElementById("prompt-files").value = targetFiles;
                
                creatorAssistantText.innerHTML = textHTML;
            } else {
                creatorAssistantText.innerHTML = `🔍 Thoughts analysis active. No exact file matches found in codebase. Type keywords matching python modules (e.g. 'math' or 'calculator') to show live boundary foresight.`;
            }
        });
    }
});
