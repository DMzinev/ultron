# Ultron Release Candidate Stabilization Plan
## Phase 6: Ship the product, stop expanding it

**Target repository:** `DMzinev/ultron`  
**Authoritative local baseline:** `master` at `2253f71`  
**Current remote baseline:** `origin/master` at `0442e1c`  
**Candidate version:** `1.5.0rc1`  
**Plan type:** Release stabilization, not a feature phase  

---

## 1. Executive decision

Ultron is technically strong enough to become a public release candidate, but
it is not ready to be published as stable `1.5.0`.

The correct next move is:

1. Freeze new features.
2. Converge local and remote history.
3. Fix remote CI and the GitHub Action.
4. Make package and documentation claims match observed behavior.
5. Validate built artifacts on clean supported platforms.
6. Publish `1.5.0rc1` to TestPyPI and a GitHub pre-release.
7. Dogfood the candidate on real external repositories.
8. Promote the exact candidate artifact to stable only after the evidence gate
   passes.

Do not start Phase 6 by adding analyzers, languages, dashboards, agent
supervision features, editors, hosted services, or desktop packaging.

---

## 2. Verified baseline

The following facts were independently checked against the repository:

| Area | Verified state |
|---|---|
| Local source gate | `973` tests discovered, `0` failures, `0` errors, `3` skips |
| Package version | `1.5.0` in package metadata, `setup.py`, `ultron.__version__`, and MCP |
| Wheel | Builds as `ultron_risk_scorer-1.5.0-py3-none-any.whl` |
| Clean wheel install | Succeeds with no required third-party dependencies |
| Installed commands | `scan`, `brief`, `gate`, `verify`, `init`, `mcp`, `hook`, `impact`, `export`, and `watch` respond to `--help` |
| Installed version flag | Broken: `ultron --version` is unrecognized |
| Remote CI | Red across recent Linux and Windows matrix runs |
| Action workflow | Invalid: composite action references `secrets.GITHUB_TOKEN` in input metadata |
| PyPI | `ultron-risk-scorer` returns 404; package is not published |
| GitHub releases | No release/tag was found |
| Standalone action | `DMzinev/ultron-action` repository does not exist |
| Local/remote divergence | Local `master` is 13 commits ahead of `origin/master` |
| Python support | Metadata says `>=3.8`; documentation and CI cover `3.10`-`3.12` |
| Stable skip claim | False as written: observed release-candidate run had 3 environment-dependent skips |
| Production size | 141 production Python files, approximately 27,000 lines |
| Test size | 173 test files, approximately 24,600 lines |
| Large production modules | 10 production Python files exceed 500 lines |
| Governance residue | `PROJECT_LOG.md` is over 5,000 lines; 88 legacy audit reports remain archived |

These numbers form the release baseline. Do not replace them with counters from
old task reports.

---

## 3. Release-blocking defects

### Blocker B1: Remote CI is red

The latest core CI run fails on multiple Python/OS combinations. One confirmed
failure is:

```text
test_gate_command_color_and_no_color_options
AssertionError: ANSI output not found
```

The test runs under `GITHUB_ACTIONS=true`; the gate automatically selects
GitHub annotation output, bypassing forced color output.

### Blocker B2: The composite action cannot load

The action manifest contains an input description/default expression involving:

```yaml
${{ secrets.GITHUB_TOKEN }}
```

The `secrets` context is not valid in that composite action metadata location.
The runner rejects the manifest before the action executes.

### Blocker B3: Latest Phase 5 work is not fully remote

Local `master` contains 13 commits absent from `origin/master`, including
monorepo support, the end-to-end audit, version `1.5.0`, and release notes.

### Blocker B4: No distribution channel exists

There is no PyPI artifact, GitHub release, release workflow, release tag, or
TestPyPI rehearsal.

### Blocker B5: Installed support surface is incomplete

The installed wheel has no working:

```text
ultron --version
```

This makes issue reports and environment diagnosis harder.

