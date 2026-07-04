# Codebase Context Brief: cost accounting
Generated on: 2026-06-28T09:11:25Z

## 1. Directory Structure
```text
cost accounting\
├── EXECUTION_PLAN.md
├── NEXT.md
├── PROJECT_LOG.md
├── PROTOCOL.md
├── README.md
├── ROADMAP.md
├── SYSTEM_MAP.md
├── THOUGHT_LOG.md
├── UMAGS.md
├── research-notes\
│   └── speculative-ideas.md
├── scratch\
│   ├── DO_NOT_RUN_simulates_human_input.py
│   ├── brief_output.md
│   ├── clean_blind_feedback_filter.py
│   ├── create_analyzer_bak.py
│   ├── debug_classifier.py
│   ├── evaluate_logistic.py
│   ├── generate_equivalent_mutants.py
│   ├── get_next_blind_target.py
│   ├── get_study_target.py
│   ├── prepare_blind_feedback_filter.py
│   ├── reorg_hashes.json
│   ├── run_reorg_verification_tests.py
│   ├── run_validation_experiment.py
│   ├── search_ui.py
│   ├── test_anomaly_dir\
│   │   ├── baseline.py
│   │   └── target_anomaly.py
│   ├── test_ast_checks.py
│   ├── test_ast_checks_test.py
│   ├── test_git_warning.py
│   ├── test_mcp_server.py
│   ├── test_rate_srs.js
│   ├── ultron_playground\
│   │   ├── math_utils.py
│   │   ├── run_tests.py
│   │   └── test_math_utils.py
│   └── update_roadmap_git.py
├── start_ultron.py
├── synapse_project\
│   ├── README.md
│   ├── benchmarks\
│   │   └── pymitter\
│   │       ├── LICENSE
│   │       ├── README.md
│   │       ├── assets\
│   │       │   ├── favicon.ico
│   │       │   ├── logo.png
│   │       │   └── logo250.png
│   │       ├── codecov.yml
│   │       ├── docs\
│   │       │   ├── Makefile
│   │       │   ├── _static\
│   │       │   │   └── style.css
│   │       │   ├── conf.py
│   │       │   └── index.rst
│   │       ├── examples.py
│   │       ├── pyproject.toml
│   │       ├── src\
│   │       │   └── pymitter\
│   │       │       ├── __init__.py
│   │       │       └── py.typed
│   │       └── tests\
│   │           ├── __init__.py
│   │           └── test_all.py
│   ├── docs\
│   │   ├── experiment_plan.md
│   │   ├── math_spec.md
│   │   └── thesis_outline.md
│   ├── synapse_core\
│   │   ├── README.md
│   │   ├── demo_refactor.py
│   │   ├── docs\
│   │   │   └── system_boundary.md
│   │   ├── examples\
│   │   │   ├── sample_project\
│   │   │   │   ├── data\
│   │   │   │   │   ├── ledger.json
│   │   │   │   │   └── mutation_report.patch
│   │   │   │   └── target.py
│   │   │   └── sample_tests\
│   │   │       └── test_target.py
│   │   ├── pyproject.toml
│   │   ├── synapse\
│   │   │   ├── __init__.py
│   │   │   ├── cli\
│   │   │   │   ├── __init__.py
│   │   │   │   └── run.py
│   │   │   ├── core\
│   │   │   │   ├── __init__.py
│   │   │   │   ├── analyzer.py
│   │   │   │   ├── fitness.py
│   │   │   │   ├── graph_builder.py
│   │   │   │   └── mutator.py
│   │   │   ├── evolve\
│   │   │   │   ├── __init__.py
│   │   │   │   ├── evolver.py
│   │   │   │   └── selection.py
│   │   │   └── runtime\
│   │   │       ├── __init__.py
│   │   │       ├── executor.py
│   │   │       └── test_runner.py
│   │   └── synapse_evolution.egg-info\
│   │       ├── PKG-INFO
│   │       ├── SOURCES.txt
│   │       ├── dependency_links.txt
│   │       ├── entry_points.txt
│   │       ├── requires.txt
│   │       └── top_level.txt
│   └── synapse_mutator\
│       ├── demo_target\
│       │   ├── __init__.py
│       │   ├── math_ops.py
│       │   └── tests\
│       │       └── test_math_ops.py
│       ├── ledger.jsonl
│       ├── mutate.py
│       ├── requirements.txt
│       ├── run.py
│       ├── score.py
│       └── scratch\
│           └── test_mvp_mutator.py
├── ultron\
│   ├── README.md
│   ├── __init__.py
│   ├── core\
│   │   ├── __init__.py
│   │   ├── analyzer.py
│   │   ├── classifier.py
│   │   ├── context_brief.py
│   │   ├── fuzz.py
│   │   ├── guard.py
│   │   ├── logistic.py
│   │   ├── meta_layer.py
│   │   ├── models.py
│   │   ├── pledge.py
│   │   ├── predict.py
│   │   ├── prompt.py
│   │   ├── risk.py
│   │   ├── sentinel.py
│   │   └── translate.py
│   ├── data\
│   │   └── ledger.json
│   ├── docs\
│   │   ├── integration_guide.md
│   │   ├── math_spec.md
│   │   ├── research_paper.md
│   │   └── system_architecture_breakdown.md
│   ├── experimental\
│   │   ├── __init__.py
│   │   ├── delta.py
│   │   ├── design_oracle.py
│   │   └── reality_delta.py
│   ├── hooks\
│   │   └── pre-commit
│   ├── interfaces\
│   │   ├── __init__.py
│   │   ├── mcp_server.py
│   │   ├── server.py
│   │   ├── ultron.py
│   │   └── web\
│   │       ├── index.css
│   │       ├── index.html
│   │       └── index.js
│   ├── meta\
│   │   ├── active_pledges.json
│   │   ├── audit_package.yaml
│   │   ├── audit_telemetry.jsonl
│   │   ├── blind_feedback.jsonl
│   │   ├── blind_feedback_INVALID_self_rated.jsonl
│   │   ├── blind_feedback_test_fixtures.jsonl
│   │   ├── blind_study_sample.txt
│   │   ├── blind_study_scores_DO_NOT_LOOK.csv
│   │   ├── calibrated_weights.json
│   │   ├── evolution_ledger.json
│   │   ├── experiment_log.jsonl
│   │   ├── fusion_weights.json
│   │   ├── human_feedback.jsonl
│   │   ├── logistic_weights.json
│   │   ├── reality_deltas.jsonl
│   │   └── subagents_config.json
│   ├── requirements.txt
│   ├── tests\
│   │   ├── __init__.py
│   │   ├── run_academic_tests.py
│   │   └── run_tests.py
│   ├── validation\
│   │   ├── __init__.py
│   │   ├── ai_rater.py
│   │   └── blind_rate.py
│   └── walkthrough.md
└── umags\
    ├── checks.py
    ├── config.py
    ├── failure_space.py
    ├── governor.py
    ├── run_verification_loop.py
    └── tools\
        ├── __init__.py
        ├── analyze_blind_study.py
        ├── compare_ai_ratings.py
        └── run_stratified_sampling.py
```

