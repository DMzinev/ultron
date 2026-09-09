Below is a product + architecture review of Ultron from the perspective of making it feel like a serious engineering workstation: closer to JetBrains, Datadog, Linear, Sentry, and Sourcegraph than a generic analytics dashboard.

---

# 1. Overall Product Direction

Ultron should not feel like a “dashboard with charts.”

It should feel like an **architecture cockpit**:

- persistent project state
- inspectable evidence
- stable visual continuity
- progressive loading
- trustworthy scoring
- local-first AI assistance
- fast navigation between risk, code, history, and remediation

The core product promise should be:

> “Ultron continuously maps your architecture, explains architectural risk, and suggests refactorings with evidence.”

That means every visual component should answer one of these:

1. **What is happening?**
2. **Why does it matter?**
3. **Where in the code is the evidence?**
4. **What should I do next?**
5. **How confident is Ultron?**

---

# 2. Recommended Visual Layout

## High-Level Layout

Use a dense engineering-tool layout:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Top Command Bar                                                              │
│ Repo Selector | Branch | Scan Status | Omnibar | Mode | Watch | Local AI     │
├───────────────┬──────────────────────────────────────────────────────────────┤
│ Left Sidebar  │ Main Workspace                                               │
│               │                                                              │
│ Navigation    │ 1. Repo Health Header                                         │
│ Scan Status   │ 2. Risk Overview Strip                                        │
│ Local AI      │ 3. Primary Investigation Area                                 │
│ Policies      │ 4. Evidence + Recommendations Panel                          │
│ History       │                                                              │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

The current dashboard structure is strong, but I would reorganize it around **triage first, analysis second, remediation third**.

---

# 3. Top Command Bar

The top command bar should be compact, always visible, and status-oriented.

## Recommended Structure

```text
[Ultron] [repo-name ▾] [branch ▾] [scan: complete / indexing / stale] 
[⌘K Search anything...] 
[Architecture Mode ▾] [Watch: On] [Local AI: Ollama Connected] [User/Settings]
```

## Required Behaviors

### Repo Selector

Should show:

- repository name
- branch
- last scan time
- dirty/stale indicator
- scan source: local / CI / uploaded snapshot

Example:

```text
payment-platform
main
Last scan: 4m ago
1,284 files indexed
Confidence: 87%
```

### Scan Status

Do not hide this in a sidebar only. Developers need constant feedback.

Use statuses like:

- `Idle`
- `Indexing files`
- `Parsing AST`
- `Building dependency graph`
- `Computing metrics`
- `Generating AI suggestions`
- `Complete`
- `Stale`
- `Offline`
- `Failed with partial results`

### Omnibar

The command bar should support:

- open file/module
- search symbol
- jump to risk
- run scan
- ask local AI
- explain metric
- filter graph
- compare with previous scan

Example commands:

```text
> Show god objects
> Explain risk score for AuthService
> Compare architecture drift since last week
> Run policy checks
> Focus graph on billing module
```

---

# 4. Left Sidebar

The sidebar should not just be navigation. It should be an operational console.

## Recommended Sections

```text
Architecture
  Overview
  Topology
  Risk Matrix
  Modularity
  Drift History

Remediation
  Refactoring ROI
  Anti-Patterns
  Policy Violations
  AI Suggestions

System
  Scan Pipeline
  Data Sources
  Local AI
  Settings
```

## Status Panel at Bottom

Add a persistent bottom sidebar status module:

```text
Repository Status
● Watch active
● Local cache ready
● Ollama connected
● 1,284 files indexed
● 92 modules detected
Last scan: 4m ago
```

If something breaks, users should not be confused.

Bad:

```text
blank cards
```

Good:

```text
Dependency graph unavailable
Using cached scan from 14:32
Reason: AST parser timed out on 3 files
[Retry graph build] [View logs]
```

---

# 5. Main Dashboard Information Hierarchy

Your current Hero Section is good, but it should become more structured.

## Recommended Main Overview Layout

