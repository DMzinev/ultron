/**
 * Ultron Web SPA — Modals & Dialog Manager
 * Campaign 7 & 10: Onboarding Tour, Folder Picker & Keyboard ESC Handlers
 */

export class ModalManager {
    static init() {
        // Keyboard ESC Listener to close all open modals or drawer
        window.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                this.closeAll();
            }
        });

        // Close Tour Modal Button
        const btnCloseTour = document.getElementById("btn-close-tour");
        if (btnCloseTour) {
            btnCloseTour.onclick = () => this.closeModal("tour-modal");
        }

        // Tour Slide Navigation
        const btnPrev = document.getElementById("tour-btn-prev");
        const btnNext = document.getElementById("tour-btn-next");
        if (btnPrev && btnNext) {
            let currentSlide = 0;
            const slides = document.querySelectorAll(".tour-slide");
            const updateSlides = (idx) => {
                slides.forEach((s, i) => s.classList.toggle("active", i === idx));
                btnPrev.disabled = idx === 0;
                btnNext.textContent = idx === slides.length - 1 ? "Finish Tour" : "Next";
            };

            btnPrev.onclick = () => {
                if (currentSlide > 0) {
                    currentSlide--;
                    updateSlides(currentSlide);
                }
            };
            btnNext.onclick = () => {
                if (currentSlide < slides.length - 1) {
                    currentSlide++;
                    updateSlides(currentSlide);
                } else {
                    this.closeModal("tour-modal");
                }
            };
        }
        // Close Shortcuts Modal Button & Backdrop Click
        const btnShortcuts = document.getElementById("btn-shortcuts-help");
        if (btnShortcuts) {
            btnShortcuts.onclick = () => toggleShortcutsModal();
        }
        const btnCloseShortcuts = document.getElementById("close-shortcuts-btn");
        if (btnCloseShortcuts) {
            btnCloseShortcuts.onclick = () => closeShortcutsModal();
        }
        const shortcutsModal = document.getElementById("shortcuts-modal");
        if (shortcutsModal) {
            shortcutsModal.addEventListener("click", (e) => {
                if (e.target === shortcutsModal) closeShortcutsModal();
            });
        }
    }

    static openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove("hidden");
            modal.hidden = false;
        }
    }

    static closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add("hidden");
            modal.hidden = true;
        }
    }

    static closeAll() {
        document.querySelectorAll(".modal-backdrop, .drawer-sidebar, .modal-overlay, .evidence-drawer, .drawer-backdrop").forEach(el => {
            el.classList.add("hidden");
            el.hidden = true;
        });
    }
}

export function toggleShortcutsModal() {
    const modal = document.getElementById("shortcuts-modal");
    if (!modal) return;
    if (modal.hidden) {
        modal.hidden = false;
        modal.classList.remove("hidden");
    } else {
        modal.hidden = true;
        modal.classList.add("hidden");
    }
}

export function closeShortcutsModal() {
    const modal = document.getElementById("shortcuts-modal");
    if (modal) {
        modal.hidden = true;
        modal.classList.add("hidden");
    }
}
