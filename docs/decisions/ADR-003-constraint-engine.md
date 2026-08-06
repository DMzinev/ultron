# ADR-003: Stateless Constraint Engine Plugin Design

## Status
Accepted

## Context
Architecture rule enforcement must be deterministic and reproducible.

## Decision
Design rule evaluators as stateless plugins accepting fact metrics and returning structured `RkmViolation` evidence objects.

## Consequences
- Side-effect free rule execution.
