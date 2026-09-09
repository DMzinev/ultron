# Ultron — UX Friction Ledger

## Taxonomy & Schema

Every entry in this ledger strictly follows the evidence schema:
- **ID**: `UX-XXX`
- **Stage**: Overview | Structure | Work & Plan | Agent Context | Verify & Safety
- **Observed**: Concrete user behavior or stumbling block during blind task execution
- **Evidence**: Grounded observation from controlled developer walkthrough
- **Root Cause**: Architectural or visual hierarchy defect causing the friction
- **Resolution**: Surgical fix applied (if defect confirmed) or `NO MATERIAL FRICTION FOUND`
- **Verification**: Browser verification test
- **Status**: `OBSERVED` | `INFERRED` | `RESOLVED` | `NOT REPRODUCED` | `NO MATERIAL FRICTION FOUND`

---

## Ledger Entries

### `UX-001`
- **Stage**: Overview
- **Observed**: User looking for active task initially glanced past health score; wanted immediate visual confirmation of current milestone.
- **Evidence**: Controlled walkthrough observation during Task 1.
- **Root Cause**: Supporting health metric card was visually competing with Current Work.
- **Resolution**: Reordered Overview DOM so Project Identity & Current Work Card act as the top hero element; health metrics placed as supporting status card with deep diagnostics collapsible in drawer.
- **Verification**: Verified in live browser; Current Work card is first interactive component in visual hierarchy.
- **Status**: RESOLVED 🟢

### `UX-002`
- **Stage**: Structure
- **Observed**: In circular dependency networks ($A \to B \to C \to A$), user wondered if node $A$ was included in its own blast radius.
- **Evidence**: Controlled walkthrough observation during Task 2 on cyclic fixture.
- **Root Cause**: Drawer consequence sentence did not explicitly clarify that transitive impact excludes self while identifying cycle membership.
- **Resolution**: Formalized consequence formula in `modules/graph.js` where transitive blast radius includes distinct downstream nodes excluding self, with explicit cycle alert banner.
- **Verification**: Verified in live browser and automated graph unit test.
- **Status**: RESOLVED 🟢

### `UX-003`
- **Stage**: Agent Context
- **Observed**: User pasted a high-level architectural goal ("Improve distributed orchestration") with "system works" acceptance and expected the compiler to reject/warn before sending to agent.
- **Evidence**: Controlled walkthrough observation during Task 4.
- **Root Cause**: Lexical validator previously checked character length without evaluating whether acceptance criteria contained verifiable assertions.
- **Resolution**: Upgraded `AgentContextBuilder.validate_mission` to evaluate structural actionability and non-placeholder acceptance criteria.
- **Verification**: Automated false-positive test + live UI `#mission-validity-banner` renders `MISSION WEAK ⚠️`.
- **Status**: RESOLVED 🟢

### `UX-004`
- **Stage**: Verify & Safety
- **Observed**: User wondered what happens if files are edited on disk after safety analysis completes.
- **Evidence**: Controlled walkthrough observation during Task 5.
- **Root Cause**: Checkpoint authority previously compared snapshot IDs without hashing current disk contents.
- **Resolution**: Added live filesystem content hash check (`validated_content_hash` vs `checkpoint_content_hash`) in `DevelopmentSessionManager.create_checkpoint()`, returning `400 STALE_READINESS`.
- **Verification**: Verified in adversarial unit test `test_checkpoint_rejects_unrecalculated_filesystem_modifications`.
- **Status**: RESOLVED 🟢

### `UX-005`
- **Stage**: Structure
- **Observed**: Graph nodes were rendered as circles with overlapping labels, making filenames unreadable on medium-to-large repositories.
- **Evidence**: User reported "graph boxes are small and unreadable" on dense repositories.
- **Root Cause**: Hardcoded circle SVG nodes with floating text labels and no bounding box geometry.
- **Resolution**: Converted graph nodes to content-aware `<rect class="node-box">` primitives ($\ge 140\times 42$px), JetBrains Mono typography, middle ellipsis (`abc...xyz.py`), dashed selection boxes, and ray-to-box border intersection math.
- **Verification**: Verified in `audit_graph_visual_reality.py` and live browser inspection.
- **Status**: RESOLVED 🟢

### `UX-006`
- **Stage**: Structure -> Agent Context
- **Observed**: User clicking on a high-risk module in the graph had to manually navigate to Agent Context, find the file, and copy it into the prompt form.
- **Evidence**: Multi-step friction observed in developer workflow.
- **Root Cause**: Lack of direct 1-click cross-stage transition from Structure node inspection to Agent Context mission compiler.
- **Resolution**: Added prominent `[ 🚀 Prepare Agent Mission for this Module ]` button (`#btn-modal-prepare-mission`) in Structure drawer/modal that automatically populates target file, switches to Tab 4, and triggers compiler.
- **Verification**: Verified in live SPA navigation and `verify_full_user_workflow.py`.
- **Status**: RESOLVED 🟢
