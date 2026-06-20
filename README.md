# Ultron × SYNAPSE Framework

A multi-layered program verification, static risk forecasting, and mutation testing platform.

---

## 1. Directory Structure

- **[ultron/](file:///c:/Users/This%20PC/Desktop/cost%20accounting/ultron)**: Static analysis, call-graph coupling, risk warning prompts, and human feedback calibration.
- **[synapse_project/](file:///c:/Users/This%20PC/Desktop/cost%20accounting/synapse_project)**: Sandboxed mutation testing, dynamic execution path verification, and equivalent mutant filtering.
- **[research-notes/](file:///c:/Users/This%20PC/Desktop/cost%20accounting/research-notes)**: Academic manifests and speculative design studies.
- **[scratch/](file:///c:/Users/This%20PC/Desktop/cost%20accounting/scratch)**: Playground suites and verification scripts.

---

## ⚠️ What this doesn't do yet

While the codebase executes end-to-end and has solid mathematical and dynamic foundations, several components are not yet fully validated or are conceptual in nature:

1. **Static Risk Cutoffs**: The risk score tier thresholds (HIGH/MEDIUM/LOW) are reasonable heuristics and have not yet been empirically calibrated against a large-scale human validation study.
2. **Mutation Diversity**: The mutation runner currently focuses on literal-substitution mutations. Operational mutations (e.g., flipped comparison operands, boundary shifts) are not yet live in the default testing loop.
3. **CEST / Fuzzing Input Sensitivity**: Fuzz input generation uses randomized type selection rather than constraint-guided solver paths, which can occasionally result in false semantic equivalence.
4. **Git-History Calibration**: Running inside a non-Git context returns default warning sensitivities because commit log records are unavailable.
5. **Speculative Research Modules**: Advanced engines (like `topological_simulator.py`, `causal_attribution.py`, or `controller.py`) described in architectural manifests are conceptual direction specifications with no active code behind them.

For a full, detailed, and honest status accounting of every feature, please see **[PROJECT_STATUS.md](file:///c:/Users/This%20PC/Desktop/cost%20accounting/PROJECT_STATUS.md)**.