### Blocker B6: Public claims exceed evidence

The README claims 973 tests with zero skips. The independent run produced 3
skips. Package metadata claims Python 3.8 support while CI starts at Python
3.10. Documentation advertises `DMzinev/ultron-action@v1`, but that repository
does not exist.

---

## 4. Non-negotiable operating rules

1. **No new product features during stabilization.**
2. One task, one branch, one focused commit series.
3. Base all release work on local `master` commit `2253f71` or its verified
   descendant.
4. Record exact before/after source-test, wheel-smoke, and remote-CI results.
5. Never declare success from an editable install.
6. Build the wheel once per candidate and test that exact artifact everywhere.
7. Never rebuild between TestPyPI, GitHub pre-release, and stable promotion.
8. Do not publish to production PyPI or create a stable tag without owner
   approval.
9. Do not add long-lived publishing tokens. Use trusted publishing/OIDC.
10. Do not weaken or delete a test solely to make CI green.
11. Environment-dependent behavior must be explicit in tests and docs.
12. Preserve public imports and CLI compatibility while extracting internals.
13. No broad rewrites. Refactor by characterization test plus extraction.
14. Every release-facing claim must have a source-of-truth test or generated
   fact where practical.
15. If local and remote results differ, remote clean-runner evidence wins.

---

## 5. Execution order

```text
RC-A1 -> RC-A2 -> RC-A3 -> RC-A4
                           |
                           v
RC-B1 -> RC-B2 -> RC-B3 -> RC-B4
                           |
                           v
RC-C1 -> RC-C2 -> RC-C3 -> RC-C4
                           |
                           v
RC-D1 -> RC-D2 -> RC-D3
                           |
                           v
                    OWNER SHIP REVIEW
```

Phase A restores trustworthy integration. Phase B establishes the release
artifact. Phase C performs external candidate validation. Phase D prevents the
repository from becoming unmaintainable after release.

---

# Phase RC-A: Repository and CI convergence

## Task RC-A1: Reconcile local and remote master safely

**Goal:** Make one reviewable remote branch contain the complete Phase 5 state
without rewriting published history.

**Steps:**

1. Fetch all remote refs.
2. Confirm local `master` at `2253f71` is a descendant of remote
   `origin/master` at `0442e1c`.
3. Review the 13 unpublished commits as one range:

   ```powershell
   git log --oneline origin/master..master
   git diff --stat origin/master..master
   git diff --check origin/master..master
   ```

4. Resolve whitespace-only defects in a separate cleanup commit only if they
   affect touched Phase 5 files; do not rewrite historical commits.
5. Push a release-candidate integration branch, not directly to remote master:

   ```text
   release/1.5.0rc1-stabilization
   ```

6. Open a pull request showing the full Phase 5 delta and stabilization fixes.
7. Do not merge until all RC-A tasks pass remotely.

**Acceptance:**

- The integration branch includes all 13 unpublished commits.
- No force push is used.
- Pull request diff matches `origin/master..master` plus focused stabilization
  commits.
- Working tree remains clean.

## Task RC-A2: Fix the GitHub Action manifest

**Files:** `.github/actions/ultron-gate/action.yml`,
`.github/workflows/test-action.yml`, action tests.

**Steps:**

1. Remove `${{ secrets.GITHUB_TOKEN }}` from composite action input defaults or
   metadata expressions.
2. Make `github-token` default to an empty string.
3. Require callers that enable PR comments to pass:

   ```yaml
   github-token: ${{ secrets.GITHUB_TOKEN }}
   ```

4. Fail clearly if `comment-pr=true` but no token is supplied.
5. Add a workflow syntax/manifest validation test.
6. Test both Linux and Windows local-action invocation.
7. Test action load with no token.
8. Test PR-comment mode using a stubbed HTTP boundary, never a live mutation.

**Acceptance:**

- GitHub accepts the action manifest.
- Both action workflow matrix jobs load and execute the action.
- No secret context appears in `action.yml` input metadata.

