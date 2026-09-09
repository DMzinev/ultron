# Phase 2.4 — Structure & Impact Graph Audit

{
  "graph_interaction_model": "D3 force-directed SVG network",
  "node_click_behavior": "Populates file inspector drawer on the right",
  "dislikes": [
    "Node click shows generic file metrics (lines, complexity, coupling) instead of answering: 'What happens if I touch this?' and 'What may break?'.",
    "Graph lacks blast-radius visual halo: clicking a node should immediately illuminate downstream dependents and dim unrelated nodes.",
    "No direct 'Give this to an Agent' button inside the node inspection card."
  ],
  "recommendations": [
    "When a node is selected, render: THIS FILE -> WHY IT MATTERS -> WHAT IT AFFECTS -> WHAT MAY BREAK -> WHAT TO ASK AGENT TO DO.",
    "Implement visual blast-radius glow on downstream dependencies upon node selection.",
    "Add 'Compile Mission for Node' directly inside node inspector."
  ]
}