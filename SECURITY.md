# Security Policy

## Supported Versions

Ultron takes software security seriously. We provide active security patches and updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

If you discover a security vulnerability within Ultron, please report it responsibly:

1. **Do not open a public GitHub issue** for undisclosed security vulnerabilities.
2. Please report the issue privately by opening a [GitHub Security Advisory](https://github.com/DMzinev/ultron/security/advisories/new) or by emailing the project maintainers.
3. Include detailed steps to reproduce the vulnerability, sample payloads, and expected vs actual behavior.
4. You will receive an acknowledgment within **48 hours** with an assessment of the vulnerability and next steps.

---

## Architectural Security Commitments

Ultron is engineered from the ground up with defensive security principles:

1. **Zero External Telemetry / Complete Air-Gap Privacy**:
   - Ultron never sends your source code, AST metrics, or file paths to remote servers or third-party cloud APIs.
   - All risk evaluations, dependency graphs, and AST parses run 100% locally on your machine.
2. **Local Loopback Isolation**:
   - The web dashboard and REST API bind exclusively to `127.0.0.1` (loopback interface) with strict CORS origin verification. External networks cannot access the running API.
3. **Path Traversal & Host Boundary Guards**:
   - All incoming file paths are sanitized via canonical `os.path.abspath` resolution.
   - The engine explicitly refuses to scan host filesystem roots (`/` or `C:\`) to prevent host-level exposure or unbounded denial-of-service file traversals.
