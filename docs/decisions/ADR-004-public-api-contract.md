# ADR-004: Strict Public API Contract Decoupling

## Status
Accepted

## Context
Interfaces (CLI, REST server, Web dashboard) were directly importing core database engines, causing tight coupling.

## Decision
Route all interface interactions exclusively through `ultron.interfaces.api`.

## Consequences
- Prevents database leaks into UI components.
