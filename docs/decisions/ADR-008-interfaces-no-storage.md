# ADR-008: Prohibition of Direct Storage Access in Interfaces

## Status
Accepted

## Context
Direct SQL queries in HTTP endpoint handlers break layer separation.

## Decision
Forbid direct database connections inside `ultron/interfaces/`.

## Consequences
- Clean architectural boundaries.
