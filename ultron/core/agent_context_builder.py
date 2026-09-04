"""
Ultron Core — Agent Context Builder (v2.6.1)
Decoupled context projection layer that combines human objective state (ObjectiveTracker)
with repository architectural topology (SystemGraph) and evidence into canonical,
provider-neutral context payloads with renderers for Claude, Cursor, Antigravity, and Aider.
Includes explicit snapshot grounding, revision tracking, and generation timestamps.
"""

import os
import ast
import html
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class CanonicalAgentContext:
    repository_root: str
    repository_id: str
    objective_title: str
    objective_description: str
    progress_pct: float
    active_task: Optional[Dict[str, Any]]
    completed_tasks: List[Dict[str, Any]] = field(default_factory=list)
    pending_tasks: List[Dict[str, Any]] = field(default_factory=list)
    boundary_constraints: List[str] = field(default_factory=list)
    forbidden_changes: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    affected_components: List[str] = field(default_factory=list)
    relevant_dependencies: List[str] = field(default_factory=list)
    architectural_risks: List[Dict[str, Any]] = field(default_factory=list)
    verification_command: str = "python verify_release.py"
    next_safe_action: str = "Implement active milestone and verify"
    mission_intent: str = ""
    why_this_task_matters: str = ""
    snapshot_id: str = "unknown"
    model_hash: str = ""
    repository_revision: str = ""
    generated_at: str = ""
    evidence_sources: List[str] = field(default_factory=list)
    known_limitations: List[str] = field(default_factory=list)
    mission_validity: Dict[str, Any] = field(default_factory=dict)
    issue_id: str = ""
    reproduction_signature: str = ""
    execution_trace: Optional[Dict[str, Any]] = None
    decision_id: str = ""
    recommendation_id: str = ""

    def semantic_mission_hash(self) -> str:
        """
        Computes SHA-256 hash of semantic mission identity.
        Invariance guarantee:
            SemanticMission(provider A).semantic_mission_hash() == SemanticMission(provider B).semantic_mission_hash()
        """
        import hashlib, json
        semantic_payload = {
            "mission_intent": self.mission_intent,
            "target_files": sorted([str(f).replace("\\", "/") for f in self.affected_components]),
            "forbidden_boundaries": sorted([str(f).replace("\\", "/") for f in self.forbidden_changes]),
            "acceptance_criteria": sorted(self.acceptance_criteria),
            "issue_id": self.issue_id,
            "reproduction_signature": self.reproduction_signature,
            "why_this_task_matters": self.why_this_task_matters,
        }
        serialized = json.dumps(semantic_payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


class AgentContextBuilder:
    """
    Synthesizes grounded Mission Envelope packages for external AI coding agents.
    Supports objective-based context generation and automated file-level self-healing missions.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    # -------------------------------------------------------------------------
    # AST Extraction and Static Analysis Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _compute_ast_mccabe(cls, node: ast.AST) -> int:
        """
        Computes McCabe cyclomatic complexity for an AST node or subtree.
        Base complexity starts at 1, increasing with decision points.
        """
        complexity = 1
        decision_nodes = (
            ast.If, ast.For, ast.AsyncFor, ast.While,
            ast.ExceptHandler, ast.With, ast.AsyncWith,
            ast.IfExp, ast.Assert
        )
        if hasattr(ast, "match_case"):
            decision_nodes += (ast.match_case,)
        if hasattr(ast, "MatchCase"):
            decision_nodes += (ast.MatchCase,)

        for child in ast.walk(node):
            if isinstance(child, decision_nodes):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += max(0, len(child.values) - 1)
        return complexity

    @classmethod
    def extract_ast_facts(cls, file_path: str) -> Dict[str, Any]:
        """
        Extracts comprehensive AST facts from a Python source file:
        - line_count: Total physical lines
        - imports: Sorted list of imported modules and qualified names (fan-out)
        - functions: List of function/method definitions with name, lineno, args, and per-function McCabe complexity
        - max_complexity: Maximum McCabe cyclomatic complexity found in any function/block
        - file_complexity: Overall file McCabe cyclomatic complexity
        """
        if not file_path or not os.path.exists(file_path):
            return {
                "line_count": 0,
                "imports": [],
                "functions": [],
                "max_complexity": 1,
                "file_complexity": 1,
                "error": f"File not found: {file_path}"
            }

        try:
            with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
                source = f.read()
        except Exception as e:
            return {
                "line_count": 0,
                "imports": [],
                "functions": [],
                "max_complexity": 1,
                "file_complexity": 1,
                "error": f"Failed to read file: {e}"
            }

        lines = source.splitlines()
        line_count = len(lines)

        try:
            tree = ast.parse(source)
        except Exception as e:
            return {
                "line_count": line_count,
                "imports": [],
                "functions": [],
                "max_complexity": 1,
                "file_complexity": 1,
                "error": f"AST parse error: {e}"
            }

        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.add(n.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for n in node.names:
                    imports.add(f"{mod}.{n.name}" if mod else n.name)

        functions = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                posonly = [a.arg for a in getattr(node.args, "posonlyargs", [])]
                regular = [a.arg for a in node.args.args]
                vararg = [f"*{node.args.vararg.arg}"] if getattr(node.args, "vararg", None) else []
                kwonly = [a.arg for a in getattr(node.args, "kwonlyargs", [])]
                kwarg = [f"**{node.args.kwarg.arg}"] if getattr(node.args, "kwarg", None) else []
                args = posonly + regular + vararg + kwonly + kwarg
                fn_comp = cls._compute_ast_mccabe(node)
                functions.append({
                    "name": node.name,
                    "type": "function",
                    "lineno": node.lineno,
                    "args": args,
                    "complexity": fn_comp
                })
            elif isinstance(node, ast.ClassDef):
                class_name = node.name
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        posonly = [a.arg for a in getattr(child.args, "posonlyargs", [])]
                        regular = [a.arg for a in child.args.args]
                        vararg = [f"*{child.args.vararg.arg}"] if getattr(child.args, "vararg", None) else []
                        kwonly = [a.arg for a in getattr(child.args, "kwonlyargs", [])]
                        kwarg = [f"**{child.args.kwarg.arg}"] if getattr(child.args, "kwarg", None) else []
                        args = posonly + regular + vararg + kwonly + kwarg
                        m_comp = cls._compute_ast_mccabe(child)
                        functions.append({
                            "name": f"{class_name}.{child.name}",
                            "type": "method",
                            "lineno": child.lineno,
                            "args": args,
                            "complexity": m_comp
                        })

        max_comp = max((f["complexity"] for f in functions), default=1)
        file_comp = cls._compute_ast_mccabe(tree)

        return {
            "line_count": line_count,
            "imports": sorted(list(imports)),
            "functions": functions,
            "max_complexity": max_comp,
            "file_complexity": file_comp
        }

    # -------------------------------------------------------------------------
    # Git Co-Change & Hub Protection Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def extract_co_change_companions(
        cls,
        repo_path: str,
        target_file: str,
        threshold: float = 0.50
    ) -> List[Dict[str, Any]]:
        """
        Queries GitEvidenceAdapter to identify files frequently modified together with target_file (co-change ratio >= threshold).
        """
        try:
            from ultron.core.git_adapter import GitEvidenceAdapter
            adapter = GitEvidenceAdapter()
            git_analysis = adapter.analyze_repository(repo_path)
        except Exception:
            return []

        co_matrix = git_analysis.get("co_change_matrix", {})
        files_data = git_analysis.get("files", {})

        norm_target = os.path.normpath(target_file).replace("\\", "/").lstrip("./")
        
        co_changes = co_matrix.get(norm_target, [])
        if not co_changes:
            for f_key, partners in co_matrix.items():
                if f_key == norm_target or f_key.endswith(f"/{norm_target}") or norm_target.endswith(f"/{f_key}"):
                    co_changes = partners
                    break

        if not co_changes and norm_target in files_data:
            co_changes = files_data[norm_target].get("co_changes", [])

        companions = []
        for entry in co_changes:
            partner_file = str(entry.get("file", "")).replace("\\", "/").lstrip("./")
            ratio = float(entry.get("co_change_ratio", 0.0))
            if partner_file and partner_file != norm_target and ratio >= threshold:
                companions.append({
                    "file": partner_file,
                    "co_change_ratio": ratio,
                    "joint_commits": entry.get("joint_commits", 0)
                })

        companions.sort(key=lambda x: (x["co_change_ratio"], x["joint_commits"]), reverse=True)
        return companions

    @classmethod
    def get_protected_architectural_hubs(
        cls,
        repo_path: str,
        target_files: List[str]
    ) -> List[str]:
        """
        Identifies central architectural hubs that must be protected from accidental modification.
        Excludes target files from the forbidden list to maintain mission validity without contradiction.
        """
        standard_core_hubs = [
            "models.py",
            "server.py",
            "app.py",
            "main.py",
            "ultron/core/models.py",
            "ultron/core/system_model.py",
            "ultron/interfaces/server.py",
            "ultron/core/analyzer.py",
            "ultron/core/git_adapter.py",
            "ultron/core/agent_context_builder.py"
        ]
        
        norm_targets = set(os.path.normpath(t).replace("\\", "/").lstrip("./").lower() for t in target_files)
        
        forbidden = []
        for hub in standard_core_hubs:
            hub_norm = os.path.normpath(hub).replace("\\", "/").lstrip("./")
            hub_norm_lower = hub_norm.lower()
            abs_hub = os.path.join(repo_path, hub_norm)
            if os.path.exists(abs_hub) or os.path.exists(os.path.join(repo_path, hub)):
                is_target = any(
                    hub_norm_lower == t or hub_norm_lower.endswith(f"/{t}") or t.endswith(f"/{hub_norm_lower}")
                    for t in norm_targets
                )
                if not is_target:
                    forbidden.append(hub_norm)

        return sorted(list(set(forbidden)))

    # -------------------------------------------------------------------------
    # Automated File Mission Synthesizer
    # -------------------------------------------------------------------------

    @classmethod
    def build_file_mission(
        cls,
        repo_path: str,
        target_file: str,
        co_change_threshold: float = 0.50,
        complexity_threshold: int = 8,
        custom_forbidden: Optional[List[str]] = None,
        custom_verification: Optional[str] = None
    ) -> CanonicalAgentContext:
        """
        Synthesizes a grounded, bounded self-healing refactoring mission for a specific target file:
        1. Extracts AST facts (line count, fan-out imports, functions, McCabe complexity).
        2. Extracts co-change companions with ratio >= 0.50 from GitEvidenceAdapter.
        3. Identifies high-complexity functions (> 8) and creates focused refactoring tasks.
        4. Sets strict bounded scope: TARGET_FILES = [target_file, co_change_partners].
        5. Sets protected forbidden scope: Core architectural hubs (e.g. models.py, server.py if not target).
        6. Formulates concrete acceptance criteria and combined verification command.
        """
        norm_target = os.path.normpath(target_file).replace("\\", "/").lstrip("./")
        abs_target = os.path.join(repo_path, norm_target) if not os.path.isabs(target_file) else os.path.normpath(target_file)

        # 1. AST Facts Extraction
        ast_facts = cls.extract_ast_facts(abs_target)
        functions = ast_facts.get("functions", [])
        imports = ast_facts.get("imports", [])
        line_count = ast_facts.get("line_count", 0)
        max_comp = ast_facts.get("max_complexity", 1)

        # 2. Co-Change Companions (ratio >= 0.50)
        companions = cls.extract_co_change_companions(
            repo_path=repo_path,
            target_file=norm_target,
            threshold=co_change_threshold
        )
        co_change_files = [c["file"] for c in companions if c["file"] != norm_target]

        # 3. Scope Definition: Target and Co-Change Partners
        bounded_targets = [norm_target] + [f for f in co_change_files if f != norm_target]

        # 4. Protected Forbidden Hubs
        protected_hubs = cls.get_protected_architectural_hubs(repo_path, bounded_targets)
        if custom_forbidden:
            for cf in custom_forbidden:
                cf_norm = os.path.normpath(cf).replace("\\", "/").lstrip("./")
                if cf_norm not in bounded_targets and cf_norm not in protected_hubs:
                    protected_hubs.append(cf_norm)

        # 5. Task Synthesis for High Complexity Functions (> 8)
        high_comp_funcs = [f for f in functions if f["complexity"] > complexity_threshold]
        high_comp_funcs.sort(key=lambda x: x["complexity"], reverse=True)

        tasks = []
        if high_comp_funcs:
            for idx, fn in enumerate(high_comp_funcs):
                tasks.append({
                    "id": f"task_{idx + 1}",
                    "title": f"Refactor '{fn['name']}' to reduce decision branches from {fn['complexity']} to <= {complexity_threshold}",
                    "status": "in_progress" if idx == 0 else "pending",
                    "description": (
                        f"Decompose nested decision branching in '{fn['name']}' (line {fn['lineno']}), "
                        f"extract single-purpose helper subroutines, and isolate control flow while "
                        f"strictly preserving external interfaces and parameter contracts."
                    ),
                    "file": norm_target,
                    "function": fn["name"],
                    "current_complexity": fn["complexity"],
                    "target_complexity": complexity_threshold
                })
            tasks.append({
                "id": f"task_{len(high_comp_funcs) + 1}",
                "title": "Verify regression-free behavior and run Ultron quality gate",
                "status": "pending",
                "description": (
                    f"Execute test runner and Ultron architectural quality gate to confirm zero "
                    f"behavioral or boundary regressions across {norm_target} and companions."
                ),
                "file": norm_target
            })
        else:
            tasks = [
                {
                    "id": "task_1",
                    "title": f"Audit and optimize '{norm_target}' modularity",
                    "status": "in_progress",
                    "description": (
                        f"Review {norm_target} ({line_count} LOC, {len(functions)} functions, "
                        f"max decision complexity {max_comp} branches) and maintain clean boundary encapsulation."
                    ),
                    "file": norm_target
                },
                {
                    "id": "task_2",
                    "title": "Run regression test suite and quality verification",
                    "status": "pending",
                    "description": "Execute test suite and Ultron quality gate to verify zero regressions.",
                    "file": norm_target
                }
            ]

        # 6. Boundary Constraints & Acceptance Criteria
        companion_desc = f" ({', '.join(co_change_files)})" if co_change_files else ""
        boundary_constraints = [
            f"Scope strictly bounded to target file '{norm_target}' and co-change companions{companion_desc}.",
            "Preserve all public function and class signatures without breaking backward compatibility.",
            f"Enforce decision complexity <= {complexity_threshold} branches for all modified functions.",
            "Do not introduce circular import dependencies or foreign coupling."
        ]

        acceptance_criteria = [
            f"Decision complexity of all functions in '{norm_target}' is strictly <= {complexity_threshold} branches.",
            f"All public class and function signatures in '{norm_target}' remain backwards-compatible.",
            f"Co-change synchronization verified for target and companions: {', '.join(bounded_targets)}.",
            "All unit and integration tests pass with zero regressions.",
            "Ultron architectural quality gate passes with zero policy violations."
        ]

        # 7. Verification Command Formulation
        if custom_verification:
            verify_cmd = custom_verification
        elif os.path.exists(os.path.join(repo_path, "ultron", "tests")):
            verify_cmd = "python -m unittest discover -s ultron/tests -p test_*.py && ultron gate"
        elif os.path.exists(os.path.join(repo_path, "tests")):
            verify_cmd = "python -m unittest discover -s tests -p test_*.py && ultron gate"
        elif os.path.exists(os.path.join(repo_path, "pytest.ini")) or os.path.exists(os.path.join(repo_path, "pyproject.toml")):
            verify_cmd = "pytest && ultron gate"
        else:
            verify_cmd = "python -m unittest && ultron gate"

        active_fn_str = f"'{high_comp_funcs[0]['name']}'" if high_comp_funcs else f"'{norm_target}'"
        next_safe_action = (
            f"Decompose {active_fn_str} in '{norm_target}' to reduce branching complexity <= {complexity_threshold}"
            if high_comp_funcs else f"Audit and verify '{norm_target}'"
        )
        why_task_matters = (
            f"Target file '{norm_target}' contains {len(high_comp_funcs)} function(s) exceeding complexity ceiling (> {complexity_threshold}) "
            f"with max McCabe complexity {max_comp}, creating defect hotspots and maintenance drag."
            if high_comp_funcs else f"Target file '{norm_target}' is within safe complexity bounds; maintaining modularity."
        )

        objective_state = {
            "repository_root": repo_path,
            "repository_id": os.path.basename(os.path.abspath(repo_path)) or "unknown_repo",
            "title": f"Targeted Refactoring & Complexity Containment: {norm_target}",
            "description": (
                f"Focused architectural refactoring for {norm_target} ({line_count} LOC, "
                f"{len(functions)} definitions, {len(imports)} fan-out imports, {len(high_comp_funcs)} high-complexity functions, "
                f"{len(co_change_files)} co-change companions)."
            ),
            "progress_pct": 0.0,
            "tasks": tasks,
            "constraints": boundary_constraints,
            "acceptance": acceptance_criteria,
            "affected_areas": bounded_targets,
            "verification_command": verify_cmd
        }

        architectural_risks = [
            {
                "file": norm_target,
                "complexity": max_comp,
                "coupling_score": len(imports),
                "level": "HIGH" if max_comp > 12 or len(high_comp_funcs) > 0 else "MEDIUM",
                "rationale": (
                    f"Decision complexity: {max_comp} branches, High-complexity functions (> {complexity_threshold}): {len(high_comp_funcs)}, "
                    f"Connected imports: {len(imports)}, Co-change companions: {len(co_change_files)}"
                )
            }
        ]

        return cls.build(
            objective_state=objective_state,
            repo_path=repo_path,
            target_file=norm_target,
            forbidden_changes=protected_hubs,
            relevant_dependencies=imports,
            mission_intent=f"Refactor '{norm_target}' to reduce decision branches below {complexity_threshold} and maintain architectural invariants.",
            why_this_task_matters=why_task_matters,
            next_safe_action=next_safe_action,
            risks=architectural_risks,
            evidence_sources=[
                "Static Code Analysis (Functions, Decision Branches, Connected Imports)",
                "GitEvidenceAdapter (Co-Change Coupling >= 0.50)",
                "Ultron Architectural Governance Quality Gate"
            ],
            known_limitations=[
                "Static AST extraction only; dynamic runtime dispatch and external side effects must be verified via test suite.",
                "Co-change companions are included in bounded scope to prevent out-of-sync regressions."
            ]
        )

    # -------------------------------------------------------------------------
    # Mission Validation and Core Builder Methods
    # -------------------------------------------------------------------------
    @classmethod
    def validate_mission(
        cls,
        target_file: Optional[str] = None,
        intent: Optional[str] = None,
        acceptance_criteria: Optional[List[str]] = None,
        affected_areas: Optional[List[str]] = None,
        forbidden_changes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Canonical 3-tier mission validity and actionability evaluator.
        Classifications:
          1. INCOMPLETE: Missing target file or missing intent.
          2. CONTRADICTION: Target files overlap with forbidden changes.
          3. WEAK: Syntactically present but lacks concrete structural outcome or measurable acceptance criteria.
          4. READY: Actionable target, descriptive intent, concrete acceptance criteria, and verification path.

        Returns:
            {
                "status": "READY" | "WEAK" | "INCOMPLETE" | "CONTRADICTION",
                "is_valid": bool,
                "is_actionable": bool,
                "missing": List[str],
                "warnings": List[str],
                "message": str
            }
        """
        missing = []
        warnings = []
        has_target = bool(target_file and str(target_file).strip()) or bool(affected_areas and len(affected_areas) > 0)
        clean_intent = str(intent).strip() if intent else ""
        
        if not has_target:
            missing.append("target_file")
        if not clean_intent:
            missing.append("intent")

        if missing:
            return {
                "status": "INCOMPLETE",
                "is_valid": False,
                "is_actionable": False,
                "missing": missing,
                "warnings": ["Mission requires a specific target file and an objective intent."],
                "message": f"Mission incomplete (Missing: {', '.join(missing)})"
            }

        # Contradiction Check: Target file or affected area must not be forbidden
        if forbidden_changes:
            targets_to_check = set()
            if target_file and str(target_file).strip():
                targets_to_check.add(str(target_file).strip().replace("\\", "/").lower())
            for a in (affected_areas or []):
                targets_to_check.add(str(a).strip().replace("\\", "/").lower())

            for f in forbidden_changes:
                f_norm = str(f).strip().replace("\\", "/").lower()
                for t in targets_to_check:
                    if f_norm == t or t.endswith(f"/{f_norm}") or f_norm.endswith(f"/{t}"):
                        return {
                            "status": "CONTRADICTION",
                            "is_valid": False,
                            "is_actionable": False,
                            "missing": [],
                            "warnings": [f"Target file '{t}' is explicitly listed in forbidden_changes ({f})."],
                            "message": f"Mission contradiction: Target file '{t}' is marked forbidden."
                        }

        # Structural Quality Evaluation (Differentiating WEAK from READY)
        generic_intents = {
            "fix stuff", "make better", "improve code", "do refactor", "fix", "update", 
            "refactor", "clean code", "work on it", "improve architecture", "enhance system"
        }
        trivial_acceptance = {
            "works", "pass", "ok", "done", "tests", "test pass", "tests pass", "fixed",
            "system works correctly", "works correctly", "everything works", "it works",
            "make it work", "code is clean", "no errors", "system works"
        }

        clean_intent_lower = clean_intent.lower()
        if len(clean_intent) < 15 or clean_intent_lower in generic_intents:
            warnings.append("Intent is generic or underspecified; specify concrete architectural change.")

        has_concrete_acceptance = False
        if acceptance_criteria is not None:
            if len(acceptance_criteria) == 0:
                warnings.append("No acceptance criteria defined; add measurable outcomes.")
            else:
                for crit in acceptance_criteria:
                    c_clean = str(crit).strip().lower()
                    if c_clean and c_clean not in trivial_acceptance and len(c_clean) > 12:
                        # Check for actionable verification nouns/verbs
                        has_concrete_acceptance = True
                if not has_concrete_acceptance:
                    warnings.append("Acceptance criteria are placeholder/trivial; add verifiable assertions.")
        else:
            # When acceptance_criteria is not passed, check if intent contains concrete outcome
            has_concrete_acceptance = len(clean_intent) >= 25 and any(w in clean_intent_lower for w in ["so that", "to prevent", "ensuring", "implement", "enforce", "resolve", "without", "expose", "verify"])
            if not has_concrete_acceptance:
                warnings.append("Intent lacks verifiable outcome clause (e.g. 'so that...', 'to prevent...'); add acceptance criteria.")

        if warnings:
            return {
                "status": "WEAK",
                "is_valid": True,
                "is_actionable": False,
                "missing": [],
                "warnings": warnings,
                "message": f"Mission weak: {warnings[0]}"
            }

        return {
            "status": "READY",
            "is_valid": True,
            "is_actionable": True,
            "missing": [],
            "warnings": [],
            "message": "Mission is complete, compiler-bounded, and actionable"
        }
    @classmethod
    def _extract_tasks(cls, objective_state: Dict[str, Any]):
        """Partitions tasks into completed, in_progress, and pending."""
        tasks = objective_state.get("tasks", [])
        completed = [t for t in tasks if t.get("status") == "done"]
        in_prog = [t for t in tasks if t.get("status") == "in_progress"]
        pending = [t for t in tasks if t.get("status") == "pending"]
        active_task = in_prog[0] if in_prog else (pending[0] if pending else None)
        if not in_prog and pending:
            pending = pending[1:]
        return completed, pending, active_task

    @classmethod
    def _extract_forbidden_files(cls, objective_state: Dict[str, Any], forbidden_changes: Optional[List[str]]) -> List[str]:
        """Derives forbidden files list from explicit constraints and arguments."""
        forbidden = list(forbidden_changes or [])
        constraints = list(objective_state.get("constraints", []))
        for c in constraints:
            c_str = str(c).lower()
            if any(k in c_str for k in ("do not modify", "forbidden", "protect")):
                for p in c_str.split():
                    if ("." in p and "/" in p) or p.endswith(".py") or p.endswith(".js"):
                        cleaned_p = p.strip("',\":;()[]").replace("\\", "/")
                        if cleaned_p not in forbidden:
                            forbidden.append(cleaned_p)
        return forbidden

    @classmethod
    def _extract_relevant_risks(cls, risks: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Filters architectural risk hotspots for high complexity or coupling."""
        relevant_risks = []
        if risks:
            for r in risks:
                fp = str(r.get("file") or r.get("file_path") or "").replace("\\", "/")
                comp = r.get("complexity", 1)
                coup = r.get("coupling_score", 0)
                if comp >= 6 or coup >= 3 or r.get("level") == "HIGH":
                    relevant_risks.append({
                        "file": fp,
                        "complexity": comp,
                        "coupling": round(coup, 1),
                        "level": r.get("level", "MEDIUM"),
                        "rationale": r.get("rationale") or f"McCabe complexity: {comp}, Coupling: {coup}"
                    })
        return relevant_risks

    @classmethod
    def build(
        cls,
        objective_state: Dict[str, Any],
        repo_path: str = ".",
        codebase_analysis: Optional[Dict[str, Any]] = None,
        risks: Optional[List[Dict[str, Any]]] = None,
        snapshot_id: Optional[str] = None,
        model_hash: Optional[str] = None,
        repository_revision: Optional[str] = None,
        evidence_sources: Optional[List[str]] = None,
        known_limitations: Optional[List[str]] = None,
        mission_intent: Optional[str] = None,
        why_this_task_matters: Optional[str] = None,
        forbidden_changes: Optional[List[str]] = None,
        relevant_dependencies: Optional[List[str]] = None,
        next_safe_action: Optional[str] = None,
        target_file: Optional[str] = None,
        intent: Optional[str] = None,
        issue_id: Optional[str] = None,
        reproduction_signature: Optional[str] = None,
        execution_trace: Optional[Dict[str, Any]] = None
    ) -> CanonicalAgentContext:
        """Constructs a CanonicalAgentContext Mission Envelope from objective state and repository facts."""
        obj = objective_state or {}
        completed, pending, active_task = cls._extract_tasks(obj)
        effective_intent = intent or mission_intent
        
        if target_file:
            affected = [str(target_file).replace("\\", "/")]
        else:
            affected = [str(a).replace("\\", "/") for a in obj.get("affected_areas", [])]
            
        forbidden = cls._extract_forbidden_files(obj, forbidden_changes)
        constraints = list(obj.get("constraints", []))

        deps_set = set(relevant_dependencies or [])
        if codebase_analysis and "files" in codebase_analysis:
            files_dict = codebase_analysis.get("files", {})
            for aff in affected:
                if aff in files_dict:
                    for imp in files_dict[aff].get("imports", []):
                        deps_set.add(str(imp).replace("\\", "/"))

        relevant_risks = cls._extract_relevant_risks(risks)

        # Resolve snapshot identity, model hash, and revision
        resolved_snapshot = snapshot_id or (codebase_analysis.get("snapshot_id") if codebase_analysis else None) or (codebase_analysis.get("content_hash") if codebase_analysis else None) or "snap_initial"
        resolved_model_hash = model_hash or (codebase_analysis.get("model_hash") if codebase_analysis else None) or ""
        resolved_revision = repository_revision or obj.get("repository_id") or "rev_head"
        resolved_time = datetime.now(timezone.utc).isoformat()
        resolved_evidence = evidence_sources or ["AST Static Analysis", "SystemGraph Dependency Topology", "Objective State Ledger"]
        resolved_limitations = known_limitations or ["Local repository facts only; external dynamic runtime behaviors not evaluated"]

        # Derive why task matters and next action
        active_title = active_task.get("title", "") if active_task else "Objective Complete"
        resolved_why = why_this_task_matters or f"Required milestone to advance objective '{obj.get('title', '')}' without violating architectural boundaries."
        resolved_mission = effective_intent or obj.get("description", "") or obj.get("title", "Active Development Mission")
        resolved_next = next_safe_action or (f"Implement '{active_title}', run tests, and verify Continuation Readiness." if active_task else "Objective complete — run full release verification.")
        validity = cls.validate_mission(
            target_file=affected[0] if affected else (active_task.get("file") if active_task else None),
            intent=resolved_mission,
            acceptance_criteria=list(obj.get("acceptance", [])),
            affected_areas=affected,
            forbidden_changes=forbidden
        )

        # Dynamically infer repository verification command
        custom_verify = obj.get("verification_command")
        if custom_verify:
            verify_cmd = str(custom_verify)
        elif os.path.exists(os.path.join(repo_path, "ultron", "tests")):
            verify_cmd = "python -m unittest discover -s ultron/tests -p test_*.py"
        elif os.path.exists(os.path.join(repo_path, "tests")):
            verify_cmd = "python -m unittest discover -s tests -p test_*.py"
        elif os.path.exists(os.path.join(repo_path, "test")):
            verify_cmd = "python -m unittest discover -s test -p test_*.py"
        elif os.path.exists(os.path.join(repo_path, "pytest.ini")) or os.path.exists(os.path.join(repo_path, "pyproject.toml")):
            verify_cmd = "pytest"
        else:
            verify_cmd = "python -m unittest"

        effective_acceptance = list(obj.get("acceptance", []))
        if reproduction_signature:
            sig_req = f"Reproduction signature '{reproduction_signature}' must be eliminated and verified non-reproducible."
            if not any(reproduction_signature in str(a) for a in effective_acceptance):
                effective_acceptance.insert(0, sig_req)

        return CanonicalAgentContext(
            repository_root=str(obj.get("repository_root", repo_path)).replace("\\", "/"),
            repository_id=str(obj.get("repository_id", "unknown_repo")),
            objective_title=obj.get("title", "Active Development Objective"),
            objective_description=obj.get("description", ""),
            progress_pct=float(obj.get("progress_pct", 0.0)),
            active_task=active_task,
            completed_tasks=completed,
            pending_tasks=pending,
            boundary_constraints=constraints,
            forbidden_changes=forbidden,
            acceptance_criteria=effective_acceptance,
            affected_components=affected,
            relevant_dependencies=sorted(list(deps_set)),
            architectural_risks=relevant_risks,
            verification_command=verify_cmd,
            next_safe_action=resolved_next,
            mission_intent=resolved_mission,
            why_this_task_matters=resolved_why,
            snapshot_id=str(resolved_snapshot),
            model_hash=str(resolved_model_hash),
            repository_revision=str(resolved_revision),
            generated_at=resolved_time,
            evidence_sources=resolved_evidence,
            known_limitations=resolved_limitations,
            mission_validity=validity,
            issue_id=str(issue_id or obj.get("issue_id", "")),
            reproduction_signature=str(reproduction_signature or obj.get("reproduction_signature", "")),
            execution_trace=execution_trace or obj.get("execution_trace")
        )

    @classmethod
    def render_markdown(cls, ctx: CanonicalAgentContext) -> str:
        """Standard Markdown Mission Envelope."""
        completed_lines = "\n".join(f"- [x] {t.get('title')}" for t in ctx.completed_tasks) or "- (None yet)"
        pending_lines = "\n".join(f"- [ ] {t.get('title')}" for t in ctx.pending_tasks) or "- (Final milestone)"
        constraint_lines = "\n".join(f"- ⚠️ {c}" for c in ctx.boundary_constraints) or "- Maintain backward compatibility."
        forbidden_lines = "\n".join(f"- 🚫 `{f}`" for f in ctx.forbidden_changes) or "- None declared"
        acceptance_lines = "\n".join(f"- [ ] {a}" for a in ctx.acceptance_criteria) or "- [ ] All unit tests pass with zero regressions."
        deps_lines = "\n".join(f"- `{d}`" for d in ctx.relevant_dependencies) or "- Standard library / internal core"
        target_lines = "\n".join(f"- `{t}`" for t in ctx.affected_components) or "- (Determined during execution)"
        
        risk_lines = ""
        if ctx.architectural_risks:
            risk_lines = "\n## Architectural Risk Hotspots\n" + "\n".join(
                f"- `{r['file']}`: {r['rationale']}" for r in ctx.architectural_risks
            )

        active_title = ctx.active_task.get("title", "Proceed with implementation") if ctx.active_task else "Objective Complete"
        active_desc = ctx.active_task.get("description", "") if ctx.active_task else ""

        trace_section = ""
        if ctx.execution_trace:
            tr = ctx.execution_trace
            trace_section = f"""
---

## 6. Execution Reality Trace (Observed Runtime Chain)
- **Trace ID**: `{tr.get('trace_id', 'TRACE-001')}`
- **User Trigger**: {tr.get('trigger', 'N/A')} (`{tr.get('element', 'N/A')}`)
- **State Trajectory**: `{tr.get('state_before', 'UNKNOWN')}` -> `{tr.get('state_after', 'UNKNOWN')}`
- **Failure Point**: `{tr.get('failure_point') or 'None (Clean Baseline)'}`
- **Root Cause**: `{tr.get('root_cause') or 'Under Investigation'}`
- **Result**: `{tr.get('result', 'PASS')}`
"""

        return f"""<!-- ULTRON MISSION ENVELOPE | SNAPSHOT: {ctx.snapshot_id} | MODEL_HASH: {ctx.model_hash or 'N/A'} | REVISION: {ctx.repository_revision} | TIMESTAMP: {ctx.generated_at} -->
# ULTRON MISSION ENVELOPE

**Mission Intent**: {ctx.mission_intent}
**Current Objective**: {ctx.objective_title} ({ctx.progress_pct}% Complete)
**Repository Root**: `{ctx.repository_root}` (ID: `{ctx.repository_id}`)
**Grounded Snapshot**: `{ctx.snapshot_id}` (Model: `{ctx.model_hash or 'N/A'}`)

---

## 1. Current Focus Milestone
-> **{active_title}**
{f'*{active_desc}*' if active_desc else ''}

**Why This Task Matters**:
{ctx.why_this_task_matters}

**Next Recommended Action**:
`{ctx.next_safe_action}`

---

## 2. Hard Boundaries & Forbidden Files
**Strict Constraints**:
{constraint_lines}

**Forbidden Modifications**:
{forbidden_lines}

---

## 3. Grounded Architecture Facts
**Declared Target Files**:
{target_lines}

**Relevant Dependencies**:
{deps_lines}
{risk_lines}

---

## 4. Completed Work vs. Upcoming
**Completed Milestones**:
{completed_lines}

**Upcoming Milestones**:
{pending_lines}

---

## 5. Acceptance Criteria & Verification Command
**Acceptance Criteria**:
{acceptance_lines}

**Verification Command**:
```bash
{ctx.verification_command}
```
{trace_section}"""

    @classmethod
    def render_claude(cls, ctx: CanonicalAgentContext) -> str:
        """XML-tagged Mission Envelope optimized for Anthropic Claude context window structure."""
        active_title = ctx.active_task.get("title", "Proceed with implementation") if ctx.active_task else "Objective Complete"
        active_desc = ctx.active_task.get("description", "") if ctx.active_task else ""

        completed_xml = "\n".join(f"    <task status='completed'>{html.escape(str(t.get('title', '')))}</task>" for t in ctx.completed_tasks)
        pending_xml = "\n".join(f"    <task status='pending'>{html.escape(str(t.get('title', '')))}</task>" for t in ctx.pending_tasks)
        constraints_xml = "\n".join(f"    <constraint>{html.escape(str(c))}</constraint>" for c in ctx.boundary_constraints)
        forbidden_xml = "\n".join(f"    <forbidden>{html.escape(str(f))}</forbidden>" for f in ctx.forbidden_changes)
        acceptance_xml = "\n".join(f"    <criteria>{html.escape(str(a))}</criteria>" for a in ctx.acceptance_criteria)
        deps_xml = "\n".join(f"    <dependency>{html.escape(str(d))}</dependency>" for d in ctx.relevant_dependencies)
        targets_xml = "\n".join(f"    <target>{html.escape(str(t))}</target>" for t in ctx.affected_components)

        return f"""<ultron_mission_envelope snapshot_id="{html.escape(ctx.snapshot_id)}" model_hash="{html.escape(ctx.model_hash)}" revision="{html.escape(ctx.repository_revision)}" generated_at="{html.escape(ctx.generated_at)}">
  <mission>{html.escape(ctx.mission_intent)}</mission>
  <target_files>
{targets_xml or '    <target>none</target>'}
  </target_files>
  <objective title="{html.escape(ctx.objective_title)}" progress="{ctx.progress_pct}%">
    <description>{html.escape(ctx.objective_description)}</description>
    <active_task>{html.escape(active_title)}</active_task>
    <task_detail>{html.escape(active_desc)}</task_detail>
    <why_it_matters>{html.escape(ctx.why_this_task_matters)}</why_it_matters>
    <next_safe_action>{html.escape(ctx.next_safe_action)}</next_safe_action>
  </objective>
  <dependencies>
{deps_xml or '    <dependency>none</dependency>'}
  </dependencies>
  <boundary_rules>
{constraints_xml or '    <constraint>Preserve module APIs</constraint>'}
  </boundary_rules>
  <forbidden_changes>
{forbidden_xml or '    <forbidden>none</forbidden>'}
  </forbidden_changes>
  <milestone_history>
{completed_xml or '    <task status="none">No prior milestones</task>'}
  </milestone_history>
  <upcoming_milestones>
{pending_xml or '    <task status="final">No remaining milestones</task>'}
  </upcoming_milestones>
  <acceptance_criteria>
{acceptance_xml or '    <criteria>All tests pass</criteria>'}
  </acceptance_criteria>
  <verification_command>{ctx.verification_command}</verification_command>
{f'''  <execution_reality_trace id="{html.escape(str(ctx.execution_trace.get('trace_id', 'TRACE-001')))}">
    <trigger>{html.escape(str(ctx.execution_trace.get('trigger', '')))}</trigger>
    <element>{html.escape(str(ctx.execution_trace.get('element', '')))}</element>
    <state_trajectory>{html.escape(str(ctx.execution_trace.get('state_before', '')))} -&gt; {html.escape(str(ctx.execution_trace.get('state_after', '')))}</state_trajectory>
    <failure_point>{html.escape(str(ctx.execution_trace.get('failure_point') or 'None'))}</failure_point>
    <result>{html.escape(str(ctx.execution_trace.get('result', 'PASS')))}</result>
  </execution_reality_trace>''' if ctx.execution_trace else ''}
</ultron_mission_envelope>
"""

    @classmethod
    def render_cursor(cls, ctx: CanonicalAgentContext) -> str:
        """Rule-formatted directive optimized for Cursor Composer and .cursorrules."""
        active_title = ctx.active_task.get("title", "Proceed with implementation") if ctx.active_task else "Objective Complete"
        constraints = "; ".join(ctx.boundary_constraints) or "Preserve existing signatures"
        forbidden = "; ".join(ctx.forbidden_changes) or "None"
        acceptance = "; ".join(ctx.acceptance_criteria) or "Ensure all tests pass"
        targets = ", ".join(ctx.affected_components) or "None declared"
        trace_str = f"\nREALITY TRACE: {ctx.execution_trace.get('trace_id')} | Trigger: {ctx.execution_trace.get('trigger')} | Trajectory: {ctx.execution_trace.get('state_before')} -> {ctx.execution_trace.get('state_after')} | Failure: {ctx.execution_trace.get('failure_point') or 'None'}" if ctx.execution_trace else ""

        return f"""# Cursor Mission Envelope — Ultron Grounded Directive
# SNAPSHOT: {ctx.snapshot_id} | GENERATED: {ctx.generated_at} | REPO: {ctx.repository_id}
# Mission: {ctx.mission_intent}
# Target Files: {targets}
# Objective: {ctx.objective_title} ({ctx.progress_pct}% Complete){trace_str}

ACTIVE MILESTONE: "{active_title}"
TARGET FILES: {targets}
WHY IT MATTERS: {ctx.why_this_task_matters}
NEXT ACTION: {ctx.next_safe_action}

CRITICAL RULES:
1. Target Files: {targets}
2. Hard Constraints: {constraints}
3. Forbidden Files: {forbidden}
4. Acceptance Criteria: {acceptance}
5. Run verification before completion: `{ctx.verification_command}`
"""

    @classmethod
    def render_codex(cls, ctx: CanonicalAgentContext) -> str:
        """Rule-formatted directive optimized for OpenAI Codex / ChatGPT / Cursor."""
        return cls.render_cursor(ctx)

    @classmethod
    def render_windsurf(cls, ctx: CanonicalAgentContext) -> str:
        """Rule-formatted directive optimized for Windsurf Cascade and .windsurfrules."""
        targets = ", ".join(ctx.affected_components) or "None declared"
        constraints = "; ".join(ctx.boundary_constraints) or "Preserve existing signatures"
        forbidden = "; ".join(ctx.forbidden_changes) or "None"
        acceptance = "; ".join(ctx.acceptance_criteria) or "Ensure all tests pass"
        active_title = ctx.active_task.get("title", "Proceed with implementation") if ctx.active_task else "Objective Complete"
        return f"""# Windsurf Cascade Directive — Ultron Architecture Guard
# REPO: {ctx.repository_id} | SNAPSHOT: {ctx.snapshot_id}
# Active Milestone: "{active_title}"

## Objective
{ctx.mission_intent or ctx.objective_title}

## File Scope
- Allowed Target Files: {targets}
- Forbidden Boundary Files: {forbidden}

## Hard Constraints
{constraints}

## Acceptance & Verification
- {acceptance}
- Run verification command: `{ctx.verification_command}`
"""

    @classmethod
    def render_antigravity(cls, ctx: CanonicalAgentContext) -> str:
        """Constitutional multi-agent directive optimized for Antigravity & UMAGS."""
        active_title = ctx.active_task.get("title", "Proceed with implementation") if ctx.active_task else "Objective Complete"
        targets = "\n".join(f"- `{t}`" for t in ctx.affected_components) or "- None declared"
        trace_block = ""
        if ctx.execution_trace:
            tr = ctx.execution_trace
            trace_block = f"""
[EXECUTION_REALITY_TRACE]
ID: {tr.get('trace_id', 'TRACE-001')}
Trigger: {tr.get('trigger', '')} ({tr.get('element', '')})
Trajectory: {tr.get('state_before', '')} -> {tr.get('state_after', '')}
Failure Point: {tr.get('failure_point') or 'None (Clean Baseline)'}
Result: {tr.get('result', 'PASS')}
"""
        return f"""[UMAGS MISSION ENVELOPE]
SNAPSHOT_ID: {ctx.snapshot_id}
MODEL_HASH: {ctx.model_hash or 'N/A'}
GENERATED_AT: {ctx.generated_at}
REPOSITORY_ROOT: {ctx.repository_root} (ID: {ctx.repository_id})
MISSION_INTENT: {ctx.mission_intent}
TARGET_FILES:
{targets}
TARGET_OBJECTIVE: {ctx.objective_title} ({ctx.progress_pct}% Complete)
{trace_block}
[ACTIVE_FOCUS_MILESTONE]
{active_title}
{ctx.active_task.get('description', '') if ctx.active_task else ''}
Rationale: {ctx.why_this_task_matters}
Next Action: {ctx.next_safe_action}

[CONSTRAINTS_AND_FORBIDDEN]
Constraints:
{chr(10).join(f"- {c}" for c in ctx.boundary_constraints) or "- No boundary violations"}
Forbidden Files:
{chr(10).join(f"- {f}" for f in ctx.forbidden_changes) or "- None declared"}

[ACCEPTANCE_CRITERIA]
{chr(10).join(f"- {a}" for a in ctx.acceptance_criteria) or "- Zero test regressions"}

[VERIFICATION_RUNNER]
{ctx.verification_command}
"""

    @classmethod
    def render_aider(cls, ctx: CanonicalAgentContext) -> str:
        """CLI instruction format for Aider."""
        active_title = ctx.active_task.get("title", "Proceed with implementation") if ctx.active_task else "Objective Complete"
        affected_files = " ".join(ctx.affected_components)
        prefix = "/add "
        add_cmd = (prefix + affected_files) if affected_files else "# (Add modified files as needed)"
        return f"""# Aider Mission Directive — Ultron (Snapshot: {ctx.snapshot_id})
{add_cmd}

Mission: {ctx.mission_intent}
Target Files: {affected_files or 'None declared'}
Active Milestone: "{active_title}"
Objective: {ctx.objective_title} ({ctx.progress_pct}% Complete)
Why It Matters: {ctx.why_this_task_matters}
Next Action: {ctx.next_safe_action}

Constraints:
{chr(10).join(f"- {c}" for c in ctx.boundary_constraints) or "- Preserve signatures"}

Acceptance:
{chr(10).join(f"- {a}" for a in ctx.acceptance_criteria) or "- All unit tests pass"}

Run verification: {ctx.verification_command}
"""
