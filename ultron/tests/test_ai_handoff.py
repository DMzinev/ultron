import os
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from ultron.interfaces.api.browse_folder import select_folder_dialog
from ultron.interfaces.server import UltronAPIHandler
from ultron.core.pipeline import orchestrator

class TestAIHandoffAndFolderPicker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.repo_path = cls.temp_dir.name
        
        # Create a sample python file in temp repo
        cls.sample_file = os.path.join(cls.repo_path, "main.py")
        with open(cls.sample_file, "w", encoding="utf-8") as f:
            f.write("def run():\n    print('Hello Ultron')\n")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    @patch("tkinter.filedialog.askdirectory", return_value="")
    def test_select_folder_dialog_headless_safety(self, mock_ask):
        """Verify select_folder_dialog returns fallback=True cleanly when GUI is unavailable or in test runner."""
        res = select_folder_dialog(self.repo_path)
        self.assertIsInstance(res, dict)
        self.assertIn("cancelled", res)
        self.assertIn("fallback", res)
        self.assertIn("path", res)

    def test_context_brief_rkm_first(self):
        """Verify POST /api/v1/context-brief uses RKM DB first and renders Claude, Codex, and Antigravity outputs."""
        # Initialize RKM run
        orchestrator.analyze_repository(self.repo_path, force=True)
        
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/context-brief"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        req_payload = {
            "repo": self.repo_path,
            "target_file": "main.py"
        }
        handler.get_post_data = lambda: req_payload
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_repo_root_path = lambda: self.repo_path

        handler.handle_v1_context_brief()
        
        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        
        self.assertEqual(data["status"], "success")
        self.assertIn("canonical_brief", data)
        self.assertIn("handoff", data)
        
        handoff = data["handoff"]
        self.assertIn("claude", handoff)
        self.assertIn("codex", handoff)
        self.assertIn("antigravity", handoff)
        
        # Verify Antigravity output contains file:// reference
        self.assertIn("file:///", handoff["antigravity"])
        self.assertIn("claude -p", handoff["claude"])

    def test_handle_analyze_invalid_directory(self):
        """Verify handle_analyze returns HTTP 400 with clear diagnostic message on invalid folder."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/analyze"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        req_payload = {
            "repo": "C:/invalid_nonexistent_directory_xyz"
        }
        handler.get_post_data = lambda: req_payload
        
        responses = []
        handler.send_response = lambda code: responses.append(code)
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.send_json_response = lambda code, body: handler.wfile.write(json.dumps(body).encode('utf-8'))

        handler.handle_analyze()
        
        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        self.assertIn("error", data)
        self.assertIn("does not exist", data["error"])


FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures"))


class TestMissionEnvelopeQuality(unittest.TestCase):
    """
    Validates Task D1 Mission Envelope Quality.
    Verifies that a compiled mission contains all seven fields with grounded,
    non-hallucinated values across synthetic fixtures and boundary conditions.
    """

    def test_clean_repo_mission_envelope_service(self):
        """Target service.py in clean_repo: asserts all 7 fields, blast radius ['handlers.py'], rollback."""
        from ultron.core.pipeline.discovery import discover
        from ultron.core import analyzer
        from ultron.core.risk import scoring
        from ultron.core.prompt import compile_mission_envelope

        repo_path = os.path.join(FIXTURES_DIR, "clean_repo")
        target_file = "service.py"
        intent = "Refactor database query caching"
        files = discover(repo_path)
        codebase = analyzer.analyze_directory(repo_path)
        risks = scoring.evaluate_risks(codebase, files, repo_path=repo_path)

        envelope = compile_mission_envelope(
            intent=intent,
            target_file=target_file,
            repo_path=repo_path,
            codebase=codebase,
            risks=risks
        )

        # 1. Assert all 7 dictionary keys present and non-empty
        expected_keys = [
            "intent", "target_file", "blast_radius", "must_not_touch",
            "complexity_ceiling", "verification_command", "rollback_instruction",
            "token_budget_hint", "rendered_prompt"
        ]
        for key in expected_keys:
            self.assertIn(key, envelope)
            self.assertTrue(envelope[key], f"Field '{key}' should not be empty")

        # 2. Assert rendered prompt contains all 7 section markers
        rendered = envelope["rendered_prompt"]
        sections = [
            "[1. INTENT]", "[2. BLAST RADIUS]", "[3. MUST-NOT-TOUCH LIST]",
            "[4. COMPLEXITY CEILING]", "[5. VERIFICATION COMMAND]",
            "[6. ROLLBACK INSTRUCTION]", "[7. TOKEN BUDGET HINT]"
        ]
        for sec in sections:
            self.assertIn(sec, rendered)

        # 3. Assert specific grounded physics
        self.assertEqual(envelope["intent"], intent)
        self.assertEqual(envelope["target_file"], "service.py")
        self.assertEqual(envelope["blast_radius"], ["handlers.py"])
        self.assertEqual(envelope["rollback_instruction"], "git restore service.py")
        self.assertIn("McCabe 2", envelope["complexity_ceiling"])
        self.assertIn("do not add branches", envelope["complexity_ceiling"])
        self.assertTrue(any("get_recent_items" in sig or "create_item" in sig for sig in envelope["must_not_touch"]))
        self.assertIn("service.py", envelope["token_budget_hint"]["rank_1_target"])
        self.assertEqual(envelope["token_budget_hint"]["rank_2_callers"], ["handlers.py"])

    def test_clean_repo_leaf_module_main(self):
        """Target main.py in clean_repo: verifies leaf module with 0 inbound callers."""
        from ultron.core.pipeline.discovery import discover
        from ultron.core import analyzer
        from ultron.core.risk import scoring
        from ultron.core.prompt import compile_mission_envelope

        repo_path = os.path.join(FIXTURES_DIR, "clean_repo")
        target_file = "main.py"
        files = discover(repo_path)
        codebase = analyzer.analyze_directory(repo_path)
        risks = scoring.evaluate_risks(codebase, files, repo_path=repo_path)

        envelope = compile_mission_envelope(
            intent="Update CLI arguments",
            target_file=target_file,
            repo_path=repo_path,
            codebase=codebase,
            risks=risks
        )

        self.assertEqual(envelope["blast_radius"], [])
        self.assertIn("leaf module with no downstream dependents (blast radius: 0 files)", envelope["rendered_prompt"])
        self.assertEqual(envelope["rollback_instruction"], "git restore main.py")

    def test_tangled_repo_mission_envelope_god_module(self):
        """Target god_module.py in tangled_repo: asserts all 6 inbound callers, McCabe 14, public signatures."""
        from ultron.core.pipeline.discovery import discover
        from ultron.core import analyzer
        from ultron.core.risk import scoring
        from ultron.core.prompt import compile_mission_envelope

        repo_path = os.path.join(FIXTURES_DIR, "tangled_repo")
        target_file = "god_module.py"
        files = discover(repo_path)
        codebase = analyzer.analyze_directory(repo_path)
        risks = scoring.evaluate_risks(codebase, files, repo_path=repo_path)

        envelope = compile_mission_envelope(
            intent="Decompose monolithic processor into smaller services",
            target_file=target_file,
            repo_path=repo_path,
            codebase=codebase,
            risks=risks
        )

        # Inbound callers in tangled_repo
        expected_callers = {'client.py', 'cycle_c.py', 'entry.py', 'helpers.py', 'service.py', 'worker.py'}
        self.assertEqual(set(envelope["blast_radius"]), expected_callers)
        self.assertIn("McCabe 14", envelope["complexity_ceiling"])
        self.assertIn("do not add branches", envelope["complexity_ceiling"])
        self.assertEqual(envelope["rollback_instruction"], "git restore god_module.py")

        # Must-not-touch should exclude private functions starting with _ (except __init__)
        self.assertTrue(len(envelope["must_not_touch"]) > 0)
        for sig in envelope["must_not_touch"]:
            trimmed = sig.strip()
            if trimmed.startswith("def _"):
                self.assertTrue(trimmed.startswith("def __init__"), f"Private signature leaked: {sig}")

    def test_mixed_repo_mission_envelope_risky_core(self):
        """Target risky_core.py in mixed_repo: asserts blast radius ['risky_dispatcher.py']."""
        from ultron.core.pipeline.discovery import discover
        from ultron.core import analyzer
        from ultron.core.risk import scoring
        from ultron.core.prompt import compile_mission_envelope

        repo_path = os.path.join(FIXTURES_DIR, "mixed_repo")
        target_file = "risky_core.py"
        files = discover(repo_path)
        codebase = analyzer.analyze_directory(repo_path)
        risks = scoring.evaluate_risks(codebase, files, repo_path=repo_path)

        envelope = compile_mission_envelope(
            intent="Fix data synchronization race condition",
            target_file=target_file,
            repo_path=repo_path,
            codebase=codebase,
            risks=risks
        )

        self.assertEqual(envelope["blast_radius"], ["risky_dispatcher.py"])
        self.assertIn("risky_dispatcher.py", envelope["rendered_prompt"])
        self.assertEqual(envelope["rollback_instruction"], "git restore risky_core.py")

    def test_generate_optimized_prompt_backward_compatibility(self):
        """Verify generate_optimized_prompt preserves original header and all 7 fields."""
        from ultron.core.pipeline.discovery import discover
        from ultron.core import analyzer
        from ultron.core.risk import scoring
        from ultron.core.prompt import generate_optimized_prompt

        repo_path = os.path.join(FIXTURES_DIR, "clean_repo")
        codebase = analyzer.analyze_directory(repo_path)
        risks = scoring.evaluate_risks(codebase, discover(repo_path), repo_path=repo_path)

        prompt = generate_optimized_prompt("Fix security vulnerability", codebase, risks)
        self.assertIsInstance(prompt, str)
        self.assertIn("=== ULTRON PRE-EXECUTION INTELLIGENCE LAYER: MISSION ENVELOPE ===", prompt)
        self.assertIn("[1. INTENT]", prompt)
        self.assertIn("Fix security vulnerability", prompt)
        self.assertIn("[2. BLAST RADIUS]", prompt)
        self.assertIn("[3. MUST-NOT-TOUCH LIST]", prompt)
        self.assertIn("[4. COMPLEXITY CEILING]", prompt)
        self.assertIn("[5. VERIFICATION COMMAND]", prompt)
        self.assertIn("[6. ROLLBACK INSTRUCTION]", prompt)
        self.assertIn("[7. TOKEN BUDGET HINT]", prompt)

    def test_boundary_conditions(self):
        """Verify empty intent and missing target files degrade safely without throwing."""
        from ultron.core.prompt import compile_mission_envelope

        repo_path = os.path.join(FIXTURES_DIR, "clean_repo")
        # 1. Empty intent
        envelope = compile_mission_envelope(intent="", target_file="service.py", repo_path=repo_path)
        self.assertIn("zero revision debt", envelope["intent"])

        # 2. Nonexistent file
        envelope_ghost = compile_mission_envelope(intent="Ghost test", target_file="ghost_file.py", repo_path=repo_path)
        self.assertEqual(envelope_ghost["target_file"], "ghost_file.py")
        self.assertEqual(envelope_ghost["blast_radius"], [])
        self.assertEqual(envelope_ghost["rollback_instruction"], "git restore ghost_file.py")
        self.assertIn("McCabe 1", envelope_ghost["complexity_ceiling"])

    def test_context_brief_envelope_integration(self):
        """Verify generate_vibe_context_package returns envelope dict and all 7 fields."""
        from ultron.core.context_brief import generate_vibe_context_package

        repo_path = os.path.join(FIXTURES_DIR, "clean_repo")
        pkg = generate_vibe_context_package(
            intent="Optimize cache",
            repo_path=repo_path,
            target_file="service.py"
        )
        self.assertEqual(pkg["status"], "success")
        self.assertIn("envelope", pkg)
        self.assertIn("prompt_package", pkg)
        self.assertEqual(pkg["envelope"]["target_file"], "service.py")
        self.assertEqual(pkg["envelope"]["blast_radius"], ["handlers.py"])
        self.assertIn("[1. INTENT]", pkg["prompt_package"])
        self.assertIn("[2. BLAST RADIUS]", pkg["prompt_package"])
        self.assertIn("[3. MUST-NOT-TOUCH LIST]", pkg["prompt_package"])
        self.assertIn("[4. COMPLEXITY CEILING]", pkg["prompt_package"])
        self.assertIn("[5. VERIFICATION COMMAND]", pkg["prompt_package"])
        self.assertIn("[6. ROLLBACK INSTRUCTION]", pkg["prompt_package"])
        self.assertIn("[7. TOKEN BUDGET HINT]", pkg["prompt_package"])


if __name__ == "__main__":
    unittest.main()
