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
        const btnPrev = document.getElementById("btn-prev-slide") || document.getElementById("tour-btn-prev");
        const btnNext = document.getElementById("btn-next-slide") || document.getElementById("tour-btn-next");
        const slides = document.querySelectorAll(".tour-slide");
        const dots = document.querySelectorAll(".tour-dot");

        if (slides.length > 0) {
            let currentSlide = 0;
            const updateSlides = (idx) => {
                currentSlide = idx;
                slides.forEach((s, i) => s.classList.toggle("active", i === idx));
                dots.forEach((d, i) => {
                    d.classList.toggle("active", i === idx);
                    d.style.background = i === idx ? "var(--neon-cyan, #38bdf8)" : "rgba(255,255,255,0.2)";
                });
                if (btnPrev) {
                    btnPrev.disabled = idx === 0;
                    btnPrev.classList.toggle("disabled", idx === 0);
                }
                if (btnNext) {
                    btnNext.textContent = idx === slides.length - 1 ? "Finish Tour" : "Next";
                }
            };

            if (btnPrev) {
                btnPrev.onclick = () => {
                    if (currentSlide > 0) {
                        updateSlides(currentSlide - 1);
                    }
                };
            }

            if (btnNext) {
                btnNext.onclick = () => {
                    if (currentSlide < slides.length - 1) {
                        updateSlides(currentSlide + 1);
                    } else {
                        this.closeModal("tour-modal");
                    }
                };
            }

            dots.forEach((dot, i) => {
                dot.onclick = () => updateSlides(i);
            });
        }
    }

    static openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove("hidden");
        }
    }

    static closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add("hidden");
        }
    }

    static closeAll() {
        document.querySelectorAll(".modal-backdrop, .modal-overlay, .drawer-sidebar, .evidence-drawer, .drawer-backdrop").forEach(el => {
            el.classList.add("hidden");
        });
    }
}