```text
┌────────────────────────────────────────────────────────────────────┐
│ Repo Health Header                                                  │
│ Health Score | Risk Trend | Confidence | Last Scan | Scan Coverage  │
├────────────────────────────────────────────────────────────────────┤
│ Top Risk Forces                                                     │
│ Coupling ↑ | Complexity ↑ | Policy Violations | Drift ↑ | Hotspots  │
├───────────────────────────────┬────────────────────────────────────┤
│ System Topology                │ Risk Matrix                         │
│ large visual canvas            │ sortable, evidence-backed table     │
├───────────────────────────────┼────────────────────────────────────┤
│ Modularity Scorecard           │ Refactoring ROI                      │
├───────────────────────────────┼────────────────────────────────────┤
│ Anti-Pattern Alerts            │ Governance Policy Checks             │
├───────────────────────────────┴────────────────────────────────────┤
│ Historical Drift Timeline                                           │
└────────────────────────────────────────────────────────────────────┘
```

## Important Change

The **System Topology** should be the main visual anchor, not just another card.

Make it large, interactive, and investigatory.

For example:

- left 60%: topology graph
- right 40%: selected node inspector or risk table

```text
┌─────────────────────────────────────────────┬──────────────────────┐
│                                             │ Selected Module       │
│         Dependency Graph                    │ AuthService           │
│                                             │ Risk: High            │
│                                             │ Instability: 0.72     │
│                                             │ Incoming: 31          │
│                                             │ Outgoing: 18          │
│                                             │ Violations: 4         │
│                                             │                      │
│                                             │ [Open Evidence]       │
│                                             │ [Ask Local AI]        │
└─────────────────────────────────────────────┴──────────────────────┘
```

---

# 6. Hero Section Recommendations

## Health Score Gauge

Avoid a decorative gauge that consumes too much space. Engineering tools need density.

Use a compact but expressive health block:

```text
Architecture Health
78 / 100
▲ +4 since previous scan
Confidence: High, 91%
Coverage: 1,284 / 1,301 files
```

Use a small radial gauge or horizontal segmented bar.

## Top Risk Forces

This should be one of the most important areas.

Example:

```text
Top Risk Forces

1. Coupling concentration in billing-core
   38 incoming dependencies · affects 14 modules

2. God object detected: OrderProcessor
   2,410 LOC · 47 methods · 19 responsibilities

3. Layer violation: api → persistence
   12 violations · Clean Architecture breach

4. Semantic drift in auth/session modules
   Naming and responsibility mismatch increasing over 4 scans
```

Each risk item should have:

- severity
- confidence
- affected files/modules
- trend
- CTA

Example CTAs:

- `Inspect`
- `Show evidence`
- `Generate refactoring plan`
- `Suppress`

---

# 7. Make Insights Trustworthy

This is critical. AI architecture tools fail when they feel mystical.

Every score should expose evidence.

## Add an “Evidence Drawer”

When a user clicks a metric, open a right-side drawer.

```text
Risk Evidence: OrderProcessor

Risk: Critical
Confidence: 93%

Signals:
✓ LOC: 2,410
✓ Cyclomatic complexity: 187
✓ Fan-in: 33
✓ Fan-out: 21
✓ Methods: 47
✓ Semantic clusters: payment, inventory, shipping, notification

Files:
- src/orders/OrderProcessor.ts
- src/orders/paymentHandlers.ts
- src/inventory/reservation.ts

Why Ultron flagged this:
This class mixes order orchestration, payment, inventory reservation,
email notification, and shipment allocation.

Recommended next step:
Extract PaymentCoordinator and InventoryReservationService.
```

## Add Confidence Explanations

Confidence metrics should not just be numbers.

Use this:

```text
Confidence: 87%

High confidence because:
- 98% of files parsed successfully
- dependency graph complete
- AST metrics available
- 3 historical scans available

Confidence reduced by:
- 17 generated files excluded
- 4 files failed parsing
- local AI unavailable during recommendation phase
```

This makes the system feel honest.

---

# 8. Risk Matrix Table Improvements

The Risk Matrix should be more than sortable rows. It should be the operational triage table.

## Recommended Columns

```text
Module
Risk
Trend
Complexity
Coupling
Instability
Policy
Anti-patterns
Confidence
Owner
Actions
```

Example row:

```text
OrderProcessor   Critical   ↑ +12%   187   54 deps   0.82   3 violations   God Object   93%   Platform   Inspect
```

## Table Features

Add:

- saved filters
- severity chips
- trend arrows
- evidence count
- owner/team column
- suppress / ignore with reason
- export to GitHub issue / Linear / Jira
- compare with previous scan

## Do Not Use Only Color

Use labels and icons because developers may use dark mode, low contrast, or colorblind settings.

Bad:

```text
red row only
```

Good:

```text
[Critical] Coupling spike ↑ 23%
```

---

# 9. System Topology Graph

