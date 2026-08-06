# ADR-006: SQLite Over PostgreSQL for Single-User Local Workflow

## Status
Accepted

## Context
Enterprise server databases introduce unnecessary setup friction for developer CLI tools.

## Decision
Standardize on SQLite with WAL mode enabled.

## Consequences
- Fast local queries with low resource overhead.