## 2. File Risk Profiles
| File | Risk Tier | Impact Score | Complexity | Coupling |
| --- | --- | --- | --- | --- |
| ultron/core/classifier.py | HIGH | 218.70 | 86 | 10.0 |
| umags/run_verification_loop.py | HIGH | 210.98 | 121 | 3.0 |
| ultron/core/risk.py | HIGH | 93.23 | 41 | 7.0 |
| ultron/validation/blind_rate.py | HIGH | 66.26 | 38 | 3.0 |
| umags/failure_space.py | HIGH | 58.47 | 27 | 6.0 |
| synapse_project/synapse_mutator/mutate.py | HIGH | 57.61 | 22 | 11.0 |
| ultron/core/analyzer.py | HIGH | 53.51 | 19 | 14.0 |
| ultron/core/predict.py | HIGH | 45.72 | 24 | 4.0 |
| ultron/interfaces/ultron.py | HIGH | 38.08 | 29 | 1.0 |
| synapse_project/synapse_core/synapse/core/mutator.py | HIGH | 36.81 | 17 | 6.0 |
| ultron/core/context_brief.py | HIGH | 35.46 | 27 | 1.0 |
| synapse_project/synapse_mutator/run.py | HIGH | 32.00 | 32 | 0.0 |
| synapse_project/synapse_core/synapse/runtime/test_runner.py | HIGH | 30.48 | 16 | 4.0 |
| ultron/interfaces/server.py | HIGH | 30.00 | 30 | 0.0 |
| umags/tools/analyze_blind_study.py | HIGH | 30.00 | 30 | 0.0 |
| scratch/run_validation_experiment.py | HIGH | 29.00 | 29 | 0.0 |
| ultron/core/sentinel.py | HIGH | 27.00 | 27 | 0.0 |
| umags/checks.py | HIGH | 25.99 | 12 | 6.0 |
| synapse_project/synapse_core/synapse/evolve/evolver.py | HIGH | 24.52 | 12 | 5.0 |
| ultron/experimental/reality_delta.py | HIGH | 21.01 | 16 | 1.0 |
| synapse_project/synapse_mutator/score.py | HIGH | 20.95 | 11 | 4.0 |
| ultron/experimental/design_oracle.py | HIGH | 19.70 | 15 | 1.0 |
| ultron/core/meta_layer.py | HIGH | 18.39 | 14 | 1.0 |
| umags/governor.py | HIGH | 17.44 | 10 | 3.0 |
| ultron/core/guard.py | HIGH | 17.32 | 8 | 6.0 |
| ultron/core/prompt.py | HIGH | 15.69 | 9 | 3.0 |
| ultron/experimental/delta.py | HIGH | 15.51 | 10 | 2.0 |
| ultron/core/fuzz.py | HIGH | 15.00 | 15 | 0.0 |
| umags/tools/compare_ai_ratings.py | HIGH | 15.00 | 15 | 0.0 |
| scratch/prepare_blind_feedback_filter.py | HIGH | 14.00 | 14 | 0.0 |
| ultron/interfaces/mcp_server.py | HIGH | 14.00 | 14 | 0.0 |
| ultron/core/models.py | HIGH | 13.95 | 4 | 30.0 |
| ultron/validation/ai_rater.py | HIGH | 13.00 | 13 | 0.0 |
| umags/tools/run_stratified_sampling.py | HIGH | 13.00 | 13 | 0.0 |
| ultron/core/logistic.py | HIGH | 12.41 | 8 | 2.0 |
| synapse_project/synapse_core/synapse/core/analyzer.py | HIGH | 11.82 | 9 | 1.0 |
| synapse_project/benchmarks/pymitter/src/pymitter/__init__.py | HIGH | 11.43 | 6 | 4.0 |
| synapse_project/synapse_core/synapse/core/graph_builder.py | HIGH (adjusted:  lowered HIGH threshold to 10.0) | 9.84 | 4 | 9.0 |
| scratch/DO_NOT_RUN_simulates_human_input.py | HIGH (adjusted: 2 bug-fix commits lowered HIGH threshold to 7.0) | 9.00 | 9 | 0.0 |
| scratch/run_reorg_verification_tests.py | HIGH (adjusted: 1 bug-fix commit lowered HIGH threshold to 8.5) | 9.00 | 9 | 0.0 |
| synapse_project/synapse_core/synapse/evolve/selection.py | MEDIUM | 7.88 | 6 | 1.0 |
| ultron/core/translate.py | MEDIUM | 7.76 | 5 | 2.0 |
| scratch/clean_blind_feedback_filter.py | MEDIUM | 7.00 | 7 | 0.0 |
| scratch/get_next_blind_target.py | HIGH (adjusted: 2 bug-fix commits lowered HIGH threshold to 7.0) | 7.00 | 7 | 0.0 |
| synapse_project/synapse_core/synapse/runtime/executor.py | MEDIUM | 6.57 | 5 | 1.0 |
| scratch/update_roadmap_git.py | MEDIUM | 6.00 | 6 | 0.0 |
| scratch/ultron_playground/math_utils.py | MEDIUM | 5.25 | 4 | 1.0 |
| ultron/core/pledge.py | MEDIUM | 5.25 | 4 | 1.0 |
| start_ultron.py | MEDIUM | 5.00 | 5 | 0.0 |
| synapse_project/synapse_mutator/scratch/test_mvp_mutator.py | MEDIUM | 4.00 | 4 | 0.0 |
| synapse_project/synapse_core/examples/sample_project/target.py | HIGH (adjusted:  lowered HIGH threshold to 10.0) | 3.81 | 2 | 4.0 |
| scratch/test_ast_checks.py | LOW | 2.63 | 2 | 1.0 |
| synapse_project/synapse_core/synapse/core/fitness.py | LOW | 2.63 | 2 | 1.0 |
| scratch/test_ast_checks_test.py | LOW | 2.00 | 2 | 0.0 |
| scratch/test_mcp_server.py | LOW | 2.00 | 2 | 0.0 |
| scratch/ultron_playground/test_math_utils.py | LOW | 2.00 | 2 | 0.0 |
| synapse_project/synapse_core/examples/sample_tests/test_target.py | LOW | 2.00 | 2 | 0.0 |
| synapse_project/synapse_core/synapse/cli/run.py | LOW | 2.00 | 2 | 0.0 |
| synapse_project/synapse_mutator/demo_target/math_ops.py | LOW | 2.00 | 2 | 0.0 |
| scratch/evaluate_logistic.py | LOW | 1.31 | 1 | 1.0 |
| scratch/test_anomaly_dir/baseline.py | LOW | 1.31 | 1 | 1.0 |
| scratch/create_analyzer_bak.py | LOW | 1.00 | 1 | 0.0 |
| scratch/debug_classifier.py | LOW | 1.00 | 1 | 0.0 |
| scratch/generate_equivalent_mutants.py | LOW | 1.00 | 1 | 0.0 |
| scratch/get_study_target.py | LOW | 1.00 | 1 | 0.0 |
| scratch/search_ui.py | LOW | 1.00 | 1 | 0.0 |
| scratch/test_git_warning.py | LOW | 1.00 | 1 | 0.0 |
| scratch/test_anomaly_dir/target_anomaly.py | LOW | 1.00 | 1 | 0.0 |
| scratch/ultron_playground/run_tests.py | LOW | 1.00 | 1 | 0.0 |
| synapse_project/benchmarks/pymitter/examples.py | LOW | 1.00 | 1 | 0.0 |
| synapse_project/benchmarks/pymitter/docs/conf.py | LOW | 1.00 | 1 | 0.0 |
| synapse_project/synapse_core/demo_refactor.py | LOW | 1.00 | 1 | 0.0 |
| synapse_project/synapse_core/synapse/__init__.py | HIGH | 1.00 | 1 | 0.0 |
| synapse_project/synapse_core/synapse/cli/__init__.py | HIGH | 1.00 | 1 | 0.0 |
| synapse_project/synapse_core/synapse/core/__init__.py | HIGH | 1.00 | 1 | 0.0 |
| synapse_project/synapse_core/synapse/evolve/__init__.py | HIGH | 1.00 | 1 | 0.0 |
| synapse_project/synapse_core/synapse/runtime/__init__.py | HIGH | 1.00 | 1 | 0.0 |
| synapse_project/synapse_mutator/demo_target/__init__.py | HIGH | 1.00 | 1 | 0.0 |
| ultron/__init__.py | HIGH | 1.00 | 1 | 0.0 |
| ultron/core/__init__.py | HIGH | 1.00 | 1 | 0.0 |
| ultron/experimental/__init__.py | HIGH | 1.00 | 1 | 0.0 |
| ultron/interfaces/__init__.py | HIGH | 1.00 | 1 | 0.0 |
| ultron/validation/__init__.py | HIGH | 1.00 | 1 | 0.0 |
| umags/config.py | LOW | 1.00 | 1 | 0.0 |
| umags/tools/__init__.py | HIGH | 1.00 | 1 | 0.0 |

