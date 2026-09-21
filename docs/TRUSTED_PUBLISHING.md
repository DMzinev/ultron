# 🔐 Ultron Trusted Publishing & OIDC Release Architecture

> **Release Candidate Stabilization Standard — Task RC-C1**  
> Formally establishes GitHub Actions OpenID Connect (OIDC) Trusted Publishing for PyPI and TestPyPI without API tokens or repository secrets.

---

## 1. Architectural Foundations & Threat Model

In accordance with **Rule 9** of [`docs/RELEASE_CANDIDATE_STABILIZATION_PLAN.md`](RELEASE_CANDIDATE_STABILIZATION_PLAN.md):
> *"Do not add long-lived publishing tokens. Use trusted publishing/OIDC."*

### Why API Tokens Are Forbidden
- **Token Leakage**: Long-lived API tokens stored in repository secrets can be exfiltrated via compromised dependencies, pull request runs, or build script side-effects.
- **Indefinite Validity**: Tokens do not expire automatically and lack cryptographic provenance binding them to a specific workflow run, Git tag, or commit SHA.
- **Shared Access**: A compromised secret allows publishing from outside the official GitHub Actions pipeline.

### OIDC Trusted Publishing Model
GitHub Actions generates short-lived, cryptographically signed JSON Web Tokens (JWTs) via OpenID Connect. The PyPA Warehouse validates the JWT claims against pre-registered publisher parameters:
1. **Issuer**: `https://token.actions.githubusercontent.com`
2. **Subject**: `repo:DMzinev/ultron:environment:<env>`
3. **Workflow**: `.github/workflows/release.yml`
4. **Ref**: `refs/tags/v*`

If all claims match, Warehouse exchanges the JWT for an ephemeral, single-use publishing token valid for 15 minutes.

---

## 2. GitHub Environments & Protection Boundaries

The release pipeline mandates two discrete GitHub Environments:

| Environment | Target Index | URL | Protection Boundary |
|:---|:---|:---|:---|
| `testpypi` | TestPyPI | `https://test.pypi.org/p/ultron-risk-scorer` | Automated staging & pre-release rehearsal |
| `pypi` | Production PyPI | `https://pypi.org/p/ultron-risk-scorer` | **Protected Environment**: Requires manual owner approval & tag restriction (`v*`) |

### GitHub Environment Configuration Instructions
1. Navigate to **Settings** > **Environments** in `DMzinev/ultron`.
2. Under `testpypi`:
   - Deployment branches and tags: Selected tags only (`v*`).
   - Secrets: **Zero secrets required**.
3. Under `pypi`:
   - Required reviewers: Repository owner.
   - Deployment branches and tags: Selected tags only (`v*`).
   - Secrets: **Zero secrets required**.

---

## 3. Four-Stage Release Pipeline (`.github/workflows/release.yml`)

```text
[ Tag: v1.5.0* ]
       │
       ▼
┌──────────────────┐
│  build-candidate │  Builds .whl & .tar.gz, hashes all 8 artifacts,
└─────────┬────────┘  stages dist/packages/ for upload.
          │
          ▼
┌──────────────────┐
│ verify-candidate │  Validates tag parity (v<version>), clean git tree,
└─────────┬────────┘  checks pre-existing version immutability, runs smoke.
          │
          ▼
┌──────────────────┐
│ publish-testpypi │  Environment: testpypi (OIDC token exchange).
└─────────┬────────┘  Publishes candidate & performs pip install rehearsal.
          │
          ▼
┌──────────────────┐
│   publish-pypi   │  Environment: pypi (Protected approval gate).
└──────────────────┘  Hard-locked (if: false) during RC stabilization.
```

### Stage Summary
1. **`build-candidate`**:
   - Executes `python scripts/build_candidate_artifacts.py --skip-smoke`.
   - Validates checksums in `dist/SHA256SUMS.txt`.
   - Stages pure distributions (`.whl` and `.tar.gz`) into `dist/packages/` to prevent non-distribution metadata files (`SHA256SUMS.txt`, `candidate_manifest.json`) from causing `InvalidDistribution` upload failures.
   - Uploads complete candidate bundle and packages artifact.
2. **`verify-candidate`**:
   - Invokes `scripts/verify_release_tag.py --tag <tag> --verify-head --check-exists --test-pypi`.
   - Enforces tag matches `ultron.get_version()` and `docs/release_facts.json`.
   - Enforces HEAD commit is an immutable tag pointing to the release.
   - Enforces clean git tree (`git status --porcelain` is empty).
   - Pre-flight probes index to guarantee version is not already published.
   - Runs `test_candidate_artifact_invariants.py`.
3. **`publish-testpypi`**:
   - Uses `pypa/gh-action-pypi-publish@7f25271a4aa483500f742f9492b2ab5648d61011` (`v1.12.4`).
   - Supports dry-run validation (`dry_run: true` on manual dispatch runs `twine check` and skips upload).
   - Rehearsal verification: tests installation with a bounded polling retry (up to 6 attempts with 10s backoff).
4. **`publish-pypi`**:
   - Production job disabled (`if: false`) during RC stabilization per Requirement 8.
   - Production PyPI is 100% untouched.

---

## 4. PyPA Warehouse Publisher Registration Steps

To link the repository to PyPI and TestPyPI:

### TestPyPI Setup (`https://test.pypi.org/manage/account/publishing/`)
- **PyPI Project Name**: `ultron-risk-scorer`
- **Owner**: `DMzinev`
- **Repository name**: `ultron`
- **Workflow name**: `release.yml`
- **Environment name**: `testpypi`

### Production PyPI Setup (`https://pypi.org/manage/account/publishing/`)
- **PyPI Project Name**: `ultron-risk-scorer`
- **Owner**: `DMzinev`
- **Repository name**: `ultron`
- **Workflow name**: `release.yml`
- **Environment name**: `pypi`

---

## 5. Verification & Immutability Enforcement Utility

The utility [`scripts/verify_release_tag.py`](../scripts/verify_release_tag.py) provides offline and online CLI checks:

```bash
# Validate tag parity against local repository
python scripts/verify_release_tag.py --tag v1.5.0rc1

# Verify HEAD is tagged and check immutability against TestPyPI
python scripts/verify_release_tag.py --tag v1.5.0rc1 --verify-head --check-exists --test-pypi

# JSON formatted audit output
python scripts/verify_release_tag.py --tag v1.5.0rc1 --json
```

All operations adhere to fail-closed error handling and pure standard library architecture.
