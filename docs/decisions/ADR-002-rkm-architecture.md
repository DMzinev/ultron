# ADR-002: Repository Knowledge Model (RKM) Core Architecture

## Status
Accepted

## Context
Static analysis tools are stateless and forget codebase state between runs.

## Decision
Establish an append-only Repository Knowledge Model (RKM) tracking file entities, AST symbols, dependencies, metrics, and constraint violations over time.

## Consequences
- Enables temporal trend detection and architectural drift tracking.