## 3. High-Level Dependency Graph
### Central Hubs (highly coupled)
*   **ultron/core/models.py** (referenced by 30 other files)
*   **ultron/core/analyzer.py** (referenced by 14 other files)
*   **synapse_project/synapse_mutator/mutate.py** (referenced by 11 other files)
*   **ultron/core/classifier.py** (referenced by 10 other files)
*   **synapse_project/synapse_core/synapse/core/graph_builder.py** (referenced by 9 other files)
*   **ultron/core/risk.py** (referenced by 7 other files)
*   **umags/failure_space.py** (referenced by 6 other files)
*   **synapse_project/synapse_core/synapse/core/mutator.py** (referenced by 6 other files)
*   **umags/checks.py** (referenced by 6 other files)
*   **ultron/core/guard.py** (referenced by 6 other files)
*   **synapse_project/synapse_core/synapse/evolve/evolver.py** (referenced by 5 other files)
*   **ultron/core/predict.py** (referenced by 4 other files)
*   **synapse_project/synapse_core/synapse/runtime/test_runner.py** (referenced by 4 other files)
*   **synapse_project/synapse_mutator/score.py** (referenced by 4 other files)
*   **synapse_project/benchmarks/pymitter/src/pymitter/__init__.py** (referenced by 4 other files)
*   **synapse_project/synapse_core/examples/sample_project/target.py** (referenced by 4 other files)
*   **umags/run_verification_loop.py** (referenced by 3 other files)
*   **ultron/validation/blind_rate.py** (referenced by 3 other files)
*   **umags/governor.py** (referenced by 3 other files)
*   **ultron/core/prompt.py** (referenced by 3 other files)
*   **ultron/experimental/delta.py** (referenced by 2 other files)
*   **ultron/core/logistic.py** (referenced by 2 other files)
*   **ultron/core/translate.py** (referenced by 2 other files)
*   **ultron/interfaces/ultron.py** (referenced by 1 other files)
*   **ultron/core/context_brief.py** (referenced by 1 other files)
*   **ultron/experimental/reality_delta.py** (referenced by 1 other files)
*   **ultron/experimental/design_oracle.py** (referenced by 1 other files)
*   **ultron/core/meta_layer.py** (referenced by 1 other files)
*   **synapse_project/synapse_core/synapse/core/analyzer.py** (referenced by 1 other files)
*   **synapse_project/synapse_core/synapse/evolve/selection.py** (referenced by 1 other files)
*   **synapse_project/synapse_core/synapse/runtime/executor.py** (referenced by 1 other files)
*   **scratch/ultron_playground/math_utils.py** (referenced by 1 other files)
*   **ultron/core/pledge.py** (referenced by 1 other files)
*   **scratch/test_ast_checks.py** (referenced by 1 other files)
*   **synapse_project/synapse_core/synapse/core/fitness.py** (referenced by 1 other files)
*   **scratch/evaluate_logistic.py** (referenced by 1 other files)
*   **scratch/test_anomaly_dir/baseline.py** (referenced by 1 other files)

