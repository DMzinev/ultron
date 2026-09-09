# Phase 2.4 — Typography, Spacing & Layout Audit

{
  "viewport_tested": "1440x900 (standard desktop)",
  "dislikes": [
    "Inconsistent font hierarchy: card titles use h3 with heavy bold, but secondary metadata uses tiny 11px muted gray text that fails readability at distance.",
    "Excessive horizontal scrolling or tight clipping on long file paths in the Current Work card (`c:\\Users\\dimmiz\\...`).",
    "Button group in Current Work has 4 buttons with 3 different background shades (cyan, slate, emerald), creating visual competition."
  ],
  "recommendations": [
    "Standardize typography: minimum 12px for metadata, clear 14px body, 18px card headers.",
    "Truncate long absolute paths with middle ellipsis (`.../pipeline/orchestrator.py`) and full tooltip on hover.",
    "Unify button group styling with one dominant primary CTA and consistent secondary outlines."
  ]
}