Force-directed graphs can look impressive but often become unusable at 1,000+ files.

You need progressive abstraction.

## Recommended Graph Levels

Let users switch between:

1. **System View**
   - services/domains/packages only
2. **Module View**
   - modules/classes/components
3. **File View**
   - individual files
4. **Symbol View**
   - classes/functions/interfaces, optional

Default should not be file-level. For large repos, default to system or module clusters.

## Graph Visual Encoding

Use:

- node size = complexity or LOC
- node color = risk
- node border = confidence
- edge thickness = dependency weight
- edge color = violation type
- dashed edge = inferred/low-confidence relationship
- halo/glow = recently changed/hotspot
- lock icon = governed/policy-protected module

## Graph Controls

Add a graph toolbar:

```text
[Layout: Force/Hierarchical/Radial] [Group by: Domain/Folder/Team]
[Filter: Risk ≥ High] [Show violations] [Show cycles] [Reset]
```

## Selected Node Inspector

Clicking a node should open an inspector:

```text
Module: billing-core

Health: 61
Risk: High
Complexity: 142
Instability: 0.76
Fan-in: 29
Fan-out: 34
Cycles: 3
Policy violations: 5

Top dependencies:
- payments
- invoices
- users

Actions:
[Open files]
[Show cycles]
[Ask AI for refactor plan]
[Create issue]
```

---

# 10. Modularity Scorecard

Martin’s Instability vs Distance from Main Sequence is useful, but many developers will not intuitively understand it.

## Recommended Design

Show the chart, but pair it with explanation.

```text
Architectural Modularity

Modules far from the main sequence are either:
- too abstract and unused
- too concrete and overly depended upon

Highest concern:
1. billing-core
2. auth-session
3. notification-engine
```

## Chart Enhancements

- label only outliers by default
- add hover tooltips
- show quadrants
- provide “why this matters”
- add “show only high-risk modules”
- add “trend over time” ghost points

Tooltip example:

```text
billing-core
Instability: 0.82
Abstractness: 0.11
Distance: 0.71

Interpretation:
Highly unstable and concrete. This module changes often and depends on many others.
```

---

# 11. Refactoring ROI Scorecard

This should feel practical and actionable.

## Recommended Fields

```text
Refactoring Opportunity

Extract PaymentCoordinator
Risk Reduction: High
Estimated LOC Reduction: 420
Complexity Delta: -38
Affected Modules: 4
Confidence: 81%
Effort: Medium
Blast Radius: Low

[View Plan] [Ask Local AI] [Create Branch Task]
```

## Add an Effort vs Impact Matrix

```text
High Impact
│       [OrderProcessor split]
│
│  [Billing dependency inversion]
│
└──────────────────────── High Effort
```

Prioritize by:

- risk reduction
- developer effort
- confidence
- blast radius
- test coverage availability

---

# 12. Anti-Pattern Alerts

Anti-pattern detection needs examples and context.

## Recommended Alert Format

```text
God Object Detected
OrderProcessor.ts

Severity: Critical
Confidence: 93%

Why:
- 2,410 LOC
- 47 methods
- 19 semantic responsibilities
- participates in 3 dependency cycles

Suggested action:
Split into OrderOrchestrator, PaymentCoordinator, InventoryReservationService.

[Show Evidence] [Generate Refactor Plan] [Suppress]
```

Add “semantic responsibility clusters”:

```text
Responsibilities detected:
- payment authorization
- inventory reservation
- shipping calculation
- notification
- refund handling
```

This makes semantic drift visible.

---

# 13. Governance Policy Checks

This should feel like CI/CD for architecture.

## Recommended Design

```text
Policy Checks

Clean Architecture
Failed
12 violations

Rules:
✓ domain must not depend on infrastructure
✕ api must not depend directly on persistence
✕ application must not import framework adapters
```

Each violation should include:

```text
api/controllers/UserController.ts imports db/UserRepository.ts

Rule:
API layer cannot depend directly on persistence.

Suggested fix:
Introduce UserService interface in application layer.
```

Add:

- severity
- rule ownership
- waiver/suppression with expiry
- “block merge” compatibility
- config preview

---

# 14. Time-Travel Historical Drift Graph

This is a key differentiator if done well.

## Recommended Timeline

Show architecture health over time, plus major events.