### Leaf Modules (safe to change)
*   **scratch/DO_NOT_RUN_simulates_human_input.py**
*   **scratch/clean_blind_feedback_filter.py**
*   **scratch/create_analyzer_bak.py**
*   **scratch/debug_classifier.py**
*   **scratch/generate_equivalent_mutants.py**
*   **scratch/get_next_blind_target.py**
*   **scratch/get_study_target.py**
*   **scratch/prepare_blind_feedback_filter.py**
*   **scratch/run_reorg_verification_tests.py**
*   **scratch/run_validation_experiment.py**
*   **scratch/search_ui.py**
*   **scratch/test_anomaly_dir/target_anomaly.py**
*   **scratch/test_ast_checks_test.py**
*   **scratch/test_git_warning.py**
*   **scratch/test_mcp_server.py**
*   **scratch/ultron_playground/run_tests.py**
*   **scratch/ultron_playground/test_math_utils.py**
*   **scratch/update_roadmap_git.py**
*   **start_ultron.py**
*   **synapse_project/benchmarks/pymitter/docs/conf.py**
*   **synapse_project/benchmarks/pymitter/examples.py**
*   **synapse_project/synapse_core/demo_refactor.py**
*   **synapse_project/synapse_core/examples/sample_tests/test_target.py**
*   **synapse_project/synapse_core/synapse/__init__.py**
*   **synapse_project/synapse_core/synapse/cli/__init__.py**
*   **synapse_project/synapse_core/synapse/cli/run.py**
*   **synapse_project/synapse_core/synapse/core/__init__.py**
*   **synapse_project/synapse_core/synapse/evolve/__init__.py**
*   **synapse_project/synapse_core/synapse/runtime/__init__.py**
*   **synapse_project/synapse_mutator/demo_target/__init__.py**
*   **synapse_project/synapse_mutator/demo_target/math_ops.py**
*   **synapse_project/synapse_mutator/run.py**
*   **synapse_project/synapse_mutator/scratch/test_mvp_mutator.py**
*   **ultron/__init__.py**
*   **ultron/core/__init__.py**
*   **ultron/core/fuzz.py**
*   **ultron/core/sentinel.py**
*   **ultron/experimental/__init__.py**
*   **ultron/interfaces/__init__.py**
*   **ultron/interfaces/mcp_server.py**
*   **ultron/interfaces/server.py**
*   **ultron/validation/__init__.py**
*   **ultron/validation/ai_rater.py**
*   **umags/config.py**
*   **umags/tools/__init__.py**
*   **umags/tools/analyze_blind_study.py**
*   **umags/tools/compare_ai_ratings.py**
*   **umags/tools/run_stratified_sampling.py**

