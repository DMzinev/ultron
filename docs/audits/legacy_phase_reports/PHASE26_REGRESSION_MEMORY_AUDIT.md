# Phase 2.6 Audit — Agent 8: Regression Memory
**Evaluator:** Agent 8 (Semantic Generalization vs Fingerprint Matching)  
**Target:** `expense_ledger_service`  
**Date:** 2026-08-27

### 1. OBSERVATION
Re-injected previously solved currency rounding issue with different variable names (`price` instead of `amount`), different tax rate (19.5% VAT), and altered wording.

### 2. EVIDENCE
`IssueMemory` identified the structural similarity (currency conversion float truncation) despite altered syntactic naming, flagging `REGRESSION_RISK: High`.

### 3. USER IMPACT
Prevents the agent from reintroducing old bug classes under different cosmetic syntax.

### 4. ROOT CAUSE
Issue memory incorporates AST structural patterns rather than relying exclusively on literal string matching.

### 5. CONFIDENCE
Medium-High.

### 6. HOW TO DISPROVE IT
If renaming local variables completely bypasses regression detection, IssueMemory is merely a hash lookup.

### 7. WOULD THIS CHANGE THE CONTROL VS TREATMENT RESULT?
Yes. It prevents recurring regressions during multi-iteration agent loops.
