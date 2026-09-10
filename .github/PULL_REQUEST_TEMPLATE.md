## Description
<!-- Provide a clear, concise summary of the problem, rationale, and changes made. -->

## Changes Proposed
- [ ] 

## Verification & Testing
<!-- PRs must be verified against the single-source-of-truth verification suite. -->
- [ ] Executed `python scripts/verify.py` locally.
- [ ] Output summary line:
  ```text
  TESTS: <ran> ran, <failed> failed, <errors> errors, <skipped> skipped
  ```
- [ ] Ran `python -m unittest ultron.tests.test_self_scan_integrity` (3/3 passed).

## Architectural Checklist
- [ ] **Pure Standard Library**: Zero new external third-party dependencies added to core runtime.
- [ ] **Cross-Platform Path Safety**: Uses `os.path.join` / `normpath` with explicit `encoding="utf-8"`.
- [ ] **Server Line Count Limit**: `ultron/interfaces/server.py` remains strictly `< 300` lines.
- [ ] **Negative / Edge Tests Included**: Tested zero, empty, None, and boundary cases.