## 4. Known Open Issues & Gaps (from ROADMAP.md)
### ⚠️ Working, not yet validated
### Multi-Signal Risk Fusion & Change-Risk Prediction (`reality_delta.py`, `delta.py`) — *Ultron feature, built during UMAGS sessions*
**Reclassified 2026-06-21 from implied governance infrastructure to Ultron risk-scoring feature.** `delta.py` implements `predict_change_risk()` — a learned three-weight model (`w_impact`, `w_mkr`, `w_cest`) updated via online SGD from `learn_from_feedback()`. `reality_delta.py` wraps a six-weight fusion layer (`w_test`, `w_git`, `w_runtime`, `w_human`, `w_test_runtime`, `w_git_human`) that combines all signal sources into a single Residual Risk Score, with backward-compatible schema migration and L2 regularization.

**Gap:** Fusion weights are calibrated against the full set of logged transactions with no held-out evaluation set — performance on unseen data is not validated. The counterfactual ablation test (`C_i = max(0, R_actual - R_ablated_i)`) has not been run on real defect data; it has only been exercised on synthetic examples.

### Git-history bug-fix extraction (`extract_git_history`)
**Confirmed:** the feature runs and correctly parses commit history. If the repo is missing or contains zero matches, it outputs clear warnings rather than failing silently.