## Task RC-A3: Make CLI rendering independent of ambient CI variables

**Files:** `ultron/interfaces/cli/commands/gate.py`,
`ultron/interfaces/cli/formatting.py`, `test_cli_formatting.py`.

**Required precedence:**

1. Explicit machine-output modes (`--json`, report file generation).
2. Explicit user choice (`--color` / `--no-color`).
3. Explicit GitHub annotation flag.
4. Ambient environment detection.
5. TTY auto-detection.

`GITHUB_ACTIONS=true` must not silently override an explicit `--color` test or
user choice.

**Tests:**

- `GITHUB_ACTIONS=true` plus forced color.
- `GITHUB_ACTIONS=true` plus `--no-color`.
- Explicit annotations with and without color.
- JSON output with no ANSI or workflow-command pollution.
- `NO_COLOR` behavior.
- Linux and Windows newline behavior.

**Acceptance:**

- The confirmed Linux CI failure is reproduced before the fix.
- The targeted test passes after the fix.
- Full matrix passes on Python 3.10-3.12.

## Task RC-A4: Make remote CI the real release gate

**Files:** `.github/workflows/ci.yml`, `.github/workflows/test-action.yml`.

**Steps:**

1. Keep source tests on Linux and Windows, Python 3.10-3.12.
2. Add macOS for clean wheel smoke testing, not necessarily the entire 973-test
   suite initially.
3. Split jobs into:
   - source unit/contract;
   - integration;
   - built-wheel smoke;
   - composite action;
   - release artifact.
4. Test zero-dependency base install separately from dev extras.
5. Stop installing `requirements.txt` before the base-install smoke, because it
   installs Radon and invalidates the zero-dependency proof.
6. Keep a dev-extras job for the full suite.
7. Upload full logs and structured summaries on failure.
8. Pin release-critical third-party actions to reviewed immutable SHAs before
   stable publication.

**Acceptance:**

- Every required job passes on the integration pull request.
- Two consecutive runs pass without rerun-only success.
- Base-wheel smoke runs without Radon, Pillow, or pystray installed.

---

# Phase RC-B: Release artifact and public truth

## Task RC-B1: Add a real version command

**Goal:** Support:

```text
ultron --version
ultron version
ultron version --json
```

**Output:**

- package version;
- Python version;
- installation path;
- optional capability availability in JSON mode.

Use `importlib.metadata` for installed package version, with a development-tree
fallback to `ultron.__version__`. One authoritative version value must drive
MCP, package metadata, CLI, API, SARIF driver metadata, and UI.

**Acceptance:**

- Works from source checkout.
- Works from built wheel outside the repository.
- Package metadata and CLI version match exactly.
- JSON schema is versioned and stable.

## Task RC-B2: Align supported Python versions

**Decision rule:**

- If Python 3.8 and 3.9 clean-wheel smoke jobs pass, keep `>=3.8`.
- Otherwise set `requires-python = ">=3.10"` and make `setup.py`, README, CI,
  classifiers, and error messages agree.

Do not claim support based solely on syntax compilation.

**Acceptance:**

- Every advertised Python version installs the wheel and completes smoke tests.
- Every unadvertised lower version is rejected by package metadata.

## Task RC-B3: Correct release documentation automatically

**Files:** README, getting-started guide, resources, tracker, new generated
release facts.

**Required corrections:**

1. Replace zero-skip absolutes with exact observed policy.
2. Stop saying `DMzinev/ultron-action@v1` exists until it does.
3. Distinguish repository-local action usage from published action usage.
4. Describe JS/TS and monorepo capabilities as experimental until external
   dogfooding passes.
5. State that `1.5.0rc1` is a pre-release.
6. Remove manually copied test counters from multiple pages where possible.

Create:

```text
python scripts/generate_release_facts.py
```

It should generate a machine-readable and Markdown fact set containing:

