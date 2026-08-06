# ADR-010: Modular Rule Pack Configuration

## Status
Accepted

## Context
Constraint rules must be configurable per repository without modifying engine code.

## Decision
Load rule packs from standard JSON schemas into the constraint engine.

## Consequences
- Declarative, extensible rule definitions.
