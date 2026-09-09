---
name: tri-agent-council
description: >
  A 3-agent council consensus system for designing or implementing solutions.
  Three independent agents (three distinct pillars: Architecture & Correctness,
  Adversarial Skepticism & Safety, and Pragmatic Product Simplicity) evaluate
  the problem independently, show their complete reasoning and work, compare
  approaches, and pick or synthesize the strongest base version. If all three
  agree on the proposal, it is implemented; if any pillar disagrees, they
  deliberate and refine the proposal iteratively until consensus is achieved.
  Use whenever designing complex features, choosing architectural directions,
  or when the user requests 'council', 'three agents', 'three pillars', 'consensus',
  or 'tri-agent deliberation'.
argument-hint: '[design|implement|review]'
license: MIT
---

# Tri-Agent Council Consensus Protocol (The Three Pillars)

When facing non-trivial architectural, design, or implementation problems, never rely on a single perspective. Instead, convene the **Tri-Agent Council** where three distinct agents operate in isolated sessions, explore the solution space independently, show their work, and achieve unanimous consensus before execution.

---

## 1. The Three Pillars (Council Roles)

Each council member embodies a specialized, non-overlapping design perspective:

### Pillar 1: The Architect (System Integrity & Soundness)
- **Focus**: End-to-end correctness, clean abstractions, backwards compatibility, API contracts, type safety, and scalability.
- **Questions**:
  - Does this fit into the broader system architecture?
  - What are the upstream and downstream contract dependencies?
  - How does data flow from user interaction to storage and back?
- **Output**: Formal design specification with exact data structures, component boundaries, and signatures.

### Pillar 2: The Skeptic (Adversarial Safety & Failure Modes)
- **Focus**: Hostile edge cases, race conditions, silent errors, performance regressions, security boundaries, and bad assumptions.
- **Questions**:
  - Where will this fail in production?
  - What happens on empty, corrupted, or malicious input?
  - Are we making assumptions without empirical evidence?
- **Output**: Attack vectors, failure mode analysis, boundary test requirements, and defensive mitigation rules.

### Pillar 3: The Pragmatist (Simplicity, YAGNI & Product Usability)
- **Focus**: Ruthless simplicity (Ponytail ladder), deletion over addition, zero bloat, stdlib over dependencies, and first-time user ergonomics.
- **Questions**:
  - Can this be done in 10 lines instead of 200?
  - Are we building speculative scaffolding that isn't needed right now?
  - Will a developer understand and trust this without reading documentation?
- **Output**: Minimal viable implementation diff, complexity reduction targets, and usability verification checklist.

---

## 2. The 4-Stage Deliberation Workflow

### Stage 1: Independent Exploration (Zero Contamination)
- The main assistant spawns or delegates tasks to three distinct subagent roles representing each pillar.
- Each pillar produces its independent solution without seeing the other pillars' work beforehand.
- Every pillar must **show its work**: show concrete code snippets, call traces, edge-case tests, or data contracts.

### Stage 2: Council Plenum (Work Presentation & Synthesis)
- The three proposals are gathered and juxtaposed in a structured comparison matrix across core approach, code footprint, edge-case coverage, complexity rating, and trade-offs.

### Stage 3: Consensus Check
- **Consensus Rule**: A proposal is approved for implementation **only if all 3 pillars vote AGREE**.
- If any pillar raises an objection:
  - The objecting pillar must state the exact blocker.
  - The pillars iterate to refine the hybrid proposal by taking the strongest elements from each (e.g. adopting Pillar 3's minimal diff augmented with Pillar 2's failure guards and Pillar 1's clean signature).
  - Deliberate until full agreement is reached.

### Stage 4: Implementation & Verification Sign-Off
- Execute the agreed-upon synthesis.
- After code is written, all three pillars review the final diff:
  1. Architect verifies contract integrity.
  2. Skeptic verifies failure mode tests pass.
  3. Pragmatist verifies no dead code or speculative abstractions were added.
- Only then is the task considered complete.

---

## 3. Operational Directives
- **Never settle for an unverified single opinion**: When facing high-stakes architectural choices, invoke this council.
- **Transparent Reasoning**: Always present the three pillars' reasoning and the final consensus synthesis clearly to the user.
- **Bias toward action**: Consensus refinement should be sharp and focused (target <= 2 iteration turns).