```text
Architecture Drift

Health Score
90 ┤          ●
80 ┤    ●  ●     ●
70 ┤ ●            ●
60 ┤                 ●
    Jan Feb Mar Apr May

Events:
- New payment module added
- Coupling spike in billing-core
- Policy violations introduced
- Refactor reduced complexity by 18%
```

## Add Compare Mode

Allow:

```text
Compare current scan with:
- previous scan
- last week
- last release
- selected Git commit
```

Output:

```text
Since last release:
+ 14 new dependencies
+ 3 new cycles
+ 2 policy violations resolved
- Health score dropped from 82 to 76
```

---

# 15. Solving Rendering Continuity Problems

Your current issue is likely a combination of:

- expensive graph rendering
- SPA rehydration race conditions
- localStorage size/serialization limits
- blocking main thread parsing
- data unavailable during React/Vue/Svelte render
- WebSocket reconnect assumptions
- no durable scan snapshot layer
- cards rendering before data contracts are satisfied

The UX principle:

> The user should always see either stable cached data, a skeleton, a partial result, or an explicit recoverable state. Never a blank card.

---

# 16. Data Architecture for Continuity

## Do Not Rely on localStorage for Large Repo State

For 1,000+ files, localStorage is too limited and synchronous.

Use:

- **IndexedDB** for scan snapshots
- localStorage only for tiny UI preferences
- Service Worker Cache for static assets
- in-memory store for active session
- Web Worker for parsing/transforming large graph payloads

Recommended persistence layers:

```text
Memory Store
Fast active UI state

IndexedDB
Durable scan snapshots, graph data, metrics, table rows

localStorage
Theme, sidebar width, selected repo id, last route

Service Worker Cache
App shell, static assets, offline fallback
```

## Store Versioned Scan Snapshots

Each scan should produce a durable snapshot:

```ts
type ScanSnapshot = {
  id: string;
  repoId: string;
  branch: string;
  commitSha?: string;
  createdAt: string;
  status: "complete" | "partial" | "failed";
  schemaVersion: number;

  summary: HealthSummary;
  topology: GraphSummary;
  riskMatrix: RiskRow[];
  modularity: ModularityPoint[];
  refactoring: RefactoringOpportunity[];
  policies: PolicyViolation[];
  drift: DriftPoint[];

  confidence: ConfidenceReport;
  errors?: ScanError[];
};
```

On reload:

1. render app shell immediately
2. load latest snapshot from IndexedDB
3. render cached snapshot with “cached” indicator
4. reconnect to backend/local scanner
5. refresh cards progressively
6. replace stale data atomically

---

# 17. Card-Level State Machine

Every analytical card should have a formal state machine.

Avoid simple `isLoading`.

Use:

```ts
type CardState =
  | "empty"
  | "loading"
  | "hydrating"
  | "cached"
  | "partial"
  | "ready"
  | "stale"
  | "error"
  | "offline";
```

Each card should render something meaningful in every state.

## Example

```text
System Topology

Hydrating cached graph...
Showing scan from 14:32
[small skeleton overlay]

or

Partial graph available
892 / 1,284 files analyzed
Parser failed on 7 files
[View errors] [Retry]
```

---

# 18. Loading Skeleton Patterns

Use skeletons that match the final layout exactly.

Bad:

```text
spinner in empty card
```

Good:

```text
graph card shows faint placeholder nodes and edges
risk table shows rows with skeleton chips
scorecard shows placeholder metric blocks
timeline shows muted line skeleton
```

## Suggested Skeletons

### Health Score

```text
[large shimmering number placeholder]
[small trend placeholder]
[confidence bar placeholder]
```

### Graph

Show:

- faded node circles
- faint connecting lines
- toolbar disabled
- status pill: `Building topology…`

### Table

Show:

- 8 to 12 skeleton rows
- skeleton badges
- fixed headers already visible

### Alerts

Show:

- alert card placeholders
- severity chip placeholders
- evidence count placeholders

---

# 19. Progressive Rendering Strategy

Do not wait for everything.

Prioritize:

1. App shell
2. latest cached health summary
3. risk table summary
4. topology metadata
5. graph clusters
6. full graph
7. AI suggestions

Recommended order:

```text
0-100ms: app shell
100-300ms: cached header + stale badge
300-800ms: summary cards
800-1500ms: tables
1500ms+: graph canvas and expensive visualizations
```

For the graph:

- render clusters first
- lazy-render edges
- use canvas/WebGL for large graphs
- use virtualization for inspectors and tables
- avoid rendering 1,000+ SVG nodes in React DOM

