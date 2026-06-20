> **Status: Speculative / Not Implemented**
> Nothing described below exists as working code in this repository.
> These are future research directions, kept for reference. See
> ROADMAP.md for what is actually built and verified.

---

# SYNAPSE Architecture Manifest (v1.0 – v9.2)

This document serves as the comprehensive audit trail for the SYNAPSE protocol. It traces the evolution from a basic conceptual scoring prompt into a grounded evolutionary program optimization toolkit.

---

## 1. Core Philosophy & Epistemology

SYNAPSE operates on a strict set of grounding principles established to prevent the system from "hallucinating causality" or over-claiming predictive power:
- **Failure Physics**: Software fragility is a topological property of failure cascade pathways.
- **Bounded Observability**: SYNAPSE does not possess "ground truth" about runtime behavior. It measures structural attributes under constrained observability.
- **State Separation**: Syntactic prediction models (Model World) must remain strictly decoupled from exogenous verification channels (Reality World) to prevent epistemic feedback loops.
- **Behavioral Preservation**: Structural risk reduction is only valid if behavioral equivalence is preserved. We never commit in-place mutations without dynamic verification passing all unit tests.
- **Pluggable Analyzers**: Metrics (complexity, coupling) are isolated in modular analyzers, allowing easy adjustment of fitness priorities.
- **Pure Observability Log**: `delta_ledger.json` is a pure audit log and is entirely decoupled from optimization parameters or online decision loops.

---

## 2. The Evolutionary Pipeline

### v1 & v2: The Vector Scoring Engine
- **Concept:** Vector-space scoring and memory models (`adaptive_scorer.py`).

### v3: Topological Simulator (Structural Layer)
- **Concept:** Parse code into a probabilistic failure manifold (`topological_simulator.py`).

### v4 & v4.5: Temporal Drift & Causal Polarity
- **Concept:** Structural drift ($\Delta S$), Risk drift ($\Delta R$), debt velocity, and Causal Polarity delta (`temporal_engine.py`).

### v5 & v5.3: Causal Intervention & Minimax Solver (Control Layer)
- **Concept:** Bounded minimax solver identifying optimal structural rewrites under worst-case adversarial decay (`intervention_optimizer.py`).

### v5.4 & v5.5: Empirical Anchoring & Causal Attribution (Calibration Layer)
- **Concept:** Aligning model risk projections with empirical defect distributions via KL divergence and matched-subgraph ATE (`empirical_anchor.py`, `causal_attribution.py`).

### v6 & v6.1: Counterfactual Simulation & Policy Learning (Offline Optimization)
- **Concept:** Offline stochastic policy gradient engine ($\pi_\theta$) trained over branching counterfactual histories (`policy_learning.py`).

### v7.0: Structural Decision-Theoretic Controller (Unification Layer)
- **Concept:** Closed-loop controller orchestrating calibrations, policy gradients, and minimax intervention choices (`controller.py`).

### v7.9: CEST Metric Geometry & Consistency Axiom Layer (Mathematical Closure)
- **Concept:** Formalizing the program state space as a mathematically well-posed metric space ($\Delta CEST$).

### v8.0: Grounded Control System (POMDP Unification)
- **Concept:** Solves the self-referential Bayesian loop of earlier versions by establishing a dual-observation feedback control loop.

### v9.1: Grounded Program Graph Control System
- **Concept:** Establishes a clean separation of concerns by isolating predicted optimization costs ($J_{model}$) from empirical constraints ($R_{real}$).

### v9.2: Program Evolution Research System (The Microscope)
- **Concept:** Complete transition from self-referential optimal control loop metaphysics to a modular **Program Evolution Microscope**.
- **Model Channel**: Computes a linear fitness score based on pluggable AST complexity metrics (cyclomatic complexity, depth, LOC) and coupling intensity.
- **Reality Channel**: Enforces external unit test execution as a strict non-degradation gate (failed tests must equal zero).
- **Evolution Channel**: Implements a hill-climbing search across generations, running sandbox verification on rule-based mutations and committing only those that improve overall fitness.

---

## 3. Codebase Components (v9.2)

The active SYNAPSE codebase is located in `custom_protocols/skills/synapse/`:

### Core Analyzer & Mutation Layer (`synapse/core/`)
1. `graph_builder.py`: Extracts syntactic program graphs $G = (V, E)$ consisting of functions, classes, variables, and invocation dependencies from Python AST.
2. `analyzers.py`: Computes structural metrics:
   - `ComplexityAnalyzer`: Calculates cyclomatic complexity, AST depth, and LOC.
   - `CouplingAnalyzer`: Calculates degree centrality, coupling intensity, and coupling hotspots.
3. `mutator.py`: Implements rule-based, grammar-preserving AST mutations (structural splitting, state parameterization, exception boundaries, async normalization).
4. `fitness.py`: Computes linear program fitness score:
    $$F(G) = -1000 \cdot \text{tests\_failed} + 10 \cdot \text{test\_coverage} - 2 \cdot \text{complexity} - 1 \cdot \text{coupling}$$

### Runtime Verification Layer (`synapse/runtime/`)
5. `executor.py`: Executes tests in a sandboxed subprocess and performs call-path execution tracing.

### CLI Orchestrator (`synapse/experiments/`)
6. `evolver.py`: The task-driven command-line harness that runs the evolutionary optimizer, updates target source files, and records runs to the audit log.

---

## 4. Evolving Toward Self-Calibrating Pre-Execution Software Intelligence (v9.5 Concept)

To close the loop and solve the static/dynamic coupling and sparse sequence modeling limitations, the system evolves into a closed-loop feedback architecture:

### 1. Hybrid Semantic Coupling & Trace Weighting
Static coupling centrality ($K(N)$) is augmented with runtime edge profiling. Cyclomatic branches ($C(N)$) are weighted by trace execution frequency $W(e)$ gathered during test runs:
\[I'(N) = C_{\text{weighted}}(N) \times \ln(e + K_{\text{hybrid}}(N))\]

### 2. Probabilistic Execution Graphs (PEGs)
Static CFG reachability analysis is combined with actual trace transition patterns to construct PEGs, mapping static path constraints to actual runtime execution flows.

### 3. Weighted Mutation Kill Rate (MKR)
Mutations are tagged by severity (syntax, logic, control flow, state). Equivalent mutants are pruned using a $\Delta CEST$ semantic similarity threshold, resulting in a normalized, robust MKR.

### 4. Constraint-Guided CEST Fuzzing
CEST is fortified via structured, boundary-value input generators to maximize execution coverage ($Coverage_{CEST}$) rather than random fuzzed sampling.

### 5. Closed-Loop Self-Calibration Loop
The Experiment Governor records all predicted risks vs actual outcomes, computing the error distribution and dynamically updating scoring weights for $I$, $MKR$, and $\Delta CEST$.
