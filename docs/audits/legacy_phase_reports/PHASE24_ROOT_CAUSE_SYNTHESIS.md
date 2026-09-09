# Ultron Phase 2.4 — Visual & Usability Root-Cause Synthesis

**Status:** WAVE 1 SYNTHESIS COMPLETE — READY FOR WAVE 2 REPAIRS  
**Input:** 10 Empirical Visual Reality Reports (`PHASE24_*.md`) + `PHASE24_PC0_BASELINE.md`  

---

## 1. The Core Product Defect

Ultron's backend control plane and runtime reality traces are technically robust, but its visual presentation violates the fundamental product law:

```text
TARGET EXPERIENCE:
SEE -> UNDERSTAND -> DECIDE -> ACT

OBSERVED PC-0 EXPERIENCE:
SEE -> READ -> INTERPRET -> CROSS-REFERENCE -> DECIDE -> ACT
```

### The Three Root Causes:

1. **Root Cause 1: Competing Visual Dominance (Navbar vs. Project Bar vs. Action Buttons):**
   - The top header has 9 controls, the project status bar adds an extra horizontal layer, and Current Work features 4 buttons in 3 different vibrant colors (Cyan, Slate, Emerald).
   - *Consequence:* The developer's eyes wander; there is no unmistakable "Next Safe Step".

2. **Root Cause 2: Technical Metrics Over Decision Surfaces (Risk Table & Graph):**
   - The UI surfaces internal metrics (McCabe complexity, fan-in, fan-out) instead of developer answers:
     `THIS FILE -> WHY IT MATTERS -> WHAT IT AFFECTS -> WHAT MAY BREAK -> WHAT TO ASK AGENT TO DO`.

3. **Root Cause 3: Fragmented Timeline & Compiler Output (Work & Agent Context):**
   - Work lifecycle progress is stored in state but rendered as a static box rather than a visible stepper.
   - Agent Context presents a prompt editor rather than a clean, structured compiler output.

---

## 2. Wave 2 Priority Roadmap

- **Iteration v2.4.1 (Priority 1 & 3):** Consolidate Navbar clutter, eliminate the redundant Active Project stripe, and establish unambiguous Primary Action Button hierarchy in Current Work.
- **Iteration v2.4.2 (Priority 4 & 5):** Transform Risk Table and D3 Graph into interactive Decision Surfaces with visual blast-radius halos.
- **Iteration v2.4.3 (Priority 6 & 7):** Render visible Development Stepper Timeline in Work and clean structured compiler cards in Agent Context.
- **Iteration v2.4.4 (Priority 8, 9, 10):** Repository Health Delta in Verify, typography standardization (middle path truncation, >=12px text), and inviting empty-state call-to-actions.
