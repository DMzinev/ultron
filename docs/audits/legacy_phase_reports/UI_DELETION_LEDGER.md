# Ultron UI Deletion Ledger

## Purpose
Permanent record of interactive controls, buttons, and DOM elements purged during the **Production Integrity & Capability Reality** pass to eliminate AI-generated placeholder clutter and enforce the **Ponytail Simplicity** principle.

---

## Purged Controls Ledger

| Control ID / Selector | Why It Existed | Why Removed (Failure Mode) | Replacement / Authoritative Path | Verified Replacement Path |
| :--- | :--- | :--- | :--- | :--- |
| `#btn-persona-dev` | Speculative role switcher in risk modal | `PLACEHOLDER`: No backend translation engine; purely cosmetic tab with no actionable state change | `Agent Context` Provider Selector (`md`, `claude`, `codex`, `antigravity`) | Tab 4 (Agent Context) $\to$ Select Provider |
| `#btn-persona-manager` | Speculative manager role view | `PLACEHOLDER`: No distinct manager projection exists; dead button | `Overview` Vital Stats & Health Score | Tab 1 (Overview) |
| `#btn-persona-founder` | Speculative founder role view | `PLACEHOLDER`: Cosmetic mock with no functional backend | `Work & Plan` Milestone Progress | Tab 3 (Work & Plan) |
| `#btn-persona-security` | Speculative security auditor view | `PLACEHOLDER`: Duplicated Verify & Safety capabilities | `Verify & Safety` Policy Engine | Tab 5 (Verify & Safety) |
| `#btn-persona-ai` | Speculative AI agent view | `PLACEHOLDER`: Duplicated Agent Context mission builder | `Agent Context` Mission Compiler | Tab 4 (Agent Context) |
| `#btn-detail-ai-explain` | Modal "Translate Risk" button | `DUPLICATE`: Fragmented risk explanation inside small popup | Structure Node Drawer `Explain with AI` / AI Critique | Structure Tab $\to$ Click Node $\to$ Node Drawer |
| `#btn-auto-push-ai` | Modal "Auto-Push to AI" button | `DEAD`: No active backend agent daemon endpoint; simulated feedback | Structure Node Drawer `Prepare Agent Mission` | Structure Tab $\to$ Click Node $\to$ `[ 🚀 Prepare Agent Mission ]` |
| `#ai-collaboration-workspace` (`#btn-copy-claude`, `#btn-copy-gpt`, `#btn-copy-gemini`) | Modal raw prompt copy buttons | `DUPLICATE / CONFUSING`: Fragmented copy buttons in risk modal without grounded AST file context or tests | `Agent Context` Canonical Mission Builder (`#btn-copy-prompt`) | Tab 4 (Agent Context) $\to$ `[ 📋 COPY MISSION ]` |
| `#btn-export-reports` / `#btn-export-report` (legacy) | Duplicate export button fallback | `DUPLICATE`: Legacy fallback ID | `#btn-export-reports-menu` | Tab 5 (Verify & Safety) $\to$ Export Reports Menu |
| `#session-timer` (legacy) | Legacy visual timer placeholder | `DEAD`: Unconnected timer element | Live Session Bar & Snapshot Timestamp | Header Session Bar |

---

## Complexity Delta Summary
- **Net UI Controls Subtracted**: `9` controls permanently removed from DOM
- **Net State Owners Reduced**: Consolidated onto single authoritative `StateStore` in `modules/state.js`
- **Remaining Placeholder Controls**: `0` (100% verified against live handlers)