Use libraries like:

- Sigma.js
- Cytoscape.js
- PixiJS
- React Flow only for smaller structured graphs
- WebGL-based renderers for large dependency maps

---

# 20. Prevent Blank Cards

## Add Error Boundaries Per Card

Each card should be isolated.

```text
If topology graph fails, risk matrix should still render.
If AI suggestions fail, policy checks should still render.
```

Use:

- route-level error boundary
- dashboard-level error boundary
- card-level error boundary
- graph renderer error boundary

Error card example:

```text
Topology renderer crashed
Your scan data is safe.

Likely cause:
Graph exceeded renderer memory limit.

[Reload graph] [Switch to cluster view] [View logs]
```

## Atomic Data Replacement

Never clear old data before new data arrives.

Bad:

```ts
setGraph(null)
fetchNewGraph()
setGraph(newGraph)
```

Good:

```ts
setGraphState({ status: "refreshing", data: previousGraph })
const next = await fetchNewGraph()
setGraphState({ status: "ready", data: next })
```

Visually:

```text
Showing previous scan while refreshing...
```

---

# 21. Reconnection UX

When users switch tabs or reload, show explicit reconnection states.

## Top Bar Indicator

```text
Scanner: reconnecting...
Using cached results
```

Then:

```text
Scanner connected
Refreshing changed files...
```

If failed:

```text
Scanner unavailable
Showing cached scan from 14:32
[Reconnect] [Open local scanner setup]
```

Do not make the user manually reconnect without guidance.

---

# 22. Offline-First Architecture

A strong offline architecture for Ultron:

```text
Browser UI
  ↓
IndexedDB Snapshot Store
  ↓
Local Scanner Service / WASM Parser / Backend Agent
  ↓
Optional Local AI Providers
  - Ollama
  - LM Studio
  - OpenAI-compatible local endpoint
```

## Offline States

Make these first-class:

- `Online with scanner`
- `Offline using cached snapshot`
- `Scanner unavailable`
- `Local AI unavailable`
- `AI suggestions cached`
- `Partial scan available`

Use small pills:

```text
[Offline Mode] [Cached Scan] [AI: Local]
```

---

# 23. Local AI Assistance

Your offline AI goal is excellent and aligned with developer trust.

## UX Principle

Local AI should be transparent:

```text
Local AI
Connected to Ollama
Model: qwen2.5-coder:7b
Context: 18 files
Telemetry: off
```

## Provider Settings

Support:

```text
Provider
○ Ollama
○ LM Studio
○ OpenAI-compatible local endpoint
○ Custom proxy

Endpoint
http://localhost:11434

Model
qwen2.5-coder:7b

Privacy
✓ No cloud telemetry
✓ Prompts stay local
✓ Code snippets never leave device
```

## Local AI Panel

Add a right-side assistant panel, not a modal.

```text
Ask Ultron Local AI

Context:
- OrderProcessor.ts
- billing-core graph cluster
- 3 policy violations
- latest risk evidence

Prompt:
"Suggest a safe refactoring plan that reduces coupling."

[Generate Plan]
```

## AI Output Format

Do not output vague suggestions. Force structured recommendations:

```text
Refactoring Plan

Goal:
Reduce OrderProcessor responsibilities from 5 to 2.

Steps:
1. Extract PaymentCoordinator
2. Extract InventoryReservationService
3. Introduce OrderWorkflow interface
4. Add integration tests around order placement

Expected effect:
- Complexity: -38
- LOC moved: 420
- Dependency cycles: -2

Risks:
- Payment side effects are poorly isolated
- Requires regression tests for refund flow

Files to inspect:
- src/orders/OrderProcessor.ts
- src/payments/PaymentGateway.ts
```

## Trust Controls

Add:

- model name
- provider
- prompt context preview
- confidence disclaimers
- “view evidence used”
- “copy as Markdown”
- “create issue”
- “never sent to cloud” indicator

---

# 24. Visual Language

## Dark Theme

Use dark mode with disciplined contrast.

Recommended palette:

```text
Background:       #0B0F14
Panel:            #111821
Panel elevated:   #151E2A
Border:           #263241
Text primary:     #E6EDF3
Text secondary:   #94A3B8
Muted:            #64748B

Success:          #22C55E
Warning:          #F59E0B
Danger:           #EF4444
Critical:         #F43F5E
Info:             #38BDF8
AI Accent:        #A78BFA
```

