/**
 * Ultron Web SPA — Main Controller & Module Orchestrator (v1.3.0)
 * Campaign 12: Production-grade ES Modular Architecture
 */

import { stateStore, STATES } from './modules/state.js';
import { APIClient } from './modules/api.js';
import { UIManager } from './modules/ui.js';
import { GraphView } from './modules/graph.js';
import { ModalManager } from './modules/modals.js';

document.addEventListener("DOMContentLoaded", () => {
    console.log("[Ultron SPA] Initializing Production UI Architecture (v1.3.0)...");

    const graphView = new GraphView("dependency-graph-full");
    ModalManager.init();

    // -------------------------------------------------------------
    // Health Check Initialization
    // -------------------------------------------------------------
    async function checkHealth() {
        const res = await APIClient.get("/api/v1/health");
        if (res.success && res.data?.status === "healthy") {
            const dbOk = res.data.rkm_database?.exists;
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
    // Analyze Repository Handler
    // -------------------------------------------------------------
    const loadRepoBtn = document.getElementById("load-repo-btn");
    const repoInput = document.getElementById("repo-path-input");

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

        // Step 2: AST Parsing
        setTimeout(() => UIManager.updateProgressStep("Parsing AST Structure & McCabe Complexity", 2, 5), 300);
        // Step 3: Coupling Topology
        setTimeout(() => UIManager.updateProgressStep("Building Dependency Graph & Coupling Metrics", 3, 5), 600);
        // Step 4: RKM Policy Evaluation
        setTimeout(() => UIManager.updateProgressStep("Evaluating RKM Rules & Scoring System Impact", 4, 5), 900);

        const res = await APIClient.post("/api/v1/analyze", { repo: repoPath, force });

        UIManager.updateProgressStep("Finalizing Dashboard Visualizations", 5, 5);
        UIManager.setButtonLoading(loadRepoBtn, false);

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

    const btnRescan = document.getElementById("btn-rescan");
    if (btnRescan) {
        btnRescan.onclick = () => triggerAnalysis(true);
    }

    // -------------------------------------------------------------
    // Dashboard UI Updater
    // -------------------------------------------------------------
    function updateDashboard(data) {
        if (!data) return;

        // Render Overview & Confidence Panel Metrics
        const stats = data.stats || {};
        UIManager.setElementText("stat-total-files", stats.total_files ?? 0);
        UIManager.setElementText("stat-total-functions", stats.total_functions ?? 0);
        UIManager.setElementText("stat-avg-complexity", (stats.avg_complexity ?? 0).toFixed(2));
        UIManager.setElementText("stat-risk-score", (stats.overall_risk_score ?? 0).toFixed(2));
        UIManager.renderConfidencePanel(data);

        // Render Graph Topology
        if (data.dependency_graph) {
            graphView.render(data.dependency_graph);
        }

        // Hide Empty State
        UIManager.toggleClass("dashboard-empty-state", "hidden", true);
    }

    // -------------------------------------------------------------
    // Quick Demo Preset Launcher
    // -------------------------------------------------------------
    const btnDemoRepo = document.getElementById("btn-demo-repo");
    if (btnDemoRepo) {
        btnDemoRepo.onclick = () => {
            if (repoInput) repoInput.value = ".";
            triggerAnalysis(true);
        };
    }

    console.log("[Ultron SPA] UI Engine Ready (v1.3.0).");
});