**Gap:** the efficacy of using bug-fix commit frequency to scale static risk warnings is not yet validated against real-world defect density.

### Mutation testing / Mutation Kill Rate (`synapse_mutator/run.py`)
Generates mutants, runs the real test suite against them, logs results to
`ledger.jsonl`. This genuinely works on real code (`demo_target/math_ops.py`
confirmed).

**Gap:** only tested so far on a trivial, literal-substitution mutation
(`1.15` → a renamed constant of the same value). This is closer to a
no-op than a real behavior change. The mutation types that actually matter
for catching weak tests — flipped comparisons, off-by-one boundaries, swapped
operands — haven't been exercised yet.

### CEST / differential fuzzing (`fuzz.py`)
Computes behavioral divergence between original and mutated code by running
both against a pool of randomly sampled inputs.

**Gap:** input generation is random sampling from a fixed pool of generic
values (`0, 1, -1, "", [], {}`, etc.), not type-aware or boundary-aware. This
means a mutant can be mislabeled "semantically equivalent" simply because the
random inputs never landed near the value where the behavior actually
diverges — false equivalence, not true equivalence. All three logged examples
so far are trivial refactors; none test a boundary-sensitive case like
`>` vs `>=`.

### Static Design Intelligence Layer (`design_oracle.py`) — *Ultron feature, built during UMAGS sessions*
**Reclassified 2026-06-21 from implied governance infrastructure to Ultron risk-scoring feature.** Performs static codebase analysis: circular dependency detection (DFS-based cycle enumeration), global mutation scanning (AST traversal for `global` declarations), future coupling simulation (path-impact modelling when moving a function between files), and design pattern recommendations keyed on intent keywords.

