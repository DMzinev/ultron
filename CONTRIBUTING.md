# Contributing to Ultron

Thank you for your interest in contributing to **Ultron**! Ultron is an autonomous, zero-dependency architectural risk engine and AI developer cockpit for Python codebases.

We welcome contributions of all kinds: bug fixes, performance optimizations, documentation improvements, architectural test cases, and edge-case hardenings.

---

## 🧭 Code of Conduct

All contributors are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) to ensure an inclusive, respectful, and collaborative environment.

---

## 🛠️ Development Setup

Ultron is engineered with a strict **zero-external-dependencies policy** for its core runtime. The entire analytical engine, REST API, Web dashboard, and MCP bridge run on the Python standard library.

### 1. Prerequisites
- Python **3.10**, **3.11**, or **3.12**
- Git

### 2. Clone & Provision
```bash
git clone https://github.com/DMzinev/ultron.git
cd ultron

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Linux / macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install editable development package & test tooling (radon)
pip install -r requirements.txt
pip install -e .
```

---

## 🧪 Verification & Testing (Single Source of Truth)

Ultron adheres to a strict single-source-of-truth verification gate. PRs cannot be merged without a completely green test suite.

### Run Canonical Verification
```bash
# Execute the entire master test suite
python scripts/verify.py

# Or via CLI
ultron verify

# Fast filtered run during feature development
python scripts/verify.py --pattern "test_my_feature*.py"
```

The runner outputs a standardized, deterministic summary:
```text
TESTS: 812 ran, 0 failed, 0 errors, 9 skipped
```

### Self-Scan Integrity Check
Ultron dogfoods its own architectural rules against its own source code:
```bash
python -m unittest ultron.tests.test_self_scan_integrity
```
*Invariants enforced:*
- Zero fixture or test file leakage into the production codebase analysis.
- The ratio of HIGH architectural risks across the repository must remain strictly $\le 15.0\%$.

---

## 📐 Core Engineering Principles

Before proposing changes, please keep our core tenets in mind:

1. **Zero Runtime Dependencies**: The core analysis pipeline, CLI, MCP bridge, and web server must only import the Python standard library (`ast`, `os`, `sys`, `json`, `http.server`, `socket`, `unittest`, etc.). External packages like `radon` are strictly test/development utilities.
2. **Lean Architectural Boundaries**:
   - `ultron/interfaces/server.py` line count must remain strictly **under 300 lines**.
   - Modular routes belong in `ultron/interfaces/api/routes/`.
3. **Cross-Platform Parity**:
   - Every file system path must use `os.path.join`, `os.path.normpath`, or `pathlib.Path`.
   - Always specify explicit `encoding="utf-8"` when reading or writing text files.
4. **Hermetic & Defensive Boundaries**:
   - Functions must explicitly validate inputs and handle zero/empty/None states.
   - Never use blank `except:` blocks without targeted logging or exception re-raising.

---

## 🚀 Submitting a Pull Request

1. **Create a branch**:
   ```bash
   git checkout -b fix/my-bug-fix
   ```
2. **Make focused, minimal changes**:
   Favor small, surgical diffs over sweeping rewrites (Ponytail Simplicity Ladder).
3. **Add automated tests**:
   Ensure every bug fix or feature has corresponding hermetic unit tests in `ultron/tests/`.
4. **Run the full test suite**:
   Ensure `python scripts/verify.py` passes with 0 failures and 0 errors.
5. **Open a Pull Request**:
   Fill out the [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md) detailing what changed and including the verified test summary line.
