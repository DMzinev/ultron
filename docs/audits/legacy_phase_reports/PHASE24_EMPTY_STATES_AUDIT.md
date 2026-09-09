# Phase 2.4 — Empty States & Edge Cases Audit

{
  "empty_states_evaluated": [
    "Unanalyzed Repo",
    "No Issues",
    "No Tests",
    "No Git"
  ],
  "dislikes": [
    "When no issue is selected, Current Work card displays 'Repository Idle \u2014 Ready to discover next improvement' but doesn't explain how issues are discovered.",
    "Structure tab displays empty canvas if repository has not been scanned, without an explicit 'Click to Scan' button in the center.",
    "Verify tab file explorer displays 'Connect a repository' without linking directly to the connection input."
  ],
  "recommendations": [
    "Add explicit 'Scan Repository to Populate Architecture Graph' prompt in center of Structure canvas when empty.",
    "Add explanatory subtitle in Current Work explaining that Ultron parses AST complexity, coupling, and historical bugs to discover improvements.",
    "Make empty file tree in Verify tab clickable to switch to Overview and focus repo input."
  ]
}