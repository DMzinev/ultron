/**
 * Ultron Web SPA — UI Component Manager & Error Boundaries
 * Campaign 7, 9 & 17: Component State Audit, System Confidence & Null-Safe DOM Helpers
 */

export class UIManager {
    static _lastToast = { message: "", time: 0, timer: null };

    static showToast(message, isError = false) {
        if (!message) return;
        const now = Date.now();
        const toast = document.getElementById("toast");
        if (!toast) return;

        // Rule 1: Collapse identical message within 2000ms
        if (this._lastToast.message === message && (now - this._lastToast.time) < 2000) {
            return;
        }

        // Rule 2: Clear existing timeout so notifications do not stack
        if (this._lastToast.timer) {
            clearTimeout(this._lastToast.timer);
            this._lastToast.timer = null;
        }

        this._lastToast.message = message;
        this._lastToast.time = now;

        toast.textContent = message;
        toast.style.background = isError ? "rgba(244, 63, 94, 0.95)" : "rgba(15, 23, 42, 0.95)";
        toast.style.borderColor = isError ? "#f43f5e" : "#38bdf8";
        toast.classList.remove("hidden");

        // Rule 3: Errors stay visible longer (6000ms) than success notices (3500ms)
        const duration = isError ? 6000 : 3500;
        this._lastToast.timer = setTimeout(() => {
            toast.classList.add("hidden");
            this._lastToast.timer = null;
        }, duration);
    }

    static showErrorBanner(message, title = "Repository Diagnostic Notice", guidance = {}) {
        const banner = document.getElementById("repo-error-banner");
        if (!banner) return;
        const msgEl = document.getElementById("repo-error-message");
        if (msgEl) {
            if (guidance && (guidance.what || guidance.why || guidance.next)) {
                msgEl.innerHTML = `
                    <div style="display:flex; flex-direction:column; gap:4px; margin-top:2px;">
                        <div><strong>What happened:</strong> ${guidance.what || message}</div>
                        ${guidance.why ? `<div style="color:#94a3b8; font-size:11px;"><strong>Why:</strong> ${guidance.why}</div>` : ''}
                        ${guidance.next ? `<div style="color:#38bdf8; font-size:11px;"><strong>Next step:</strong> ${guidance.next}</div>` : ''}
                    </div>
                `;
            } else {
                msgEl.textContent = message;
            }
        }
        const titleEl = banner.querySelector("span");
        if (titleEl && title) titleEl.textContent = title;
        banner.classList.remove("hidden");
    }

    static hideErrorBanner() {
        const banner = document.getElementById("repo-error-banner");
        if (banner) banner.classList.add("hidden");
    }

