/**
 * Ultron Web SPA — UI Component Manager & Error Boundaries
 * Campaign 7 & 9: Component State Audit & Null-Safe DOM Helpers
 */

export class UIManager {
    static showToast(message, isError = false) {
        const toast = document.getElementById("toast");
        if (!toast) return;
        toast.textContent = message;
        toast.style.background = isError ? "rgba(244, 63, 94, 0.9)" : "rgba(15, 23, 42, 0.9)";
        toast.style.borderColor = isError ? "#f43f5e" : "#38bdf8";
        toast.classList.remove("hidden");
        setTimeout(() => toast.classList.add("hidden"), 4000);
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
        const loaderText = document.getElementById("loader-step-text");
        const loaderBar = document.getElementById("loader-progress-bar");
        if (loaderText) {
            loaderText.textContent = `[${stepIndex}/${totalSteps}] ${stepName}`;
        }
        if (loaderBar) {
            const pct = Math.min(100, Math.max(0, (stepIndex / totalSteps) * 100));
            loaderBar.style.width = `${pct}%`;
        }
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
}
