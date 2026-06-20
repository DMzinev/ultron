# Ultron Integration & Setup Guide

This guide explains how to integrate **Ultron** (Pre-Execution Intelligence Layer) into AI developer tools (Claude Code, Codex, Antigravity) and git workflows.

---

## 1. Model Context Protocol (MCP) Server Setup

The built-in MCP server (`ultron/mcp_server.py`) provides stdio-based tool execution, allowing compatible LLMs to query Ultron's analyzers directly.

### A. Claude Desktop (Windows)
To add Ultron to Claude Desktop, edit your config file:
`%APPDATA%\Claude\claude_desktop_config.json`

Add the following under the `mcpServers` block (substituting the absolute path to your python executable and the `cost accounting` workspace):

```json
{
  "mcpServers": {
    "ultron": {
      "command": "python",
      "args": [
        "C:/Users/This PC/Desktop/cost accounting/ultron/mcp_server.py"
      ]
    }
  }
}
```

### B. Claude Code
For the Claude Code CLI, configure the MCP server using:
```bash
claude mcp add ultron python -- "C:/Users/This PC/Desktop/cost accounting/ultron/mcp_server.py"
```

### C. Antigravity & Gemini Agents
Add the MCP configuration to the system-wide or project-specific MCP loader configurations:
```json
{
  "servers": {
    "ultron": {
      "type": "stdio",
      "command": "python",
      "args": ["C:/Users/This PC/Desktop/cost accounting/ultron/mcp_server.py"]
    }
  }
}
```

---

## 2. CLI Integration (Codex, Cursor, Custom Shells)

AI agents that wrap terminal execution (e.g. Codex) can query Ultron using the standard CLI options. To make parsing simple, use the `--json` flag.

### Command Format:
```bash
python ultron/ultron.py --repo <repo_path> --check-anomaly <target_file> --json
```

### Exit Codes:
* **`0`**: Success. No structural, spell-check, or Markov sequence anomalies found.
* **`1`**: Execution error (e.g. invalid arguments or non-existent file).
* **`2`**: Anomalies or contract violations detected.

---

## 3. Git Pre-Commit Hook Installation

Ensure buggy code is caught before it enters version control by configuring a git pre-commit hook.

1. Copy the hook script template from `ultron/hooks/pre-commit` into your project's `.git/hooks/` folder:
   ```bash
   cp ultron/hooks/pre-commit .git/hooks/pre-commit
   ```
2. Make it executable:
   ```bash
   chmod +x .git/hooks/pre-commit
   ```

When running `git commit`, the hook will automatically inspect staged python files and abort the commit if anomalies are detected, displaying details of the errors.