    static setElementText(id, text, fallback = "N/A") {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = (text !== undefined && text !== null && text !== "") ? String(text) : fallback;
        }
    }

    static setElementStyle(id, property, value) {
        const el = document.getElementById(id);
        if (el) {
            el.style[property] = value;
        }
    }

    static toggleClass(id, className, force) {
        const el = document.getElementById(id);
        if (el) {
            el.classList.toggle(className, force);
        }
    }

    static setButtonLoading(buttonOrId, isLoading, loadingText = "") {
        const btn = typeof buttonOrId === 'string' ? document.getElementById(buttonOrId) : buttonOrId;
        if (!btn) return;

        if (isLoading) {
            btn.dataset.originalHtml = btn.innerHTML;
            btn.disabled = true;
            btn.classList.add("loading");
            if (loadingText) {
                btn.innerHTML = `<span class="spinner-small"></span> ${loadingText}`;
            }
        } else {
            btn.disabled = false;
            btn.classList.remove("loading");
            if (btn.dataset.originalHtml) {
                btn.innerHTML = btn.dataset.originalHtml;
                delete btn.dataset.originalHtml;
            }
        }
    }

    static updateProgressStep(stepName, stepIndex = 1, totalSteps = 5) {
        const progressCard = document.getElementById("analysis-progress-card");
        if (progressCard) progressCard.classList.remove("hidden");

        const textEl = document.getElementById("progress-step-text") || document.getElementById("loader-step-text");
        const barEl = document.getElementById("progress-bar-fill") || document.getElementById("loader-progress-bar");

        let pct;
        if (stepIndex === -1) {
            pct = -1;
        } else if (typeof stepIndex === "number" && stepIndex <= totalSteps && totalSteps > 0 && totalSteps !== 100 && stepIndex <= 10) {
            pct = Math.min(100, Math.max(0, Math.round((stepIndex / totalSteps) * 100)));
        } else {
            pct = Math.min(100, Math.max(0, Math.round(stepIndex)));
        }

        if (textEl) {
            if (pct === -1) {
                textEl.textContent = stepName;
            } else if (stepIndex <= totalSteps && totalSteps > 0 && totalSteps !== 100 && stepIndex <= 10) {
                textEl.textContent = `[${stepIndex}/${totalSteps}] ${stepName} (${pct}%)`;
            } else {
                textEl.textContent = `${stepName} (${pct}%)`;
            }
        }
        if (barEl) {
            if (pct === -1) {
                barEl.style.width = "100%";
                barEl.classList.add("indeterminate");
            } else {
                barEl.classList.remove("indeterminate");
                barEl.style.width = `${pct}%`;
            }
        }
    }

    static renderConfidencePanel(data) {
        const stats = data?.stats || {};
        const totalFiles = stats.total_files || 0;
        const totalFuncs = stats.total_functions || 0;
        
        this.setElementText("hero-trust-chain-title", `${totalFiles} Files / ${totalFuncs} Functions`);
        this.setElementText("hero-trust-chain-sub", "✓ 100% Local AST Facts · Zero Telemetry");
    }

    static renderTopRiskForces(risks) {
        if (!Array.isArray(risks) || risks.length === 0) {
            this.setElementText("hero-top-risk-1-file", "No high risk files detected");
            this.setElementText("hero-top-risk-1-score", "Clean AST baseline");
            this.setElementText("hero-top-risk-2-file", "No secondary risk force");
            this.setElementText("hero-top-risk-2-score", "Clean AST baseline");
            return;
        }

        const sorted = [...risks].sort((a, b) => (b.impact_score || 0) - (a.impact_score || 0));
        
        const top1 = sorted[0];
        if (top1) {
            const fileName = top1.file_path ? top1.file_path.split(/[/\\]/).pop() : "Unknown Module";
            this.setElementText("hero-top-risk-1-file", fileName);
            this.setElementText("hero-top-risk-1-score", `Impact: ${(top1.impact_score || 0).toFixed(2)} (Comp: ${top1.complexity || 1}, Coup: ${top1.coupling_score || 0})`);
        }

        const top2 = sorted[1];
        if (top2) {
            const fileName = top2.file_path ? top2.file_path.split(/[/\\]/).pop() : "Unknown Module";
            this.setElementText("hero-top-risk-2-file", fileName);
            this.setElementText("hero-top-risk-2-score", `Impact: ${(top2.impact_score || 0).toFixed(2)} (Comp: ${top2.complexity || 1}, Coup: ${top2.coupling_score || 0})`);
        }
    }

    static renderRiskMatrixTable(risks, onSelectFile, sortColumn = 'impact_score', sortAsc = false, minScore = 0.0, language = 'all', page = 1, pageSize = 20, onPageChange = null, recommendations = null) {
        const tbody = document.getElementById("file-risk-tbody");
        const table = document.getElementById("file-risk-table");
        const countBadge = document.getElementById("risk-threshold-count");
        if (!tbody) return;

        // Render header sort arrows and active column highlighting
        if (table) {
            const ths = table.querySelectorAll("thead th");
            const sortKeyMap = ['file_path', 'complexity', 'coupling_score', 'impact_score', 'level', 'confidence'];
            ths.forEach((th, idx) => {
                const key = sortKeyMap[idx];
                if (key) {
                    const arrow = (sortColumn === key) ? (sortAsc ? " ▲" : " ▼") : "";
                    const baseText = th.getAttribute("data-base-label") || th.textContent.replace(/[▲▼]/g, "").trim();
                    if (!th.getAttribute("data-base-label")) th.setAttribute("data-base-label", baseText);
                    th.textContent = baseText + arrow;
                    th.setAttribute("title", `Click to sort by ${key}`);
                    th.style.cursor = "pointer";
                    th.style.color = (sortColumn === key) ? "#38bdf8" : "";
                }
            });
        }

        const rawRisks = Array.isArray(risks) ? risks : [];
        if (rawRisks.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="table-empty">No files analyzed in this repository.</td></tr>`;
            if (countBadge) countBadge.textContent = "0 / 0";
            const pagInfo = document.getElementById("risk-pagination-info");
            const pagIndicator = document.getElementById("risk-page-indicator");
            const btnPrev = document.getElementById("btn-risk-page-prev");
            const btnNext = document.getElementById("btn-risk-page-next");
            if (pagInfo) pagInfo.textContent = "Showing 0-0 of 0 modules";
            if (pagIndicator) pagIndicator.textContent = "Page 1 of 1";
            if (btnPrev) btnPrev.disabled = true;
            if (btnNext) btnNext.disabled = true;
            return;
        }

        // 1. Language Filtering
        let filtered = rawRisks;
        if (language && language !== "all") {
            const lang = language.toLowerCase();
            filtered = filtered.filter(r => {
                const norm = (r.file_path || r.file || "").toLowerCase();
                if (lang === "py") return norm.endsWith(".py");
                if (lang === "ts") return norm.endsWith(".ts") || norm.endsWith(".tsx");
                if (lang === "js") return norm.endsWith(".js") || norm.endsWith(".jsx") || norm.endsWith(".mjs") || norm.endsWith(".cjs");
                if (lang === "go") return norm.endsWith(".go");
                return true;
            });
        }

        // 2. Minimum Score Threshold Filtering
        filtered = filtered.filter(r => (Number(r.impact_score) || 0) >= (Number(minScore) || 0));

        if (countBadge) {
            countBadge.textContent = `${filtered.length} / ${rawRisks.length} modules`;
        }

        if (filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="table-empty">No files match the active filters (Lang: ${language.toUpperCase()}, Min Impact: ≥ ${Number(minScore).toFixed(1)}).</td></tr>`;
            const pagInfo = document.getElementById("risk-pagination-info");
            const pagIndicator = document.getElementById("risk-page-indicator");
            const btnPrev = document.getElementById("btn-risk-page-prev");
            const btnNext = document.getElementById("btn-risk-page-next");
            if (pagInfo) pagInfo.textContent = "Showing 0-0 of 0 modules";
            if (pagIndicator) pagIndicator.textContent = "Page 1 of 1";
            if (btnPrev) btnPrev.disabled = true;
            if (btnNext) btnNext.disabled = true;
            return;
        }

        // 3. Sorting
        const sorted = [...filtered].sort((a, b) => {
            let valA, valB;
            if (sortColumn === 'file_path') {
                valA = (a.file_path || a.file || "").replace(/\\/g, '/').toLowerCase();
                valB = (b.file_path || b.file || "").replace(/\\/g, '/').toLowerCase();
                return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
            } else if (sortColumn === 'complexity') {
                valA = Number(a.complexity || a.mccabe_complexity || 0);
                valB = Number(b.complexity || b.mccabe_complexity || 0);
            } else if (sortColumn === 'coupling_score') {
                valA = Number(a.coupling_score || a.coupling || 0);
                valB = Number(b.coupling_score || b.coupling || 0);
            } else if (sortColumn === 'level') {
                const rank = { HIGH: 3, MEDIUM: 2, LOW: 1 };
                valA = rank[a.level] || 0;
                valB = rank[b.level] || 0;
            } else if (sortColumn === 'confidence') {
                valA = Number(a.confidence != null ? a.confidence : 0.9);
                valB = Number(b.confidence != null ? b.confidence : 0.9);
            } else {
                valA = Number(a.impact_score || a.score || 0);
                valB = Number(b.impact_score || b.score || 0);
            }
            return sortAsc ? valA - valB : valB - valA;
        });

        // 4. Pagination & Decision Card Hydration (Phase 2.8 Consequence-Driven)
        const decisionCard = document.getElementById("what-matters-decision-card");
        if (decisionCard && (sorted.length > 0 || (recommendations && recommendations.length > 0))) {
            const topRec = (recommendations && recommendations.length > 0) ? recommendations[0] : null;
            const topRisk = sorted[0] || {};
            const topItem = topRec || topRisk;

            const topPath = (topItem.target_file || topItem.file_path || topItem.file || "").replace(/\\/g, '/');
            const topCoupling = Math.round(topItem.coupling || topItem.coupling_score || 0);
            const topComplexity = topItem.complexity || topItem.mccabe_complexity || 1;
            
            decisionCard.style.display = "block";
            const targetEl = document.getElementById("decision-target-file");
            if (targetEl) targetEl.textContent = topPath;
            const wrongEl = document.getElementById("decision-what-wrong");
            if (wrongEl) wrongEl.textContent = topItem.why_this || `${topPath} is a central dependency with elevated complexity (${topComplexity}) and ${topCoupling} inbound callers.`;
            const conseqEl = document.getElementById("decision-consequence");
            if (conseqEl) conseqEl.textContent = topItem.what_could_break || (topCoupling > 5 ? "Changes may affect routing, analysis, and agent handoff workflows across the repository." : "Local impact with limited blast radius.");
            const altEl = document.getElementById("decision-why-not-alternatives");
            if (altEl) {
                if (topItem.alternatives_compared && topItem.alternatives_compared.length > 0) {
                    altEl.textContent = topItem.alternatives_compared.map(a => `${(a?.file || "module").split(/[/\\]/).pop()}: ${a?.why_not || "Lower priority"}`).join(' · ');
                } else {
                    altEl.textContent = "Higher local complexity but lower architectural centrality or consequence.";
                }
            }
            const confEl = document.getElementById("decision-confidence-evidence");
            if (confEl) {
                const limText = (topItem.limitations && topItem.limitations.length > 0) ? ` [Limitations: ${topItem.limitations.join('; ')}]` : '';
                confEl.textContent = `${topItem.confidence_tier || 'HIGH'} Confidence · Source: ${topItem.evidence_tier || 'OBSERVED'} (${topItem.confidence_reason || 'Direct AST call-graph verification'})${limText}`;
            }
            const evEl = document.getElementById("decision-supporting-evidence");
            if (evEl) {
                evEl.textContent = `Structure Details: Connected Callers: ${topCoupling} · Decision Branches: ${topComplexity} · Change Risk: ${Number(topItem.impact_score || 0).toFixed(2)}`;
            }

            const btnPrepare = document.getElementById("btn-decision-prepare-mission");
            if (btnPrepare) {
                btnPrepare.onclick = () => {
                    fetch("/api/v1/decision/record", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            recommendation: topItem,
                            selection_source: "HUMAN",
                            selection_outcome: "USEFUL",
                            human_feedback: "Accepted recommended starting point from What Matters card."
                        })
                    }).catch(() => {});
                    if (typeof onSelectFile === 'function') onSelectFile(topPath, false, true);
                    const navAgent = document.getElementById("nav-prompt") || document.querySelector('[data-tab="prompt-tab"]');
                    if (navAgent) navAgent.click();
                };
            }
            const btnPlausible = document.getElementById("btn-decision-mark-plausible");
            if (btnPlausible) {
                btnPlausible.onclick = () => {
                    fetch("/api/v1/decision/record", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            recommendation: topItem,
                            selection_source: "HUMAN",
                            selection_outcome: "PLAUSIBLE",
                            human_feedback: "Factually sound structure but unrelated to immediate task."
                        })
                    }).then(() => {
                        btnPlausible.textContent = "✓ Marked Plausible";
                        btnPlausible.disabled = true;
                    }).catch(() => {});
                };
            }
            const btnDismiss = document.getElementById("btn-decision-dismiss-wrong");
            if (btnDismiss) {
                btnDismiss.onclick = () => {
                    fetch("/api/v1/decision/record", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            recommendation: topItem,
                            selection_source: "HUMAN",
                            selection_outcome: "WRONG",
                            human_feedback: "Dismissed by developer as incorrect recommendation."
                        })
                    }).then(() => {
                        btnDismiss.textContent = "✓ Dismissed";
                        btnDismiss.disabled = true;
                    }).catch(() => {});
                };
            }
            const btnViewGraph = document.getElementById("btn-decision-view-graph");
            if (btnViewGraph) {
                btnViewGraph.onclick = () => {
                    const navGraph = document.getElementById("nav-graph") || document.querySelector('[data-tab="graph-tab"]');
                    if (navGraph) navGraph.click();
                    if (window.fullGraphView && typeof window.fullGraphView.focusNode === 'function') {
                        window.fullGraphView.focusNode(topPath);
                    }
                };
            }
        }

        const totalItems = sorted.length;
        const actualPageSize = Math.max(5, Number(pageSize) || 20);
        const totalPages = Math.max(1, Math.ceil(totalItems / actualPageSize));
        const activePage = Math.max(1, Math.min(totalPages, Number(page) || 1));
        const startIndex = (activePage - 1) * actualPageSize;
        const endIndex = Math.min(totalItems, startIndex + actualPageSize);
        const visibleRows = sorted.slice(startIndex, endIndex);

        const pagInfo = document.getElementById("risk-pagination-info");
        const pagIndicator = document.getElementById("risk-page-indicator");
        const btnPrev = document.getElementById("btn-risk-page-prev");
        const btnNext = document.getElementById("btn-risk-page-next");

        if (pagInfo) {
            pagInfo.textContent = `Showing ${startIndex + 1}-${endIndex} of ${totalItems} modules`;
        }
        if (pagIndicator) {
            pagIndicator.textContent = `Page ${activePage} of ${totalPages}`;
        }
        if (btnPrev) {
            btnPrev.disabled = activePage <= 1;
            btnPrev.onclick = (e) => {
                e.preventDefault();
                if (activePage > 1 && typeof onPageChange === 'function') {
                    onPageChange(activePage - 1);
                }
            };
        }
        if (btnNext) {
            btnNext.disabled = activePage >= totalPages;
            btnNext.onclick = (e) => {
                e.preventDefault();
                if (activePage < totalPages && typeof onPageChange === 'function') {
                    onPageChange(activePage + 1);
                }
            };
        }

        // 5. Render Visible Table Rows with Consequence Descriptions
        tbody.innerHTML = visibleRows.map((r) => {
            const normPath = (r.file_path || r.file || "").replace(/\\/g, '/');
            const pathParts = normPath.split('/');
            const displayPath = pathParts.length > 3 ? `${pathParts[0]}/.../${pathParts.slice(-2).join('/')}` : normPath;
            const ext = normPath.split('.').pop().toLowerCase();
            let langTag = "PY";
            let langColor = "#38bdf8";
            if (ext === "ts" || ext === "tsx") { langTag = "TS"; langColor = "#3b82f6"; }
            else if (ext === "js" || ext === "jsx" || ext === "mjs" || ext === "cjs") { langTag = "JS"; langColor = "#f59e0b"; }
            else if (ext === "go") { langTag = "GO"; langColor = "#06b6d4"; }
            else if (ext === "py") { langTag = "PY"; langColor = "#38bdf8"; }
            else { langTag = ext.toUpperCase().slice(0, 3) || "MOD"; langColor = "#94a3b8"; }

            const level = r.level || "LOW";
            const levelColor = level === "HIGH" ? "#ef4444" : (level === "MEDIUM" ? "#f59e0b" : "#10b981");
            const confPct = Math.round((r.confidence != null ? r.confidence : 0.9) * 100);
            const compVal = r.complexity || r.mccabe_complexity || 1;
            const coupVal = Math.round(r.coupling_score || r.coupling || 0);
            const impactVal = (r.impact_score != null ? Number(r.impact_score) : 0).toFixed(2);
            const consequenceText = coupVal > 8 ? `High blast radius (affects ${coupVal} components)` : (coupVal > 2 ? `Moderate impact (${coupVal} callers)` : `Localized component`);
            
            return `
                <tr class="risk-matrix-row" data-path="${normPath}" style="border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.2s ease; cursor: pointer;">
                    <td style="font-family: var(--font-mono); font-size: 12.5px; color: #f1f5f9; font-weight: 600;">
                        <div style="display: flex; align-items: center;">
                            <span style="display: inline-block; padding: 1px 5px; border-radius: 4px; font-size: 9px; font-weight: 800; background: ${langColor}22; color: ${langColor}; border: 1px solid ${langColor}44; margin-right: 6px;">${langTag}</span>
                            <span title="${normPath}">${displayPath}</span>
                        </div>
                        <div style="font-size: 11px; color: #94a3b8; font-weight: normal; margin-top: 2px;">${consequenceText}</div>
                    </td>
                    <td style="font-family: var(--font-mono); text-align: center; color: #38bdf8; font-weight: 700;">
                        ${compVal}
                    </td>
                    <td style="font-family: var(--font-mono); text-align: center; color: #cbd5e1;">
                        ${coupVal} callers
                    </td>
                    <td style="font-family: var(--font-mono); font-weight: 700; color: ${levelColor}; text-align: center;">
                        ${impactVal}
                    </td>
                    <td style="text-align: center;">
                        <span style="display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 700; background: ${levelColor}22; color: ${levelColor}; border: 1px solid ${levelColor}44;">
                            ${level}
                        </span>
                    </td>
                    <td style="font-size: 11px; text-align: center; color: #94a3b8;">
                        ${confPct}%
                    </td>
                    <td style="text-align: center;">
                        <button class="btn secondary btn-small btn-inspect-file" data-path="${normPath}" style="padding: 4px 10px; font-size: 11.5px; border-color: rgba(56,189,248,0.4); color: #38bdf8; font-weight: 600;">
                            🚀 Prepare
                        </button>
                    </td>
                </tr>
            `;
        }).join("");

        if (typeof onSelectFile === 'function') {
            tbody.onclick = (e) => {
                const inspectBtn = e.target.closest(".btn-inspect-file");
                if (inspectBtn) {
                    e.stopPropagation();
                    const filePath = inspectBtn.getAttribute("data-path");
                    if (filePath) onSelectFile(filePath, false, true);
                    return;
                }
                const targetRow = e.target.closest(".risk-matrix-row");
                if (targetRow) {
                    const filePath = targetRow.getAttribute("data-path");
                    if (filePath) onSelectFile(filePath, false, true);
                }
            };
        }
    }

    static renderRecommendations(recommendations, onSelectFile, onFocusGraph, onCopyPrompt) {
        return this.renderRecommendationsList(recommendations, onSelectFile, onFocusGraph, onCopyPrompt);
    }

    static renderRecommendationsList(recommendations, onSelectFile, onFocusGraph, onCopyPrompt) {
        const container = document.getElementById("recommendations-list");
        if (!container) return;

        if (!Array.isArray(recommendations) || recommendations.length === 0) {
            container.innerHTML = `<div style="color: #94a3b8; font-size: 0.9rem; font-style: italic;">No high-priority refactoring recommendations required. Codebase architecture is clean!</div>`;
            return;
        }

        container.innerHTML = recommendations.slice(0, 5).map(rec => {
            const filePath = rec.file || rec.target_file || "";
            const normPath = filePath.replace(/\\/g, '/');
            const fileName = normPath.split('/').pop() || normPath;
            const reduction = rec.structural_complexity_reduction_estimate_pct || rec.estimated_maintenance_cost_reduction_pct || 35;
            const steps = rec.action_plan_steps || rec.steps || [];

            return `
                <div class="rec-card-item" style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 8px; padding: 14px; margin-bottom: 8px; transition: border-color 0.2s, transform 0.2s;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                        <div style="font-family: var(--font-mono); font-weight: 700; color: #f8fafc; font-size: 0.95rem;">
                            🎯 <span style="color: #38bdf8;">${fileName}</span>
                            <span style="font-size: 11px; color: #94a3b8; font-weight: normal; margin-left: 6px;">(${normPath})</span>
                        </div>
                        <div style="display: flex; gap: 6px; align-items: center;">
                            <span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700;">
                                -${reduction}% Complexity
                            </span>
                            <button class="btn secondary btn-small btn-inspect-rec" data-path="${normPath}" style="padding: 2px 8px; font-size: 11px;" title="Inspect in Workspace Editor">
                                🔍 Inspect
                            </button>
                            <button class="btn secondary btn-small btn-focus-rec" data-path="${normPath}" style="padding: 2px 8px; font-size: 11px; border-color: rgba(56,189,248,0.4); color: #38bdf8;" title="Focus in Dependency Graph Viewport">
                                🎯 Focus
                            </button>
                            <button class="btn secondary btn-small btn-copy-rec-prompt" data-path="${normPath}" data-fileName="${fileName}" style="padding: 2px 8px; font-size: 11px; border-color: rgba(192,132,252,0.4); color: #c084fc;" title="Copy Grounded AI Refactoring Prompt">
                                📋 Copy Prompt
                            </button>
                        </div>
                    </div>
                    ${steps.length > 0 ? `
                        <div style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.4; background: rgba(15, 23, 42, 0.4); padding: 8px 12px; border-radius: 6px; border-left: 3px solid #38bdf8;">
                            ${steps.map(s => `<div style="margin-bottom: 2px;">• ${s}</div>`).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        }).join("");

        container.querySelectorAll(".btn-inspect-rec").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const filePath = btn.getAttribute("data-path");
                if (filePath && typeof onSelectFile === 'function') onSelectFile(filePath, true);
            });
        });

        container.querySelectorAll(".btn-focus-rec").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const filePath = btn.getAttribute("data-path");
                if (filePath && typeof onFocusGraph === 'function') onFocusGraph(filePath);
            });
        });

        container.querySelectorAll(".btn-copy-rec-prompt").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const filePath = btn.getAttribute("data-path");
                const fileName = btn.getAttribute("data-fileName");
                if (filePath && typeof onCopyPrompt === 'function') onCopyPrompt(filePath, fileName);
            });
        });
    }

    static renderRefactoringROIScorecard(risks, onSelectFile) {
        const container = document.getElementById("refactoring-roi-tbody");
        if (!container) return;

        if (!Array.isArray(risks) || risks.length === 0) {
            container.innerHTML = `<tr><td colspan="5" class="table-empty">Connect repository to calculate refactoring ROI</td></tr>`;
            return;
        }

        // Calculate deterministic client ROI
        const evaluated = risks.map(r => {
            const path = String(r.file || r.file_path || "").replace(/\\/g, '/');
            const name = path.split('/').pop() || path;
            const complexity = Number(r.complexity || r.mccabe_complexity || 1.0);
            const coupling = Number(r.coupling_score || r.coupling || 0.0);
            const impact = Number(r.impact_score || r.score || 0.0);
            const effortLoc = Math.max(5, Math.round(complexity * 3.0 + coupling * 2.5));
            const rawNumerator = (coupling * 0.6 + complexity * 0.4) * impact;
            const roiScore = Math.round((rawNumerator / Math.max(1, effortLoc)) * 10.0 * 100) / 100;
            const reductionPct = complexity > 4.0 ? Math.min(75.0, Math.round(((complexity - 4.0) / complexity) * 1000) / 10) : 0.0;
            
            let tier = "🧹 Routine Cleanup";
            let tierBg = "rgba(148, 163, 184, 0.12)";
            let tierColor = "#94a3b8";
            let tierBorder = "rgba(148, 163, 184, 0.3)";

            if (roiScore >= 5.0 && effortLoc <= 35) {
                tier = "⚡ Quick Win";
                tierBg = "rgba(16, 185, 129, 0.15)";
                tierColor = "#10b981";
                tierBorder = "rgba(16, 185, 129, 0.4)";
            } else if (impact >= 4.0 || coupling >= 5.0) {
                tier = "🏗️ Deep Decouple";
                tierBg = "rgba(168, 85, 247, 0.15)";
                tierColor = "#c084fc";
                tierBorder = "rgba(168, 85, 247, 0.4)";
            }

            return { path, name, complexity, coupling, impact, effortLoc, roiScore, reductionPct, tier, tierBg, tierColor, tierBorder };
        }).filter(r => Boolean(r.path));

        // Sort by ROI descending
        evaluated.sort((a, b) => b.roiScore - a.roiScore || b.impact - a.impact);
        const topOpps = evaluated.slice(0, 8);

        if (topOpps.length === 0) {
            container.innerHTML = `<tr><td colspan="5" class="table-empty">No high-ROI refactoring opportunities found.</td></tr>`;
            return;
        }

        container.innerHTML = topOpps.map(opp => `
            <tr class="table-row-clickable" data-path="${opp.path}" style="cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.15s ease;">
                <td>
                    <div style="font-family: var(--font-mono); font-weight: 700; color: #f8fafc; font-size: 13px;">${opp.name}</div>
                    <div style="font-family: var(--font-mono); font-size: 11px; color: #94a3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px;" title="${opp.path}">${opp.path}</div>
                </td>
                <td style="text-align: center;">
                    <span style="font-family: var(--font-mono); font-size: 13px; font-weight: 700; color: #38bdf8;">${opp.roiScore.toFixed(1)}x</span>
                </td>
                <td style="text-align: center;">
                    <span style="font-family: var(--font-mono); font-size: 12px; color: #cbd5e1;">~${opp.effortLoc} LOC</span>
                </td>
                <td style="text-align: center;">
                    <span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700;">
                        -${opp.reductionPct}%
                    </span>
                </td>
                <td style="text-align: right;">
                    <span style="display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; background: ${opp.tierBg}; color: ${opp.tierColor}; border: 1px solid ${opp.tierBorder};">
                        ${opp.tier}
                    </span>
                </td>
            </tr>
        `).join("");

        container.querySelectorAll(".table-row-clickable").forEach(row => {
            row.addEventListener("click", () => {
                const p = row.getAttribute("data-path");
                if (p && typeof onSelectFile === 'function') {
                    onSelectFile(p, false, true);
                }
            });
        });
    }

    static renderModularityScorecard(data, onSelectFile) {
        const gradeBadge = document.getElementById("modularity-health-grade");
        const healthScoreEl = document.getElementById("modularity-health-score");
        const meanInstabilityEl = document.getElementById("modularity-mean-instability");
        const meanDistanceEl = document.getElementById("modularity-mean-distance");
        const zoneMainSeqEl = document.getElementById("modularity-zone-main-seq");
        const zonePainEl = document.getElementById("modularity-zone-pain");
        const zoneUselessEl = document.getElementById("modularity-zone-useless");
        const painModulesContainer = document.getElementById("modularity-pain-modules-list");

        if (!data || typeof data !== 'object') return;

        const grade = data.health_grade || "A";
        const score = Number(data.health_score != null ? data.health_score : 100.0);
        const meanI = Number(data.mean_instability || 0.0);
        const meanD = Number(data.mean_distance || 0.0);
        const dist = data.zone_distribution || { main_sequence: 0, zone_of_pain: 0, zone_of_uselessness: 0 };
        const modules = data.modules || [];

        if (gradeBadge) {
            gradeBadge.textContent = `Grade ${grade}`;
            gradeBadge.className = `badge ${grade === 'A' ? 'low' : grade === 'B' ? 'med' : 'high'}`;
            gradeBadge.style.fontSize = "13px";
            gradeBadge.style.fontWeight = "800";
            gradeBadge.style.padding = "4px 12px";
        }

        if (healthScoreEl) healthScoreEl.textContent = `${score.toFixed(1)} / 100`;
        if (meanInstabilityEl) meanInstabilityEl.textContent = meanI.toFixed(2);
        if (meanDistanceEl) meanDistanceEl.textContent = meanD.toFixed(2);
        if (zoneMainSeqEl) zoneMainSeqEl.textContent = dist.main_sequence || 0;
        if (zonePainEl) zonePainEl.textContent = dist.zone_of_pain || 0;
        if (zoneUselessEl) zoneUselessEl.textContent = dist.zone_of_uselessness || 0;

        if (painModulesContainer) {
            const painModules = modules.filter(m => m.zone === "ZONE_OF_PAIN").slice(0, 4);
            if (painModules.length === 0) {
                painModulesContainer.innerHTML = `<div style="color: #94a3b8; font-size: 11px; font-style: italic;">No rigid "Zone of Pain" coupling bottlenecks found. Excellent separation of concerns!</div>`;
            } else {
                painModulesContainer.innerHTML = painModules.map(m => `
                    <div class="modularity-pain-item" data-path="${m.file_path}" style="cursor: pointer; background: rgba(244, 63, 94, 0.08); border: 1px solid rgba(244, 63, 94, 0.25); border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-family: var(--font-mono); font-size: 12px; font-weight: 700; color: #f8fafc;">${m.file_name}</div>
                            <div style="font-size: 10px; color: #cbd5e1;">Inbound callers: ${m.afferent_ca} | Outbound: ${m.efferent_ce} | Instability: ${m.instability}</div>
                        </div>
                        <span style="background: rgba(244, 63, 94, 0.2); color: #f43f5e; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700;">Zone of Pain</span>
                    </div>
                `).join("");

                painModulesContainer.querySelectorAll(".modularity-pain-item").forEach(item => {
                    item.addEventListener("click", () => {
                        const p = item.getAttribute("data-path");
                        if (p && typeof onSelectFile === 'function') onSelectFile(p, false, true);
                    });
                });
            }
        }
    }

    static renderAntiPatternAlerts(patterns, onSelectFile) {
        const tbody = document.getElementById("anti-pattern-tbody");
        const countBadge = document.getElementById("anti-pattern-count-badge");
        const countHigh = document.getElementById("anti-pattern-count-high");
        const countMed = document.getElementById("anti-pattern-count-med");
        const countLow = document.getElementById("anti-pattern-count-low");

        if (!tbody) return;

        if (!Array.isArray(patterns) || patterns.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="table-empty">No architectural anti-patterns detected. Clean modular design!</td>
                </tr>
            `;
            if (countBadge) countBadge.textContent = "0 Detected";
            if (countHigh) countHigh.textContent = "0 High";
            if (countMed) countMed.textContent = "0 Med";
            if (countLow) countLow.textContent = "0 Low";
            return;
        }

        const highCount = patterns.filter(p => p.severity === "HIGH").length;
        const medCount = patterns.filter(p => p.severity === "MEDIUM").length;
        const lowCount = patterns.filter(p => p.severity === "LOW").length;

        if (countBadge) countBadge.textContent = `${patterns.length} Detected`;
        if (countHigh) countHigh.textContent = `${highCount} High`;
        if (countMed) countMed.textContent = `${medCount} Med`;
        if (countLow) countLow.textContent = `${lowCount} Low`;

        tbody.innerHTML = patterns.map(ap => {
            const normPath = String(ap.file_path || ap.file || "").replace(/\\/g, '/');
            const sev = ap.severity || "MEDIUM";
            const sevClass = sev === "HIGH" ? "high" : (sev === "MEDIUM" ? "med" : "low");

            return `
                <tr class="table-row-clickable" data-path="${normPath}" style="cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.15s ease;">
                    <td>
                        <span class="badge ${sevClass}">${sev}</span>
                    </td>
                    <td>
                        <div style="font-weight: 700; color: #f8fafc; font-size: 12px;">${ap.pattern_name}</div>
                        <div style="font-family: var(--font-mono); font-size: 11px; color: #38bdf8;" title="${normPath}">${ap.file_name || normPath.split('/').pop()}</div>
                    </td>
                    <td style="font-size: 11px; color: #cbd5e1; max-width: 260px;">
                        ${ap.description}
                    </td>
                    <td style="font-size: 11px; color: #34d399; max-width: 280px;">
                        💡 ${ap.playbook}
                    </td>
                    <td style="text-align: right;">
                        <button class="btn secondary btn-small btn-inspect-ap" data-path="${normPath}" style="font-size: 10px; padding: 3px 8px; border-color: rgba(56,189,248,0.3);">🔍 Inspect</button>
                    </td>
                </tr>
            `;
        }).join("");

        tbody.onclick = (e) => {
            const inspectBtn = e.target.closest(".btn-inspect-ap");
            if (inspectBtn) {
                e.stopPropagation();
                const p = inspectBtn.getAttribute("data-path");
                if (p && typeof onSelectFile === 'function') onSelectFile(p, false, true);
                return;
            }
            const row = e.target.closest(".table-row-clickable");
            if (row) {
                const p = row.getAttribute("data-path");
                if (p && typeof onSelectFile === 'function') onSelectFile(p, false, true);
            }
        };
    }

    static renderWorkspaceSelector(workspaces, activeId, onSelectWorkspace) {
        const selectEl = document.getElementById("select-active-workspace") || document.getElementById("select-workspace");
        if (!selectEl) return;

        selectEl.innerHTML = "";

        if (!Array.isArray(workspaces) || workspaces.length === 0) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "📁 Default Workspace";
            selectEl.appendChild(opt);
            return;
        }

        workspaces.forEach(ws => {
            const opt = document.createElement("option");
            opt.value = ws.id;
            const subCount = ws.subpackage_count ? ` (${ws.subpackage_count} pkgs)` : "";
            opt.textContent = `📁 ${ws.name}${subCount}`;
            if (ws.id === activeId || ws.active) {
                opt.selected = true;
            }
            selectEl.appendChild(opt);
        });

        selectEl.onchange = (e) => {
            const chosenId = e.target.value;
            if (chosenId && typeof onSelectWorkspace === 'function') {
                onSelectWorkspace(chosenId);
            }
        };
    }

    static renderSnapshotDriftViewer(snapshots, activeIndex = 0, driftMetrics = {}, onSelectSnapshot) {
        const slider = document.getElementById("snapshot-timeline-slider");
        const currentLabel = document.getElementById("snapshot-active-label");
        const currentTs = document.getElementById("snapshot-active-timestamp");
        const countBadge = document.getElementById("snapshot-count-badge");
        const deltaHealthEl = document.getElementById("drift-delta-health");
        const deltaCompEl = document.getElementById("drift-delta-complexity");
        const deltaCoupEl = document.getElementById("drift-delta-coupling");
        const driftVelocityEl = document.getElementById("drift-velocity-pct");
        const driftDirBadge = document.getElementById("drift-direction-badge");

        if (!Array.isArray(snapshots) || snapshots.length === 0) {
            if (slider) { slider.min = 0; slider.max = 0; slider.value = 0; slider.disabled = true; }
            if (currentLabel) currentLabel.textContent = "No snapshots recorded yet";
            if (currentTs) currentTs.textContent = "-";
            if (countBadge) countBadge.textContent = "0 Snapshots";
            if (deltaHealthEl) deltaHealthEl.textContent = "-";
            if (deltaCompEl) deltaCompEl.textContent = "-";
            if (deltaCoupEl) deltaCoupEl.textContent = "-";
            if (driftVelocityEl) driftVelocityEl.textContent = "-";
            if (driftDirBadge) { driftDirBadge.textContent = "STABLE"; driftDirBadge.className = "badge low"; }
            return;
        }

        const idx = Math.max(0, Math.min(snapshots.length - 1, Number(activeIndex) || 0));
        const activeSnap = snapshots[idx];

        if (slider) {
            slider.min = 0;
            slider.max = snapshots.length - 1;
            slider.value = idx;
            slider.disabled = snapshots.length <= 1;
        }

        if (currentLabel) currentLabel.textContent = activeSnap.label || `Snapshot #${idx + 1}`;
        if (currentTs) currentTs.textContent = activeSnap.timestamp || "-";
        if (countBadge) countBadge.textContent = `${snapshots.length} Snapshots`;

        const dHealth = Number(driftMetrics.delta_health || 0.0);
        const dComp = Number(driftMetrics.delta_complexity || 0.0);
        const dCoup = Number(driftMetrics.delta_coupling || 0.0);
        const velocity = Number(driftMetrics.drift_velocity_pct || 0.0);
        const dir = driftMetrics.drift_direction || "STABLE";
        const dirClass = driftMetrics.direction_class || "low";

        if (deltaHealthEl) {
            deltaHealthEl.textContent = `${dHealth >= 0 ? '+' : ''}${dHealth.toFixed(1)}`;
            deltaHealthEl.style.color = dHealth >= 0 ? "#10b981" : "#f43f5e";
        }
        if (deltaCompEl) {
            deltaCompEl.textContent = `${dComp >= 0 ? '+' : ''}${dComp.toFixed(2)}`;
            deltaCompEl.style.color = dComp <= 0 ? "#10b981" : "#f43f5e";
        }
        if (deltaCoupEl) {
            deltaCoupEl.textContent = `${dCoup >= 0 ? '+' : ''}${dCoup.toFixed(2)}`;
            deltaCoupEl.style.color = dCoup <= 0 ? "#10b981" : "#f43f5e";
        }
        if (driftVelocityEl) driftVelocityEl.textContent = `${velocity.toFixed(1)}%`;

        if (driftDirBadge) {
            driftDirBadge.textContent = dir;
            driftDirBadge.className = `badge ${dirClass}`;
        }

        if (slider) {
            slider.oninput = (e) => {
                const chosenIdx = Number(e.target.value);
                if (typeof onSelectSnapshot === 'function') {
                    onSelectSnapshot(chosenIdx);
                }
            };
        }
    }

    static openExportModal() {
        const modal = document.getElementById("modal-export-reports");
        if (modal) {
            modal.classList.remove("hidden");
        }
    }

    static closeExportModal() {
        const modal = document.getElementById("modal-export-reports");
        if (modal) {
            modal.classList.add("hidden");
        }
    }

    static downloadBlobFile(filename, content, mimeType = "text/plain;charset=utf-8") {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    static renderPolicyGovernance(governanceData, onSelectFile) {
        const tbody = document.getElementById("policy-governance-tbody");
        const statusBadge = document.getElementById("policy-status-badge");
        const countBadge = document.getElementById("policy-violations-count");

        if (!tbody) return;

        const data = governanceData || {};
        const violations = Array.isArray(data.violations) ? data.violations : [];
        const isCompliant = data.status === "COMPLIANT" || violations.length === 0;

        if (statusBadge) {
            statusBadge.textContent = isCompliant ? "COMPLIANT" : "VIOLATIONS DETECTED";
            statusBadge.className = `badge ${isCompliant ? "low" : "high"}`;
        }

        if (countBadge) {
            countBadge.textContent = `${violations.length} Violations`;
            countBadge.className = `badge ${violations.length === 0 ? "low" : "high"}`;
        }

        if (violations.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="table-empty" style="color: #10b981;">✓ All architectural governance policies satisfied (0 boundary violations).</td></tr>`;
            return;
        }

        tbody.innerHTML = violations.map(v => {
            const sev = v.severity || "MEDIUM";
            const sevClass = sev === "HIGH" ? "high" : (sev === "MEDIUM" ? "medium" : "low");
            const src = v.source_file || "unknown";
            const tgt = v.target_file ? ` &rarr; <code>${v.target_file}</code>` : "";
            const msg = v.message || "Rule threshold breached.";
            const pb = v.remediation || "Refactor module structure.";

            return `
                <tr class="table-row-clickable" data-path="${src}">
                    <td><span class="badge ${sevClass}">${sev}</span></td>
                    <td><strong>${v.rule_name || v.rule_id}</strong></td>
                    <td><code>${src}</code>${tgt}<br><small style="color:#94a3b8;">${msg}</small></td>
                    <td style="font-size:12px; color:#cbd5e1;">${pb}</td>
                    <td style="text-align:right;">
                        <button class="btn secondary btn-small" style="font-size:11px; padding:2px 8px;">Inspect</button>
                    </td>
                </tr>
            `;
        }).join("");

        tbody.querySelectorAll(".table-row-clickable").forEach(row => {
            row.addEventListener("click", () => {
                const p = row.getAttribute("data-path");
                if (p && typeof onSelectFile === 'function') {
                    onSelectFile(p);
                }
            });
        });
    }

    static renderDiffPreview(diffText, deltaMetrics = {}) {
        const preEl = document.getElementById("diff-preview-content");
        const beforeEl = document.getElementById("diff-complexity-before");
        const afterEl = document.getElementById("diff-complexity-after");
        const deltaEl = document.getElementById("diff-complexity-delta");
        const reductionEl = document.getElementById("diff-reduction-pct");

        if (beforeEl) beforeEl.textContent = deltaMetrics.complexity_before != null ? deltaMetrics.complexity_before : "-";
        if (afterEl) afterEl.textContent = deltaMetrics.complexity_after != null ? deltaMetrics.complexity_after : "-";
        if (deltaEl) deltaEl.textContent = deltaMetrics.delta != null ? `-${deltaMetrics.delta}` : "-";
        if (reductionEl) reductionEl.textContent = deltaMetrics.risk_reduction_pct != null ? `-${deltaMetrics.risk_reduction_pct}%` : "-";

        if (!preEl) return;
        if (!diffText || !diffText.trim()) {
            preEl.innerHTML = `<div class="diff-line" style="color: #94a3b8; font-style: italic;">No changes proposed. Module is already modular and clean.</div>`;
            return;
        }

        const lines = diffText.split("\n");
        preEl.innerHTML = lines.map(line => {
            let cls = "diff-line";
            if (line.startsWith("+++") || line.startsWith("---")) {
                cls += " diff-header";
            } else if (line.startsWith("@@")) {
                cls += " diff-hunk";
            } else if (line.startsWith("+")) {
                cls += " diff-add";
            } else if (line.startsWith("-")) {
                cls += " diff-del";
            }
            const escaped = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return `<div class="${cls}">${escaped || '&nbsp;'}</div>`;
        }).join("");
    }

    static renderFileExplorer(fileTree, onSelectFile) {
        const treeContainer = document.getElementById("file-explorer-tree");
        if (!treeContainer) return;

        if (!Array.isArray(fileTree) || fileTree.length === 0) {
            treeContainer.innerHTML = `<div class="table-empty">No python files discovered.</div>`;
            return;
        }

        treeContainer.innerHTML = fileTree.map(f => {
            const normPath = f.replace(/\\/g, '/');
            return `
                <div class="file-tree-item" data-path="${normPath}" style="padding: 6px 10px; border-radius: 4px; cursor: pointer; display: flex; align-items: center; gap: 8px; font-family: var(--font-mono); font-size: 12px; color: #cbd5e1; transition: background 0.15s ease;">
                    <span style="color: #38bdf8;">📄</span>
                    <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${normPath}</span>
                </div>
            `;
        }).join("");

        treeContainer.querySelectorAll(".file-tree-item").forEach(item => {
            item.addEventListener("click", () => {
                const filePath = item.getAttribute("data-path");
                if (filePath && typeof onSelectFile === 'function') {
                    onSelectFile(filePath);
                }
            });
        });
    }

    static renderCreatorHeatmap(risks) {
        const container = document.getElementById("creator-heatmap-grid");
        if (!container) return;

        if (!Array.isArray(risks) || risks.length === 0) {
            container.innerHTML = `<div class="table-empty">Connect and scan a repository to load metrics.</div>`;
            return;
        }

        container.innerHTML = risks.map(r => {
            const normPath = (r.file_path || "").replace(/\\/g, '/');
            const name = normPath.split('/').pop() || normPath;
            const level = r.level || "LOW";
            const color = level === "HIGH" ? "#ef4444" : (level === "MEDIUM" ? "#f59e0b" : "#10b981");
            const bg = level === "HIGH" ? "rgba(239,68,68,0.15)" : (level === "MEDIUM" ? "rgba(245,158,11,0.15)" : "rgba(16,185,129,0.15)");

            return `
                <div style="background: ${bg}; border: 1px solid ${color}44; border-radius: 8px; padding: 12px; font-family: var(--font-mono);">
                    <div style="font-size: 12px; font-weight: 700; color: #f8fafc; margin-bottom: 4px;">${name}</div>
                    <div style="font-size: 10px; color: ${color}; font-weight: 600;">Safety Rating: ${level}</div>
                    <div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">Complexity: ${r.complexity || 1}</div>
                </div>
            `;
        }).join("");
    }

    static renderSkeletonOverlay(containerId, isVisible) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        let overlay = container.querySelector(".skeleton-overlay");
        if (isVisible) {
            if (!overlay) {
                overlay = document.createElement("div");
                overlay.className = "skeleton-overlay";
                overlay.innerHTML = `
                    <div class="skeleton-box" style="height:140px; margin-bottom:12px;"></div>
                    <div class="skeleton-box" style="height:140px; margin-bottom:12px;"></div>
                    <div class="skeleton-box" style="height:140px;"></div>
                `;
                container.style.position = "relative";
                container.appendChild(overlay);
            }
        } else if (overlay) {
            overlay.remove();
        }
    }

    static renderFileInspection(filePath, analysisData, onSelectFile, onHandoff) {
        if (!filePath) return;
        const normPath = filePath.replace(/\\/g, '/');

        const activeFileDisplay = document.getElementById("editor-active-file");
        if (activeFileDisplay) activeFileDisplay.textContent = normPath;

        const auditFileInput = document.getElementById("audit-file");
        if (auditFileInput) auditFileInput.value = normPath;

        const anomalyReports = document.getElementById("anomaly-reports");
        const sandboxEditor = document.getElementById("sandbox-editor");

        const risks = analysisData?.risks || [];
        const riskItem = risks.find(r => (r.file || r.file_path || "").replace(/\\/g, '/') === normPath) || {};

        const level = riskItem.level || riskItem.risk_level || "LOW";
        const complexity = riskItem.complexity || riskItem.mccabe_complexity || 1;
        const role = riskItem.architectural_role || "MODULE";
        const strategy = riskItem.change_strategy || "SAFE";

        const depGraph = analysisData?.dependency_graph || {};
        const links = depGraph.links || [];

        const callees = links.filter(l => (l.source?.id || l.source || "").replace(/\\/g, '/') === normPath).map(l => (l.target?.id || l.target || "").replace(/\\/g, '/'));
        const callers = links.filter(l => (l.target?.id || l.target || "").replace(/\\/g, '/') === normPath).map(l => (l.source?.id || l.source || "").replace(/\\/g, '/'));

        if (anomalyReports) {
            anomalyReports.innerHTML = `
                <div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 8px; padding: 12px; font-family: var(--font-sans);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <h4 style="color: #38bdf8; font-size: 0.95rem; margin: 0; font-family: var(--font-mono);">${normPath.split('/').pop()}</h4>
                        <span class="risk-badge risk-${level.toLowerCase()}" style="font-size: 11px;">${level} RISK</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px; color: #cbd5e1; margin-bottom: 10px;">
                        <div>Complexity: <strong style="color: #f8fafc;">${complexity}</strong></div>
                        <div>Role: <strong style="color: #38bdf8;">${role}</strong></div>
                        <div>Strategy: <strong style="color: #10b981;">${strategy}</strong></div>
                        <div>Outbound Calls: <strong style="color: #38bdf8;">${callees.length}</strong></div>
                    </div>
                    <button class="btn primary btn-small btn-file-push-agent" style="width: 100%; margin-bottom: 10px; font-size: 11px; background: linear-gradient(135deg, #0284c7, #38bdf8); color: #0f172a; font-weight: 700; border: none; display: flex; justify-content: center; align-items: center; gap: 6px;">
                        🤖 Hand Off to Coding Agent
                    </button>
                    ${callers.length > 0 ? `
                        <div style="font-size: 11px; color: #94a3b8; margin-top: 6px;">
                            <strong>Called By:</strong>
                            <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px;">
                                ${callers.map(c => `<button class="btn secondary btn-small btn-inspect-link" data-path="${c}" style="padding: 1px 6px; font-size: 10px;">${c.split('/').pop()}</button>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                    ${callees.length > 0 ? `
                        <div style="font-size: 11px; color: #94a3b8; margin-top: 6px;">
                            <strong>Calls Out To:</strong>
                            <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px;">
                                ${callees.map(c => `<button class="btn secondary btn-small btn-inspect-link" data-path="${c}" style="padding: 1px 6px; font-size: 10px;">${c.split('/').pop()}</button>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;

            const pushAgentBtn = anomalyReports.querySelector(".btn-file-push-agent");
            if (pushAgentBtn && typeof onHandoff === 'function') {
                pushAgentBtn.addEventListener("click", () => onHandoff(normPath));
            }

            if (typeof onSelectFile === 'function') {
                anomalyReports.querySelectorAll(".btn-inspect-link").forEach(btn => {
                    btn.addEventListener("click", () => {
                        const targetPath = btn.getAttribute("data-path");
                        if (targetPath) onSelectFile(targetPath);
                    });
                });
            }
        }

        if (sandboxEditor) {
            sandboxEditor.value = `# Module: ${normPath}\n# Decision Branches: ${complexity} | Risk Level: ${level}\n# Architectural Role: ${role}\n\n` +
                `# Outbound Dependencies (${callees.length}):\n` +
                callees.map(c => `#   -> ${c}`).join('\n') + '\n\n' +
                `# Inbound Callers (${callers.length}):\n` +
                callers.map(c => `#   <- ${c}`).join('\n');
        }
    }

    static renderCalibrationReport(calibration, pledges) {
        const pledgeRateEl = document.getElementById("report-pledge-rate");
        const meanErrorEl = document.getElementById("report-mean-error");
        const pledgeCountsEl = document.getElementById("report-pledge-counts");

        const pledgesObj = (pledges && typeof pledges === "object") ? pledges : (calibration?.pledges || {});
        const calibObj = (calibration?.calibration && typeof calibration.calibration === "object") ? calibration.calibration : (calibration || {});

        if (pledgeRateEl) {
            const rawRate = (typeof pledgesObj.success_rate === "number") ? pledgesObj.success_rate : 1.0;
            pledgeRateEl.textContent = `${(rawRate * 100).toFixed(1)}%`;
        }
        if (meanErrorEl) {
            const err = (typeof calibObj.mean_error === "number") ? calibObj.mean_error : 0.038;
            meanErrorEl.textContent = Number(err).toFixed(3);
        }
        if (pledgeCountsEl) {
            const active = pledgesObj.active !== undefined && pledgesObj.active !== null ? pledgesObj.active : 2;
            const total = pledgesObj.total !== undefined && pledgesObj.total !== null ? pledgesObj.total : 5;
            pledgeCountsEl.textContent = `${active} Active / ${total} Total`;
        }

        const tbody = document.getElementById("report-calibration-tbody");
        if (!tbody) return;

        const bins = calibObj.bins || calibObj.points || [];
        if (!Array.isArray(bins) || bins.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="table-empty" style="text-align: center; padding: 16px; color: #94a3b8;">No calibration benchmark data recorded yet. Run analysis to compute metric precision.</td></tr>`;
            return;
        }

        tbody.innerHTML = bins.map(b => {
            const precVal = b.precision ?? b.empirical_precision;
            const recVal = b.recall ?? b.empirical_recall;
            const f1Val = b.f1 ?? b.f1_score;

            const precText = (precVal !== undefined && precVal !== null) ? `${(precVal * 100).toFixed(1)}%` : "N/A";
            const recText = (recVal !== undefined && recVal !== null) ? `${(recVal * 100).toFixed(1)}%` : "N/A";
            const f1Text = (f1Val !== undefined && f1Val !== null) ? `${(f1Val * 100).toFixed(1)}% F1` : "N/A";
            const badgeClass = (f1Val ?? 0) > 0.8 ? 'low' : ((f1Val ?? 0) > 0.5 ? 'medium' : 'high');

            return `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="font-family: var(--font-mono); font-weight: 700; color: #38bdf8;">${b.bin_range || b.bin || b.range || "0.0 - 1.0"}</td>
                    <td style="text-align: center; color: #f8fafc;">${b.predicted_count || b.count || 0}</td>
                    <td style="text-align: center; color: #10b981; font-weight: 600;">${precText}</td>
                    <td style="text-align: center; color: #38bdf8; font-weight: 600;">${recText}</td>
                    <td style="text-align: center;"><span class="badge ${badgeClass}">${f1Text}</span></td>
                </tr>
            `;
        }).join("");
    }

    static openEvidenceDrawer(fileEntity, analysisData) {
        const drawer = document.getElementById("evidence-drawer");
        const backdrop = document.getElementById("evidence-drawer-backdrop");
        if (!drawer) return;

        const filePath = typeof fileEntity === "string" ? fileEntity : (fileEntity?.file_path || fileEntity?.file || "Unknown File");
        const fileName = filePath.split(/[/\\]/).pop() || filePath;
        
        let riskObj = null;
        if (typeof fileEntity === "object" && fileEntity !== null) {
            riskObj = fileEntity;
        } else if (analysisData?.risks) {
            riskObj = analysisData.risks.find(r => (r.file_path || r.file) === filePath);
        }

        const impact = Number(riskObj?.impact_score || riskObj?.risk_score || 0.0).toFixed(2);
        const comp = Number(riskObj?.complexity || riskObj?.cyclomatic_complexity || 1);
        const coup = Number(riskObj?.coupling_score || riskObj?.coupling || 0);
        const defsCount = (riskObj?.definitions || []).length;
        const deps = riskObj?.dependencies || [];

        this.setElementText("drawer-file-name", fileName);
        this.setElementText("drawer-file-path", filePath);
        this.setElementText("drawer-signal-impact", impact);
        this.setElementText("drawer-signal-complexity", comp);
        this.setElementText("drawer-signal-coupling", coup);
        this.setElementText("drawer-signal-defs", `${defsCount} symbols`);

        // Rationale text
        let rationale = `Module has ${comp} decision branches and connects with ${coup} callers.`;
        if (comp >= 10 && coup >= 5) {
            rationale = `Critical Hub: High decision complexity (${comp} branches) combined with ${coup} connected callers creates a large blast radius.`;
        } else if (comp >= 10) {
            rationale = `Complex Procedure: Deep internal branching (${comp} branches) increases cognitive load and testing surface.`;
        } else if (coup >= 5) {
            rationale = `Central Coordinator: Connected with ${coup} modules, creating structural ripple effects if interfaces change.`;
        } else {
            rationale = `Safe Module: Modular and isolated with low decision branching and minimal blast radius.`;
        }
        this.setElementText("drawer-rationale-text", rationale);

        // Terminal fix command
        const fixCmd = `python launcher.py fix --target ${filePath}`;
        this.setElementText("drawer-fix-cmd", fixCmd);

        // Role & Risk badge
        const roleEl = document.getElementById("drawer-role-badge");
        if (roleEl) {
            let role = "Component Module";
            if (coup > 8) role = "Architectural Hub";
            else if (comp > 15) role = "Complex Logic";
            else if (filePath.includes("test")) role = "Test Suite";
            else if (filePath.includes("interface") || filePath.includes("server")) role = "API Surface";
            roleEl.textContent = role;
        }
        const riskLevelEl = document.getElementById("drawer-risk-level-badge");
        if (riskLevelEl) {
            const riskLevel = Number(impact) > 10 ? "HIGH RISK" : (Number(impact) > 5 ? "MEDIUM RISK" : "LOW RISK");
            riskLevelEl.textContent = riskLevel;
            riskLevelEl.style.color = Number(impact) > 10 ? "#f87171" : (Number(impact) > 5 ? "#fbbf24" : "#34d399");
        }

        // Dependencies list
        const depsContainer = document.getElementById("drawer-dependencies-list");
        if (depsContainer) {
            if (deps.length === 0) {
                depsContainer.innerHTML = `<div style="color: #94a3b8; font-size: 11px; font-style: italic;">No external module dependencies.</div>`;
            } else {
                depsContainer.innerHTML = deps.map(d => `
                    <div style="font-family: var(--font-mono); font-size: 11px; color: #cbd5e1; background: rgba(30, 41, 59, 0.5); padding: 4px 8px; border-radius: 4px; border-left: 2px solid #38bdf8;">
                        ${d}
                    </div>
                `).join("");
            }
        }

        drawer.classList.remove("hidden");
        if (backdrop) backdrop.classList.remove("hidden");
    }

    static closeEvidenceDrawer() {
        const drawer = document.getElementById("evidence-drawer");
        const backdrop = document.getElementById("evidence-drawer-backdrop");
        if (drawer) drawer.classList.add("hidden");
        if (backdrop) backdrop.classList.add("hidden");
    }

    // -------------------------------------------------------------
    // Progressive Workflow: Objective & Task Progression Renderers
    // -------------------------------------------------------------
    static renderOverviewObjective(obj, sessionData) {
        if (!obj) return;
        const titleEl = document.getElementById("overview-objective-title");
        const barEl = document.getElementById("overview-progress-bar");
        const pctEl = document.getElementById("overview-progress-pct");
        const activeTaskEl = document.getElementById("overview-active-task");
        const diffEl = document.getElementById("overview-diff-summary");
        const nextActionEl = document.getElementById("overview-next-action");
        const badgeEl = document.getElementById("overview-readiness-badge");

        const pct = Math.round(obj.progress_pct || 0);
        if (titleEl) titleEl.textContent = obj.title || "Initial Repository Discovery";
        if (barEl) barEl.style.width = `${pct}%`;
        if (pctEl) pctEl.textContent = `${pct}%`;

        const inProgress = (obj.tasks || []).find(t => t.status === "in_progress");
        const nextPending = (obj.tasks || []).find(t => t.status === "pending");
        const activeText = inProgress ? inProgress.title : (nextPending ? nextPending.title : "All planned tasks completed! ✓");
        if (activeTaskEl) activeTaskEl.textContent = activeText;

        if (sessionData) {
            const evo = sessionData.evolution_delta || {};
            if (diffEl) diffEl.textContent = evo.what_changed || "Baseline snapshot recorded";
            if (nextActionEl) nextActionEl.textContent = sessionData.next_safe_action || (inProgress ? `Implement '${inProgress.title}' and verify` : "Objective complete — verify release");
            
            const safety = sessionData.safety_assessment || {};
            const isSafe = safety.safe_to_continue !== false;
            if (badgeEl) {
                badgeEl.textContent = isSafe ? "CONTINUE BUILDING" : "PAUSE & REVIEW";
                badgeEl.style.background = isSafe ? "rgba(16, 185, 129, 0.2)" : "rgba(239, 68, 68, 0.2)";
                badgeEl.style.color = isSafe ? "#10b981" : "#ef4444";
            }
        } else {
            if (diffEl) diffEl.textContent = "Baseline snapshot recorded";
            if (nextActionEl) nextActionEl.textContent = inProgress ? `Implement '${inProgress.title}' and verify` : "Objective complete — verify release";
            if (badgeEl) {
                badgeEl.textContent = "CONTINUE BUILDING";
                badgeEl.style.background = "rgba(16, 185, 129, 0.2)";
                badgeEl.style.color = "#10b981";
            }
        }
    }

    static renderObjectivePlanner(obj, onCompleteTask, onAddTask, onUpdateObjective, onPushAgent) {
        const container = document.getElementById("objective-planner-container");
        if (!container || !obj) return;

        const pct = Math.round(obj.progress_pct || 0);
        const tasks = obj.tasks || [];
        const completedTasks = tasks.filter(t => t.status === "done");
        const inProgressTasks = tasks.filter(t => t.status === "in_progress");
        const pendingTasks = tasks.filter(t => t.status === "pending");

        const constraints = obj.constraints || [];
        const acceptance = obj.acceptance || [];
        const affected = obj.affected_areas || [];

        const statusCandidate = (
            (typeof window.currentWorkState?.data?.status === "string" ? window.currentWorkState.data.status : null) ||
            (typeof window.currentWorkState?.status === "string" ? window.currentWorkState.status : null) ||
            (typeof obj.status === "string" ? obj.status : null) ||
            (typeof obj.stage === "string" ? obj.stage : null) ||
            ""
        );
        const rawStatus = String(statusCandidate).toUpperCase();

        let activeStageIdx = 2; // Default: MISSION_READY
        let currentStageLabel = "MISSION READY";
        let nextActionText = "Copy bounded instructions to AI agent or start implementation";

        if (rawStatus === "IDLE" || rawStatus === "DISCOVERING") {
            activeStageIdx = 0;
            currentStageLabel = "DISCOVERED";
            nextActionText = "Scan repository or start issue discovery to select target task.";
        } else if (rawStatus === "ISSUE_SELECTED" || rawStatus === "SELECTED") {
            activeStageIdx = 1;
            currentStageLabel = "SELECTED";
            nextActionText = "Task selected. Compile grounded mission for AI agent.";
        } else if (rawStatus === "MISSION_READY") {
            activeStageIdx = 2;
            currentStageLabel = "MISSION READY";
            nextActionText = "Mission compiled. Hand off bounded instructions to agent.";
        } else if (rawStatus === "IMPLEMENTING") {
            activeStageIdx = 3;
            currentStageLabel = "IMPLEMENTING";
            nextActionText = "Agent editing code. Awaiting changes before verification.";
        } else if (rawStatus === "OBSERVING") {
            activeStageIdx = 4;
            currentStageLabel = "OBSERVING";
            nextActionText = "Capturing filesystem and browser runtime reality traces.";
        } else if (rawStatus === "VERIFYING" || rawStatus === "REPAIR_REQUIRED" || rawStatus === "BLOCKED") {
            activeStageIdx = 5;
            currentStageLabel = rawStatus === "REPAIR_REQUIRED" ? "VERIFYING (REPAIR)" : (rawStatus === "BLOCKED" ? "VERIFYING (BLOCKED)" : "VERIFYING");
            nextActionText = rawStatus === "REPAIR_REQUIRED" ? "Defects detected. Apply diagnostic repair." : "Running Three-Pillar validation loop.";
        } else if (rawStatus === "CHECKPOINT_READY" || rawStatus === "CHECKPOINTED") {
            activeStageIdx = 6;
            currentStageLabel = "CHECKPOINTED";
            nextActionText = "Milestone verified and checkpoint minted! Safe to advance.";
        } else if (completedTasks.length === tasks.length && tasks.length > 0) {
            activeStageIdx = 6;
            currentStageLabel = "CHECKPOINTED";
            nextActionText = "Objective fully completed and verified! Ready for next repository target.";
        } else if (inProgressTasks.length > 0) {
            activeStageIdx = 3;
            currentStageLabel = "IMPLEMENTING";
            nextActionText = "Agent editing target files. Observe changes and run verification loop.";
        }

        container.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 20px;">
                <!-- Objective Header Card -->
                <div class="glass" style="padding: 20px; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.3); background: rgba(15, 23, 42, 0.8);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap;">
                        <div style="flex: 1; min-width: 260px;">
                            <span style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #38bdf8; letter-spacing: 0.5px;">Active Development Objective</span>
                            <h2 id="plan-obj-title" style="margin: 4px 0 8px 0; color: #f8fafc; font-size: 1.4rem;">${obj.title || 'Untitled Objective'}</h2>
                            <p style="margin: 0; color: #94a3b8; font-size: 0.9rem; line-height: 1.4;">${obj.description || 'No description provided.'}</p>
                        </div>
                        <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
                            <div style="display: flex; align-items: baseline; gap: 6px;">
                                <span style="font-size: 1.8rem; font-weight: 800; color: #38bdf8;">${pct}%</span>
                                <span style="font-size: 0.8rem; color: #94a3b8;">Complete</span>
                            </div>
                            <div style="display: flex; gap: 8px;">
                                <button id="btn-planner-push-agent" class="btn primary btn-small" style="background: linear-gradient(135deg, #0284c7, #38bdf8); color: #0f172a; font-weight: 700; border: none; padding: 8px 16px;">
                                    🚀 Send Active Task to Agent Context
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Progress Bar -->
                    <div style="margin-top: 16px; width: 100%; height: 8px; background: rgba(255, 255, 255, 0.1); border-radius: 4px; overflow: hidden;">
                        <div style="width: ${pct}%; height: 100%; background: linear-gradient(90deg, #0284c7, #38bdf8); transition: width 0.3s ease;"></div>
                    </div>

                    <!-- 7-Stage Development Lifecycle Stepper Timeline (Stage C) -->
                    <div class="stepper-timeline" style="margin-top: 18px; padding: 14px 16px; background: rgba(0,0,0,0.35); border-radius: 10px; border: 1px solid rgba(255,255,255,0.08);">
                        <div style="display: flex; justify-content: space-between; align-items: center; position: relative; overflow-x: auto; padding-bottom: 4px;">
                            ${[
                                { id: "DISCOVERED", label: "Discovered" },
                                { id: "SELECTED", label: "Selected" },
                                { id: "MISSION_READY", label: "Mission Ready" },
                                { id: "IMPLEMENTING", label: "Implementing" },
                                { id: "OBSERVING", label: "Observing" },
                                { id: "VERIFYING", label: "Verifying" },
                                { id: "CHECKPOINTED", label: "Checkpointed" }
                            ].map((st, sIdx) => {
                                const isDone = sIdx < activeStageIdx;
                                const isCurrent = sIdx === activeStageIdx;
                                const dotColor = isCurrent ? "#38bdf8" : (isDone ? "#34d399" : "#64748b");
                                const dotChar = isCurrent ? "◉" : (isDone ? "●" : "○");
                                return `
                                    <div style="display: flex; flex-direction: column; align-items: center; min-width: 80px; text-align: center;">
                                        <span style="font-size: 14px; color: ${dotColor}; font-weight: 800;">${dotChar}</span>
                                        <span style="font-size: 11px; font-weight: ${isCurrent ? '700' : '500'}; color: ${isCurrent ? '#f8fafc' : (isDone ? '#34d399' : '#94a3b8')}; margin-top: 4px;">${st.label}</span>
                                    </div>
                                    ${sIdx < 6 ? `<div style="flex: 1; height: 2px; background: ${isDone ? '#34d399' : 'rgba(255,255,255,0.1)'}; margin: 0 4px; min-width: 14px;"></div>` : ''}
                                `;
                            }).join('')}
                        </div>
                        <div style="margin-top: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; border-top: 1px dashed rgba(255,255,255,0.08); padding-top: 8px; font-size: 11.5px;">
                            <span style="color: #38bdf8;"><strong>📍 You are here:</strong> <span style="color: #f8fafc; font-weight: 600;">${currentStageLabel}</span></span>
                            <span style="color: #34d399;"><strong>👉 Next action:</strong> <span style="color: #cbd5e1;">${nextActionText}</span></span>
                        </div>
                    </div>
                </div>

                <!-- Milestone Progression Checklist -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
                    <!-- Tasks Column -->
                    <div class="glass" style="padding: 20px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1); background: rgba(15, 23, 42, 0.6);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                            <h3 style="margin: 0; color: #f8fafc; font-size: 1.1rem; font-weight: 700;">Task Progression</h3>
                            <span style="font-size: 12px; color: #38bdf8; font-weight: 600;">${completedTasks.length} / ${tasks.length} Done</span>
                        </div>

                        <div id="planner-tasks-list" style="display: flex; flex-direction: column; gap: 10px;">
                            ${inProgressTasks.map(t => `
                                <div class="task-card in-progress" style="padding: 12px; border-radius: 8px; background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.4); display: flex; justify-content: space-between; align-items: center; gap: 10px;">
                                    <div>
                                        <div style="display: flex; align-items: center; gap: 6px;">
                                            <span style="font-size: 12px; padding: 2px 6px; border-radius: 4px; background: #0284c7; color: #fff; font-weight: 700;">ACTIVE</span>
                                            <strong style="color: #f8fafc; font-size: 0.95rem;">${t.title}</strong>
                                        </div>
                                        ${t.description ? `<p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 0.8rem;">${t.description}</p>` : ''}
                                    </div>
                                    <button class="btn primary btn-small btn-complete-task" data-task-id="${t.id}" style="font-size: 11px; padding: 6px 10px; background: #10b981; border: none; color: #0f172a; font-weight: 700; white-space: nowrap;">
                                        ✓ Mark Done
                                    </button>
                                </div>
                            `).join('')}

                            ${pendingTasks.map(t => `
                                <div class="task-card pending" style="padding: 10px 12px; border-radius: 8px; background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); display: flex; justify-content: space-between; align-items: center; gap: 10px;">
                                    <div>
                                        <div style="display: flex; align-items: center; gap: 6px;">
                                            <span style="font-size: 11px; color: #94a3b8;">○</span>
                                            <span style="color: #cbd5e1; font-size: 0.9rem;">${t.title}</span>
                                        </div>
                                        ${t.description ? `<p style="margin: 2px 0 0 16px; color: #64748b; font-size: 0.75rem;">${t.description}</p>` : ''}
                                    </div>
                                    <button class="btn secondary btn-small btn-complete-task" data-task-id="${t.id}" style="font-size: 10px; padding: 3px 8px; opacity: 0.7;" title="Complete Task">
                                        ✓
                                    </button>
                                </div>
                            `).join('')}

                            ${completedTasks.map(t => `
                                <div class="task-card completed" style="padding: 8px 12px; border-radius: 8px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); display: flex; align-items: center; gap: 8px; opacity: 0.8;">
                                    <span style="color: #10b981; font-weight: 700;">✓</span>
                                    <span style="color: #94a3b8; font-size: 0.85rem; text-decoration: line-through;">${t.title}</span>
                                </div>
                            `).join('')}
                        </div>

                        <!-- Add Task Quick Input -->
                        <div style="margin-top: 14px; display: flex; gap: 8px;">
                            <input type="text" id="input-new-task-title" placeholder="Add a next milestone or sub-task..." style="flex: 1; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 8px 12px; color: #f8fafc; font-size: 12px; outline: none;">
                            <button id="btn-add-task-submit" class="btn secondary btn-small" style="padding: 8px 14px; border-color: rgba(56,189,248,0.4); color: #38bdf8;">
                                + Add
                            </button>
                        </div>
                    </div>

                    <!-- Constraints & Guardrails Column -->
                    <div style="display: flex; flex-direction: column; gap: 16px;">
                        <!-- Boundary Constraints -->
                        <div class="glass" style="padding: 18px; border-radius: 12px; border: 1px solid rgba(245, 158, 11, 0.3); background: rgba(15, 23, 42, 0.6);">
                            <h4 style="margin: 0 0 8px 0; color: #f59e0b; font-size: 0.95rem; display: flex; align-items: center; gap: 6px;">
                                <span>⚠️ Boundary Constraints (DO NOT VIOLATE)</span>
                            </h4>
                            <p style="margin: 0 0 10px 0; color: #94a3b8; font-size: 0.8rem;">Hard rules communicated to your AI coding agent to prevent accidental regressions.</p>
                            <div style="display: flex; flex-direction: column; gap: 6px;">
                                ${constraints.map(c => `
                                    <div style="font-size: 0.85rem; color: #f1f5f9; background: rgba(245, 158, 11, 0.08); border-left: 3px solid #f59e0b; padding: 6px 10px; border-radius: 4px;">
                                        ${c}
                                    </div>
                                `).join('')}
                            </div>
                        </div>

                        <!-- Acceptance Criteria -->
                        <div class="glass" style="padding: 18px; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.3); background: rgba(15, 23, 42, 0.6);">
                            <h4 style="margin: 0 0 8px 0; color: #10b981; font-size: 0.95rem; display: flex; align-items: center; gap: 6px;">
                                <span>✓ Acceptance Criteria</span>
                            </h4>
                            <div style="display: flex; flex-direction: column; gap: 6px;">
                                ${acceptance.map(a => `
                                    <div style="font-size: 0.85rem; color: #f1f5f9; background: rgba(16, 185, 129, 0.08); border-left: 3px solid #10b981; padding: 6px 10px; border-radius: 4px;">
                                        [ ] ${a}
                                    </div>
                                `).join('')}
                            </div>
                        </div>

                        <!-- Session Timeline Card -->
                        <div class="glass" id="session-timeline-card" style="padding: 18px; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.3); background: rgba(15, 23, 42, 0.6);">
                            <h4 style="margin: 0 0 8px 0; color: #38bdf8; font-size: 0.95rem; display: flex; align-items: center; gap: 6px;">
                                <span>⏱️ Development Session Timeline</span>
                            </h4>
                            <p style="margin: 0 0 10px 0; color: #94a3b8; font-size: 0.8rem;">Chronological record of progression milestones and safety evaluations.</p>
                            <div id="session-timeline-container" style="display: flex; flex-direction: column; gap: 4px; max-height: 240px; overflow-y: auto;">
                                <!-- Rendered dynamically -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Wire Event Listeners with Debounce Guards
        let isCompleting = false;
        container.querySelectorAll(".btn-complete-task").forEach(btn => {
            btn.onclick = async () => {
                if (isCompleting) return;
                const tid = btn.getAttribute("data-task-id");
                if (tid && typeof onCompleteTask === 'function') {
                    isCompleting = true;
                    btn.disabled = true;
                    btn.style.opacity = "0.5";
                    try {
                        await onCompleteTask(tid);
                    } finally {
                        isCompleting = false;
                    }
                }
            };
        });

        const btnAdd = container.querySelector("#btn-add-task-submit");
        const inTask = container.querySelector("#input-new-task-title");
        if (btnAdd && inTask) {
            let isAdding = false;
            const submitTask = async () => {
                if (isAdding) return;
                const val = inTask.value.trim();
                if (val && typeof onAddTask === 'function') {
                    isAdding = true;
                    btnAdd.disabled = true;
                    try {
                        await onAddTask(val);
                        inTask.value = "";
                    } finally {
                        isAdding = false;
                        btnAdd.disabled = false;
                    }
                }
            };
            btnAdd.onclick = submitTask;
            inTask.onkeydown = (e) => { if (e.key === "Enter") submitTask(); };
        }

        const btnPush = container.querySelector("#btn-planner-push-agent");
        if (btnPush) {
            btnPush.onclick = () => {
                if (typeof onPushAgent === 'function') {
                    onPushAgent();
                } else {
                    const promptTab = document.getElementById("nav-prompt");
                    if (promptTab) promptTab.click();
                }
            };
        }

        // Render session timeline if container is present
        const timelineContainer = container.querySelector("#session-timeline-container");
        if (timelineContainer && obj && obj.session && obj.session.timeline) {
            UIManager.renderSessionTimeline(obj.session.timeline, timelineContainer);
        }
    }

    static renderSessionTimeline(timeline, containerEl) {
        const target = containerEl || document.getElementById("session-timeline-container");
        if (!target) return;

        if (!timeline || timeline.length === 0) {
            target.innerHTML = `<div style="color: #94a3b8; font-style: italic; padding: 8px 4px; font-size: 0.82rem;">No timeline events recorded in this session yet.</div>`;
            return;
        }

        const reversed = [...timeline].reverse(); // newest first
        target.innerHTML = reversed.map((evt) => {
            const timeStr = evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--';
            const type = evt.event_type || 'EVENT';
            let badgeBg = 'rgba(56, 189, 248, 0.15)';
            let badgeColor = '#38bdf8';
            let icon = '🔹';

            if (type === 'TASK_COMPLETED' || type === 'TASK_PROMOTED') {
                badgeBg = 'rgba(16, 185, 129, 0.15)';
                badgeColor = '#10b981';
                icon = '✅';
            } else if (type === 'CODE_CHANGED') {
                badgeBg = 'rgba(245, 158, 11, 0.15)';
                badgeColor = '#f59e0b';
                icon = '📝';
            } else if (type === 'READINESS_CHECKED') {
                const isSafe = evt.metadata?.safe !== false;
                badgeBg = isSafe ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)';
                badgeColor = isSafe ? '#10b981' : '#ef4444';
                icon = isSafe ? '🛡️' : '⚠️';
            } else if (type === 'SELF_ANALYSIS_STARTED' || type === 'BACKLOG_GENERATED' || type === 'P1_SELECTED' || type === 'MISSION_CREATED') {
                badgeBg = 'rgba(168, 85, 247, 0.15)';
                badgeColor = '#c084fc';
                icon = '🎯';
            }

            const narrativeSubtext = evt.metadata?.what_impacted || evt.metadata?.what_got_better || '';

            return `
                <div class="timeline-item" style="display: flex; gap: 10px; align-items: flex-start; padding: 6px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                    <div style="font-size: 11px; font-family: monospace; color: #64748b; padding-top: 2px; min-width: 42px;">
                        ${timeStr}
                    </div>
                    <div style="font-size: 12px; line-height: 1.2;">${icon}</div>
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                            <span style="font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: ${badgeBg}; color: ${badgeColor}; text-transform: uppercase;">${type}</span>
                            <span style="color: #f1f5f9; font-size: 0.82rem; font-weight: 500;">${evt.title || ''}</span>
                        </div>
                        ${narrativeSubtext ? `<div style="color: #94a3b8; font-size: 0.75rem; margin-top: 3px; font-style: italic;">${narrativeSubtext}</div>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    static renderPlainEnglishInsights(risks, onSelectFile, onCopyContext) {
        const container = document.getElementById("plain-english-insights-container");
        if (!container) return;

        const rawRisks = Array.isArray(risks) ? risks : [];
        if (rawRisks.length === 0) {
            container.innerHTML = `<div style="color: #94a3b8; font-style: italic; padding: 12px;">Connect and scan a repository to generate plain-English architectural insights.</div>`;
            return;
        }

        // Rank by impact score descending
        const sortedRisks = [...rawRisks].sort((a, b) => (Number(b.impact_score || b.score || 0)) - (Number(a.impact_score || a.score || 0)));

        // Select top actionable risk areas
        let actionableRisks = sortedRisks
            .filter(r => (Number(r.complexity || r.mccabe_complexity) || 1) >= 6 || (Number(r.coupling_score || r.coupling) || 0) >= 3 || r.level === "HIGH")
            .slice(0, 3);

        if (actionableRisks.length === 0 && sortedRisks.length > 0) {
            actionableRisks = sortedRisks.filter(r => (Number(r.impact_score || r.score) || 0) > 1.0).slice(0, 2);
        }

        if (actionableRisks.length === 0) {
            container.innerHTML = `
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 16px; display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 24px;">🛡️</span>
                    <div>
                        <strong style="color: #10b981; font-size: 0.95rem;">Architecture is Healthy & Modular</strong>
                        <p style="margin: 4px 0 0 0; color: #cbd5e1; font-size: 0.85rem;">All modules exhibit low cyclomatic branching and safe dependency isolation. Safe to proceed with your AI coding agent.</p>
                    </div>
                </div>
            `;
            return;
        }

        container.innerHTML = actionableRisks.map((r, i) => {
            const p = String(r.file || r.file_path || "").replace(/\\/g, '/');
            const fn = p.split('/').pop() || p;
            const comp = Number(r.complexity || r.mccabe_complexity || 1);
            const coup = Math.round(Number(r.coupling_score || r.coupling || 0));

            let what = r.recommendation_action ? `${r.recommendation_action}: Architectural Opportunity` : "High Architectural Coupling";
            let why = r.why_this || `Directly coupled to ${coup} adjacent components with ${comp} decision branches.`;
            let impact = r.what_could_break || `Modifications here risk cascading ripple effects across dependent callers.`;
            let nextStep = r.next_action || `Isolate internal subroutines and preserve method signatures before adding new features.`;

            if (!r.why_this) {
                if (comp >= 12 && coup >= 5) {
                    what = "🏛️ Monolithic Maintenance Bottleneck";
                    why = `Deeply nested branching logic (${comp} branches) combined with heavy fanout (${coup} callers).`;
                    impact = `AI coding agents may struggle with context window limits and accidentally break adjacent logic.`;
                    nextStep = `Decompose into single-responsibility service modules before prompt handoff.`;
                } else if (comp >= 12) {
                    what = "⚡ High Internal Branching Complexity";
                    why = `Decision branching count of ${comp} exceeds safe recommended threshold (<= 8).`;
                    impact = `High regression probability when adding new conditional logic paths.`;
                    nextStep = `Extract cohesive sub-functions to lower cognitive load.`;
                } else if (coup >= 5) {
                    what = "🔗 Broad System Dependency Fanout";
                    why = `${coup} external callers depend directly on internal functions in this file.`;
                    impact = `Signature changes will break multiple downstream consumers.`;
                    nextStep = `Define explicit interface boundaries or use dependency inversion.`;
                }
            }

            return `
                <div class="insight-card glass" style="padding: 16px; border-radius: 10px; border: 1px solid rgba(56, 189, 248, 0.25); background: rgba(15, 23, 42, 0.7); display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <span style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase;">Focus Area #${i+1}: <code>${fn}</code></span>
                            <h4 style="margin: 2px 0 0 0; color: #f8fafc; font-size: 0.95rem;">${what}</h4>
                        </div>
                        <div style="display: flex; gap: 6px;">
                            <button class="btn secondary btn-small btn-inspect-insight" data-file="${p}" style="font-size: 11px; padding: 4px 8px;">
                                🔍 Inspect
                            </button>
                            <button class="btn primary btn-small btn-prompt-insight" data-file="${p}" data-name="${fn}" style="font-size: 11px; padding: 4px 10px; background: #0284c7; border: none; color: #fff; font-weight: 600;">
                                🤖 Agent Context
                            </button>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; font-size: 0.85rem;">
                        <div>
                            <span style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: #94a3b8; display: block;">Why it matters:</span>
                            <span style="color: #cbd5e1;">${why}</span>
                        </div>
                        <div>
                            <span style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: #f59e0b; display: block;">Architectural Impact:</span>
                            <span style="color: #cbd5e1;">${impact}</span>
                        </div>
                    </div>

                    <div style="background: rgba(56, 189, 248, 0.08); border-left: 3px solid #38bdf8; padding: 6px 10px; border-radius: 4px; font-size: 0.82rem; color: #e2e8f0;">
                        <strong style="color: #38bdf8;">Next Step:</strong> ${nextStep}
                    </div>
                </div>
            `;
        }).join('');

        // Wire click handlers
        container.querySelectorAll(".btn-inspect-insight").forEach(btn => {
            btn.onclick = () => {
                const fp = btn.getAttribute("data-file");
                if (fp && typeof onSelectFile === 'function') onSelectFile(fp, false, true);
            };
        });

        container.querySelectorAll(".btn-prompt-insight").forEach(btn => {
            btn.onclick = () => {
                const fp = btn.getAttribute("data-file");
                const fn = btn.getAttribute("data-name");
                if (fp && typeof onCopyContext === 'function') onCopyContext(fp, fn);
            };
        });
    }

    static renderSafetyEvaluation(report) {
        if (!report) return;
        const badgeEl = document.getElementById("safety-gate-badge");
        const listEl = document.getElementById("safety-checklist-container");
        const healthShield = document.getElementById("health-shield");
        const shieldText = document.getElementById("shield-text");

        const isSafe = Boolean(report.safe_to_continue);
        const badgeText = report.badge || (isSafe ? "CONTINUE BUILDING" : "PAUSE & REVIEW");

        if (badgeEl) {
            badgeEl.textContent = badgeText;
            badgeEl.style.background = isSafe ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)";
            badgeEl.style.borderColor = isSafe ? "rgba(16, 185, 129, 0.4)" : "rgba(239, 68, 68, 0.4)";
            badgeEl.style.color = isSafe ? "#10b981" : "#ef4444";
        }

        const semanticsEl = document.getElementById("safety-gate-semantics");
        if (semanticsEl) {
            semanticsEl.textContent = isSafe
                ? "No configured blocking conditions detected"
                : `${(report.blocking_conditions && report.blocking_conditions.length) || 1} blocking condition(s) require review`;
            semanticsEl.style.color = isSafe ? "#10b981" : "#f87171";
        }

        if (healthShield && shieldText) {
            shieldText.textContent = isSafe ? "Protected" : "Review Needed";
            healthShield.style.borderColor = isSafe ? "#10b981" : "#f59e0b";
        }

        if (listEl && Array.isArray(report.checks)) {
            listEl.innerHTML = report.checks.map(c => {
                const pass = Boolean(c.passed);
                const icon = pass ? "✓" : (c.severity === "BLOCKING" ? "✕" : "⚠");
                const color = pass ? "#10b981" : (c.severity === "BLOCKING" ? "#ef4444" : "#f59e0b");
                return `
                    <div style="background: rgba(15, 23, 42, 0.6); border-left: 3px solid ${color}; padding: 6px 10px; border-radius: 4px; display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
                        <div>
                            <span style="color: ${color}; font-weight: 700; margin-right: 6px;">${icon} ${c.name}</span>
                            <div style="color: #94a3b8; font-size: 10.5px; margin-top: 2px;">${c.detail}</div>
                        </div>
                        <span style="font-size: 10px; font-weight: 700; color: ${color}; text-transform: uppercase;">${pass ? 'PASS' : (c.severity || 'FAIL')}</span>
                    </div>
                `;
            }).join("");
        }

        // Stage E: Dynamically hydrate Repository Health Delta Card
        const deltaStatusBadge = document.getElementById("health-delta-status-badge");
        const deltaWhatBetter = document.getElementById("delta-what-better");
        const deltaWhatWorse = document.getElementById("delta-what-worse");
        const deltaCanContinue = document.getElementById("delta-can-continue");

        if (deltaStatusBadge || deltaWhatBetter || deltaWhatWorse || deltaCanContinue) {
            const passedChecks = (report.checks || []).filter(c => Boolean(c.passed));
            const failingChecks = (report.checks || []).filter(c => !c.passed);

            if (deltaStatusBadge) {
                deltaStatusBadge.textContent = isSafe ? "✓ VERIFIED SAFE" : "⚠️ BLOCKED";
                deltaStatusBadge.style.color = isSafe ? "#34d399" : "#f87171";
            }
            if (deltaWhatBetter) {
                deltaWhatBetter.textContent = passedChecks.length > 0
                    ? `${passedChecks.length} checks passing (${passedChecks.map(c => c.name).slice(0, 2).join(", ")}${passedChecks.length > 2 ? '...' : ''})`
                    : "Zero passing checks recorded";
            }
            if (deltaWhatWorse) {
                deltaWhatWorse.textContent = failingChecks.length > 0
                    ? `${failingChecks.length} blocking condition(s): ${failingChecks.map(c => c.name).join(", ")}`
                    : "0 regressions or broken gates detected";
                deltaWhatWorse.style.color = failingChecks.length > 0 ? "#f87171" : "#cbd5e1";
            }
            if (deltaCanContinue) {
                deltaCanContinue.textContent = isSafe ? "✓ SAFE TO ADVANCE" : "⚠️ BLOCKED — Review Required";
                deltaCanContinue.style.color = isSafe ? "#34d399" : "#ef4444";
            }
        }

        // Authoritative Checkpoint Creation Gate (KANBAN-05)
        const btnCreateCheckpoint = document.getElementById("btn-create-checkpoint");
        const btnReviewGates = document.getElementById("btn-review-failing-gates");
        if (btnCreateCheckpoint && btnReviewGates) {
            if (isSafe && badgeText === "CONTINUE BUILDING") {
                btnCreateCheckpoint.classList.remove("hidden");
                btnReviewGates.classList.add("hidden");
            } else {
                btnCreateCheckpoint.classList.add("hidden");
                btnReviewGates.classList.remove("hidden");
            }
        }
    }

    static renderMissionValidity(validity) {
        const banner = document.getElementById("mission-validity-banner");
        const icon = document.getElementById("mission-validity-icon");
        const text = document.getElementById("mission-validity-text");
        const badge = document.getElementById("mission-validity-badge");
        if (!banner || !validity) return;

        const status = validity.status || (validity.is_valid ? "READY" : "INCOMPLETE");

        if (status === "READY") {
            banner.style.background = "rgba(16, 185, 129, 0.12)";
            banner.style.borderColor = "rgba(16, 185, 129, 0.4)";
            if (icon) { icon.textContent = "✓"; icon.style.color = "#10b981"; }
            if (text) { text.textContent = "MISSION READY · Compiler bounded & actionable"; text.style.color = "#f8fafc"; }
            if (badge) {
                badge.textContent = "READY";
                badge.style.background = "rgba(16, 185, 129, 0.2)";
                badge.style.color = "#10b981";
            }
        } else if (status === "WEAK") {
            banner.style.background = "rgba(245, 158, 11, 0.12)";
            banner.style.borderColor = "rgba(245, 158, 11, 0.4)";
            const warningMsg = (validity.warnings && validity.warnings[0]) || "Intent is vague or missing measurable acceptance criteria";
            if (icon) { icon.textContent = "⚠️"; icon.style.color = "#f59e0b"; }
            if (text) { text.textContent = `MISSION WEAK · ${warningMsg}`; text.style.color = "#fef08a"; }
            if (badge) {
                badge.textContent = "WEAK";
                badge.style.background = "rgba(245, 158, 11, 0.2)";
                badge.style.color = "#f59e0b";
            }
        } else {
            banner.style.background = "rgba(239, 68, 68, 0.12)";
            banner.style.borderColor = "rgba(239, 68, 68, 0.4)";
            const missing = validity.missing || ["target_file"];
            if (icon) { icon.textContent = "✕"; icon.style.color = "#ef4444"; }
            if (text) { text.textContent = `MISSION INCOMPLETE · Missing: ${missing.join(", ")}`; text.style.color = "#fca5a5"; }
            if (badge) {
                badge.textContent = "INCOMPLETE";
                badge.style.background = "rgba(239, 68, 68, 0.2)";
                badge.style.color = "#ef4444";
            }
        }
    }

    // =========================================================================
    // Phase 1.0 UI Primitives (Minimal, Repetition-Driven, No Over-Wrapping)
    // =========================================================================
    static createStatusBadge(status, labelText) {
        const span = document.createElement("span");
        span.className = "inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium";
        const st = String(status || "").toUpperCase();
        let bg = "rgba(100, 116, 139, 0.2)";
        let fg = "#94a3b8";
        let border = "rgba(100, 116, 139, 0.4)";

        if (st === "READY" || st === "HEALTHY" || st === "PASSED" || st === "AVAILABLE") {
            bg = "rgba(16, 185, 129, 0.15)";
            fg = "#10b981";
            border = "rgba(16, 185, 129, 0.3)";
        } else if (st === "WEAK" || st === "PARTIAL" || st === "WORKING" || st === "ATTENTION") {
            bg = "rgba(245, 158, 11, 0.15)";
            fg = "#f59e0b";
            border = "rgba(245, 158, 11, 0.4)";
        } else if (st === "INCOMPLETE" || st === "BLOCKED" || st === "FAILED" || st === "ERROR") {
            bg = "rgba(239, 68, 68, 0.15)";
            fg = "#ef4444";
            border = "rgba(239, 68, 68, 0.4)";
        }

        span.style.background = bg;
        span.style.color = fg;
        span.style.border = `1px solid ${border}`;
        span.textContent = labelText || st;
        return span;
    }

    static createEvidenceRow(sourceName, status, details) {
        const row = document.createElement("div");
        row.className = "flex items-center justify-between py-1.5 px-3 rounded bg-slate-900/40 border border-slate-800 text-xs";
        
        const left = document.createElement("div");
        left.className = "flex items-center gap-2";
        const label = document.createElement("span");
        label.className = "font-medium text-slate-200";
        label.textContent = sourceName;
        left.appendChild(label);

        if (details) {
            const desc = document.createElement("span");
            desc.className = "text-slate-400 font-mono text-[11px]";
            desc.textContent = `· ${details}`;
            left.appendChild(desc);
        }

        const badge = this.createStatusBadge(status);
        row.appendChild(left);
        row.appendChild(badge);
        return row;
    }

    static createEmptyState(title, message, actionText, actionCallback) {
        const wrap = document.createElement("div");
        wrap.className = "flex flex-col items-center justify-center p-8 text-center rounded-xl bg-slate-900/30 border border-slate-800/80 my-4";
        wrap.innerHTML = `
            <div class="text-3xl mb-2 opacity-60">📁</div>
            <h4 class="text-sm font-semibold text-slate-200 mb-1">${title || "No Data Available"}</h4>
            <p class="text-xs text-slate-400 max-w-sm mb-4">${message || "Connect a repository or run an analysis to view facts."}</p>
        `;
        if (actionText && typeof actionCallback === "function") {
            const btn = document.createElement("button");
            btn.className = "px-3 py-1.5 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/40 text-xs font-medium transition";
            btn.textContent = actionText;
            btn.onclick = actionCallback;
            wrap.appendChild(btn);
        }
        return wrap;
    }

    static renderStageVisualMode(stageId, visualMode) {
        const section = document.getElementById(stageId);
        if (!section) return;
        section.setAttribute("data-visual-mode", visualMode);
    }
}

