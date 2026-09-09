# Phase 2.4 — Visual Hierarchy & Attention Audit

{
  "header_controls_count": 9,
  "primary_attention_competing_elements": [
    {
      "element": "#header-top",
      "issue": "9 distinct controls in header bar (Browse, Connect, Demo, Export, Watch, Help, Engine Dot, Search, Path) distract from central task."
    },
    {
      "element": "#active-project-bar",
      "issue": "Redundant 'Active Project 100% ANALYZED' banner sits between Hero Card and Current Work, creating a sandwich effect."
    },
    {
      "element": "#btn-current-work-action",
      "issue": "Action button 'Start Issue Discovery' visually clashes in color (cyan) with 'Send to Agent Context' (emerald green)."
    }
  ],
  "recommendations": [
    "Simplify header bar to primary workspace actions (Repo input + Connect/Scan + Demo). Move secondary tools (Export, Watch, Help) into a compact utility menu.",
    "Consolidate 'Active Project' metadata directly into the Current Work header to eliminate horizontal stripe clutter.",
    "Establish unambiguous primary CTA hierarchy: one dominant solid button for the next safe step."
  ]
}