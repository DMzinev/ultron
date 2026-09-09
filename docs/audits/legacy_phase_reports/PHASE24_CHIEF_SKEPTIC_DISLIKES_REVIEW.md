# Phase 2.4 — Chief Skeptic Review: 10 Things a Human Developer Would Dislike

[
  {
    "rank": 1,
    "complaint": "Top Navbar Clutter & Visual Noise",
    "detail": "9 controls in the top bar (Path, Browse, Connect, Demo, Export, Watch, Help, Engine Dot, Search) visually overwhelm the user upon opening the app before they can see the Hero Card or Current Work.",
    "fix": "Consolidate into 3 primary elements: Repository Path + Connect/Scan + Demo, moving secondary utilities into a dropdown."
  },
  {
    "rank": 2,
    "complaint": "Active Project Horizontal Stripe Sandwich",
    "detail": "The 'Active Project 100% ANALYZED' bar forms an unnecessary horizontal barrier between the Welcome Hero card and the Current Work card, adding visual friction without new actionable value.",
    "fix": "Merge project status badges directly into the Current Work header or sidebar."
  },
  {
    "rank": 3,
    "complaint": "Competing Action Button Colors in Current Work",
    "detail": "Current Work presents 4 action buttons with 3 distinct solid colors (Cyan 'Start Issue Discovery', Slate 'Diagnostic Detail', Emerald 'Send to Agent Context'), violating visual hierarchy so the user doesn't know which action is the primary next step.",
    "fix": "Use one solid primary accent button for the recommended next action; style other controls as subtle secondary outline buttons."
  },
  {
    "rank": 4,
    "complaint": "Technical McCabe Numbers Instead of Actionable Risk Decisions",
    "detail": "Risk hotspots are presented as analytical rows of cyclomatic complexity numbers rather than answering: 'What happens if I touch this?' and 'What should I ask an agent to do?'.",
    "fix": "Redesign Risk section into a Decision Surface with 1-click 'Create Mission' buttons and plain-language impact descriptions."
  },
  {
    "rank": 5,
    "complaint": "Structure Graph Lacks Visual Blast-Radius Impact Halo",
    "detail": "Clicking a node in the D3 graph simply opens a generic file info card instead of illuminating downstream dependents and dimming unaffected modules to show blast radius.",
    "fix": "Implement blast-radius highlighting: highlight downstream dependents in amber/red and dim unrelated nodes on selection."
  },
  {
    "rank": 6,
    "complaint": "Work Tab Lacks Visible Stepper Development Timeline",
    "detail": "The 7-stage development lifecycle (DISCOVERED -> SELECTED -> MISSION READY -> IMPLEMENTING -> OBSERVING -> VERIFYING -> CHECKPOINTED) is not visually visible as a progressive stepper timeline.",
    "fix": "Render a clean linear milestone stepper in the Work card showing active gate progression."
  },
  {
    "rank": 7,
    "complaint": "Agent Context Screen Looks Like a Raw Text Dump Rather Than a Compiler",
    "detail": "The Agent Context view displays an intimidating textarea rather than clearly delineated compiler output segments (Target, Why, Boundaries, Evidence, Verify).",
    "fix": "Format Agent Context as clean compiler cards with dedicated copy buttons per provider."
  },
  {
    "rank": 8,
    "complaint": "Verify Tab Focuses on Test Counts Rather Than 'Did It Make the Repo Better?'",
    "detail": "Verification displays test numbers and green badges without explaining the repository health delta: What got better? What got worse? What was preserved?",
    "fix": "Add explicit 'Repository Health Delta' summary: files improved, violations resolved, zero regressions."
  },
  {
    "rank": 9,
    "complaint": "Tiny 11px Muted Text and Unformatted Absolute Paths",
    "detail": "Long Windows file paths (`c:\\Users\\dimmiz\\...`) stretch across cards without middle truncation, and tiny 11px gray text strains readability.",
    "fix": "Apply middle-truncation (`.../core/orchestrator.py`) and enforce minimum 12px font size with WCAG AAA contrast."
  },
  {
    "rank": 10,
    "complaint": "Empty Canvas Without Direct Call-to-Action in Structure & Verify",
    "detail": "Before scanning, the Structure canvas and Verify file tree display blank or disabled text instead of a prominent 'Scan Repository' button in the center.",
    "fix": "Provide inviting empty-state illustrations with direct click-to-scan buttons in the center of unpopulated tabs."
  }
]