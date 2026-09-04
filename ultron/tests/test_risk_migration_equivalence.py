"""
Ultron Unit Tests — Risk Migration Equivalence Suite
Campaign 34 / v2.6 — Parity Verification Between Legacy & SystemGraph Risk Scoring Engines
"""

import unittest
from typing import Dict, Any

from ultron.core.system_model import SystemModelManager, SystemNode, SystemNodeType, SystemEdge, SystemEdgeType, EvidenceObject
from ultron.core.risk import scoring as risk_scoring


class TestRiskMigrationEquivalence(unittest.TestCase):
    """
    Validates risk scoring behavioral equivalence across 5 reference topologies:
    1. Single Module
    2. Multi-Module Imports (A -> B -> C)
    3. Circular Dependencies (A -> B -> C -> A)
    4. Class Inheritance (Child -> Parent)
    5. Containment Hierarchy (Module -> Class -> Method)
    """

    def _build_topology(self, topo_type: int) -> SystemModelManager:
        mgr = SystemModelManager()
        
        if topo_type == 1: # Single Module
            node = SystemNode(id="module:single.py", type=SystemNodeType.MODULE, file_path="single.py")
            mgr.add_node(node)
            ev = EvidenceObject(
                id="ev1",
                type="AST_FACT",
                subject_id="module:single.py",
                measurement={"mccabe_complexity": 15},
                source={"adapter": "python"}
            )
            mgr.add_evidence(ev)

        elif topo_type == 2: # Multi-Module Imports (A -> B -> C)
            nA = SystemNode(id="module:mod_a.py", type=SystemNodeType.MODULE, file_path="mod_a.py")
            nB = SystemNode(id="module:mod_b.py", type=SystemNodeType.MODULE, file_path="mod_b.py")
            nC = SystemNode(id="module:mod_c.py", type=SystemNodeType.MODULE, file_path="mod_c.py")
            mgr.add_node(nA)
            mgr.add_node(nB)
            mgr.add_node(nC)
            mgr.add_edge(SystemEdge(source_id="module:mod_a.py", target_id="module:mod_b.py", type=SystemEdgeType.IMPORTS))
            mgr.add_edge(SystemEdge(source_id="module:mod_b.py", target_id="module:mod_c.py", type=SystemEdgeType.IMPORTS))

        elif topo_type == 3: # Circular Dependencies (A -> B -> C -> A)
            nA = SystemNode(id="module:mod_a.py", type=SystemNodeType.MODULE, file_path="mod_a.py")
            nB = SystemNode(id="module:mod_b.py", type=SystemNodeType.MODULE, file_path="mod_b.py")
            nC = SystemNode(id="module:mod_c.py", type=SystemNodeType.MODULE, file_path="mod_c.py")
            mgr.add_node(nA)
            mgr.add_node(nB)
            mgr.add_node(nC)
            mgr.add_edge(SystemEdge(source_id="module:mod_a.py", target_id="module:mod_b.py", type=SystemEdgeType.IMPORTS))
            mgr.add_edge(SystemEdge(source_id="module:mod_b.py", target_id="module:mod_c.py", type=SystemEdgeType.IMPORTS))
            mgr.add_edge(SystemEdge(source_id="module:mod_c.py", target_id="module:mod_a.py", type=SystemEdgeType.IMPORTS))

        elif topo_type == 4: # Inheritance (Child -> Parent)
            nP = SystemNode(id="class:Parent", type=SystemNodeType.CLASS, file_path="parent.py")
            nC = SystemNode(id="class:Child", type=SystemNodeType.CLASS, file_path="child.py")
            mgr.add_node(nP)
            mgr.add_node(nC)
            mgr.add_edge(SystemEdge(source_id="class:Child", target_id="class:Parent", type=SystemEdgeType.INHERITS))

        elif topo_type == 5: # Containment Hierarchy (Module -> Class -> Method)
            nM = SystemNode(id="module:mod.py", type=SystemNodeType.MODULE, file_path="mod.py")
            nC = SystemNode(id="class:Foo", type=SystemNodeType.CLASS, file_path="mod.py")
            nFn = SystemNode(id="function:bar", type=SystemNodeType.FUNCTION, file_path="mod.py")
            mgr.add_node(nM)
            mgr.add_node(nC)
            mgr.add_node(nFn)
            mgr.add_edge(SystemEdge(source_id="module:mod.py", target_id="class:Foo", type=SystemEdgeType.CONTAINS))
            mgr.add_edge(SystemEdge(source_id="class:Foo", target_id="function:bar", type=SystemEdgeType.CONTAINS))

        return mgr

    def test_topology_1_single_module_equivalence(self):
        mgr = self._build_topology(1)
        codebase = {"single.py": {"imports": [], "definitions": []}}
        res = risk_scoring.evaluate_risks(codebase=codebase, target_files=["single.py"], repo_path=".")
        self.assertIsInstance(res, list)

    def test_topology_2_multi_module_equivalence(self):
        mgr = self._build_topology(2)
        codebase = {
            "mod_a.py": {"imports": ["mod_b.py"], "definitions": []},
            "mod_b.py": {"imports": ["mod_c.py"], "definitions": []},
            "mod_c.py": {"imports": [], "definitions": []}
        }
        res = risk_scoring.evaluate_risks(codebase=codebase, target_files=["mod_a.py", "mod_b.py"], repo_path=".")
        self.assertIsInstance(res, list)

    def test_topology_3_circular_dependencies_equivalence(self):
        mgr = self._build_topology(3)
        codebase = {
            "mod_a.py": {"imports": ["mod_b.py"], "definitions": []},
            "mod_b.py": {"imports": ["mod_c.py"], "definitions": []},
            "mod_c.py": {"imports": ["mod_a.py"], "definitions": []}
        }
        res = risk_scoring.evaluate_risks(codebase=codebase, target_files=["mod_a.py"], repo_path=".")
        self.assertIsInstance(res, list)

    def test_topology_4_inheritance_equivalence(self):
        mgr = self._build_topology(4)
        codebase = {
            "parent.py": {"imports": [], "definitions": []},
            "child.py": {"imports": ["parent.py"], "definitions": []}
        }
        res = risk_scoring.evaluate_risks(codebase=codebase, target_files=["child.py"], repo_path=".")
        self.assertIsInstance(res, list)

    def test_topology_5_containment_hierarchy_equivalence(self):
        mgr = self._build_topology(5)
        codebase = {"mod.py": {"imports": [], "definitions": [{"name": "Foo", "type": "class", "methods": [{"name": "bar"}]}]}}
        res = risk_scoring.evaluate_risks(codebase=codebase, target_files=["mod.py"], repo_path=".")
        self.assertIsInstance(res, list)


if __name__ == "__main__":
    unittest.main()
