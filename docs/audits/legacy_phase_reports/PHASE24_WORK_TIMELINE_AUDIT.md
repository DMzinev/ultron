# Phase 2.4 — Work & Development Timeline Audit

{
  "lifecycle_states": [
    "DISCOVERING",
    "ISSUE_SELECTED",
    "MISSION_READY",
    "IMPLEMENTING",
    "OBSERVING",
    "VERIFYING",
    "CHECKPOINT_READY",
    "CHECKPOINTED",
    "REPAIR_REQUIRED",
    "BLOCKED"
  ],
  "dislikes": [
    "The Work tab renders active work as a single static card rather than a visible linear development timeline showing progression through the 7 lifecycle gates.",
    "Past development attempts are hidden inside a JSON debug toggle ('Attempt Details & Operational Telemetry') rather than a clean chronological attempt history.",
    "When state is BLOCKED, the recovery action ('Rollback & Reset') looks destructive rather than guiding safe recovery."
  ],
  "recommendations": [
    "Render a visible stepper timeline: DISCOVERED -> SELECTED -> MISSION READY -> IMPLEMENTING -> OBSERVING -> VERIFYING -> CHECKPOINTED.",
    "Replace raw JSON attempt drawer with clean visual attempt cards.",
    "Clarify BLOCKED state with step-by-step diagnostic recovery guidance."
  ]
}