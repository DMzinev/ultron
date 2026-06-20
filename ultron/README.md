# Ultron: Pre-Execution AI Prompt Optimizer

Ultron is a lightweight static analysis utility that acts as an **Ahead-of-Time (AOT) intelligence layer** before code generation. It analyzes a developer's natural language intent, maps system-wide call dependencies and imports using Python's `ast` module, evaluates risk metrics, and constructs a context-pruned prompt containing only the interface contracts the AI coding agent must satisfy.

---

## 1. Directory Structure

```text
ultron/
├── README.md               # User guide & research description
├── requirements.txt         # Minimal Python dependencies
├── ultron.py               # Main CLI entrypoint
├── analyzer.py             # AST-based dependency parser
├── risk.py                 # Coupling risk metrics engine
└── prompt.py               # Prompt generator & contract compiler
```

---

## 2. Usage

To evaluate code dependencies and generate an optimized contract-preserving prompt:

```bash
python ultron/ultron.py --repo <path_to_codebase> --intent "<change_description>" --files "<relative_path_to_modify>"
```

### Example:
```bash
python ultron/ultron.py --repo synapse_project/benchmarks/pymitter --intent "add a default TTL argument value of 10 to once method" --files "src/pymitter/__init__.py"
```
This maps the methods in `__init__.py`, finds downstream caller scripts (e.g. `examples.py`), evaluates risk, and prints an XML prompt.