- version;
- Python requirement;
- canonical CLI commands;
- MCP canonical tool names;
- optional extras;
- current test result from an input artifact;
- supported artifact formats.

Documentation-reality tests compare public claims with these facts.

**Acceptance:**

- No stale `973/0 skipped` assertion remains unless produced by that exact run.
- No unavailable action/release is advertised as live.

## Task RC-B4: Build one immutable candidate artifact

**Artifacts:**

- wheel;
- source distribution;
- SHA-256 checksum file;
- package manifests;
- software bill of materials or dependency inventory;
- test result summary;
- license and notices;
- release facts.

**Steps:**

1. Build from a clean tagged candidate commit.
2. Ensure wheel contains runtime modules, web assets, migrations, rulepacks, and
   console entry points.
3. Ensure wheel excludes tests, UMAGS governance, databases, audit logs, plans,
   and local secrets.
4. Install wheel and sdist into separate clean environments.
5. Run all CLI help/version checks.
6. Run MCP initialize/tools-list.
7. Start server on an ephemeral port and check root and health.
8. Scan one external temporary repository.
9. Record artifact hashes.
10. Never rebuild this candidate for later promotion.

**Acceptance:**

- Windows, Ubuntu, and macOS smoke the same artifact hash successfully.
- `pip install ultron-risk-scorer==1.5.0rc1` is not claimed until TestPyPI or
  PyPI actually contains it.

---

# Phase RC-C: Candidate publication and external dogfooding

## Task RC-C1: Add trusted publishing in non-production mode

**Files:** new release workflow and release documentation.

**Requirements:**

1. Use PyPI/TestPyPI trusted publishing with GitHub OIDC.
2. No API token in repository secrets.
3. Separate build, verify, TestPyPI, and production jobs.
4. Require protected GitHub environments.
5. Validate Git tag equals package version.
6. Refuse dirty-tree or branch-only publication.
7. Refuse replacement of an existing immutable version.
8. Production job stays disabled or approval-gated during implementation.

**Acceptance:**

- Workflow validates and reaches the approval boundary.
- TestPyPI rehearsal succeeds.
- Production PyPI is untouched.

## Task RC-C2: Make the GitHub Action consumable

Choose one approach:

### Recommended initial approach

Keep the action in `DMzinev/ultron` and document:

```yaml
uses: DMzinev/ultron/.github/actions/ultron-gate@v1.5.0rc1
```

The action must install the pinned Ultron candidate itself unless a documented
input says to use a preinstalled executable.

### Deferred approach

Create `DMzinev/ultron-action` only after the action contract stabilizes.

**Required test:** Create a separate minimal consumer repository or temporary
fixture workflow that does not contain Ultron source. It must invoke the action,
pass on a clean fixture, and fail on a degraded fixture.

**Acceptance:**

- Public documentation uses a repository/ref that actually exists.
- External consumer workflow passes.
- Action version is pinned, not `master`.

## Task RC-C3: Publish GitHub pre-release and TestPyPI candidate

**Release:** `v1.5.0rc1`

Include:

- candidate wheel and sdist;
- checksums;
- compatibility matrix;
- known limitations;
- exact skip/environment notes;
- JS/TS and monorepo experimental labels;
- upgrade and uninstall instructions;
- rollback instructions;
- MCP configuration repair/uninstall instructions.

Do not call the candidate enterprise-ready or production-ready.

**Acceptance:**

- TestPyPI installation works using only published artifacts.
- GitHub pre-release assets match recorded hashes.
- `ultron --version` reports `1.5.0rc1`.

## Task RC-C4: External dogfooding matrix

Run the candidate on at least four repositories:

1. Normal Python library/application.
2. Mixed Python and JavaScript/TypeScript repository.
3. Monorepo with at least three workspaces.
4. Mature repository with substantial pre-existing debt.

For each repository record:

- scan duration and peak memory;
- file counts by language;
- top findings reviewed by a human;
- false-positive sample;
- `brief`, `impact`, `gate`, SARIF, and MCP behavior;
- baseline adoption experience;
- action installation result;
- any filesystem/configuration changes;
- uninstall/rollback result.

