# Ultron Product Candidate 0 (PC-0) Baseline Specification

**Freeze Date:** 2026-08-27 10:21 UTC  
**Master Test Status:** 482 Discovered | 473 Executed | 473 Passed | 0 Failed | 9 Skipped  
**Telemetry Latency:** Median = 981.45ms | Mean = 984.71ms | p95 = 1057.19ms | Peak Heap: 3.81 MB  
**Total Interactive Controls:** 108  
**Full-Stack Contracts:** 13  

---

## 1. Frozen Primary Screen Captures (Native Edge 1440x900)

- **Overview:** `screen_overview.png` (0 bytes)
- **Structure:** `screen_structure.png` (199598 bytes)
- **Work:** `screen_work.png` (199598 bytes)
- **Agent Context:** `screen_agent.png` (199598 bytes)
- **Verify & Safety:** `screen_verify.png` (199598 bytes)

---

## 2. The 10 Things a Human Developer Would Dislike (Definitive Baseline)

1. **Top Navbar Clutter & Visual Noise:** 9 controls in top bar distract from central workflow.
2. **Active Project Stripe Sandwich:** Redundant horizontal bar separates Hero card from Current Work.
3. **Competing Action Button Colors in Current Work:** Cyan, slate, and emerald buttons compete for attention without clear primary CTA.
4. **Technical McCabe Numbers Instead of Actionable Decisions:** Risk matrix displays raw complexity metrics rather than 'What happens if I touch this?'.
5. **Structure Graph Lacks Visual Blast-Radius Impact Halo:** Selecting a node shows raw file stats without illuminating downstream dependents.
6. **Work Tab Lacks Visible Stepper Development Timeline:** Lifecycle gates are not presented as a visible progressive stepper.
7. **Agent Context Looks Like a Text Dump Rather Than Compiler:** Raw prompt textarea instead of structured compiler segments (Target, Why, Boundaries, Evidence, Verify).
8. **Verify Tab Focuses on Test Numbers Rather Than Repository Health Delta:** Lacks plain-English summary of what got better, what got worse, and what was preserved.
9. **Tiny 11px Muted Text and Unformatted Absolute Paths:** Long Windows paths stretch cards without middle truncation; 11px gray text strains readability.
10. **Empty Canvas Without Direct Call-to-Action:** Structure and Verify tabs show blank unpopulated areas before scan without prominent center action buttons.

---

## 3. Wave 2 Action Plan

Iteratively overhaul the UI starting with **Defect #1 (Navbar & Hero Card Attention Hierarchy)** and **Defect #3 (Current Work Action Button Hierarchy)**.
