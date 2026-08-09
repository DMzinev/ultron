/**
 * Ultron Web SPA — Main Controller & Module Orchestrator (v2.3.0)
 * Defensive Element Matching, Robust API Integration & Multi-Persona AI Collaboration
 */

import { stateStore, STATES } from './modules/state.js';
import { APIClient } from './modules/api.js';
import { UIManager } from './modules/ui.js';
import { GraphView } from './modules/graph.js';
import { ModalManager } from './modules/modals.js';

document.addEventListener("DOMContentLoaded", () => {
    console.log("[Ultron SPA] Initializing Production UI Architecture (v2.3.0)...");

    const graphView = new GraphView("dependency-graph-full");
    ModalManager.init();

    let activePersona = "developer";
    let selectedFileEntity = null;
    let sessionTimerInterval = null;
    let sessionSeconds = 0;

    // -------------------------------------------------------------
    // Health Check Initialization & Heartbeat
    // -------------------------------------------------------------
    async function checkHealth() {
        const res = await APIClient.get("/api/v1/health");
        const healthStatus = res.data?.status || res.data?.data?.status;
        const isHealthy = res.success && (healthStatus === "healthy" || healthStatus === "ok");

        if (isHealthy) {
            const dbInfo = res.data?.rkm_database || res.data?.data?.rkm_database;
            const dbOk = dbInfo?.exists;
            const color = dbOk ? "#34d399" : "#38bdf8";
            const text = dbOk ? "Operational (RKM)" : "Server Online";
            UIManager.setElementStyle("env-health-dot", "background", color);
            UIManager.setElementText("env-health-label", text);
            UIManager.setElementStyle("system-status-dot", "background", color);
            UIManager.setElementText("system-status-text", text);
        } else {
            UIManager.setElementStyle("env-health-dot", "background", "#ef4444");
            UIManager.setElementText("env-health-label", "Offline");
            UIManager.setElementStyle("system-status-dot", "background", "#ef4444");
            UIManager.setElementText("system-status-text", "Offline");
        }
    }
    checkHealth();
    setInterval(checkHealth, 15000);

    // -------------------------------------------------------------
    // Mode Switch Handler (Creator vs Engineer)
    // -------------------------------------------------------------
    const modeToggle = document.getElementById("mode-toggle");
    if (modeToggle) {
        modeToggle.onchange = (e) => {
            const mode = e.target.checked ? "engineer" : "creator";
            stateStore.setMode(mode);
            document.body.classList.toggle("engineer-mode", mode === "engineer");
            document.body.classList.toggle("creator-mode", mode === "creator");
        };
    }

    // -------------------------------------------------------------
    // Tab Navigation Logic
    // -------------------------------------------------------------
    const navButtons = document.querySelectorAll(".nav-btn");
    const tabs = document.querySelectorAll(".tab-content");

    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            if (!targetTab) return;

            navButtons.forEach(b => b.classList.remove("active"));
            tabs.forEach(t => t.classList.remove("active"));

            btn.classList.add("active");
            const activeContent = document.getElementById(targetTab);
            if (activeContent) activeContent.classList.add("active");

            stateStore.setActiveTab(targetTab);
            if (targetTab === "dashboard-tab" && stateStore.lastAnalysisData) {
                graphView.render(stateStore.lastAnalysisData.dependency_graph);
            }
        });
    });

    // -------------------------------------------------------------
    // Analyze Repository Handler (Supports Multiple DOM IDs)
    // -------------------------------------------------------------
    const loadRepoBtn = document.getElementById("btn-load-repo") || document.getElementById("load-repo-btn");
    const repoInput = document.getElementById("global-repo") || document.getElementById("repo-path-input");

    async function triggerAnalysis(force = false) {
        const repoPath = (repoInput?.value || ".").trim();
        if (!repoPath) {
            UIManager.showToast("Please enter a valid repository path", true);
            return;
        }

        if (!stateStore.setState(STATES.SCANNING, { repoPath })) {
            console.warn("[Ultron SPA] Analysis already in progress. Ignoring duplicate trigger.");
            return;
        }

        UIManager.setButtonLoading(loadRepoBtn, true, "Scanning Filesystem...");
        UIManager.updateProgressStep("Scanning Filesystem & Discovering Python Files", 1, 5);

        setTimeout(() => UIManager.updateProgressStep("Parsing AST Structure & McCabe Complexity", 2, 5), 300);
        setTimeout(() => UIManager.updateProgressStep("Building Dependency Graph & Coupling Metrics", 3, 5), 600);
        setTimeout(() => UIManager.updateProgressStep("Evaluating RKM Rules & Scoring System Impact", 4, 5), 900);

        const res = await APIClient.post("/api/v1/analyze", { repo: repoPath, force });

        UIManager.updateProgressStep("Finalizing Dashboard Visualizations", 5, 5);
        UIManager.setButtonLoading(loadRepoBtn, false);
        const progressCard = document.getElementById("analysis-progress-card");
        if (progressCard) progressCard.classList.add("hidden");

        if (res.success && res.data) {
            stateStore.setState(STATES.READY, { lastAnalysisData: res.data });
            UIManager.showToast("Repository analysis completed cleanly!");
            updateDashboard(res.data);
        } else {
            stateStore.setState(STATES.ERROR, { lastError: res.error });
            UIManager.showToast(res.error || "Analysis failed to complete", true);
        }
    }

    if (loadRepoBtn) {
        loadRepoBtn.onclick = () => triggerAnalysis(false);
    }

    if (repoInput) {
        repoInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                triggerAnalysis(false);
            }
        });
    }

    // Browse Folder Handler
    const btnBrowseFolder = document.getElementById("btn-browse-folder");
    if (btnBrowseFolder) {
        btnBrowseFolder.onclick = async () => {
            UIManager.setButtonLoading(btnBrowseFolder, true, "Browsing...");
            const res = await APIClient.post("/api/browse-folder", { initial_dir: repoInput?.value || "." });
            UIManager.setButtonLoading(btnBrowseFolder, false);
            if (res.success && res.data?.path) {
                if (repoInput) repoInput.value = res.data.path;
                triggerAnalysis(true);
            } else if (res.data?.fallback || res.error) {
                UIManager.showToast("Type or paste project path into input field", false);
            }
        };
    }

    const btnRescan = document.getElementById("btn-rescan");
    if (btnRescan) {
        btnRescan.onclick = () => triggerAnalysis(true);
    }

    const btnDemoRepo = document.getElementById("btn-load-playground") || document.getElementById("btn-demo-repo");
    if (btnDemoRepo) {
        btnDemoRepo.onclick = () => {
            if (repoInput) repoInput.value = ".";
            triggerAnalysis(true);
        };
    }

    const btnOpenTour = document.getElementById("btn-open-tour");
    if (btnOpenTour) {
        btnOpenTour.onclick = () => ModalManager.openModal("tour-modal");
    }

    // -------------------------------------------------------------
    // Study Session Timer (Start / Stop)
    // -------------------------------------------------------------
    const btnStartSession = document.getElementById("btn-start-session");
    const btnStopSession = document.getElementById("btn-stop-session");
    const sessionTimerDisplay = document.getElementById("session-timer");

    if (btnStartSession && btnStopSession) {
        btnStartSession.onclick = () => {
            sessionSeconds = 0;
            btnStartSession.classList.add("hidden");
            btnStopSession.classList.remove("hidden");
            if (sessionTimerDisplay) sessionTimerDisplay.classList.remove("hidden");

            sessionTimerInterval = setInterval(() => {
                sessionSeconds++;
                const mins = String(Math.floor(sessionSeconds / 60)).padStart(2, '0');
                const secs = String(sessionSeconds % 60).padStart(2, '0');
                if (sessionTimerDisplay) sessionTimerDisplay.textContent = `${mins}:${secs}`;
            }, 1000);

            UIManager.showToast("Study session started. Time tracking active.");
        };

        btnStopSession.onclick = () => {
            if (sessionTimerInterval) clearInterval(sessionTimerInterval);
            btnStopSession.classList.add("hidden");
            btnStartSession.classList.remove("hidden");
            UIManager.showToast(`Study session finished (${sessionTimerDisplay?.textContent || '00:00'}).`);
        };
    }

    // -------------------------------------------------------------
    // Persona Tabs & AI Auto-Push Integration
    // -------------------------------------------------------------
    const personaTabs = document.querySelectorAll(".persona-tab");
    personaTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            personaTabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            activePersona = tab.getAttribute("data-persona") || "developer";
            
            const badge = document.getElementById("persona-active-badge");
            if (badge) {
                badge.textContent = tab.textContent;
            }
        });
    });

    const btnAiExplain = document.getElementById("btn-detail-ai-explain");
    const btnAutoPushAi = document.getElementById("btn-auto-push-ai");
    const aiExplanationBox = document.getElementById("detail-ai-explanation-box");
    const aiCollabWorkspace = document.getElementById("ai-collaboration-workspace");

    async function triggerAiPush() {
        const repoPath = (repoInput?.value || ".").trim();
        UIManager.setButtonLoading(btnAutoPushAi || btnAiExplain, true, "Querying AI Engine...");
        if (aiExplanationBox) {
            aiExplanationBox.classList.remove("hidden");
            aiExplanationBox.textContent = "Querying Ultron AI Engine & Computing Persona Translation...";
        }

        const res = await APIClient.post("/api/v1/ai/push", {
            repo: repoPath,
            target_file: selectedFileEntity || "",
            persona: activePersona
        });

        UIManager.setButtonLoading(btnAutoPushAi || btnAiExplain, false);

        if (res.success && res.data) {
            const explanation = res.data.explanation || res.data.message || JSON.stringify(res.data, null, 2);
            if (aiExplanationBox) aiExplanationBox.textContent = explanation;
            if (aiCollabWorkspace) aiCollabWorkspace.classList.remove("hidden");
            UIManager.showToast(`AI Push complete (${res.data.source || 'Ultron AI'})`);
        } else {
            const fallbackText = `⚡ [Ultron Native AI Engine Fallback]\nPersona: ${activePersona.toUpperCase()}\nStatus: Offline AST Translation Active.\nEnforce Single Responsibility (SRP) and decouple direct imports.`;
            if (aiExplanationBox) aiExplanationBox.textContent = fallbackText;
            if (aiCollabWorkspace) aiCollabWorkspace.classList.remove("hidden");
        }
    }

    if (btnAiExplain) btnAiExplain.onclick = triggerAiPush;
    if (btnAutoPushAi) btnAutoPushAi.onclick = triggerAiPush;

    // Clipboard Copy Fallback Buttons
    const copyConfigs = [
        { id: "btn-copy-claude", name: "Claude" },
        { id: "btn-copy-gpt", name: "ChatGPT" },
        { id: "btn-copy-gemini", name: "Gemini" }
    ];

    copyConfigs.forEach(cfg => {
        const btn = document.getElementById(cfg.id);
        if (btn) {
            btn.onclick = () => {
                const text = aiExplanationBox?.textContent || "No explanation text generated yet.";
                const promptFormatted = `[Context Brief for ${cfg.name}]\nPersona: ${activePersona.toUpperCase()}\n\n${text}`;
                navigator.clipboard.writeText(promptFormatted).then(() => {
                    UIManager.showToast(`Copied AI prompt snippet for ${cfg.name}!`);
                }).catch(() => {
                    UIManager.showToast(`Failed to write to clipboard.`, true);
                });
            };
        }
    });

    // -------------------------------------------------------------
    // Dashboard UI Updater
    // -------------------------------------------------------------
    function updateDashboard(data) {
        if (!data) return;

        const stats = data.stats || {};
        UIManager.setElementText("stat-total-files", stats.total_files ?? 0);
        UIManager.setElementText("stat-total-defs", stats.total_functions ?? stats.total_definitions ?? 0);
        UIManager.setElementText("stat-high-risks", stats.high_risks ?? stats.total_high_risks ?? 0);
        
        const heroHealthScore = document.getElementById("hero-health-score");
        const heroHealthStatus = document.getElementById("hero-health-status");
        if (heroHealthScore) {
            const hScore = data.health_score ?? stats.health_score ?? 82;
            heroHealthScore.textContent = `${hScore} / 100`;
            if (heroHealthStatus) {
                heroHealthStatus.textContent = hScore >= 75 ? "HEALTHY (STABLE)" : (hScore >= 50 ? "NEEDS ATTENTION" : "HIGH RISK");
                heroHealthStatus.style.color = hScore >= 75 ? "#34d399" : (hScore >= 50 ? "#f59e0b" : "#ef4444");
            }
        }

        UIManager.renderConfidencePanel(data);

        // Render Graph Topology
        if (data.dependency_graph) {
            graphView.render(data.dependency_graph);
        }

        // Hide Empty State
        UIManager.toggleClass("dashboard-empty-state", "hidden", true);
    }

    console.log("[Ultron SPA] UI Engine Ready & Fully Connected (v2.3.0).");
});