**Minimum qualitative gate:**

- No data loss.
- No corrupted MCP/client configuration.
- No false gate failure caused solely by unchanged pre-existing debt.
- No crash on supported languages/repository shapes.
- At least 70% of sampled HIGH findings judged actionable or defensibly risky.
- No critical installation or uninstall defect.

---

# Phase RC-D: Refinement without destructive rewrites

## Task RC-D1: Define stability tiers and compatibility boundaries

Classify public capabilities:

| Tier | Initial recommendation |
|---|---|
| Stable | `scan`, `brief`, `gate`, Python analysis, core MCP read tools |
| Beta | Web dashboard, export, SARIF, impact simulator |
| Experimental | JS/TS lexical analysis, monorepo federation, watch daemon, Git-hook automation |

Document:

- CLI compatibility policy;
- JSON schema versioning;
- MCP canonical tool and alias deprecation policy;
- persistence/migration policy;
- experimental-feature change policy.

Stable interfaces cannot be renamed or removed during cleanup without a
deprecation period and compatibility test.

## Task RC-D2: Introduce layered test tiers

Do not remove the full canonical suite. Add faster feedback:

1. **Fast:** pure unit and contract tests, target under 60 seconds.
2. **Integration:** subprocess, SQLite, server, MCP, target under 3 minutes.
3. **Release:** wheel, clean install, real coverage, action, monorepo, E2E,
   target under 10 minutes.
4. **Canonical:** all tiers, mandatory before merge and release.

Tag tests through an explicit manifest or test module convention. Add a
meta-test proving every discovered test belongs to at least one tier and the
canonical total equals full discovery.

**Acceptance:**

- Developers get fast feedback without weakening final verification.
- No test silently disappears from the canonical gate.

## Task RC-D3: Reduce governance and documentation entropy

**Current problem:** `PROJECT_LOG.md` exceeds 5,000 lines, and 88 archived audit
reports remain in the repository.

**Steps:**

1. Freeze the historical project log as a versioned archive.
2. Start a concise release/decision log.
3. Keep only these active documents:
   - README;
   - getting started;
   - architecture overview;
   - compatibility policy;
   - roadmap;
   - release checklist;
   - security policy.
4. Keep historical reports accessible but out of the primary navigation and
   package.
5. Generate counters and capability lists rather than copying them manually.
6. Stop creating a new audit document for every small task.

No history is deleted during this task.

## Task RC-D4: Establish safe module extraction rules

Ten production files exceed 500 lines. Do not rewrite them wholesale.

For each selected module:

1. Measure change frequency and dependency fan-in/fan-out.
2. Prioritize high-change/high-coupling modules, not merely longest files.
3. Freeze public behavior with characterization tests.
4. Extract one cohesive concern.
5. Keep original import/function/class facade.
6. Add an architectural dependency rule preventing reverse imports.
7. Run targeted, integration, and canonical gates.
8. Merge and observe before the next extraction.

Initial candidates:

- `ultron/interfaces/ultron.py`: extract CLI parser/registry while preserving
  entry point.
- `ultron/core/rkm/store.py`: extract schema/migration and query concerns while
  preserving storage facade and transaction behavior.
- large API route modules: extract application services, not route fragments.
- `agent_context_builder.py` and `issue_orchestrator.py`: first determine whether
  they are stable product scope or speculative complexity before extracting.

**Forbidden during RC stabilization:**

- changing risk formulas;
- changing health thresholds;
- renaming CLI commands;
- changing JSON contracts;
- replacing SQLite;
- replacing the web stack;
- deleting legacy compatibility shims without usage evidence.

---

## 6. Ship/no-ship gate

### Required to ship `1.5.0rc1`

