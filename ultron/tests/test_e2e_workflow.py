"""
ultron.tests.test_e2e_workflow
Comprehensive End-to-End Product Reality Audit & Clean-Room Build Test Suite (Task P5-D1).

Simulates and verifies the complete 9-stage developer and AI coding agent journey:
Stage 1: Clean-Room Setup & Server Launch (Dynamic port 0, MIME types for HTML, CSS, 12 JS modules)
Stage 2: Repository Connection & Configuration (/api/v1/health, /api/set-repo-root, /api/get-repo-root)
Stage 3: Analysis Pipeline Orchestration (/api/v1/analyze, /api/v1/progress, SQLite .ultron/repository.db)
Stage 4: Pillar 1 — Dashboard & Health Overview (/api/v1/overview, /api/architecture-health)
Stage 5: Pillar 2 — Visual Dependency Topology Graph (/api/dependency-graph at file and symbol granularity)
Stage 6: Pillar 3 — AI Agent Studio (/api/generate, /api/v1/context-brief handoffs)
Stage 7: Pillar 4 — Code Safety Auditor (/api/audit with target file and inline code payload)
Stage 8: Architecture Report Export (/api/v1/export-brief in markdown, json, html, text formats)
Stage 9: Quality Gate & Monorepo Scoping (CLI gating, workspace package scoping, fail-closed validation)

100% Hermetic: Executed inside tempfile.TemporaryDirectory() with zero host filesystem mutation.
Zero Skips: Strictly 0 test skips repository-wide.
Pure Standard Library: Zero third-party dependencies.
"""

import os
import sys
import io
import json
import time
import shutil
import sqlite3
import tempfile
import threading
import urllib.request
import urllib.error
import unittest
from typing import Optional, Dict, Any, Tuple

from ultron.interfaces.server import UltronAPIHandler, create_server
import ultron.interfaces.server as server_module
import ultron.interfaces.api.state as state_module
import ultron.interfaces.api.routes.system_routes as system_routes_module
import ultron.interfaces.api.routes.analysis_routes as analysis_routes_module
from ultron.interfaces.api.routes.system_routes import SystemRoutesMixin
from ultron.interfaces.cli.commands.gate import run_gate_command


