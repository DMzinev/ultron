# ADR-007: Append-Only RKM Evaluation History

## Status
Accepted

## Context
Overwriting past analysis runs destroys historical lineage.

## Decision
Treat analysis run records as immutable append-only history.

## Consequences
- Preserves full audit log of codebase evolution.