- [ ] All local Phase 5 commits are present on the RC integration branch.
- [ ] Core CI is green on Linux and Windows Python 3.10-3.12.
- [ ] Clean-wheel smoke passes on Windows, Linux, and macOS.
- [ ] Composite action workflow is green on Windows and Linux.
- [ ] `ultron --version` works from the installed wheel.
- [ ] Python metadata matches tested versions.
- [ ] Documentation does not claim zero skips or unavailable distribution.
- [ ] TestPyPI trusted-publishing rehearsal succeeds.
- [ ] GitHub pre-release assets and checksums are present.
- [ ] External consumer action test passes.

### Required to promote to stable `1.5.0`

- [ ] All RC requirements remain green on the exact candidate artifact.
- [ ] External dogfooding matrix completed.
- [ ] No critical/high installation, data-loss, config-corruption, or rollback
      defects remain.
- [ ] No unresolved remote CI flakiness for seven consecutive days or ten
      consecutive required workflow runs, whichever is longer.
- [ ] Known limitations and experimental capabilities are documented.
- [ ] Owner explicitly approves promotion.

If any stable gate fails, publish another candidate (`1.5.0rc2`) rather than
mutating or rebuilding `rc1`.

---

## 7. Program Definition of Done

| # | Criterion | Required evidence |
|---|---|---|
| 1 | Repository converged | RC branch contains all intended local commits |
| 2 | Remote source CI green | All required matrix jobs pass twice |
| 3 | Action valid | Manifest loads and external consumer test passes |
| 4 | Package truthful | Version, dependencies, Python floor align |
| 5 | Wheel usable | Clean install and smoke on three OS families |
| 6 | Version diagnosable | `ultron --version` and JSON version work |
| 7 | Candidate immutable | One artifact hash used everywhere |
| 8 | TestPyPI rehearsal | Install and smoke from TestPyPI |
| 9 | GitHub pre-release | Assets, checksums, notes, limitations present |
| 10 | Dogfooding complete | Four repository classes evaluated |
| 11 | Rollback safe | MCP/action/package uninstall tested |
| 12 | Documentation honest | No unavailable feature or false counter claimed |
| 13 | Test growth controlled | Every test belongs to a tier and canonical gate |
| 14 | Refactoring controlled | Characterize, extract, facade, verify |
| 15 | Stable promotion approved | Owner explicitly approves exact artifact |

---

## 8. Kickoff prompt for the executing agent

> You are executing Ultron's Release Candidate Stabilization Plan. Read
> `docs/RELEASE_CANDIDATE_STABILIZATION_PLAN.md` completely before changing
> code. This is not Phase 6 feature development: freeze all new product
> capabilities. Use local `master` at `2253f71` as the authoritative Phase 5
> baseline; remote `origin/master` was at `0442e1c` and is missing 13 local
> commits. Start with RC-A1 by pushing a non-destructive RC integration branch,
> not by force-pushing master. Then fix the two confirmed remote failures:
> `.github/actions/ultron-gate/action.yml` illegally references
> `secrets.GITHUB_TOKEN` in composite-action metadata, and Linux CI's
> `GITHUB_ACTIONS=true` ambient variable overrides explicit forced-color
> behavior in `test_gate_command_color_and_no_color_options`. Make remote clean
> runners authoritative. Next add a real installed-wheel `ultron --version`,
> align Python metadata with tested versions, correct false zero-skip and
> unavailable-action claims, and build one immutable `1.5.0rc1` wheel/sdist
> candidate. Validate that exact artifact on Windows, Linux, and macOS. Add
> trusted publishing but stop at TestPyPI and a GitHub pre-release until owner
> approval. Test the GitHub Action from a separate consumer repository and
> dogfood the candidate on normal Python, mixed-language, monorepo, and
> high-debt repositories. Do not rewrite large modules during stabilization.
> Any cleanup must follow characterization test -> single concern extraction ->
> compatibility facade -> targeted tests -> canonical 973-test gate. If a ship
> gate fails, cut `rc2`; never mutate or rebuild `rc1`.