## Card Styling

Cards should look technical, not flashy.

Use:

- subtle borders
- low-shadow elevation
- dense spacing
- visible card headers
- status pills
- consistent toolbar placement

Card header example:

```text
System Topology                         [Cluster View ▾] [Risk ≥ High] [⋯]
Dependency graph generated from 1,284 files · Confidence 91%
```

---

# 25. UI Components to Add

## 1. Global Scan Pipeline Indicator

Show pipeline progress:

```text
Scan Pipeline

✓ Files discovered       1,284
✓ AST parsed             1,271
✓ Dependencies mapped    4,892
✓ Metrics computed       92 modules
◐ AI suggestions         6 / 12
```

This solves anxiety during long scans.

## 2. Evidence Drawer

Mandatory for trust.

## 3. Node Inspector

Mandatory for graph usability.

## 4. Snapshot Switcher

Allow users to switch between scans:

```text
Current scan
Previous scan
Last release
Commit abc123
```

## 5. Issue Export

Refactoring findings should become work items.

Support:

- Markdown copy
- GitHub issue
- Linear
- Jira

## 6. Suppression/Waiver System

Architectural tools need noise control.

```text
Suppress violation
Reason: Accepted legacy boundary
Expires: 30 days
Owner: Platform Team
```

## 7. Confidence Explainer

A reusable component for every AI/risk score.

## 8. “Why am I seeing this?” Tooltip

For every alert and score.

---

# 26. Recommended Empty States

Do not show blank cards.

## No Repo Selected

```text
Connect a repository to begin architecture analysis.

[Select local repo] [Upload scan snapshot] [Open demo project]
```

## Scan Not Run

```text
No architecture scan yet.

Run a local scan to generate topology, risk scores, and policy checks.
[Run scan]
```

## Local AI Unavailable

```text
Local AI unavailable

Ultron can analyze architecture without AI, but refactoring suggestions
require a local model provider.

[Connect Ollama] [Connect LM Studio] [Use without AI]
```

## Partial Results

```text
Partial scan available

1,271 of 1,284 files analyzed.
13 files were skipped or failed parsing.

[View skipped files] [Retry failed files]
```

---

# 27. Engineering Recommendations

## Frontend State

Use a durable query/cache architecture:

- TanStack Query for server/local API data
- Zustand/Jotai for UI state
- IndexedDB via Dexie
- XState or explicit reducers for scan/card state machines

## Web Workers

Move expensive work off the main thread:

- graph normalization
- layout preprocessing
- large JSON parsing
- metric aggregation
- diff computation

## Virtualization

Use:

- virtualized tables
- virtualized lists
- canvas/WebGL graph rendering
- lazy loading for historical data

## Schema Versioning

Every cached snapshot must have a schema version.

On app boot:

```text
Found cached snapshot v2
Current schema v3
Migrating...
```

If migration fails:

```text
Cached snapshot is incompatible
[Rescan repository] [Export old snapshot]
```

---

# 28. Ideal Reload Experience

The reload experience should look like this:

1. User presses F5.
2. App shell appears immediately.
3. Top bar says:

```text
Hydrating cached workspace...
```

4. Cards show last known data with subtle stale badges:

```text
Showing cached scan from 14:32
```

5. Scanner reconnects:

```text
Local scanner connected
Checking for file changes...
```

6. Only changed cards refresh.
7. No blank states.
8. If graph is slow, show cached graph and overlay:

```text
Refreshing topology layout...
```

This is the standard to aim for.

---

# 29. Most Important Product Improvements

If I had to prioritize, I would do these first:

1. **Replace localStorage cache with IndexedDB scan snapshots**
2. **Add per-card state machines**
3. **Render cached data before live reconnect**
4. **Add evidence drawer for every risk**
5. **Make topology graph cluster-first, not file-first**
6. **Add scan pipeline status**
7. **Add local AI connection status and provider settings**
8. **Add explicit partial/stale/offline states**
9. **Use Web Workers for graph and metric processing**
10. **Add confidence explanations**

---

# 30. Final Recommendation

Ultron has the right feature surface, but the next level is not more charts. The next level is **operational trust**.

The app should constantly communicate:

- what data it has
- how fresh that data is
- how confident it is
- what evidence supports each conclusion
- what the developer can do next
- whether analysis is local, cached, partial, or live

If you solve continuity, evidence, and local-first AI well, Ultron can feel less like a dashboard and more like an architectural IDE.