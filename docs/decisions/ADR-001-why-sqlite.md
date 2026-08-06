# ADR-001: Why SQLite for Repository Knowledge Model (RKM)

## Status
Accepted

## Context
Ultron requires a persistent, relational store for software facts, AST symbols, dependency edges, metrics, and constraint violations across analysis runs.

## Decision
Use local embedded SQLite (`.ultron/repository.db`) as the primary database storage engine.

## Consequences
- Zero-config deployment without requiring external database servers (e.g. Postgres).
- Embedded transactional integrity and historical snapshot lineage.
