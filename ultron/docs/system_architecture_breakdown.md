# System Architecture Breakdown: Ultron & Synapse Cognitive Stacks

This document provides a comprehensive analysis of the repository's contents, detailing the mathematical foundations, system integrations, and directory roles of **Ultron**, **Synapse Core**, and **Synapse Mutator (MVP)**.

---

## 1. Directory Topology Map

```text
├── start_ultron.py            # Universal cross-platform launcher (v1.7)
├── ultron\                    # Ultron Pre-Execution Intelligence
│   ├── server.py              # Single-threaded HTTP API daemon (v1.6/v1.7)
│   ├── analyzer.py            # AST module parser and dependency builder
│   ├── risk.py                # Complexity, coupling, and confidence calculations
│   ├── classifier.py          # Levenshtein typo and reachability rule models
│   ├── predict.py             # Test impact prediction engine (transitive BFS)
│   ├── guard.py               # Call contract signature validator
│   ├── meta_layer.py          # Meta-Ultron calibration sweep governor
│   └── web\                   # Vanilla HTML/CSS/JS frontend dashboard
├── synapse_project\           # SYNAPSE Program Evolution Framework
│   └── synapse_mutator\       
│       └── ledger.jsonl       # Adversarial mutation log (MKR records)
└── scratch\                   # Sandbox playground and temporary files
    └── ultron_playground\     # Generated playground target (math_utils.py)
```

---

## 2. Ultron: Pre-Execution Software Foresight

Ultron operates as a **three-layered software verification environment** that predicts and audits risks before code changes are accepted.

### Layer A: Structural Risk (Static Foresight)
Ultron calculates a **System Impact Score** ($I$) for every file node in the codebase:
\[I(N) = C(N) \times \ln(e + K(N))\]
Where:
*   **$C(N)$ (McCabe Cyclomatic Complexity)**: Extracted from AST branch nodes.
*   **$K(N)$ (Coupling Centrality)**: Calculated by resolving static function/class calls. *Assumption*: Call pathways are assumed to be static; dynamic dispatch (e.g. `getattr` indirection) is out of scope.

#### Risk Classification Tiers:
*   **HIGH** ($I \ge 10.0$): Critical system boundary. Signature changes require concurrent caller refactoring.
*   **MEDIUM** ($3.0 \le I < 10.0$): Shared utility zone.
*   **LOW** ($I < 3.0$): Leaf module. Safe, isolated modification area.

### Layer B: Behavioral Consistency (CFG Reachability & Typo Audits)
*   **Typo / Name Confusion Detection**: Uses normalized **Levenshtein String Similarity** to check if calls made in modified code match a global database of valid identifiers. If similarity satisfies:
    \[T_{\text{typo}} \le \text{Similarity}(id_1, id_2) < 1.0\]
    it flags a potential typo/identifier confusion.
*   **CFG Reachability Rules (Replacing Learned Markov Chains)**: Instead of training a statistically starved probability chain over sparse local sequences, Ultron uses an explicit, rule-based check over the static Control Flow Graph (CFG) of functions. It asserts ordering constraints such as:
    *   `X` (e.g. `close_db`) must not be reachable before `Y` (e.g. `query`) on any path.
    *   `Y` (e.g. `cleanup`) must follow `X` on all terminating execution paths.

### Layer C: Adversarial Calibration (Combined Confidence)
Combines static structural scores with adversarial test coverage metrics (MKR) to yield a **Combined Confidence Score** ($U_c$):
\[U_c = \frac{\text{MKR}}{1.0 + 0.1 \times I} \times 100\%\]
*   **$\text{MKR}$ (Mutation Kill Rate)**: Fed from the Synapse Mutator ledger.
*   **Asynchronous Caching Policy**: Since running mutation testing on every edit is computationally prohibitive, MKR stats are cached per file and only updated asynchronously when structural git diffs are detected in the target file.

---

## 3. SYNAPSE: Program Evolution & Behavioral Equivalence

SYNAPSE is a framework designed to calibrate and optimize software architectures through mutation testing and AST mutations.

### SYNAPSE Core: Differential Trace checking (CEST)
True semantic preservation is undecidable. Therefore, CEST is defined as **Differential Trace Checking** over fuzzed input sets:
1.  **Fuzzed Input Generator**: Generates fuzzed, property-based inputs independent of the existing unit test suite to cover wider edge cases.
2.  **State Delta Capture**: Runs both original and modified codes on the fuzzed inputs, capturing outputs, side-effects, and call sequences.
3.  **Trace Distance ($\Delta \text{CEST}$)**: Calculated as the fraction of fuzzed inputs that produce divergent observable state deltas:
    \[\Delta \text{CEST} = \frac{\text{Divergent Runs}}{\text{Total Fuzzed Runs}} < \epsilon\]

### SYNAPSE Mutator / MVP (Test Sensitivity Engine)
*   Injects synthetic, non-compilation-breaking defects into target code.
*   Runs the project's test suite to see if the tests detect the mutation.
*   **MKR Filtering**: Enforces a minimum mutation count per file (to prevent noise in files with low lines of code) and flags suspected equivalent mutants (mutants that cannot be killed because they are semantically identical to the original).