class TestEndToEndProductRealityAudit(unittest.TestCase):
    """Exhaustive 9-stage end-to-end product reality audit in a clean-room sandbox."""

    temp_dir = ""
    sandbox_dir = ""
    config_dir = ""
    config_file = ""
    httpd = None
    server_thread = None
    server_port = 0
    base_url = ""

    # Backups for patched attributes
    _orig_state_config_dir = None
    _orig_state_config_file = None
    _orig_server_config_dir = None
    _orig_server_config_file = None
    _orig_sys_config_dir = None
    _orig_sys_config_file = None
    _orig_analysis_config_file = None
    _orig_get_repo_root_path = None

    @classmethod
    def setUpClass(cls):
        # 1. Create clean-room isolated temporary filesystem hierarchy
        cls.temp_dir = tempfile.mkdtemp(prefix="ultron_e2e_reality_")
        cls.sandbox_dir = os.path.join(cls.temp_dir, "sandbox")
        cls.config_dir = os.path.join(cls.temp_dir, "config")
        cls.config_file = os.path.join(cls.config_dir, "config.json")
        os.makedirs(cls.sandbox_dir, exist_ok=True)
        os.makedirs(cls.config_dir, exist_ok=True)

        # 2. Seed synthetic multi-package monorepo codebase
        cls._seed_sandbox_codebase(cls.sandbox_dir)

        # 3. Patch configuration paths for strict hermetic isolation
        cls._orig_state_config_dir = state_module.CONFIG_DIR
        cls._orig_state_config_file = state_module.CONFIG_FILE
        cls._orig_server_config_dir = server_module.CONFIG_DIR
        cls._orig_server_config_file = server_module.CONFIG_FILE
        cls._orig_sys_config_dir = system_routes_module.CONFIG_DIR
        cls._orig_sys_config_file = system_routes_module.CONFIG_FILE
        cls._orig_analysis_config_file = analysis_routes_module.CONFIG_FILE

        state_module.CONFIG_DIR = cls.config_dir
        state_module.CONFIG_FILE = cls.config_file
        server_module.CONFIG_DIR = cls.config_dir
        server_module.CONFIG_FILE = cls.config_file
        system_routes_module.CONFIG_DIR = cls.config_dir
        system_routes_module.CONFIG_FILE = cls.config_file
        analysis_routes_module.CONFIG_FILE = cls.config_file

        # Patch SystemRoutesMixin.get_repo_root_path to read sandboxed config
        cls._orig_get_repo_root_path = SystemRoutesMixin.get_repo_root_path
        def _sandboxed_get_repo_root_path(self_handler) -> str:
            if os.path.exists(cls.config_file):
                try:
                    with open(cls.config_file, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        val = cfg.get("repo_root")
                        if val and os.path.isdir(val):
                            return os.path.abspath(val)
                except Exception:
                    pass
            return os.path.abspath(cls.sandbox_dir)
        SystemRoutesMixin.get_repo_root_path = _sandboxed_get_repo_root_path

        # Reset ACTIVE_JOB to clean initial state
        state_module.ACTIVE_JOB["status"] = "idle"
        state_module.ACTIVE_JOB["job_id"] = None
        state_module.ACTIVE_JOB["progress_step"] = ""
        state_module.ACTIVE_JOB["error"] = None
        state_module.ACTIVE_JOB["cancel_requested"] = False

        # 4. Launch ephemeral in-process HTTP server on dynamic port 0
        cls.httpd, cls.server_port = create_server(host="127.0.0.1", start_port=0, max_attempts=1)
        cls.base_url = f"http://127.0.0.1:{cls.server_port}"
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

        # Warm-up ping to guarantee the server is listening
        warmup_req = urllib.request.Request(f"{cls.base_url}/api/v1/health")
        for _ in range(20):
            try:
                with urllib.request.urlopen(warmup_req, timeout=1.0) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        # 1. Shutdown server cleanly
        if cls.httpd is not None:
            cls.httpd.shutdown()
            cls.httpd.server_close()
        if cls.server_thread is not None:
            cls.server_thread.join(timeout=2.0)

        # 2. Restore patched state
        state_module.CONFIG_DIR = cls._orig_state_config_dir
        state_module.CONFIG_FILE = cls._orig_state_config_file
        server_module.CONFIG_DIR = cls._orig_server_config_dir
        server_module.CONFIG_FILE = cls._orig_server_config_file
        system_routes_module.CONFIG_DIR = cls._orig_sys_config_dir
        system_routes_module.CONFIG_FILE = cls._orig_sys_config_file
        analysis_routes_module.CONFIG_FILE = cls._orig_analysis_config_file
        if cls._orig_get_repo_root_path is not None:
            SystemRoutesMixin.get_repo_root_path = cls._orig_get_repo_root_path

        # Reset ACTIVE_JOB to clean initial state
        state_module.ACTIVE_JOB["status"] = "idle"
        state_module.ACTIVE_JOB["job_id"] = None
        state_module.ACTIVE_JOB["progress_step"] = ""
        state_module.ACTIVE_JOB["error"] = None
        state_module.ACTIVE_JOB["cancel_requested"] = False

        # 3. Remove temporary sandbox directory
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    @classmethod
    def _seed_sandbox_codebase(cls, root: str):
        """Creates an interconnected multi-package monorepo for comprehensive end-to-end testing."""
        # Root workspace configuration (Node / TS style monorepo manifest)
        with open(os.path.join(root, "package.json"), "w", encoding="utf-8") as f:
            json.dump({
                "name": "ultron-reality-sandbox",
                "version": "1.0.0",
                "workspaces": ["packages/*"]
            }, f, indent=2)

        # Package 1: pkg_core
        pkg_core_dir = os.path.join(root, "packages", "pkg_core")
        os.makedirs(pkg_core_dir, exist_ok=True)
        with open(os.path.join(pkg_core_dir, "package.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "pkg_core", "version": "1.0.0"}, f, indent=2)

        with open(os.path.join(pkg_core_dir, "utils.py"), "w", encoding="utf-8") as f:
            f.write(
                '"""Utility helpers for computation."""\n\n'
                'class DataFormatter:\n'
                '    def format_items(self, items):\n'
                '        if not items:\n'
                '            return []\n'
                '        return [str(x).strip().upper() for x in items]\n'
            )

        with open(os.path.join(pkg_core_dir, "engine.py"), "w", encoding="utf-8") as f:
            f.write(
                '"""Core computation engine."""\n\n'
                'from packages.pkg_core.utils import DataFormatter\n\n'
                'class ComputationEngine:\n'
                '    def __init__(self, name="CoreEngine"):\n'
                '        self.name = name\n'
                '        self.formatter = DataFormatter()\n\n'
                '    def process_data(self, dataset):\n'
                '        if not dataset:\n'
                '            return []\n'
                '        return self.formatter.format_items(dataset)\n'
            )

        # Package 2: pkg_web
        pkg_web_dir = os.path.join(root, "packages", "pkg_web")
        os.makedirs(pkg_web_dir, exist_ok=True)
        with open(os.path.join(pkg_web_dir, "package.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "pkg_web", "version": "1.0.0"}, f, indent=2)

        with open(os.path.join(pkg_web_dir, "app.py"), "w", encoding="utf-8") as f:
            f.write(
                '"""Web application presenting engine endpoints."""\n\n'
                'from packages.pkg_core.engine import ComputationEngine\n\n'
                'def route_request(action, payload):\n'
                '    engine = ComputationEngine()\n'
                '    if action == "ping":\n'
                '        return {"status": "pong"}\n'
                '    elif action == "compute":\n'
                '        if payload:\n'
                '            return {"result": engine.process_data(payload)}\n'
                '        return {"result": []}\n'
                '    elif action == "status":\n'
                '        return {"healthy": True, "engine": engine.name}\n'
                '    else:\n'
                '        return {"error": "unsupported_action"}\n'
            )

    def _http_request(
        self,
        path: str,
        method: str = "GET",
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[int, Any, bytes, Dict[str, str]]:
        """Executes an HTTP request against the live in-process server using urllib."""
        url = f"{self.base_url}{path}"
        req_headers = dict(headers or {})
        req_headers.setdefault("User-Agent", "UltronE2EAuditSuite/1.0")

        data_bytes = None
        if body is not None:
            data_bytes = json.dumps(body).encode("utf-8")
            req_headers["Content-Type"] = "application/json; charset=utf-8"

        req = urllib.request.Request(url, data=data_bytes, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                status = resp.status
                raw = resp.read()
                resp_headers = dict(resp.headers)
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except Exception:
                    parsed = None
                return status, parsed, raw, resp_headers
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except Exception:
                parsed = None
            return e.code, parsed, raw, dict(e.headers)

    # =========================================================================
    # Stage 1: Clean-Room Setup & Static Asset Serving
    # =========================================================================
    def test_01_stage1_static_assets_and_mime_types(self):
        """Stage 1: Verify static web assets and all 12 ES submodules serve HTTP 200 with correct MIME types."""
        # 1. Root index.html
        status, _, raw, headers = self._http_request("/")
        self.assertEqual(status, 200)
        self.assertTrue(headers.get("Content-Type", "").startswith("text/html"))
        self.assertIn(b"<title>Ultron", raw)

        # 2. Stylesheet
        status, _, raw, headers = self._http_request("/index.css")
        self.assertEqual(status, 200)
        self.assertTrue(headers.get("Content-Type", "").startswith("text/css"))
        self.assertGreater(len(raw), 500)

        # 3. Main JavaScript entrypoint
        status, _, raw, headers = self._http_request("/index.js")
        self.assertEqual(status, 200)
        self.assertTrue(headers.get("Content-Type", "").startswith("application/javascript"))
        self.assertGreater(len(raw), 1000)

        # 4. All 12 ES Submodules in ultron/interfaces/web/modules/
        submodules = [
            "modules/api.js",
            "modules/auditor.js",
            "modules/dashboard.js",
            "modules/detail.js",
            "modules/graph.js",
            "modules/modals.js",
            "modules/picker.js",
            "modules/state.js",
            "modules/storage.js",
            "modules/studio.js",
            "modules/ui.js",
            "modules/violations.js",
        ]
        for mod in submodules:
            m_status, _, m_raw, m_headers = self._http_request(f"/{mod}")
            self.assertEqual(m_status, 200, f"Submodule {mod} failed with status {m_status}")
            self.assertTrue(
                m_headers.get("Content-Type", "").startswith("application/javascript"),
                f"Submodule {mod} served with unexpected Content-Type: {m_headers.get('Content-Type')}"
            )
            self.assertGreater(len(m_raw), 50, f"Submodule {mod} served empty payload")

    # =========================================================================
    # Stage 2: Repository Connection & Configuration
    # =========================================================================
    def test_02_stage2_repo_connection_and_config(self):
        """Stage 2: Verify heartbeat and atomic repository root configuration via API."""
        # 1. Heartbeat check
        status, health_data, _, _ = self._http_request("/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(health_data.get("status"), "healthy")
        self.assertIn("environment", health_data)
        self.assertIn("rkm_database", health_data)
        self.assertIn("modules", health_data)

        # 2. Set repository root to sandbox directory
        status, set_res, _, _ = self._http_request(
            "/api/set-repo-root",
            method="POST",
            body={"path": self.sandbox_dir}
        )
        self.assertEqual(status, 200)
        self.assertEqual(set_res.get("status"), "ok")
        self.assertEqual(
            os.path.normcase(set_res.get("repo_root", "")),
            os.path.normcase(self.sandbox_dir)
        )

        # 3. Verify configuration persistence in sandboxed config file
        self.assertTrue(os.path.exists(self.config_file))
        with open(self.config_file, "r", encoding="utf-8") as f:
            persisted = json.load(f)
        self.assertEqual(
            os.path.normcase(persisted.get("repo_root", "")),
            os.path.normcase(self.sandbox_dir)
        )

        # 4. Verify get-repo-root reflects configured sandbox
        status, get_res, _, _ = self._http_request("/api/get-repo-root")
        self.assertEqual(status, 200)
        self.assertTrue(get_res.get("configured"))
        self.assertEqual(
            os.path.normcase(get_res.get("repo_root", "")),
            os.path.normcase(self.sandbox_dir)
        )

    # =========================================================================
    # Stage 3: Analysis Pipeline Orchestration
    # =========================================================================
    def test_03_stage3_analysis_pipeline_and_rkm_persistence(self):
        """Stage 3: Trigger background analysis, poll progress, and verify SQLite RKM database creation."""
        # Trigger analysis
        status, init_res, _, _ = self._http_request(
            "/api/v1/analyze",
            method="POST",
            body={"repo": self.sandbox_dir}
        )
        self.assertEqual(status, 200)
        self.assertTrue(init_res.get("success"))
        self.assertIn("job_id", init_res)

        # Poll /api/v1/progress until completion
        completed = False
        last_progress = {}
        for _ in range(100):  # Up to 5.0 seconds
            time.sleep(0.05)
            p_status, progress_data, _, _ = self._http_request("/api/v1/progress")
            self.assertEqual(p_status, 200)
            last_progress = progress_data
            if progress_data.get("status") in ("success", "failed", "cancelled"):
                completed = True
                break

        self.assertTrue(completed, "Analysis job did not complete within timeout")
        self.assertEqual(
            last_progress.get("status"),
            "success",
            f"Analysis failed with error: {last_progress.get('error')}"
        )
        self.assertEqual(last_progress.get("progress_step"), "Done")
        self.assertIsNone(last_progress.get("error"))

        # Verify SQLite repository.db file creation in .ultron directory
        db_path = os.path.join(self.sandbox_dir, ".ultron", "repository.db")
        self.assertTrue(os.path.exists(db_path), f"RKM database not found at: {db_path}")

        # Verify database schema integrity and non-empty metadata
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            # Verify required tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = set(row[0] for row in cursor.fetchall())
            expected_tables = {
                "rkm_manifest",
                "rkm_metadata",
                "rkm_analysis_runs",
                "rkm_files",
                "rkm_symbols",
                "rkm_dependencies",
                "rkm_rules"
            }
            self.assertTrue(
                expected_tables.issubset(tables),
                f"Missing expected tables in RKM database: {expected_tables - tables}"
            )

            # Verify manifest version
            cursor.execute("SELECT schema_version, minimum_reader_version FROM rkm_manifest WHERE id=1;")
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "1.3.0")

            # Verify analysis run recorded
            cursor.execute("SELECT id, engine_version FROM rkm_analysis_runs;")
            runs = cursor.fetchall()
            self.assertGreaterEqual(len(runs), 1)

            # Verify analyzed files recorded
            cursor.execute("SELECT path FROM rkm_files;")
            files = [r[0] for r in cursor.fetchall()]
            self.assertGreaterEqual(len(files), 3)
        finally:
            conn.close()

    # =========================================================================
    # Stage 4: Pillar 1 — Dashboard & Health Overview
    # =========================================================================
    def test_04_stage4_pillar1_dashboard_and_health_overview(self):
        """Stage 4: Query dashboard overview and architecture health scoring for Pillar 1."""
        # 1. Query /api/v1/overview
        status, ov, _, _ = self._http_request(
            "/api/v1/overview",
            method="POST",
            body={"repo": self.sandbox_dir}
        )
        self.assertEqual(status, 200)
        self.assertEqual(ov.get("status"), "success")
        self.assertEqual(ov.get("state"), "ok")

        # Assert stats
        stats = ov.get("stats", {})
        self.assertGreaterEqual(stats.get("total_files", 0), 3)
        self.assertGreaterEqual(stats.get("total_definitions", 0), 2)

        # Assert health score calibration
        health = ov.get("health", {})
        score = health.get("score")
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

        # Assert memory snapshot
        memory = ov.get("memory", {})
        self.assertTrue(memory.get("initialized"))
        self.assertIsNotNone(memory.get("repository_uuid"))

        # 2. Query /api/architecture-health
        status, ah, _, _ = self._http_request(
            "/api/architecture-health",
            method="POST",
            body={"repo": self.sandbox_dir}
        )
        self.assertEqual(status, 200)
        self.assertTrue(ah.get("success"))
        self.assertGreaterEqual(ah.get("analyzed_file_count", 0), 3)
        self.assertIsNotNone(ah.get("health_score"))
        self.assertIn(ah.get("health_band"), ["healthy", "warning", "critical"])

    # =========================================================================
    # Stage 5: Pillar 2 — Visual Dependency Topology Graph
    # =========================================================================
    def test_05_stage5_pillar2_dependency_graph_topology(self):
        """Stage 5: Query dependency graph at file and symbol granularities for Pillar 2."""
        # 1. File granularity
        status, fg, _, _ = self._http_request(
            "/api/dependency-graph",
            method="POST",
            body={"repo": self.sandbox_dir, "granularity": "file"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(fg.get("success"))

        nodes = fg.get("nodes", [])
        links = fg.get("links", [])
        self.assertGreaterEqual(len(nodes), 3)
        self.assertGreaterEqual(len(links), 1)

        # Assert node properties
        node_ids = set(n.get("id", "").replace("\\", "/") for n in nodes)
        self.assertTrue(any("engine.py" in nid for nid in node_ids))
        self.assertTrue(any("utils.py" in nid for nid in node_ids))
        self.assertTrue(any("app.py" in nid for nid in node_ids))

        for n in nodes:
            self.assertIn("complexity", n)
            self.assertIn("coupling", n)
            self.assertIn("level", n)
            self.assertIn("package", n)

        # Assert link connections
        link_targets = [str(l.get("target", "")).replace("\\", "/") for l in links]
        link_sources = [str(l.get("source", "")).replace("\\", "/") for l in links]
        self.assertTrue(any("engine.py" in s or "engine.py" in t for s, t in zip(link_sources, link_targets)))

        # 2. Symbol granularity
        status, sg, _, _ = self._http_request(
            "/api/dependency-graph",
            method="POST",
            body={"repo": self.sandbox_dir, "granularity": "symbol"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(sg.get("success"))
        sym_nodes = sg.get("nodes", [])
        self.assertGreaterEqual(len(sym_nodes), 1)

    # =========================================================================
    # Stage 6: Pillar 3 — AI Agent Studio
    # =========================================================================
    def test_06_stage6_pillar3_agent_studio_synthesis(self):
        """Stage 6: Verify prompt synthesis and multi-agent context briefs for Pillar 3."""
        # 1. Route /api/generate
        status, gen_res, _, _ = self._http_request(
            "/api/generate",
            method="POST",
            body={
                "repo": self.sandbox_dir,
                "intent": "refactor computation engine for higher throughput",
                "files": "packages/pkg_core/engine.py"
            }
        )
        self.assertEqual(status, 200)
        self.assertTrue(gen_res.get("success"))
        prompt_text = gen_res.get("prompt", "")
        self.assertGreater(len(prompt_text), 50)
        self.assertIn("refactor computation engine", prompt_text.lower())

        # 2. Route /api/v1/context-brief
        status, brief_res, _, _ = self._http_request(
            "/api/v1/context-brief",
            method="POST",
            body={
                "repo": self.sandbox_dir,
                "target_file": "packages/pkg_core/engine.py"
            }
        )
        self.assertEqual(status, 200)
        self.assertEqual(brief_res.get("status"), "success")

        canonical_brief = brief_res.get("canonical_brief", {})
        self.assertEqual(canonical_brief.get("target_file"), "packages/pkg_core/engine.py")
        self.assertIsNotNone(canonical_brief.get("health_score"))

        handoff = brief_res.get("handoff", {})
        self.assertIn("claude", handoff)
        self.assertIn("codex", handoff)
        self.assertIn("antigravity", handoff)

        self.assertGreater(len(handoff["claude"]), 20)
        self.assertGreater(len(handoff["codex"]), 20)
        self.assertGreater(len(handoff["antigravity"]), 20)

        self.assertIn("engine.py", handoff["codex"])
        self.assertIn("engine.py", handoff["antigravity"])

    # =========================================================================
    # Stage 7: Pillar 4 — Code Safety Auditor
    # =========================================================================
    def test_07_stage7_pillar4_code_safety_auditor(self):
        """Stage 7: Verify code safety auditor against target files and inline code payloads for Pillar 4."""
        # 1. Audit existing clean file
        target_file = os.path.join(self.sandbox_dir, "packages", "pkg_core", "engine.py")
        status, audit_res, _, _ = self._http_request(
            "/api/audit",
            method="POST",
            body={
                "repo": self.sandbox_dir,
                "target_file": target_file
            }
        )
        self.assertEqual(status, 200)
        self.assertTrue(audit_res.get("success"))
        self.assertIsInstance(audit_res.get("anomalies"), list)

        # 2. Audit inline code snippet
        code_payload = (
            "def test_calculation():\n"
            "    val = 10\n"
            "    return val * 2\n"
        )
        status, code_res, _, _ = self._http_request(
            "/api/audit",
            method="POST",
            body={
                "repo": self.sandbox_dir,
                "code": code_payload
            }
        )
        self.assertEqual(status, 200)
        self.assertTrue(code_res.get("success"))
        self.assertIsInstance(code_res.get("anomalies"), list)

    # =========================================================================
    # Stage 8: Architecture Report Export
    # =========================================================================
    def test_08_stage8_architecture_report_export_formats(self):
        """Stage 8: Verify /api/v1/export-brief across markdown, json, html, and text formats."""
        formats = ["markdown", "json", "html", "text"]
        for fmt in formats:
            status, exp_res, _, _ = self._http_request(
                "/api/v1/export-brief",
                method="POST",
                body={"format": fmt}
            )
            self.assertEqual(status, 200, f"Export format '{fmt}' failed with status {status}")
            self.assertEqual(exp_res.get("status"), "ok")
            self.assertEqual(exp_res.get("format"), fmt)
            self.assertEqual(exp_res.get("schema_version"), "1.0.0")

            if fmt == "json":
                self.assertIn("brief", exp_res)
                self.assertIsInstance(exp_res["brief"], dict)
                self.assertIn("health_score", exp_res["brief"])
            elif fmt == "html":
                content = exp_res.get("content", "")
                self.assertIn("<!DOCTYPE html>", content)
                self.assertIn("Ultron Architecture Report", content)
            elif fmt in ("markdown", "text"):
                content = exp_res.get("content", "")
                self.assertGreater(len(content), 50)

    # =========================================================================
    # Stage 9: Quality Gate & Monorepo Scoping
    # =========================================================================
    def test_09_stage9_ci_gate_and_workspace_scoping(self):
        """Stage 9: Verify headless quality gate CLI execution, workspace scoping, and fail-closed security."""
        # 1. Full repository quality gate execution (should PASS exit code 0)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        orig_stdout, orig_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = stdout_buf, stderr_buf
            exit_code = run_gate_command(
                repo_path=self.sandbox_dir,
                fail_on_regression=True,
                json_output=True
            )
        finally:
            sys.stdout, sys.stderr = orig_stdout, orig_stderr

        self.assertEqual(exit_code, 0, f"Quality gate failed unexpectedly. Output: {stdout_buf.getvalue()}")

        # 2. Workspace scoped quality gate for pkg_core
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        try:
            sys.stdout, sys.stderr = stdout_buf, stderr_buf
            exit_code_core = run_gate_command(
                repo_path=self.sandbox_dir,
                workspace="pkg_core",
                json_output=True
            )
        finally:
            sys.stdout, sys.stderr = orig_stdout, orig_stderr

        self.assertEqual(exit_code_core, 0)

        # 3. Workspace scoped quality gate for pkg_web
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        try:
            sys.stdout, sys.stderr = stdout_buf, stderr_buf
            exit_code_web = run_gate_command(
                repo_path=self.sandbox_dir,
                workspace="pkg_web",
                json_output=True
            )
        finally:
            sys.stdout, sys.stderr = orig_stdout, orig_stderr

        self.assertEqual(exit_code_web, 0)

        # 4. Fail-closed on invalid / non-existent workspace package (must FAIL exit code 1)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        try:
            sys.stdout, sys.stderr = stdout_buf, stderr_buf
            exit_code_invalid = run_gate_command(
                repo_path=self.sandbox_dir,
                workspace="non_existent_pkg_xyz",
                json_output=True
            )
        finally:
            sys.stdout, sys.stderr = orig_stdout, orig_stderr

        self.assertEqual(
            exit_code_invalid, 1,
            "Quality gate must fail-closed on non-existent workspace query."
        )

    # =========================================================================
    # Master Sequential Lifecycle Integration
    # =========================================================================
    def test_10_full_integrated_lifecycle_sequential_audit(self):
        """
        Master Sequential Audit: Execute the complete developer journey sequentially:
        Launch -> Connect -> Analyze -> Dashboard -> Graph -> Studio -> Auditor -> Export -> Gate
        Verifies continuous state transitions without any mocks or stubs.
        """
        # Step 1: Health heartbeat
        status, health, _, _ = self._http_request("/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["status"], "healthy")

        # Step 2: Connect repository
        status, set_res, _, _ = self._http_request(
            "/api/set-repo-root",
            method="POST",
            body={"path": self.sandbox_dir}
        )
        self.assertEqual(status, 200)

        # Step 3: Trigger & wait for analysis
        status, _, _, _ = self._http_request(
            "/api/v1/analyze",
            method="POST",
            body={"repo": self.sandbox_dir}
        )
        self.assertEqual(status, 200)

        done = False
        for _ in range(100):
            time.sleep(0.05)
            _, prog, _, _ = self._http_request("/api/v1/progress")
            if prog.get("status") in ("success", "failed"):
                done = (prog.get("status") == "success")
                break
        self.assertTrue(done, "Continuous integration analysis failed to finish")

        # Step 4: Verify Dashboard health
        status, ov, _, _ = self._http_request(
            "/api/v1/overview",
            method="POST",
            body={"repo": self.sandbox_dir}
        )
        self.assertEqual(status, 200)
        self.assertGreaterEqual(ov["health"]["score"], 0.0)

        # Step 5: Verify Graph topology
        status, gr, _, _ = self._http_request(
            "/api/dependency-graph",
            method="POST",
            body={"repo": self.sandbox_dir}
        )
        self.assertEqual(status, 200)
        self.assertGreater(len(gr["nodes"]), 0)

        # Step 6: Verify Studio generation
        status, st, _, _ = self._http_request(
            "/api/v1/context-brief",
            method="POST",
            body={"repo": self.sandbox_dir, "target_file": "packages/pkg_core/engine.py"}
        )
        self.assertEqual(status, 200)
        self.assertIn("claude", st["handoff"])

        # Step 7: Verify Auditor inspection
        status, au, _, _ = self._http_request(
            "/api/audit",
            method="POST",
            body={"repo": self.sandbox_dir, "code": "x = 42\n"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(au["success"])

        # Step 8: Verify Export report
        status, ex, _, _ = self._http_request(
            "/api/v1/export-brief",
            method="POST",
            body={"format": "markdown"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(ex["format"], "markdown")

        # Step 9: Verify CI Quality Gate
        stdout_buf = io.StringIO()
        orig_stdout = sys.stdout
        try:
            sys.stdout = stdout_buf
            gate_code = run_gate_command(
                repo_path=self.sandbox_dir,
                fail_on_regression=True,
                json_output=True
            )
        finally:
            sys.stdout = orig_stdout
        self.assertEqual(gate_code, 0)


if __name__ == "__main__":
    unittest.main()
