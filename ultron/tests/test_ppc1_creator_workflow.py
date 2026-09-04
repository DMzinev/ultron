"""
Ultron PPC-1 Master Creator Workflow Test Suite.
Verifies the non-negotiable 10-step creator loop on an unfamiliar repository:
Connect -> Understand -> What Matters -> Why -> What Affected -> Mission Compiler -> Observe -> Verify -> Recover -> Checkpoint.
"""

import os
import sys
import tempfile
import shutil
import unittest

from ultron.core.analyzer import analyze_directory
from ultron.core.evidence import compile_repository_evidence
from ultron.core.recommendation import build_consequence_recommendations
from ultron.core.decision_journal import record_recommendation_decision, update_decision_outcome
from ultron.core.agent_context_builder import AgentContextBuilder
from ultron.core.issue_orchestrator import IssueOrchestrator
from ultron.core.issue_memory import IssueRecord
from ultron.core.models import DecisionOutcome

class TestPPC1CreatorWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ultron_ppc1_unit_")
        os.makedirs(os.path.join(self.tmp_dir, "payment"), exist_ok=True)
        os.makedirs(os.path.join(self.tmp_dir, "checkout"), exist_ok=True)
        os.makedirs(os.path.join(self.tmp_dir, "billing"), exist_ok=True)
        os.makedirs(os.path.join(self.tmp_dir, "tests"), exist_ok=True)

        self.payment_py = os.path.join(self.tmp_dir, "payment", "service.py")
        with open(self.payment_py, "w", encoding="utf-8") as f:
            f.write('''"""Payment Processing Core Service."""

def process_transaction(amount, card_token, retry_count=0):
    if amount <= 0:
        raise ValueError("Invalid amount")
    if retry_count > 3:
        raise RuntimeError("Max retries exceeded")
    return {"status": "SUCCESS", "tx_id": "TX-12345", "amount": amount}

def refund_transaction(tx_id):
    return {"status": "REFUNDED", "tx_id": tx_id}
''')

        self.checkout_py = os.path.join(self.tmp_dir, "checkout", "controller.py")
        with open(self.checkout_py, "w", encoding="utf-8") as f:
            f.write('''"""Checkout Controller."""
from payment.service import process_transaction

def handle_checkout(cart, user_token):
    total = sum(item["price"] for item in cart)
    return process_transaction(total, user_token)
''')

        self.billing_py = os.path.join(self.tmp_dir, "billing", "invoices.py")
        with open(self.billing_py, "w", encoding="utf-8") as f:
            f.write('''"""Billing & Invoicing Service."""
from payment.service import process_transaction

def generate_invoice(user_id, amount, token):
    res = process_transaction(amount, token)
    return {"invoice_id": "INV-999", "result": res}
''')

        self.test_py = os.path.join(self.tmp_dir, "tests", "test_payment.py")
        with open(self.test_py, "w", encoding="utf-8") as f:
            f.write('''import unittest
from payment.service import process_transaction

class TestPayment(unittest.TestCase):
    def test_success(self):
        res = process_transaction(100, "tok_valid")
        self.assertEqual(res["status"], "SUCCESS")

    def test_zero_amount(self):
        with self.assertRaises(ValueError):
            process_transaction(0, "tok_valid")

if __name__ == "__main__":
    unittest.main()
''')

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_end_to_end_creator_lifecycle(self):
        # Step 1 & 2: Connect
        self.assertTrue(os.path.isdir(self.tmp_dir))

        # Step 3: Understand
        codebase = analyze_directory(self.tmp_dir)
        bundle = compile_repository_evidence(self.tmp_dir, codebase)
        self.assertGreaterEqual(len(codebase), 3)
        self.assertEqual(bundle.status, "FRESH")

        # Step 4: Decision Surface
        recs = build_consequence_recommendations(codebase, repo_path=self.tmp_dir, evidence_bundle=bundle)
        self.assertGreater(len(recs), 0)
        top_rec = recs[0]
        self.assertIn(top_rec.confidence_tier, ("HIGH", "MEDIUM", "LOW"))

        # Step 5: Record Decision
        dec_rec = record_recommendation_decision(
            repo_path=self.tmp_dir,
            recommendation=top_rec,
            selection_source="HUMAN",
            human_feedback="Accept top architectural recommendation for payment service resilience."
        )
        self.assertTrue(dec_rec.decision_id.startswith("dec-"))

        # Step 6: Mission Compiler
        ctx = AgentContextBuilder.build(
            objective_state={},
            repo_path=self.tmp_dir,
            target_file=top_rec.target_file,
            intent="Harden payment retry resilience.",
            why_this_task_matters=top_rec.why_this,
            codebase_analysis=codebase,
            snapshot_id="snap-ppc1-v1"
        )
        claude_mission = AgentContextBuilder.render_claude(ctx)
        cursor_mission = AgentContextBuilder.render_cursor(ctx)
        self.assertIn("<ultron_mission_envelope", claude_mission)
        self.assertIn("# Cursor Mission Envelope", cursor_mission)

        # Step 7: Handoff to Agent
        orch = IssueOrchestrator(self.tmp_dir)
        issue = IssueRecord(
            issue_id="ISS-PAYMENT-01",
            pillar="FUNCTIONAL",
            component="payment",
            target="payment/service.py",
            failure_class="RETRY_EXHAUSTION",
            symptom="Payment retry lacks backoff",
            reproduction="python -m unittest tests/test_payment.py",
            reproduction_signature="test_payment_retry"
        )
        orch.issue_memory.record_issue(issue)
        orch.select_issue(issue.issue_id)
        mission_res = orch.compile_mission(issue.issue_id)
        self.assertIn("mission_id", mission_res)

        # Step 8 & 9: Observe and Verify Code Change
        target_full_path = os.path.join(self.tmp_dir, issue.target)
        with open(target_full_path, "w", encoding="utf-8") as f:
            f.write('''"""Payment Processing Core Service (Hardened by AI Agent)."""

def process_transaction(amount, card_token, retry_count=0):
    if amount <= 0:
        raise ValueError("Invalid amount")
    if retry_count > 3:
        raise RuntimeError("Max retries exceeded")
    return {"status": "SUCCESS", "tx_id": "TX-12345", "amount": amount, "retries": retry_count}

def refund_transaction(tx_id):
    return {"status": "REFUNDED", "tx_id": tx_id}
''')

        attempt = orch.execute_attempt(modified_files=[issue.target])
        orch.observe_state(
            snapshot_id="snap-ppc1-v2",
            test_results={"executed": True, "passed_count": 2, "failed_count": 0, "failures": []},
            visual_snapshot={"browser_reality": "FULL", "wireframe_fallback": False}
        )
        verified, reasons = orch.verify_attempt()
        self.assertTrue(verified, f"Expected verification to pass, got reasons: {reasons}")
        self.assertTrue(attempt.three_pillar_results["FUNCTIONAL"])
        self.assertTrue(attempt.three_pillar_results["CONNECTIVITY"])

        # Step 10: Human Judged & Tangible Checkpoint
        orch.record_human_judgment(rating="BETTER", rationale="Payment retry successfully hardened.")
        orch.guard_regression_and_advance()
        update_decision_outcome(
            repo_path=self.tmp_dir,
            decision_id=dec_rec.decision_id,
            outcome=DecisionOutcome.RESOLVED.value,
            feedback="Payment retry hardened cleanly."
        )

        ckpt_id = orch.checkpoint_progression(fix_summary="Harden payment service retry logic")
        self.assertTrue(ckpt_id.startswith("CHK-"))

if __name__ == "__main__":
    unittest.main()
