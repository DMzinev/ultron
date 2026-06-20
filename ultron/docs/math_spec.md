# Mathematical Specification: Ultron System Impact & Contract Verification

This document specifies the mathematical formulations and heuristics used in the **Ultron Pre-Execution Intelligence Layer** to evaluate codebase modification risks.

---

## 1. System Impact Score ($I$)

For any Abstract Syntax Tree (AST) node $N$ (representing a function, method, or class) targeted for modification, we compute a continuous quantitative **System Impact Score $I(N)$**:

$$I(N) = \text{Complexity}(N) \times \ln(e + \text{Coupling}(N))$$

Where:
- $\text{Complexity}(N) \in \mathbb{Z}^+$ is the McCabe cyclomatic complexity score of the target node $N$:
  $$\text{Complexity}(N) = E - V + 2P$$
  *(where $E$ is the number of edges, $V$ is the number of vertices, and $P$ is the number of connected components in the control flow graph).*
- $\text{Coupling}(N) \in \mathbb{N}$ is the incoming degree centrality (the number of external modules/callers depending on node $N$):
  $$\text{Coupling}(N) = |\{ C \in \text{Codebase} \mid C \text{ imports or calls } N \}|$$
- $e$ is Euler's constant ($\approx 2.71828$), establishing the boundary condition:
  $$\text{Coupling}(N) = 0 \implies I(N) = \text{Complexity}(N)$$

---

## 2. Risk Categorization Tiers

Based on the value of $I(N)$, the targeted node is classified into one of three risk tiers, which dictate the strictness of the generated prompt instructions:

| Tier | Range | Heuristic Instruction |
| --- | --- | --- |
| **LOW** | $I(N) < 3.0$ | Isolated modification. Leaf node; safe to modify without caller updates. |
| **MEDIUM** | $3.0 \le I(N) < 10.0$ | Shared utility. Ensure backward-compatibility or update the caller list. |
| **HIGH** | $I(N) \ge 10.0$ | Critical system interface. Locked signature; do NOT change interface contracts without simultaneous refactoring of all callers. |

---

## 3. Static Argument Constraint Validation

Let function definition $F$ have arguments $A = \{a_1, a_2, \dots, a_n\}$ and default values $D = \{d_1, \dots, d_m\}$. We define the valid argument count bounds $[A_{min}, A_{max}]$ as:

$$A_{max} = |A|$$
$$A_{min} = |A| - |D|$$

For any call site $S$ querying $F$, passing $k$ positional arguments:
- If $k < A_{min}$ $\implies$ **Argument Underflow Error** (Contract violation).
- If $k > A_{max}$ $\implies$ **Argument Overflow Error** (Contract violation).

This check is executed statically by `guard.py` before runtime testing.

---

## 4. Probabilistic Anomaly Detection

To identify spelling slips and execution path violations before runtime, Ultron implements two statistical learning models:

### A. Normalized Levenshtein Spelling Similarity

Let $S_1$ be a called identifier and $S_2$ be a defined name in the repository. We define the normalized spelling similarity $\text{Sim}(S_1, S_2) \in [0, 1]$ as:

$$\text{Sim}(S_1, S_2) = 1.0 - \frac{\text{Levenshtein}(S_1, S_2)}{\max(|S_1|, |S_2|)}$$

Where $\text{Levenshtein}(S_1, S_2)$ is the minimum number of single-character edits (insertions, deletions, or substitutions) required to change $S_1$ into $S_2$.

A **Spelling Typo / Name Confusion** anomaly is flagged if there exists a defined identifier $S_2$ satisfying:

$$\text{Threshold}_{\text{typo}} \le \text{Sim}(S_1, S_2) < 1.0$$

*(where the default $\text{Threshold}_{\text{typo}} = 0.75$, configurable via `--typo-threshold`)*.

### B. Markovian Call Sequence Transition Probability

Let a method body contain an ordered sequence of function calls $(c_1, c_2, \dots, c_n)$. We model this as a first-order Markov Chain where the probability of transition from call $c_{i-1}$ to call $c_i$ is estimated from the repository baseline:

$$P(c_i \mid c_{i-1}) = \frac{\text{Count}(c_{i-1} \to c_i)}{\sum_{x} \text{Count}(c_{i-1} \to x)}$$

Where:
- $\text{Count}(c_{i-1} \to c_i)$ is the number of times $c_i$ is called immediately after $c_{i-1}$ inside any block in the baseline codebase.
- The denominator is the total number of transitions originating from $c_{i-1}$ in the baseline codebase.

A **Markov Causal Flow Anomaly** is flagged at call step $i$ if $c_{i-1}$ has known outgoing transitions in the baseline, but the actual transition probability satisfies:

$$P(c_i \mid c_{i-1}) \le \text{Threshold}_{\text{prob}}$$

*(where the default $\text{Threshold}_{\text{prob}} = 0.0$, configurable via `--prob-threshold`)*.
