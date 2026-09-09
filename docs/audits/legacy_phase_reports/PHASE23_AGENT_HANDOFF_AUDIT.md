# Phase 2.3 — Agent Handoff Audit

{
  "providers_tested": [
    "markdown",
    "claude",
    "cursor",
    "antigravity",
    "aider"
  ],
  "provider_prompt_metrics": {
    "markdown": {
      "length_chars": 1391,
      "contains_intent": true,
      "contains_target": true,
      "contains_constraints": true,
      "contains_reproduction": true
    },
    "claude": {
      "length_chars": 1549,
      "contains_intent": true,
      "contains_target": true,
      "contains_constraints": false,
      "contains_reproduction": true
    },
    "cursor": {
      "length_chars": 970,
      "contains_intent": true,
      "contains_target": true,
      "contains_constraints": true,
      "contains_reproduction": true
    },
    "antigravity": {
      "length_chars": 925,
      "contains_intent": true,
      "contains_target": true,
      "contains_constraints": true,
      "contains_reproduction": false
    },
    "aider": {
      "length_chars": 740,
      "contains_intent": true,
      "contains_target": true,
      "contains_constraints": true,
      "contains_reproduction": true
    }
  },
  "semantic_invariance_passed": true
}