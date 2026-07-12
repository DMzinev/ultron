# Roadmap Corrections & Caveats Resolution

This document tracks historical caveats, quirks, and deviations in the development roadmap of Ultron, and their current resolution status.

---

## 1. Import-Mapping Collision in Design Oracle (Resolved)
*   **Deviation:** Alphabetical import-mapping collision bug in `get_import_mappings()` that corrupted the dependency graph by matching imports (e.g. `analyzer`) to scratch files (e.g. `scratch/create_analyzer_bak.py`) and breaking early, leading to incorrect metrics across the Design Oracle.
*   **Resolution:** Implemented symmetric filtering of `EXCLUDED_PATTERNS` across the codebase keys and introduced a rank-based matching heuristic (Exact, Suffix, Substring) to ensure robust import mapping within the production codebase bounds.

---

## 2. Windows BOM Parsing Compatibility (Resolved)
*   **Deviation:** Parsing errors on Windows systems due to UTF-8 Byte Order Mark (BOM) prefixes in configuration files (`pyproject.toml`) and source files.
*   **Resolution:** Modified all file-reading and AST-parsing operations across core and experimental modules to utilize `encoding="utf-8"` (and fallback gracefully to BOM-aware parsers) ensuring cross-platform stability.

---

## 3. Web UI Dashboard Traversals & Propagation (Resolved)
*   **Deviation:** Missing directory-level metric propagation (e.g. taking `max()` of child file risk levels) and potential directory traversal security vulnerabilities.
*   **Resolution:** Added path validation checks and traversal guards (preventing arbitrary path resolutions outside repository root) and implemented recursive max-metric propagation up the file tree UI hierarchy.

---

## 4. Package Initializer (`__init__.py`) Forced-HIGH Risk Quirk (Resolved)
*   **Deviation:** In early versions of Ultron, package initializers (`__init__.py`) and constructors (`__init__`) were unconditionally forced to `HIGH` risk, conflating architectural role/boundary with actual implementation risk (complexity and coupling).
*   **Resolution:** Removed the arbitrary `is_public` override from the risk scoring engine. Introduced a separate `boundary_type` metadata field (`"Package Initializer"`, `"Public API"`, `"Internal"`) to serialize and display role information independently in briefs and the UI heatmap tooltips, letting the risk tier reflect the true structural metrics.