**Gap:** Built entirely inside UMAGS-scoped sessions and never evaluated against real-world outcomes. No ground-truth data confirming that circular dependency or coupling warnings correspond to actual defects. No negative test cases confirming the DFS cycle detector handles pathological graphs (self-loops, highly-connected subgraphs). Integration tests exist but only cover happy paths.

### 🔇 Silently inert
### Human feedback collection (`human_feedback.jsonl`)
**Confirmed:** 2 entries, covering 1 file, no rater identity tracked, no
blinding — the risk score is visible before the rating is given. This isn't
broken, but it's not yet data; it's a UI control waiting for an actual
study to use it properly (see Phase 1 plan).

### 🔇 DORMANT — Working code, not in active use
### AI Rater + Compare AI Ratings (`ultron/validation/ai_rater.py`, `umags/tools/compare_ai_ratings.py`)
Both files are syntactically valid and were written for an AI-vs-human rating comparison
study. Neither is currently called by any active pipeline. The comparison study they support
is BLOCKED on the human feedback collection step (see `ultron/validation/blind_rate.py` above — the
`blind_feedback.jsonl` file is still empty).

**Decision (2026-06-24):** Kept in place, not deleted. If human ratings are collected and
the pipeline resumes, these are the correct next step. Removing them would require
re-implementation. Marked dormant, not dead. Do not touch without a specific plan.

### Constitutional Sentinel (`ultron/core/sentinel.py`)
Computes codebase structural entropy, scans comments/docstrings for behavioral assumptions, and flags potential abstraction bloat or architecture drift.

**Decision (2026-06-26):** Marked dormant in `umags/run_verification_loop.py` to keep the UMAGS governance process lightweight and token-efficient. The code is preserved but skipped during verification loops. Do not reactivate without explicit instruction.

### 🪦 Documented, not implemented
The following are described in `research-notes/speculative-ideas.md` but have
**no corresponding code anywhere in the repository**:

- Vector Scoring Engine (`adaptive_scorer.py`)
- Topological Simulator (`topological_simulator.py`)
- Temporal Drift & Causal Polarity Engine (`temporal_engine.py`)
- Minimax Solver / Control Layer (`intervention_optimizer.py`)
- Structural Decision-Theoretic Controller (`controller.py`)

**Decision:** these are interesting future directions, not current
features. The manifest describing them has been moved to
`research-notes/speculative-ideas.md` with an explicit disclaimer, so it's
clear to anyone reading the repo that nothing in that document is live code.
