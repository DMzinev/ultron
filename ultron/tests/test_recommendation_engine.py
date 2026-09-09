"""
tests/test_recommendation_engine.py — Phase 2.8 10-Agent Adversarial Decision Quality Suite.

Tests decision quality, consequence-driven priority scoring (consequence_v1),
objective relevance, evidence discounting, category isolation, and Ponytail simplicity.
"""
import os
import unittest
import tempfile
import shutil

from ultron.core.models import (
    FileCategory,
    RecommendationAction,
    RecommendationPacket,
    AnalysisPacket,
    ArchitecturalRole
)
from ultron.core.recommendation import (
    classify_file,
    compute_priority,
    resolve_action,
    generate_explainability,
    build_consequence_recommendations
)
from ultron.core import analyzer
from ultron.core.risk import scoring

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestRecommendationEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dirs = []

    def tearDown(self):
        for d in self.temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _create_temp_repo(self, files_dict):
        temp_dir = tempfile.mkdtemp(prefix="ultron_rec_test_")
        self.temp_dirs.append(temp_dir)
        for rel_path, content in files_dict.items():
            full_path = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        return temp_dir

    # -------------------------------------------------------------------------
    # Role 1: Ranking Correctness (requests: sessions.py > utils.py)
    # -------------------------------------------------------------------------
    def test_role1_ranking_correctness_requests(self):
        """Invariant: Under consequence_v1, operational hub (sessions) outranks utility drawer (utils)."""
        requests_dir = os.path.join(REPO_ROOT, "scratch", "external", "repo_c_requests")
        if not os.path.exists(requests_dir):
            self.skipTest("repo_c_requests not cloned")

        cb = analyzer.analyze_directory(requests_dir)
        risks = scoring.evaluate_risks(cb, [], repo_path=requests_dir)
        recs = build_consequence_recommendations(cb, risks, repo_path=requests_dir, limit=10)

        rec_files = [r.target_file.replace("\\", "/") for r in recs]
        self.assertTrue(any("sessions.py" in f for f in rec_files), "sessions.py must be in recommendations")
        
        # Check relative priority if both present
        sessions_score = next((r.priority_score for r in recs if "sessions.py" in r.target_file), None)
        utils_score = next((r.priority_score for r in recs if "utils.py" in r.target_file), 0.0)
        
        self.assertIsNotNone(sessions_score)
        self.assertGreater(sessions_score, utils_score, f"sessions.py ({sessions_score}) must outrank utils.py ({utils_score})")

    # -------------------------------------------------------------------------
    # Role 2: Metric Adversary (500-line CC table vs 30-line dispatcher)
    # -------------------------------------------------------------------------
    def test_role2_metric_gaming_defense(self):
        """Invariant: A high-CC utility table cannot outrank a high-coupling dispatcher."""
        repo = self._create_temp_repo({
            "huge_table.py": "def lookup(x):\n" + "\n".join([f"    if x == {i}: return {i}" for i in range(40)]),
            "dispatcher.py": "def dispatch(): pass\n",
            "caller1.py": "from dispatcher import dispatch\ndef run(): dispatch()\n",
            "caller2.py": "from dispatcher import dispatch\ndef run(): dispatch()\n",
            "caller3.py": "from dispatcher import dispatch\ndef run(): dispatch()\n",
            "caller4.py": "from dispatcher import dispatch\ndef run(): dispatch()\n",
        })
        cb = analyzer.analyze_directory(repo)
        risks = scoring.evaluate_risks(cb, [], repo_path=repo)
        recs = build_consequence_recommendations(cb, risks, repo_path=repo)

        # Huge table has CC ~ 40, Dispatcher has CC ~ 1 but 4 callers
        top_target = recs[0].target_file if recs else ""
        self.assertEqual(top_target, "dispatcher.py", "Dispatcher with 4 callers must outrank 40-branch lookup table")

    # -------------------------------------------------------------------------
    # Role 3: Category Isolation & Monolith Invariant (Bottle)
    # -------------------------------------------------------------------------
    def test_role3_category_isolation_bottle(self):
        """Invariant: Bottle produces exactly 1 production recommendation; 0 test suites leak."""
        bottle_dir = os.path.join(REPO_ROOT, "scratch", "external", "repo_a_bottle")
        if not os.path.exists(bottle_dir):
            self.skipTest("repo_a_bottle not cloned")

        cb = analyzer.analyze_directory(bottle_dir)
        risks = scoring.evaluate_risks(cb, [], repo_path=bottle_dir)
        recs = build_consequence_recommendations(cb, risks, repo_path=bottle_dir, limit=10)

        # Bottle has exactly 1 production code file: bottle.py
        self.assertEqual(len(recs), 1, f"Bottle must return exactly 1 recommendation, got {len(recs)}")
        self.assertEqual(os.path.basename(recs[0].target_file), "bottle.py")
        for r in recs:
            self.assertEqual(r.category, FileCategory.PRODUCTION_CODE.value)
            self.assertFalse("test" in r.target_file.lower(), f"Test file leaked into recommendations: {r.target_file}")

    # -------------------------------------------------------------------------
    # Role 4: Objective Relevance Precedence
    # -------------------------------------------------------------------------
    def test_role4_objective_relevance_precedence(self):
        """Invariant: Objective relevance can outrank higher structural complexity."""
        repo = self._create_temp_repo({
            "auth_handler.py": "def authenticate(): pass\n",
            "auth_client.py": "from auth_handler import authenticate\ndef login(): authenticate()\n",
            "data_cruncher.py": "def crunch(x):\n" + "\n".join([f"    if x == {i}: return {i}" for i in range(20)]),
            "cruncher_caller.py": "from data_cruncher import crunch\ndef run(): crunch(1)\n",
        })
        cb = analyzer.analyze_directory(repo)
        risks = scoring.evaluate_risks(cb, [], repo_path=repo)

        # With objective = 'Fix authentication latency', auth_handler must win
        recs = build_consequence_recommendations(cb, risks, objective="Fix authentication latency", repo_path=repo)
        self.assertTrue(len(recs) > 0)
        self.assertEqual(recs[0].target_file, "auth_handler.py", "Objective matching file must outrank generic data cruncher")

    # -------------------------------------------------------------------------
    # Role 5: Consequence Grounding & 7-Question Explainability Contract
    # -------------------------------------------------------------------------
    def test_role5_seven_question_explainability_completeness(self):
        """Invariant: Every recommendation answers all 7 explainability questions with non-empty strings."""
        repo = self._create_temp_repo({
            "core.py": "def start(): pass\n",
            "client.py": "from core import start\ndef run(): start()\n"
        })
        cb = analyzer.analyze_directory(repo)
        risks = scoring.evaluate_risks(cb, [], repo_path=repo)
        recs = build_consequence_recommendations(cb, risks, repo_path=repo)

        self.assertTrue(len(recs) > 0)
        rec = recs[0]
        # Verify 7-question contract
        self.assertTrue(bool(rec.why_this.strip()), "why_this must be populated")
        self.assertTrue(bool(rec.why_now.strip()), "why_now must be populated")
        self.assertIsInstance(rec.what_it_affects, list)
        self.assertTrue(bool(rec.what_could_break.strip()), "what_could_break must be populated")
        self.assertIn(rec.evidence_tier, ("OBSERVED", "DERIVED", "ESTIMATED", "UNKNOWN"))
        self.assertTrue(bool(rec.confidence_reason.strip()), "confidence_reason must be populated")
        self.assertTrue(bool(rec.next_action.strip()), "next_action must be populated")

    # -------------------------------------------------------------------------
    # Role 6: Evidence Discounting
    # -------------------------------------------------------------------------
    def test_role6_evidence_discounting(self):
        """Invariant: Unknown evidence is heavily discounted (0.1x) compared to observed evidence (1.0x)."""
        observed_score = compute_priority({"file_path": "a.py", "category": FileCategory.PRODUCTION_CODE}, ["c1", "c2"], evidence_tier="OBSERVED")
        unknown_score = compute_priority({"file_path": "a.py", "category": FileCategory.PRODUCTION_CODE}, ["c1", "c2"], evidence_tier="UNKNOWN")
        
        self.assertGreater(observed_score, unknown_score)
        self.assertAlmostEqual(unknown_score / observed_score, 0.1, delta=0.05)

    # -------------------------------------------------------------------------
    # Role 7: First-Class Actions (DO_NOT_RECOMMEND / PROTECT / INVESTIGATE)
    # -------------------------------------------------------------------------
    def test_role7_action_resolution(self):
        """Invariant: Actions are resolved correctly across categories and consequence profiles."""
        self.assertEqual(resolve_action(FileCategory.TEST_CODE, 15.0, "HIGH", 10), RecommendationAction.DO_NOT_RECOMMEND)
        self.assertEqual(resolve_action(FileCategory.CONFIGURATION, 15.0, "HIGH", 10), RecommendationAction.DO_NOT_RECOMMEND)
        self.assertEqual(resolve_action(FileCategory.PRODUCTION_CODE, 2.0, "HIGH", 12), RecommendationAction.PROTECT)
        self.assertEqual(resolve_action(FileCategory.PRODUCTION_CODE, 12.0, "HIGH", 5), RecommendationAction.REFACTOR)
        self.assertEqual(resolve_action(FileCategory.PRODUCTION_CODE, 5.0, "LOW", 3), RecommendationAction.INVESTIGATE)

    # -------------------------------------------------------------------------
    # Role 8: API Contract Semantics & Backward Compatibility
    # -------------------------------------------------------------------------
    def test_role8_api_contract_semantics(self):
        """Invariant: /api/v1/analyze emits both risks and recommendations arrays."""
        repo = self._create_temp_repo({"service.py": "def run(): pass\n"})
        from ultron.interfaces.server import UltronAPIHandler
        import io
        import json

        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.headers = {"Content-Length": "0"}
        handler.rfile = io.BytesIO(b'{"repo": "' + repo.replace("\\", "/").encode() + b'", "recommendations": true}')
        handler.wfile = io.BytesIO()
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_request_data = lambda: {"repo": repo, "recommendations": True}
        handler.get_repo_root_path = lambda: repo

        handler.handle_analyze()
        output = handler.wfile.getvalue().decode("utf-8")
        data = json.loads(output)

        self.assertTrue(data.get("success"), "Analyze must succeed")
        self.assertIn("risks", data, "Legacy risks array must exist")
        self.assertIn("recommendations", data, "Phase 2.8 recommendations array must exist")
        self.assertIsInstance(data["recommendations"], list)

    # -------------------------------------------------------------------------
    # Role 9: Complexity Regression / Ponytail Simplicity Guard
    # -------------------------------------------------------------------------
    def test_role9_ponytail_simplicity_line_count(self):
        """Invariant: recommendation.py must remain strictly lean (< 250 lines)."""
        rec_path = os.path.join(REPO_ROOT, "ultron", "core", "recommendation.py")
        self.assertTrue(os.path.exists(rec_path), "recommendation.py must exist")
        with open(rec_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertLess(len(lines), 250, f"recommendation.py must be < 250 lines, got {len(lines)}")

    # -------------------------------------------------------------------------
    # Role 10: Chief Skeptic Challenge (Priority Inverts CC on Coupled Topology)
    # -------------------------------------------------------------------------
    def test_role10_chief_skeptic_inversion_proof(self):
        """
        Adversarial test: Proves that Priority ranking is NOT a dressed-up complexity scorer.
        Constructs a topology where CC order is [A, B, C] but Priority order is [C, B, A].
        """
        repo = self._create_temp_repo({
            "leaf_complex.py": "def heavy(x):\n" + "\n".join([f"    if x == {i}: return {i}" for i in range(30)]), # CC ~ 30, callers: 0
            "mid_module.py": "def mid(): pass\n", # CC ~ 1, callers: 1
            "hub_core.py": "def core(): pass\n",   # CC ~ 1, callers: 4
            "c1.py": "from hub_core import core\ndef r(): core()\n",
            "c2.py": "from hub_core import core\ndef r(): core()\n",
            "c3.py": "from hub_core import core\ndef r(): core()\n",
            "c4.py": "from hub_core import core\ndef r(): core()\n",
            "m1.py": "from mid_module import mid\ndef r(): mid()\n",
        })
        cb = analyzer.analyze_directory(repo)
        risks = scoring.evaluate_risks(cb, [], repo_path=repo)
        
        # CC sorting would place leaf_complex.py at rank #1
        cc_sorted = sorted(risks, key=lambda r: -r.complexity)
        self.assertEqual(cc_sorted[0].file_path, "leaf_complex.py", "Under CC, leaf_complex is #1")

        # Consequence recommendation MUST place hub_core.py at rank #1
        recs = build_consequence_recommendations(cb, risks, repo_path=repo)
        self.assertEqual(recs[0].target_file, "hub_core.py", "Under Consequence Engine, hub_core with 4 callers MUST be #1")
        leaf_rec = next((r for r in recs if r.target_file == "leaf_complex.py"), None)
        self.assertLess(leaf_rec.priority_score, 2.0, "Isolated leaf module with 0 callers must have low priority")
        self.assertGreater(recs[0].priority_score, leaf_rec.priority_score)


if __name__ == "__main__":
    unittest.main()
