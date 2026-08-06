# ADR-011: Observation Data Pipeline & 4-Tier Audience Translation Model

## Status
Accepted

## Context
Ultron previously evolved multiple specialized engines (Analyzer, Risk Scoring, Constraint Engine, Evolution Engine, Recommendation Engine). This created conceptual weight and risk of mixing fact acquisition, storage, and derived interpretation.

## Decision
Refactor the core repository intelligence model around a 6-Layer Scientific Data Pipeline operating on a unified Observation entity model, accompanied by a 4-Tier Plain-Language Audience Translator:

### 1. The 6-Layer Scientific Observation Pipeline
1. Layer 1 (Discovery): Identifies physical repository structure (files, folders, packages, commits) without scoring or opinions.
2. Layer 2 (Extraction): Measures raw technical metrics (LOC, McCabe complexity, coupling, AST nodes, imports).
3. Layer 3 (Validation): Attaches confidence metrics to every extracted fact (e.g. 100% AST parsed, 42% heuristic).
4. Layer 4 (Normalization): Standardizes all observations into a single relational Observation schema (entity, property, value, unit, confidence, source, timestamp).
5. Layer 5 (Knowledge Graph): Maps graph relationships (imports, calls, belongs_to, owns).
6. Layer 6 (Interpretation): Derives constraint violations, health trends, and risk vectors dynamically from underlying observations rather than mutating stored facts.

### 2. The 4-Tier Plain-Language Audience Translator
Translates identical underlying observations into context-tailored explanations:
* Tier 1 (Raw): Metric values (McCabe Complexity: 18).
* Tier 2 (Developer): Actionable code-level impact (High decision branching; testing effort increases).
* Tier 3 (Engineering Manager): Maintenance & regression risk (Module maintenance cost increasing; prioritize refactoring).
* Tier 4 (Founder / Executive): Business & velocity impact (Feature delivery velocity will degrade if complexity accumulates).

## Consequences
- Elevates Ultron into a trustworthy scientific repository instrument.
- Eliminates engine sprawl by aligning modules into a single pipeline flow: Collectors -> Validators -> Normalizers -> Storage -> Rules -> Interpreters -> Translators -> Interfaces.
- Decouples AI generation from deterministic fact extraction; AI functions strictly as a consumer/translator of normalized observations.
