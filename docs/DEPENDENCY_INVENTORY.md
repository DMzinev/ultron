# 📦 Ultron Software Bill of Materials (SBOM) & Dependency Inventory

> **Release Candidate Stabilization Artifact — Task RC-B4**  
> Formally documents runtime dependencies, optional extras, build tooling, and security attributes for `ultron-risk-scorer`.

---

## 1. Distribution Identity
| Attribute | Specification |
| :--- | :--- |
| **Package Name** | `ultron-risk-scorer` |
| **Package Version** | `1.5.0` (PEP 440) |
| **Release Candidate** | `1.5.0rc1` (Stabilization Milestone) |
| **Required Python** | `>=3.10` |
| **Supported Python** | `3.10`, `3.11`, `3.12` |
| **Build Backend** | `setuptools.build_meta` |
| **License** | MIT License |

---

## 2. Core Runtime Dependency Census

Ultron's core architectural engine and developer interfaces are strictly **zero-dependency**:

```toml
# pyproject.toml
dependencies = []
```

```python
# setup.py
install_requires = []
```

### Standard Library Foundations
Ultron relies exclusively on the Python standard library for its primary analysis and server pipeline:
- **Static Analysis & Parsing**: `ast`, `tokenize`, `symtable`
- **Topology & Graph Algorithms**: `collections`, `heapq`, `dataclasses`
- **Repository Knowledge Model (RKM)**: `sqlite3` (WAL mode), `hashlib` (SHA-256)
- **Local Control Plane Server**: `http.server`, `socket`, `urllib.parse`
- **Model Context Protocol (MCP)**: `json`, `sys.stdin`, `sys.stdout`
- **CLI & Formatting**: `argparse`, `re`, `shutil`, `ctypes` (Windows console mode)
- **Filesystem & Process**: `os`, `pathlib`, `subprocess`, `tempfile`

---

## 3. Optional Feature Extras Census

Optional extras provide non-essential enhancements without affecting core static analysis, CLI gating, or MCP capabilities:

| Extra Name | Direct Dependency | Version Specifier | Purpose |
| :--- | :--- | :--- | :--- |
| `tray` | `pystray` | `>=0.19.0` | Desktop system tray notifications and menu launcher |
| `tray` | `Pillow` | `>=9.0.0` | Tray icon rasterization and image buffer handling |
| `metrics` | `radon` | `>=5.1.0` | Secondary cyclomatic complexity cross-validation |
| `dev` | `radon` | `>=5.1.0` | Local developer development and testing fixture support |
| `dev` | `pystray` | `>=0.19.0` | Local tray testing fixture support |
| `dev` | `Pillow` | `>=9.0.0` | Local tray icon testing fixture support |

---

## 4. Build-Time Dependencies

The distribution artifacts (wheel and source distribution) are built in accordance with PEP 517 / PEP 518:

| Build Tool | Required Version | Role |
| :--- | :--- | :--- |
| `setuptools` | `>=61.0.0` | Standard build backend supporting dynamic metadata and pyproject.toml |
| `wheel` | Latest / Standard | Binary distribution archive generation |
| `uv` (optional) | `>=0.12.0` | Fast clean-room PEP 517 build orchestrator |

---

## 5. Security & Isolation Architecture

1. **Zero External Telemetry**: All network operations bind strictly to `127.0.0.1`. Ultron transmits zero analytical data, metrics, or logs to remote servers.
2. **Deterministic Hermetic Packaging**: Wheel archive (`.whl`) contains zero test fixtures, scratch files, development databases, or governance logs.
3. **Reproducible Checksums**: Every release candidate artifact is cryptographically hashed with SHA-256 and recorded in `dist/SHA256SUMS.txt`.
