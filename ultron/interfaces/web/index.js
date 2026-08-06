    let codebaseData = null;
    let hotspotsCache = { repo: "", data: null };

    // -------------------------------------------------------------
    // Environment Health Diagnostic Check
    // -------------------------------------------------------------
    const envHealthDot = document.getElementById("env-health-dot");
    const envHealthLabel = document.getElementById("env-health-label");
    const envHealthBadge = document.getElementById("env-health-badge");
    const systemStatusDot = document.getElementById("system-status-dot");
    const systemStatusText = document.getElementById("system-status-text");

    async function initEnvironmentHealthCheck() {
        try {
            const res = await fetch("/api/v1/health");
            const data = await res.json();
            if (data.status === "healthy") {
                const dbOk = data.rkm_database?.exists;
                const modulesOk = data.modules?.design_oracle && data.modules?.delta_engine;
                
                let color = "#38bdf8";
                let text = "Server Online";

                if (dbOk && modulesOk) {
                    color = "#34d399";
                    text = "Operational (RKM)";
                } else if (dbOk) {
                    color = "#fbbf24";
                    text = "RKM Online";
                }

                if (envHealthDot) envHealthDot.style.background = color;
                if (envHealthLabel) {
                    envHealthLabel.style.color = color;
                    envHealthLabel.textContent = text;
                }

                if (systemStatusDot) systemStatusDot.style.background = color;
                if (systemStatusText) {
                    systemStatusText.style.color = color;
                    systemStatusText.textContent = text;
                }

                if (envHealthBadge) {
                    envHealthBadge.title = `Python ${data.environment?.python_version} (${data.environment?.platform})\nDB: ${dbOk ? 'Ready' : 'Not Init'}\nModules: Oracle=${data.modules?.design_oracle ? 'Yes':'No'}, Delta=${data.modules?.delta_engine ? 'Yes':'No'}`;
                }
            } else {
                if (envHealthDot) envHealthDot.style.background = "#ef4444";
                if (envHealthLabel) {
                    envHealthLabel.style.color = "#ef4444";
                    envHealthLabel.textContent = "Unhealthy";
                }
                if (systemStatusDot) systemStatusDot.style.background = "#ef4444";
                if (systemStatusText) {
                    systemStatusText.style.color = "#ef4444";
                    systemStatusText.textContent = "Unhealthy";
                }
            }
        } catch (err) {
            if (envHealthDot) envHealthDot.style.background = "#ef4444";
            if (envHealthLabel) {
                envHealthLabel.style.color = "#ef4444";
                envHealthLabel.textContent = "Offline";
            }
            if (systemStatusDot) systemStatusDot.style.background = "#ef4444";
            if (systemStatusText) {
                systemStatusText.style.color = "#ef4444";
                systemStatusText.textContent = "Offline";
            }
        }
    }
    initEnvironmentHealthCheck();

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function setButtonText(btn, text) {
        if (!btn) return;
        const spans = btn.querySelectorAll("span");
        if (spans.length > 0) {
            spans.forEach(span => {
                span.textContent = text;
            });
        } else {
            btn.textContent = text;
        }
    }

    // -------------------------------------------------------------
    // Tab Navigation Logic
    // -------------------------------------------------------------
    const navButtons = document.querySelectorAll(".nav-btn");
    const tabs = document.querySelectorAll(".tab-content");

    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            navButtons.forEach(b => b.classList.remove("active"));
            tabs.forEach(t => {
                t.classList.remove("active");
                t.style.display = "none";
            });
            
            btn.classList.add("active");
            const activeTabEl = document.getElementById(targetTab);
            if (activeTabEl) {
                activeTabEl.classList.add("active");
                activeTabEl.style.display = "flex";
                
                // Re-render SVG Graph if Dependency Graph tab activated
                if (targetTab === "graph-tab" && codebaseData && codebaseData.risks) {
                    renderSVGGraph(codebaseData.risks);
                }
            }
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
            if (labelEngineer) labelEngineer.classList.add("active");
            if (labelCreator) labelCreator.classList.remove("active");
        } else {
            // Creator Mode active
            document.body.className = "mode-creator";
            if (labelCreator) labelCreator.classList.add("active");
            if (labelEngineer) labelEngineer.classList.remove("active");
        }
        
        // Re-render dashboard if data exists
        if (codebaseData) {
            renderDashboard(codebaseData);
        }
    }

    if (labelCreator) {
        labelCreator.addEventListener("click", () => {
            if (modeToggle.checked) {
                modeToggle.checked = false;
                applyMode();
            }
        });
    }

    if (labelEngineer) {
        labelEngineer.addEventListener("click", () => {
            if (!modeToggle.checked) {
                modeToggle.checked = true;
                applyMode();
            }
        });
    }

    if (modeToggle) {
        modeToggle.addEventListener("change", applyMode);
        applyMode(); // run once on boot
    }

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
    // (codebaseData declared at top of DOMContentLoaded to prevent TDZ ReferenceError)

    const btnBrowseFolder = document.getElementById("btn-browse-folder");
    if (btnBrowseFolder) {
        btnBrowseFolder.addEventListener("click", async () => {
            btnBrowseFolder.disabled = true;
            try {
                const initial_dir = repoInput.value.trim() || ".";
                const response = await fetch("/api/browse-folder", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: jsonStringify({ initial_dir })
                });
                const data = await response.json();
                if (data.path) {
                    repoInput.value = data.path;
                    showToast("Folder selected!");
                    loadRepoBtn.click();
                } else if (data.fallback) {
                    showToast("Native folder picker unavailable. Please type path manually.");
                }
            } catch (err) {
                console.error("Browse folder error:", err);
                showToast("Failed to open folder picker.");
            } finally {
                btnBrowseFolder.disabled = false;
            }
        });
    }

    const repoErrorBanner = document.getElementById("repo-error-banner");
    const repoErrorMessage = document.getElementById("repo-error-message");

    loadRepoBtn.addEventListener("click", async () => {
        hotspotsCache = { repo: "", data: null }; // invalidate cache on new load or re-analysis
        const repo = repoInput.value.trim();
        if (!repo) {
            if (repoErrorBanner) {
                repoErrorBanner.classList.remove("hidden");
                repoErrorMessage.textContent = "Please specify a valid repository path or click 'Browse...'.";
            }
            return;
        }

        loadRepoBtn.disabled = true;
        setButtonText(loadRepoBtn, "Connecting...");
        if (repoErrorBanner) repoErrorBanner.classList.add("hidden");

        // Show loading indicator immediately — hide only on success, failure, or cancel
        const progressCard = document.getElementById("analysis-progress-card");
        const progressStepText = document.getElementById("progress-step-text");
        const progressBarFill = document.getElementById("progress-bar-fill");
        if (progressCard) {
            progressCard.classList.remove("hidden");
            if (progressStepText) progressStepText.textContent = "Connecting to repository...";
            if (progressBarFill) progressBarFill.style.width = "15%";
        }

        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo })
            });
            const data = await response.json();
            
            if (data.error) {
                if (repoErrorBanner) {
                    repoErrorBanner.classList.remove("hidden");
                    repoErrorMessage.textContent = data.error;
                } else {
                    showToast(`Error: ${data.error}`);
                }
            } else {
                if (repoErrorBanner) repoErrorBanner.classList.add("hidden");
                codebaseData = data;
                renderDashboard(data);
                loadFileTree(); // Load visual directory tree
                showToast("Project modules connected!");
            }
        } catch (err) {
            console.error(err);
            if (repoErrorBanner) {
                repoErrorBanner.classList.remove("hidden");
                repoErrorMessage.textContent = `Failed to connect to API server: ${err.message}`;
            } else {
                showToast(`Connection error: ${err.message}`);
            }
        } finally {
            loadRepoBtn.disabled = false;
            setButtonText(loadRepoBtn, "Connect Project");
            // Hide progress card on resolution
            if (progressCard) progressCard.classList.add("hidden");
        }
    });

    function jsonStringify(obj) {
        return JSON.stringify(obj);
    }

    function setActionsEnabled(enabled) {
        const actionBtnIds = ["btn-run-audit", "btn-calibrate", "btn-detail-ai-explain", "btn-generate-prompt", "btn-auto-push-ai"];
        actionBtnIds.forEach(id => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.disabled = !enabled;
                btn.title = enabled ? "" : "Connect a project folder to unlock this action.";
                if (!enabled) {
                    btn.style.opacity = "0.5";
                    btn.style.cursor = "not-allowed";
                } else {
                    btn.style.opacity = "1.0";
                    btn.style.cursor = "pointer";
                }
            }
        });
    }

    function renderExecutiveHeroBanner(data) {
        const heroScore = document.getElementById("hero-health-score");
        const heroStatus = document.getElementById("hero-health-status");
        const heroRisk1File = document.getElementById("hero-top-risk-1-file");
        const heroRisk1Score = document.getElementById("hero-top-risk-1-score");
        const heroRisk2File = document.getElementById("hero-top-risk-2-file");
        const heroRisk2Score = document.getElementById("hero-top-risk-2-score");

        if (!data || !data.risks) return;

        const risks = [...data.risks].sort((a, b) => (b.impact_score || b.complexity) - (a.impact_score || a.complexity));
        const highCount = risks.filter(r => r.level === "HIGH").length;
        const healthScore = Math.max(40, Math.round(100 - (highCount * 8)));

        if (heroScore) heroScore.textContent = `${healthScore} / 100`;
        if (heroStatus) {
            if (healthScore >= 80) {
                heroStatus.textContent = "✓ Repository Healthy";
                heroStatus.style.color = "#4ade80";
            } else if (healthScore >= 60) {
                heroStatus.textContent = "⚠️ Moderate Structural Risk";
                heroStatus.style.color = "#f59e0b";
            } else {
                heroStatus.textContent = "🔴 Critical Refactoring Required";
                heroStatus.style.color = "#f43f5e";
            }
        }

        if (risks.length > 0 && heroRisk1File) {
            heroRisk1File.textContent = risks[0].file;
            if (heroRisk1Score) heroRisk1Score.textContent = `Complexity: ${risks[0].complexity} (${risks[0].level} Priority)`;
        } else if (heroRisk1File) {
            heroRisk1File.textContent = "No risks detected";
            if (heroRisk1Score) heroRisk1Score.textContent = "Clean codebase";
        }

        if (risks.length > 1 && heroRisk2File) {
            heroRisk2File.textContent = risks[1].file;
            if (heroRisk2Score) heroRisk2Score.textContent = `Complexity: ${risks[1].complexity} (${risks[1].level} Priority)`;
        } else if (heroRisk2File) {
            heroRisk2File.textContent = "None";
            if (heroRisk2Score) heroRisk2Score.textContent = "Single file analyzed";
        }
    }

    // Set initial button state to locked until project is connected
    setActionsEnabled(false);

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

        // Dynamically compute and render Executive Hero Banner from real AST data
        renderExecutiveHeroBanner(data);

        // Unlock action buttons & interactive controls
        setActionsEnabled(true);

        // Draw Interactive SVG Graph
        renderSVGGraph(data.risks);

        // Render Engineer Mode Table
        renderRiskTable(data.risks);

        // Fetch Top Architectural Recommendations
        fetchRecommendations();

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
        if (!tbody) return;
        tbody.innerHTML = "";

        if (!risks || risks.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="table-empty">No modules found.</td></tr>`;
            return;
        }

        risks.forEach(risk => {
            const tr = document.createElement("tr");
            
            const tdFile = document.createElement("td");
            tdFile.className = "file-name";
            tdFile.textContent = risk.file;
            tdFile.style.cursor = "pointer";
            tdFile.style.textDecoration = "underline";
            tdFile.title = "Click to open Entity Profile and Machine-to-Human translation";
            tdFile.addEventListener("click", () => window.openEntityDetail(risk.file));
            tr.appendChild(tdFile);

            const tdComp = document.createElement("td");
            tdComp.textContent = risk.complexity;
            tr.appendChild(tdComp);

            const tdCoup = document.createElement("td");
            tdCoup.textContent = risk.coupling;
            tr.appendChild(tdCoup);

            const tdScore = document.createElement("td");
            tdScore.style.fontFamily = "var(--font-mono)";
            tdScore.textContent = (risk.impact_score || 0).toFixed(2);
            tr.appendChild(tdScore);

            const tdBadge = document.createElement("td");
            const badge = document.createElement("span");
            badge.className = `badge ${(risk.level || "MEDIUM").toLowerCase()}`;
            badge.textContent = risk.level || "MEDIUM";
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
                const promptFiles = document.getElementById("prompt-files");
                if (promptFiles) promptFiles.value = risk.file;
                const navPrompt = document.getElementById("nav-prompt");
                if (navPrompt) navPrompt.click();
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
                if (row) {
                    const feedbackBtns = row.querySelectorAll(".btn-feedback");
                    feedbackBtns.forEach(b => {
                        if (b !== btn) {
                            b.style.opacity = "0.4";
                            b.style.transform = "none";
                        }
                    });
                }
                const btnAnalyze = document.getElementById("btn-load-repo");
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
                if (tbody) {
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
            }
        } catch (err) {
            console.error("Error loading verification report:", err);
        }
    }

    // 3. Render Heatmap grid (Creator Mode)
    function renderHeatmapGrid(risks) {
        const grid = document.getElementById("creator-heatmap-grid");
        if (!grid) return;
        grid.innerHTML = "";

        if (risks.length === 0) {
            grid.innerHTML = `<div class="table-empty">No modules found.</div>`;
            return;
        }

        risks.forEach(risk => {
            const card = document.createElement("div");
            card.className = `heatmap-card ${risk.level.toLowerCase()} glass`;
            card.style.cursor = "pointer";
            card.title = "Click to open Entity Profile and Machine-to-Human translation";
            card.addEventListener("click", () => window.openEntityDetail(risk.file));

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

    const runAuditBtn = document.getElementById("btn-run-audit");
    const auditFile = document.getElementById("audit-file");
    const auditStatusEl = document.getElementById("audit-status");
    const healthShield = document.getElementById("health-shield");
    const shieldText = document.getElementById("shield-text");
    const anomalyReportsArea = document.getElementById("anomaly-reports");

    if (runAuditBtn) {
        runAuditBtn.addEventListener("click", async () => {
            const repo = repoInput ? repoInput.value.trim() : ".";
            const target_file = auditFile ? auditFile.value : "";
            const typo_threshold = sliderTypo ? parseFloat(sliderTypo.value) : 15.0;
            const prob_threshold = sliderProb ? parseFloat(sliderProb.value) : 0.95;
            const sandbox_code = sandboxEditor ? sandboxEditor.value : "";

            runAuditBtn.disabled = true;
            if (typeof logSessionEvent === "function") {
                logSessionEvent("audit", { file: activeFileRelativePath });
            }
        setButtonText(runAuditBtn, "Auditing...");
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
                showToast(`Audit error: ${data.error}`);
                auditStatusEl.textContent = "Error";
                shieldText.textContent = "error";
            } else {
                renderAuditReport(data.anomalies);
            }
        } catch (err) {
            console.error(err);
            showToast(`API error: ${err.message}`);
            auditStatusEl.textContent = "Error";
            shieldText.textContent = "error";
        } finally {
            runAuditBtn.disabled = false;
            setButtonText(runAuditBtn, modeToggle.checked ? "Run Anomaly Audit" : "Run Safety Check");
        }
    });
}

    const btnGeneratePrompt = document.getElementById("btn-generate-prompt");
    const btnCopyPrompt = document.getElementById("btn-copy-prompt");

    if (btnGeneratePrompt) {
        btnGeneratePrompt.addEventListener("click", async () => {
            const repo = repoInput ? repoInput.value.trim() : ".";
            const files = document.getElementById("prompt-files") ? document.getElementById("prompt-files").value : "";
            const intent = document.getElementById("prompt-intent") ? document.getElementById("prompt-intent").value : "";
            const promptOutput = document.getElementById("prompt-output");

            btnGeneratePrompt.disabled = true;
            try {
                const response = await fetch("/api/v1/context-brief", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: jsonStringify({ repo, intent, target_files: files ? [files] : [] })
                });
                const data = await response.json();
                if (promptOutput) {
                    promptOutput.value = data.brief || data.vibe_context_envelope || JSON.stringify(data, null, 2);
                }
                showToast("AI Context Brief generated successfully!");
            } catch (err) {
                console.error(err);
                showToast(`Error generating prompt: ${err.message}`);
            } finally {
                btnGeneratePrompt.disabled = false;
            }
        });
    }

    if (btnCopyPrompt) {
        btnCopyPrompt.addEventListener("click", () => {
            const promptOutput = document.getElementById("prompt-output");
            if (promptOutput && promptOutput.value) {
                navigator.clipboard.writeText(promptOutput.value);
                showToast("Prompt copied to clipboard!");
            }
        });
    }

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
                    <span class="tree-file-info-btn" style="margin-left:auto; opacity:0.6; cursor:pointer; font-size:11px;" title="View Entity Profile">ℹ️</span>
                `;
                
                const infoBtn = fileEl.querySelector(".tree-file-info-btn");
                infoBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    window.openEntityDetail(node.name, "file");
                });
                
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
        if (activeFileRelativePath && repoInput.value.trim()) {
            clearTimeout(editorChangeTimeout);
            editorChangeTimeout = setTimeout(runChangeAnalysis, 800);
        }
    });

    sandboxEditor.addEventListener("scroll", () => {
        lineGutter.scrollTop = sandboxEditor.scrollTop;
    });

    saveFileBtn.addEventListener("click", async () => {
        if (!activeFileRelativePath) return;
        const repo = repoInput.value.trim();
        const content = sandboxEditor.value;
        
        if (typeof logSessionEvent === "function") {
            logSessionEvent("save", { file: activeFileRelativePath });
        }
        saveFileBtn.disabled = true;
        saveFileBtn.classList.add("disabled");
        setButtonText(saveFileBtn, "Saving...");
        
        try {
            const response = await fetch("/api/save-file", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo, file: activeFileRelativePath, content })
            });
            const data = await response.json();
            if (data.error) {
                showToast(`Save failed: ${data.error}`);
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
            showToast(`Save error: ${err.message}`);
        } finally {
            saveFileBtn.disabled = false;
            saveFileBtn.classList.remove("disabled");
            setButtonText(saveFileBtn, "Save Changes");
        }
    });

    const runTestsBtn = document.getElementById("btn-run-tests");
    const terminalLog = document.getElementById("terminal-log");

    runTestsBtn.addEventListener("click", async () => {
        const repo = repoInput.value.trim();
        if (!repo) {
            showToast("Connect a repository first.");
            return;
        }
        
        runTestsBtn.disabled = true;
        runTestsBtn.classList.add("disabled");
        setButtonText(runTestsBtn, "Running...");
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
            setButtonText(runTestsBtn, "Run Project Tests");
        }
    });

    // -------------------------------------------------------------
    // Diff-Aware Risk and Test Prediction Logic
    // -------------------------------------------------------------
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
        const svg = document.getElementById("dependency-graph-full");
        if (svg) {
            const loadingText = document.createElementNS("http://www.w3.org/2000/svg", "text");
            loadingText.setAttribute("x", "50%");
            loadingText.setAttribute("y", "50%");
            loadingText.setAttribute("text-anchor", "middle");
            loadingText.setAttribute("fill", "#38bdf8");
            loadingText.setAttribute("font-size", "14px");
            loadingText.setAttribute("id", "graph-loading-text");
            loadingText.textContent = "Loading dependency graph topology...";
            svg.appendChild(loadingText);
        }
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
            if (svg) {
                const loadingText = svg.querySelector("#graph-loading-text");
                if (loadingText) loadingText.textContent = "Failed to load graph.";
            }
        }
    }

    let currentZoom = 1.0;
    let currentPanX = 0;
    let currentPanY = 0;

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
            <g id="viewport-transform">
                <g id="viewport-links"></g>
                <g id="viewport-nodes"></g>
            </g>
        `;

        const width = svg.clientWidth || 800;
        const height = svg.clientHeight || 500;
        currentZoom = 1.0;
        currentPanX = 0;
        currentPanY = 0;

        const applyTransform = () => {
            const viewport = svg.querySelector("#viewport-transform");
            if (viewport) {
                viewport.setAttribute("transform", `translate(${currentPanX}, ${currentPanY}) scale(${currentZoom})`);
            }
        };
        applyTransform();

        // Bind Zoom / Pan Controls
        const btnIn = document.getElementById("btn-zoom-in");
        const btnOut = document.getElementById("btn-zoom-out");
        const btnReset = document.getElementById("btn-zoom-reset");
        const filterRisk = document.getElementById("graph-filter-risk");
        const filterType = document.getElementById("graph-filter-type");

        if (btnIn) btnIn.onclick = () => { currentZoom = Math.min(3.0, currentZoom * 1.25); applyTransform(); };
        if (btnOut) btnOut.onclick = () => { currentZoom = Math.max(0.3, currentZoom / 1.25); applyTransform(); };
        if (btnReset) btnReset.onclick = () => { currentZoom = 1.0; currentPanX = 0; currentPanY = 0; applyTransform(); };

        // Mousewheel zoom
        svg.onwheel = (e) => {
            e.preventDefault();
            const delta = e.deltaY < 0 ? 1.15 : 0.85;
            currentZoom = Math.min(4.0, Math.max(0.2, currentZoom * delta));
            applyTransform();
        };

        // Canvas pan
        let isPanning = false;
        let panStartX = 0, panStartY = 0;
        svg.onmousedown = (e) => {
            if (e.target === svg || e.target.tagName === 'svg' || e.target.id === 'viewport-transform') {
                isPanning = true;
                panStartX = e.clientX - currentPanX;
                panStartY = e.clientY - currentPanY;
                svg.style.cursor = "grabbing";
            }
        };
        window.onmousemove = (e) => {
            if (isPanning) {
                currentPanX = e.clientX - panStartX;
                currentPanY = e.clientY - panStartY;
                applyTransform();
            }
        };
        window.onmouseup = () => {
            if (isPanning) {
                isPanning = false;
                svg.style.cursor = "grab";
            }
        };

        nodes = graph.nodes.map(n => ({
            ...n,
            x: width / 2 + (Math.random() - 0.5) * 350,
            y: height / 2 + (Math.random() - 0.5) * 350,
            vx: 0,
            vy: 0,
            r: n.type === "file" ? 10 : 7,
            visible: true
        }));

        links = graph.links.map(l => ({
            ...l,
            sourceNode: nodes.find(n => n.id === l.source),
            targetNode: nodes.find(n => n.id === l.target),
            visible: true
        })).filter(l => l.sourceNode && l.targetNode);

        const linkGroup = svg.querySelector("#viewport-links");
        const nodeGroup = svg.querySelector("#viewport-nodes");

        // Render Links
        links.forEach(l => {
            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.setAttribute("class", `graph-link ${l.type}`);
            if (l.type === "call") {
                line.setAttribute("marker-end", "url(#arrow)");
            }
            l.element = line;
            linkGroup.appendChild(line);
        });

        // Render Nodes
        nodes.forEach(n => {
            const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
            g.setAttribute("class", "graph-node-group");

            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("class", "node-circle");

            let color = "var(--text-secondary)";
            if (n.level === "HIGH") {
                color = "#f43f5e";
            } else if (n.type === "file") {
                color = "#38bdf8";
            } else if (n.type === "function") {
                color = "#c084fc";
            }

            circle.setAttribute("fill", color);
            circle.setAttribute("r", n.r);
            circle.setAttribute("stroke", "rgba(0,0,0,0.6)");
            if (n.level === "HIGH") {
                circle.setAttribute("filter", "drop-shadow(0 0 6px #f43f5e)");
            }

            const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
            text.setAttribute("class", "node-label");
            text.setAttribute("dy", n.r + 12);
            text.setAttribute("fill", "#e2e8f0");
            text.setAttribute("font-size", "11px");
            text.setAttribute("text-anchor", "middle");
            text.setAttribute("pointer-events", "none");
            text.textContent = n.label;

            g.appendChild(circle);
            g.appendChild(text);

            n.element = g;
            n.circle = circle;

            // Drag behavior
            circle.addEventListener("mousedown", (e) => {
                e.stopPropagation();
                n.dragged = true;
                svg.style.cursor = "grabbing";
            });

            // Hover highlight behavior
            g.addEventListener("mouseenter", () => {
                const connectedNodes = new Set([n.id]);
                links.forEach(l => {
                    if (l.source === n.id || l.target === n.id) {
                        connectedNodes.add(l.source);
                        connectedNodes.add(l.target);
                        if (l.element) l.element.classList.add("highlighted");
                    } else {
                        if (l.element) l.element.classList.add("dimmed");
                    }
                });
                nodes.forEach(other => {
                    if (other.element && !connectedNodes.has(other.id)) {
                        other.element.classList.add("dimmed");
                    }
                });
            });

            g.addEventListener("mouseleave", () => {
                links.forEach(l => {
                    if (l.element) {
                        l.element.classList.remove("highlighted");
                        l.element.classList.remove("dimmed");
                    }
                });
                nodes.forEach(other => {
                    if (other.element) other.element.classList.remove("dimmed");
                });
            });

            nodeGroup.appendChild(g);
        });

        // Filter Logic Handler
        const applyFilters = () => {
            const rVal = filterRisk ? filterRisk.value : "ALL";
            const tVal = filterType ? filterType.value : "ALL";
            let visibleCount = 0;

            nodes.forEach(n => {
                const rMatch = (rVal === "ALL" || n.level === rVal);
                const tMatch = (tVal === "ALL" || n.type === tVal);
                n.visible = rMatch && tMatch;
                if (n.element) {
                    n.element.style.display = n.visible ? "" : "none";
                }
                if (n.visible) visibleCount++;
            });

            links.forEach(l => {
                l.visible = l.sourceNode.visible && l.targetNode.visible;
                if (l.element) {
                    l.element.style.display = l.visible ? "" : "none";
                }
            });

            const emptyState = document.getElementById("graph-empty-state");
            if (emptyState) {
                if (visibleCount === 0) {
                    emptyState.classList.remove("hidden");
                } else {
                    emptyState.classList.add("hidden");
                }
            }
        };

        if (filterRisk) filterRisk.onchange = applyFilters;
        if (filterType) filterType.onchange = applyFilters;
        applyFilters();

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

        const kForce = 0.035;
        const visibleNodes = nodes.filter(n => n.visible);
        const kRepulsion = Math.max(2500, visibleNodes.length * 90);
        const kGravity = 0.012;
        const damping = 0.86;
        const desiredDistance = 90;

        // Repulsion with collision avoidance
        for (let i = 0; i < visibleNodes.length; i++) {
            for (let j = i + 1; j < visibleNodes.length; j++) {
                const n1 = visibleNodes[i];
                const n2 = visibleNodes[j];
                const dx = n2.x - n1.x;
                const dy = n2.y - n1.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1.0;
                const minDist = n1.r + n2.r + 35; // Collision radius avoidance
                if (dist < 320) {
                    const force = (dist < minDist) ? (kRepulsion * 2.5) / (dist * dist) : kRepulsion / (dist * dist);
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
        links.filter(l => l.visible).forEach(l => {
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
            if (n.visible && !n.dragged) {
                const dx = centerX - n.x;
                const dy = centerY - n.y;
                n.vx += dx * kGravity;
                n.vy += dy * kGravity;

                n.x += n.vx;
                n.y += n.vy;

                n.vx *= damping;
                n.vy *= damping;

                n.x = Math.max(30, Math.min(width - 30, n.x));
                n.y = Math.max(30, Math.min(height - 30, n.y));
            }

            if (n.element) {
                n.element.setAttribute("transform", `translate(${n.x}, ${n.y})`);
            }
        });

        // Update Link lines
        links.forEach(l => {
            if (l.visible && l.element) {
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

    // -------------------------------------------------------------
    // Modal Backdrop Click-to-Close
    // -------------------------------------------------------------
    const tourModalEl = document.getElementById("tour-modal");
    if (tourModalEl) {
        tourModalEl.addEventListener("click", (e) => {
            if (e.target === tourModalEl) {
                tourModalEl.classList.add("hidden");
            }
        });
    }
    const entityModalEl = document.getElementById("entity-detail-modal");
    if (entityModalEl) {
        entityModalEl.addEventListener("click", (e) => {
            if (e.target === entityModalEl) {
                entityModalEl.classList.add("hidden");
            }
        });
    }

    // -------------------------------------------------------------
    // Auto-Calibration logic
    // -------------------------------------------------------------
    const btnCalibrate = document.getElementById("btn-calibrate");
    const calibrationResults = document.getElementById("calibration-results");

    if (btnCalibrate) {
        btnCalibrate.addEventListener("click", async () => {
            const repo = repoInput.value.trim();
            if (!repo) {
                showToast("Connect a project first.");
                return;
            }

            btnCalibrate.disabled = true;
            setButtonText(btnCalibrate, "Calibrating...");
            calibrationResults.style.display = "none";

            try {
                const response = await fetch("/api/calibrate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: jsonStringify({ repo })
                });
                const data = await response.json();

                if (data.error) {
                    showToast(`Calibration error: ${data.error}`);
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
                showToast(`API error: ${err.message}`);
            } finally {
                btnCalibrate.disabled = false;
                setButtonText(btnCalibrate, "Calibrate Thresholds");
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
            setButtonText(nextSlideBtn, "Get Started");
        } else {
            setButtonText(nextSlideBtn, "Next");
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

    // -------------------------------------------------------------
    // Milestone F: Interactive Repository Intelligence Additions
    // -------------------------------------------------------------
    const progressCard = document.getElementById("analysis-progress-card");
    const progressStepText = document.getElementById("progress-step-text");
    const progressBarFill = document.getElementById("progress-bar-fill");
    const cancelAnalysisBtn = document.getElementById("btn-cancel-analysis");
    const runSelectDropdown = document.getElementById("run-select-dropdown");
    
    const entityDetailModal = document.getElementById("entity-detail-modal");
    const closeDetailBtn = document.getElementById("btn-close-detail");
    const detailEntityName = document.getElementById("detail-entity-name");
    const detailComplexity = document.getElementById("detail-complexity");
    const detailCoupling = document.getElementById("detail-coupling");
    const detailDepsList = document.getElementById("detail-dependencies-list");
    const detailViosList = document.getElementById("detail-violations-list");
    const detailTrendsList = document.getElementById("detail-trends-list");
    const detailAiExplainBtn = document.getElementById("btn-detail-ai-explain");
    const detailAiExplainBox = document.getElementById("detail-ai-explanation-box");

    let progressInterval = null;
    let currentActiveJobId = null;

    const progressStepMap = {
        "Scanning repository": 15,
        "Building AST": 35,
        "Resolving dependencies": 55,
        "Computing metrics": 75,
        "Executing rules": 90,
        "Generating report": 95,
        "Done": 100
    };

    function startProgressPolling(jobId) {
        currentActiveJobId = jobId;
        if (progressInterval) clearInterval(progressInterval);
        
        progressCard.classList.remove("hidden");
        
        progressInterval = setInterval(async () => {
            try {
                const res = await fetch("/api/v1/progress");
                const progressData = await res.json();
                
                const step = progressData.progress_step || "Scanning repository";
                const status = progressData.status || "running";
                
                progressStepText.textContent = step;
                const pct = progressStepMap[step] || 10;
                progressBarFill.style.width = `${pct}%`;
                
                if (status === "success" || status === "failed" || status === "cancelled") {
                    clearInterval(progressInterval);
                    progressInterval = null;
                    progressBarFill.style.width = "100%";
                    setTimeout(() => {
                        progressCard.classList.add("hidden");
                    }, 1000);
                    
                    if (status === "success") {
                        showToast("Analysis completed successfully!");
                        fetchLatestData();
                    } else if (status === "failed") {
                        showToast(`Analysis failed: ${progressData.error}`);
                    } else if (status === "cancelled") {
                        showToast("Analysis cancelled.");
                    }
                }
            } catch (err) {
                console.error("Progress poll failed:", err);
            }
        }, 500);
    }

    async function fetchLatestData() {
        const repo = repoInput.value.trim();
        if (!repo) return;
        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo })
            });
            const data = await response.json();
            if (!data.error) {
                codebaseData = data;
                renderDashboard(data);
                loadFileTree();
                loadRunsDropdown();
            }
        } catch (err) {
            console.error("Failed to fetch latest data:", err);
        }
    }

    async function loadRunsDropdown() {
        try {
            const res = await fetch("/api/v1/runs");
            const data = await res.json();
            runSelectDropdown.innerHTML = "";
            
            if (!data.runs || data.runs.length === 0) {
                const opt = document.createElement("option");
                opt.value = "latest";
                opt.textContent = "Latest Analysis Run";
                runSelectDropdown.appendChild(opt);
                return;
            }
            
            data.runs.forEach((run, idx) => {
                const opt = document.createElement("option");
                opt.value = run.run_id;
                opt.textContent = `Run #${run.run_id} (${new Date(run.timestamp).toLocaleString()})`;
                if (idx === data.runs.length - 1) {
                    opt.selected = true;
                }
                runSelectDropdown.appendChild(opt);
            });
        } catch (err) {
            console.error("Failed to load runs dropdown:", err);
        }
    }

    // Cancel analysis button
    cancelAnalysisBtn.addEventListener("click", async () => {
        try {
            await fetch("/api/v1/cancel-analysis", { method: "POST" });
            showToast("Cancelling analysis...");
        } catch (err) {
            console.error("Cancel failed:", err);
        }
    });

    // Demo Playground button
    const playgroundBtn = document.getElementById("btn-load-playground");
    if (playgroundBtn) {
        playgroundBtn.addEventListener("click", async () => {
            playgroundBtn.disabled = true;
            setButtonText(playgroundBtn, "Creating...");
            try {
                const response = await fetch("/api/playground", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" }
                });
                const data = await response.json();
                if (data.error) {
                    showToast(`Playground failed: ${data.error}`);
                } else if (data.success) {
                    repoInput.value = data.path;
                    loadRepoBtn.click();
                    showToast("Playground Connected!");
                }
            } catch (err) {
                console.error("Playground request failed:", err);
                showToast(`API error: ${err.message}`);
            } finally {
                playgroundBtn.disabled = false;
                setButtonText(playgroundBtn, "Demo Playground");
            }
        });
    }

    // Run selector dropdown
    runSelectDropdown.addEventListener("change", async () => {
        const runId = runSelectDropdown.value;
        if (runId === "latest") return;
        showToast(`Loading Run #${runId}...`);
    });

    // -------------------------------------------------------------
    // Entity Detail Modal — Close Button
    // -------------------------------------------------------------
    if (closeDetailBtn) {
        closeDetailBtn.addEventListener("click", () => {
            entityDetailModal.classList.add("hidden");
        });
    }

    // Persona state & translation switcher logic
    let currentPersonaCommunications = null;
    let currentActivePersona = "developer";

    const personaTabs = document.querySelectorAll(".persona-tab");
    const personaActiveBadge = document.getElementById("persona-active-badge");

    const personaBadgeMap = {
        "developer": "👨‍💻 Developer",
        "manager": "📊 Manager",
        "founder": "🚀 Founder",
        "security": "🛡️ Security",
        "ai_agent": "🤖 AI Agent"
    };

    function updatePersonaView(personaKey) {
        currentActivePersona = personaKey;
        personaTabs.forEach(tab => {
            if (tab.dataset.persona === personaKey) {
                tab.classList.add("active");
                tab.style.background = "var(--neon-cyan)";
                tab.style.color = "#0d1b2a";
                tab.style.fontWeight = "bold";
            } else {
                tab.classList.remove("active");
                tab.style.background = "transparent";
                tab.style.color = "var(--text-color)";
                tab.style.fontWeight = "normal";
            }
        });

        if (personaActiveBadge) {
            personaActiveBadge.textContent = personaBadgeMap[personaKey] || personaKey;
        }

        if (currentPersonaCommunications && detailAiExplainBox) {
            const explanation = currentPersonaCommunications[personaKey] || currentPersonaCommunications.developer || "No persona translation available.";
            detailAiExplainBox.classList.remove("hidden");
            detailAiExplainBox.textContent = explanation;
        }
    }

    personaTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            updatePersonaView(tab.dataset.persona);
        });
    });

    // Entity Detail Modal — AI Explain Button
    if (detailAiExplainBtn) {
        detailAiExplainBtn.addEventListener("click", async () => {
            if (!codebaseData) return;
            const entityName = detailEntityName.textContent;
            const match = codebaseData.risks.find(r => r.file.endsWith(entityName) || entityName.includes(r.file));
            if (!match) {
                detailAiExplainBox.classList.remove("hidden");
                detailAiExplainBox.textContent = "No analysis data available for this entity.";
                return;
            }
            detailAiExplainBtn.disabled = true;
            setButtonText(detailAiExplainBtn, "Analyzing...");
            try {
                const repo = repoInput.value.trim();
                const response = await fetch("/api/design-oracle", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: jsonStringify({ repo, entity_id: match.file, file: match.file, action: "explain" })
                });
                const data = await response.json();
                detailAiExplainBox.classList.remove("hidden");
                if (data.error) {
                    detailAiExplainBox.textContent = `Error: ${data.error}`;
                } else {
                    currentPersonaCommunications = data.communication || { developer: data.explanation };
                    updatePersonaView(currentActivePersona);
                    // Show AI workspace handoff buttons
                    const aiWorkspace = document.getElementById("ai-collaboration-workspace");
                    if (aiWorkspace) aiWorkspace.classList.remove("hidden");
                    // Try rendering trust chain and repair sim
                    renderTrustChainAndRepairSim(data);
                }
            } catch (err) {
                detailAiExplainBox.classList.remove("hidden");
                detailAiExplainBox.textContent = `API Error: ${err.message}`;
            } finally {
                detailAiExplainBtn.disabled = false;
                setButtonText(detailAiExplainBtn, "Explain Entity & Translate Machine Risk");
            }
        });
    }

    // ⚡ Auto-Push to AI Assistant (Zero Copy-Pasting)
    const btnAutoPushAi = document.getElementById("btn-auto-push-ai");
    if (btnAutoPushAi) {
        btnAutoPushAi.addEventListener("click", async () => {
            const repo = repoInput.value.trim();
            const entityName = detailEntityName ? detailEntityName.textContent : "";
            if (!repo) {
                showToast("Connect a project folder first.");
                return;
            }
            btnAutoPushAi.disabled = true;
            setButtonText(btnAutoPushAi, "⚡ Pushing to AI...");
            try {
                const response = await fetch("/api/v1/ai-push", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: jsonStringify({ repo, target_file: entityName, persona: currentActivePersona })
                });
                const data = await response.json();
                if (data.status === "success") {
                    detailAiExplainBox.classList.remove("hidden");
                    detailAiExplainBox.textContent = data.ai_response;
                    showToast(`Pushed to AI (${data.source})!`);
                    const aiWorkspace = document.getElementById("ai-collaboration-workspace");
                    if (aiWorkspace) aiWorkspace.classList.remove("hidden");
                } else {
                    showToast(`AI Push error: ${data.message || 'Failed'}`);
                }
            } catch (err) {
                console.error("AI Push error:", err);
                showToast("AI Push failed: " + err.message);
            } finally {
                btnAutoPushAi.disabled = false;
                setButtonText(btnAutoPushAi, "⚡ Auto-Push to AI Assistant");
            }
        });
    }

    // AI Workspace Handoff Buttons
    async function copyWorkspaceHandoff(aiName) {
        const repo = repoInput.value.trim();
        const entityName = detailEntityName.textContent;
        
        try {
            const response = await fetch("/api/v1/context-brief", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringify({ repo, target_file: entityName })
            });
            const data = await response.json();
            
            let textToCopy = "";
            if (data.handoff) {
                if (aiName === "Claude") textToCopy = data.handoff.claude;
                else if (aiName === "ChatGPT") textToCopy = data.handoff.codex;
                else textToCopy = data.handoff.antigravity;
            }
            
            if (!textToCopy) {
                const match = codebaseData ? codebaseData.risks.find(r => r.file.endsWith(entityName) || entityName.includes(r.file)) : null;
                const context = match ? `File: ${match.file}\nRisk: ${match.level}` : `Entity: ${entityName}`;
                textToCopy = `[${aiName} Workspace Handoff from Ultron]\nAnalyze code entity:\n${context}`;
            }

            await navigator.clipboard.writeText(textToCopy);
            showToast(`Copied context for ${aiName}!`);
        } catch (err) {
            console.error("Handoff fetch failed:", err);
            showToast("Failed to copy: " + err.message);
        }
    }

    const btnCopyClaude = document.getElementById("btn-copy-claude");
    const btnCopyGpt = document.getElementById("btn-copy-gpt");
    const btnCopyGemini = document.getElementById("btn-copy-gemini");
    if (btnCopyClaude) btnCopyClaude.addEventListener("click", () => copyWorkspaceHandoff("Claude"));
    if (btnCopyGpt) btnCopyGpt.addEventListener("click", () => copyWorkspaceHandoff("ChatGPT"));
    if (btnCopyGemini) btnCopyGemini.addEventListener("click", () => copyWorkspaceHandoff("Gemini"));

    // -------------------------------------------------------------
    // Open Entity Detail (global function for SVG node clicks)
    // -------------------------------------------------------------
    window.openEntityDetail = function(entityName, entityType) {
        if (!codebaseData) return;

        const escName = escapeHtml(entityName);
        detailEntityName.innerHTML = escName;
        detailAiExplainBox.classList.add("hidden");
        const aiWorkspace = document.getElementById("ai-collaboration-workspace");
        if (aiWorkspace) aiWorkspace.classList.add("hidden");
        entityDetailModal.classList.remove("hidden");

        const match = codebaseData.risks.find(r => r.file.endsWith(entityName) || entityName.includes(r.file));

        if (match) {
            detailComplexity.textContent = escapeHtml(String(match.complexity || "-"));
            detailCoupling.textContent = escapeHtml(String(match.coupling_score || "-"));
            detailDepsList.textContent = match.callers ? match.callers.map(c => escapeHtml(String(c))).join(", ") : "None";

            detailViosList.innerHTML = "";
            const levelColor = match.level === "HIGH" ? "var(--risk-high)" : match.level === "MEDIUM" ? "var(--risk-med)" : "var(--risk-low)";
            detailViosList.innerHTML = `<span style="color:${levelColor}; font-weight:700;">${escapeHtml(match.level)} Risk Zone</span><p style="margin-top:4px; font-size:12px;">${escapeHtml(match.summary || "")}</p>`;

            // Repo/run-scoped hotspot trend rendering
            const currentRepo = repoInput ? repoInput.value.trim() : "";
            function renderSpotText(spots) {
                if (spots && spots.length > 0) {
                    const spot = spots.find(h => h.file_path.endsWith(entityName) || entityName.includes(h.file_path));
                    if (spot) {
                        detailTrendsList.innerHTML = `Complexity Trend: <strong>${escapeHtml(spot.complexity_trend)}</strong><br>Coupling Trend: <strong>${escapeHtml(spot.coupling_trend)}</strong><br>Historical Changes: <strong>${spot.change_count}</strong><br>Hotspot Score: <strong>${spot.hotspot_score.toFixed(1)}</strong> (${escapeHtml(spot.severity_level)})`;
                        return;
                    }
                }
                detailTrendsList.innerHTML = `Complexity: Stable <br> Coupling: Stable <br> Historical Changes: 0`;
            }

            if (hotspotsCache.repo === currentRepo && hotspotsCache.data) {
                renderSpotText(hotspotsCache.data);
            } else {
                detailTrendsList.innerHTML = `Loading RKM trend metrics...`;
                fetch("/api/v1/hotspots")
                    .then(res => res.json())
                    .then(data => {
                        hotspotsCache = { repo: currentRepo, data: data.hotspots || [] };
                        renderSpotText(hotspotsCache.data);
                    })
                    .catch(err => {
                        detailTrendsList.innerHTML = `Complexity: Stable <br> Coupling: Stable <br> Trend error: ${escapeHtml(err.message)}`;
                    });
            }
        } else {
            detailComplexity.textContent = "-";
            detailCoupling.textContent = "-";
            detailDepsList.textContent = "None";
            detailViosList.innerHTML = `<span style="opacity: 0.5; font-size: 13px;">No risk data for this entity.</span>`;
            detailTrendsList.innerHTML = "No trend data available.";
        }
    };

    // Render Trust Chain & Repair Simulation with Plain English lead labels
    function renderTrustChainAndRepairSim(data) {
        const trustBox = document.getElementById("detail-trust-chain-box");
        const repairBox = document.getElementById("detail-repair-simulation-box");

        if (!trustBox || !repairBox) return;

        if (data.trust_chain) {
            const tc = data.trust_chain;
            trustBox.innerHTML = `
                <div style="font-size: 13px; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">
                    ${tc.plain_label}
                </div>
                <div style="font-size: 11px; color: #94a3b8; margin-bottom: 8px;">
                    Technical Rule: <code style="color: #38bdf8; background: rgba(56,189,248,0.1); padding: 2px 6px; border-radius: 4px;">${tc.rule_technical_name}</code> | Confidence: <strong>${(tc.confidence * 100).toFixed(0)}%</strong>
                </div>
                <div style="font-size: 11px; color: #e2e8f0; background: rgba(255,255,255,0.03); padding: 8px; border-radius: 4px;">
                    <strong>Observed Evidence:</strong> ${tc.evidence[0]?.description || tc.entity} (${tc.evidence[0]?.value || 'Threshold Exceeded'})
                </div>
            `;
        }

        if (data.repair_simulation) {
            const rs = data.repair_simulation;
            repairBox.innerHTML = `
                <div style="font-size: 13px; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">
                    ${rs.plain_summary}
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 11px; margin: 8px 0;">
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <th style="text-align: left; padding: 4px; color: #ef4444;">Before Refactoring</th>
                        <th style="text-align: left; padding: 4px; color: #34d399;">After Refactoring</th>
                    </tr>
                    <tr>
                        <td style="padding: 6px 4px; color: #cbd5e1;">Risk Score: <strong>${rs.before_state.risk_score}</strong> (${rs.before_state.status})</td>
                        <td style="padding: 6px 4px; color: #cbd5e1;">Estimated Risk: <strong style="color: #34d399;">${rs.after_state.estimated_risk_score}</strong> (${rs.after_state.status})</td>
                    </tr>
                </table>
                <div style="font-size: 11px; color: #94a3b8;">
                    <strong>Action Plan:</strong>
                    <ul style="margin: 4px 0 0 16px; padding: 0;">
                        ${rs.recommended_steps.map(step => `<li>${step}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
    }

    // -------------------------------------------------------------
    // Shared Error Vocabulary (matches backend response schemas)
    // -------------------------------------------------------------
    const UltronState = {
        NO_RKM_DB:        "db_uninitialized",
        ANALYSIS_EMPTY:   "analysis_empty",
        ANALYSIS_FAILED:  "analysis_failed",
        DB_READ_ERROR:    "db_read_error"
    };

    const STATE_MESSAGES = {
        [UltronState.NO_RKM_DB]:       "No RKM database found. Run an analysis to generate recommendations.",
        [UltronState.ANALYSIS_EMPTY]:   "Analysis completed with no violations. Your codebase is clean.",
        [UltronState.ANALYSIS_FAILED]:  "Analysis failed. Check the server console for details.",
        [UltronState.DB_READ_ERROR]:    "Could not read the RKM database. It may be locked by another process."
    };

    // -------------------------------------------------------------
    // Recommendations & AI Export Handoff Logic
    // -------------------------------------------------------------
    async function fetchRecommendations() {
        const recListEl = document.getElementById("recommendations-list");
        const recSourceBadge = document.getElementById("rec-source-badge");
        const btnRefresh = document.getElementById("btn-refresh-recs");
        if (!recListEl) return;

        // Loading state: show immediately, hide only on success/failure/cancel
        if (btnRefresh) btnRefresh.disabled = true;
        recListEl.innerHTML = `<div style="color: #94a3b8; font-size: 0.85rem;"><span style="display:inline-block; animation: pulse 1.5s infinite; opacity: 0.7;">Loading recommendations...</span></div>`;

        try {
            const resp = await fetch("/api/v1/recommendations?limit=10");
            const data = await resp.json();

            // Update source badge
            if (recSourceBadge) {
                const isLive = data.source === "rkm_db";
                recSourceBadge.textContent = isLive ? "RKM DB" : "Fallback";
                recSourceBadge.style.background = isLive ? "rgba(56, 189, 248, 0.15)" : "rgba(245, 158, 11, 0.15)";
                recSourceBadge.style.color = isLive ? "#38bdf8" : "#f59e0b";
            }

            // Contextual empty state
            const recs = data.recommendations || [];
            if (recs.length === 0) {
                const reason = data.fallback_reason || UltronState.ANALYSIS_EMPTY;
                const msg = STATE_MESSAGES[reason] || STATE_MESSAGES[UltronState.ANALYSIS_EMPTY];
                const icon = reason === UltronState.ANALYSIS_EMPTY ? "&#10003;" : "&#9432;";
                const color = reason === UltronState.ANALYSIS_EMPTY ? "#4ade80" : "#f59e0b";
                recListEl.innerHTML = `<div style="color: ${color}; font-size: 0.85rem; display: flex; align-items: center; gap: 8px;"><span style="font-size: 1.1rem;">${icon}</span> ${msg}</div>`;
                return;
            }

            // Render recommendation cards
            recListEl.innerHTML = recs.map(r => `
                <div style="background: rgba(30, 41, 59, 0.6); padding: 10px 14px; border-radius: 6px; border-left: 3px solid ${r.severity === 'HIGH' ? '#f43f5e' : (r.severity === 'MEDIUM' ? '#f59e0b' : '#38bdf8')}; display: flex; justify-content: space-between; align-items: center; gap: 10px;">
                    <div>
                        <div style="color: #f1f5f9; font-weight: 600; font-size: 0.88rem;">${r.target_file || 'Global'} <span style="font-size: 11px; opacity: 0.7; color: #94a3b8;">(${r.rule_id})</span></div>
                        <div style="color: #cbd5e1; font-size: 0.8rem; margin-top: 2px;">${r.suggested_action}</div>
                    </div>
                    <span style="font-size: 11px; font-weight: 700; color: ${r.severity === 'HIGH' ? '#f43f5e' : '#38bdf8'}; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; white-space: nowrap;">
                        Impact: -${(r.risk_reduction_score || 0).toFixed(1)}
                    </span>
                </div>
            `).join('');
        } catch (err) {
            console.error("Failed to fetch recommendations:", err);
            recListEl.innerHTML = `<div style="color: #f43f5e; font-size: 0.85rem;">&#9888; Could not load recommendations. Server may be unreachable.</div>`;
        } finally {
            if (btnRefresh) btnRefresh.disabled = false;
        }
    }

    const btnRefreshRecs = document.getElementById("btn-refresh-recs");
    if (btnRefreshRecs) {
        btnRefreshRecs.addEventListener("click", fetchRecommendations);
    }

    // AI Handoff Export Buttons Handler with Clipboard Fallback
    document.querySelectorAll(".btn-export-ai").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            const thisBtn = e.currentTarget;
            const format = thisBtn.getAttribute("data-format");
            if (!format) return;

            // Disable during async to prevent double-click
            thisBtn.disabled = true;
            const originalText = thisBtn.textContent;
            thisBtn.textContent = "Exporting...";

            try {
                const resp = await fetch("/api/v1/export-brief", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ format: format })
                });
                const data = await resp.json();
                if (data.status === "ok") {
                    const textToCopy = data.content || JSON.stringify(data.brief, null, 2);
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        await navigator.clipboard.writeText(textToCopy);
                    } else {
                        const textarea = document.createElement("textarea");
                        textarea.value = textToCopy;
                        document.body.appendChild(textarea);
                        textarea.select();
                        document.execCommand("copy");
                        document.body.removeChild(textarea);
                    }
                    showToast(`Copied ${format.toUpperCase()} Context Brief!`);
                } else {
                    showToast(data.message || "Export failed.");
                }
            } catch (err) {
                console.error("Export brief error:", err);
                showToast("Export error: " + err.message);
            } finally {
                thisBtn.disabled = false;
                thisBtn.textContent = originalText;
            }
        });
    });

    // Auto-connect repository on initial page load if valid path present
    if (repoInput && repoInput.value.trim()) {
        setTimeout(() => {
            if (loadRepoBtn) loadRepoBtn.click();
        }, 100);
    }
