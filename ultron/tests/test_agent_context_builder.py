"""
Unit Test Suite for Decoupled AgentContextBuilder
"""

import unittest
from ultron.core.agent_context_builder import AgentContextBuilder, CanonicalAgentContext


class TestAgentContextBuilder(unittest.TestCase):
    def setUp(self):
        self.sample_objective = {
            "repository_root": "/workspace/my_project",
            "repository_id": "a1b2c3d4e5f6",
            "title": "Build WebSocket Notification Streamer",
            "description": "Stream live order updates to connected browser clients via WebSocket.",
            "progress_pct": 50.0,
            "tasks": [
                {"id": "t1", "title": "Setup WS server endpoint", "status": "done"},
                {"id": "t2", "title": "Implement broadcast hub", "status": "in_progress", "description": "Channel manager"},
                {"id": "t3", "title": "Add client reconnect loop", "status": "pending"}
            ],
            "constraints": [
                "Do not modify auth tokens module",
                "Ensure heartbeat ping every 30s"
            ],
            "acceptance": [
                "Unit tests for broadcast hub pass",
                "Zero memory leaks under 100 connections"
            ],
            "affected_areas": ["interfaces/ws.py", "core/events.py"]
        }
        self.sample_risks = [
            {
                "file": "interfaces/ws.py",
                "complexity": 14,
                "coupling_score": 6.2,
                "level": "HIGH",
                "rationale": "High branching and fanout"
            }
        ]

    def test_canonical_context_construction(self):
        ctx = AgentContextBuilder.build(
            objective_state=self.sample_objective,
            risks=self.sample_risks
        )
        self.assertIsInstance(ctx, CanonicalAgentContext)
        self.assertEqual(ctx.objective_title, "Build WebSocket Notification Streamer")
        self.assertEqual(ctx.progress_pct, 50.0)
        self.assertIsNotNone(ctx.active_task)
        self.assertEqual(ctx.active_task["title"], "Implement broadcast hub")
        self.assertEqual(len(ctx.completed_tasks), 1)
        self.assertEqual(len(ctx.pending_tasks), 1)
        self.assertEqual(len(ctx.boundary_constraints), 2)
        self.assertEqual(len(ctx.acceptance_criteria), 2)
        self.assertEqual(len(ctx.architectural_risks), 1)

    def test_render_markdown(self):
        ctx = AgentContextBuilder.build(self.sample_objective, risks=self.sample_risks)
        md = AgentContextBuilder.render_markdown(ctx)
        self.assertIn("# ULTRON MISSION ENVELOPE", md)
        self.assertIn("Build WebSocket Notification Streamer", md)
        self.assertIn("- [x] Setup WS server endpoint", md)
        self.assertIn("-> **Implement broadcast hub**", md)
        self.assertIn("- [ ] Add client reconnect loop", md)
        self.assertIn("- ⚠️ Do not modify auth tokens module", md)
        self.assertIn("python -m unittest discover -s ultron/tests -p test_*.py", md)

    def test_render_claude(self):
        ctx = AgentContextBuilder.build(self.sample_objective, snapshot_id="snap_cl_99")
        claude_out = AgentContextBuilder.render_claude(ctx)
        self.assertIn('<ultron_mission_envelope snapshot_id="snap_cl_99"', claude_out)
        self.assertIn("<active_task>Implement broadcast hub</active_task>", claude_out)
        self.assertIn("<boundary_rules>", claude_out)
        self.assertIn("Setup WS server endpoint", claude_out)

    def test_render_cursor(self):
        ctx = AgentContextBuilder.build(self.sample_objective, snapshot_id="snap_cur_88")
        cursor_out = AgentContextBuilder.render_cursor(ctx)
        self.assertIn("# SNAPSHOT: snap_cur_88", cursor_out)
        self.assertIn('ACTIVE MILESTONE: "Implement broadcast hub"', cursor_out)
        self.assertIn("CRITICAL RULES:", cursor_out)

    def test_render_codex(self):
        ctx = AgentContextBuilder.build(self.sample_objective, snapshot_id="snap_codex_55")
        codex_out = AgentContextBuilder.render_codex(ctx)
        self.assertIn("# SNAPSHOT: snap_codex_55", codex_out)
        self.assertIn('ACTIVE MILESTONE: "Implement broadcast hub"', codex_out)
        self.assertIn("CRITICAL RULES:", codex_out)

    def test_render_antigravity(self):
        ctx = AgentContextBuilder.build(self.sample_objective, snapshot_id="snap_agy_77")
        agy_out = AgentContextBuilder.render_antigravity(ctx)
        self.assertIn("[UMAGS MISSION ENVELOPE]", agy_out)
        self.assertIn("SNAPSHOT_ID: snap_agy_77", agy_out)
        self.assertIn("TARGET_OBJECTIVE: Build WebSocket Notification Streamer", agy_out)
        self.assertIn("[VERIFICATION_RUNNER]", agy_out)

    def test_render_aider(self):
        ctx = AgentContextBuilder.build(self.sample_objective, snapshot_id="snap_aid_66")
        aider_out = AgentContextBuilder.render_aider(ctx)
        self.assertIn("# Aider Mission Directive", aider_out)
        self.assertIn("Snapshot: snap_aid_66", aider_out)
        self.assertIn("/add interfaces/ws.py", aider_out)


if __name__ == "__main__":
    unittest.main()
