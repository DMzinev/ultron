"""
ultron.core.policy_engine
Deterministic Architectural Governance Policy Engine & Custom Rule Validator.
"""

import re
from typing import Dict, List, Any, Optional


def norm_path(path_str: Any) -> str:
    """Normalizes file paths to POSIX forward slashes."""
    return str(path_str or "").replace("\\", "/").strip()


class PolicyEngine:
    """
    Deterministic rule evaluation engine verifying codebase architecture
    against declarative boundaries, complexity limits, and layer isolation rules.
    """

    ENGINE_VERSION = "1.0-governance-policy"

    DEFAULT_RULES = [
        {
            "id": "POL-NO-DIRECT-DB-FROM-CONTROLLER",
            "name": "Prohibit Direct Database Imports in Controllers",
            "type": "FORBIDDEN_DEPENDENCY",
            "source_pattern": r"(controllers?|routes?|views?|handlers?)/",
            "target_pattern": r"(repositories?|models?|database|db|sql)/",
            "severity": "HIGH",
            "message": "Controller directly imports Database/Repository layer. Must route through Service or UseCase layer.",
            "remediation": "Inject service interface and delegate database access to application service components."
        },
        {
            "id": "POL-MAX-MODULE-COMPLEXITY",
            "name": "Maximum Module McCabe Complexity Ceiling",
            "type": "MAX_COMPLEXITY",
            "threshold": 12.0,
            "severity": "MEDIUM",
            "message": "Module cyclomatic complexity exceeds policy threshold (12.0).",
            "remediation": "Extract helper functions and decompose nested conditionals into cohesive sub-routines."
        },
        {
            "id": "POL-MAX-MODULE-COUPLING",
            "name": "Maximum Inbound Caller Coupling Ceiling",
            "type": "MAX_COUPLING",
            "threshold": 8.0,
            "severity": "HIGH",
            "message": "Module has excessive inbound dependents (Ca > 8.0). High risk for Shotgun Surgery.",
            "remediation": "Introduce façade or mediator pattern to isolate direct callers."
        }
    ]

    def __init__(self, load_defaults: bool = True):
        self._rules: List[Dict[str, Any]] = []
        if load_defaults:
            self.load_default_rulepack()

    def add_rule(self, rule_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registers a declarative policy rule with schema validation.
        """
        if not isinstance(rule_dict, dict):
            raise ValueError("Rule definition must be a dictionary")

        rule_id = str(rule_dict.get("id") or f"RULE-{len(self._rules) + 1}").strip()
        rule_type = str(rule_dict.get("type", "FORBIDDEN_DEPENDENCY")).strip()
        severity = str(rule_dict.get("severity", "MEDIUM")).upper()

        if severity not in {"HIGH", "MEDIUM", "LOW"}:
            severity = "MEDIUM"

        rule_record = {
            "id": rule_id,
            "name": str(rule_dict.get("name") or rule_id),
            "type": rule_type,
            "severity": severity,
            "source_pattern": str(rule_dict.get("source_pattern", "")),
            "target_pattern": str(rule_dict.get("target_pattern", "")),
            "threshold": float(rule_dict.get("threshold", 10.0)),
            "message": str(rule_dict.get("message", "Policy threshold violated.")),
            "remediation": str(rule_dict.get("remediation", "Refactor module to comply with architectural boundaries."))
        }

        # Validate regex patterns if present
        if rule_record["source_pattern"]:
            try:
                re.compile(rule_record["source_pattern"])
            except re.error as e:
                raise ValueError(f"Invalid source regex in rule {rule_id}: {e}")

        if rule_record["target_pattern"]:
            try:
                re.compile(rule_record["target_pattern"])
            except re.error as e:
                raise ValueError(f"Invalid target regex in rule {rule_id}: {e}")

        self._rules.append(rule_record)
        return rule_record

    def load_default_rulepack(self) -> None:
        """Loads default Clean Layered Architecture rules."""
        self._rules = []
        for r in self.DEFAULT_RULES:
            self.add_rule(r)

    def list_rules(self) -> List[Dict[str, Any]]:
        """Returns list of registered governance rules."""
        return list(self._rules)

    def evaluate_codebase(self, analysis_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluates active codebase AST facts and dependency edges against registered policy rules.
        """
        data = analysis_data or {}
        risks = data.get("risks", []) or []
        edges = data.get("dependency_graph", {}).get("edges", []) if isinstance(data.get("dependency_graph"), dict) else (data.get("edges", []) or [])

        violations: List[Dict[str, Any]] = []

        for rule in self._rules:
            rtype = rule["type"]

            # 1. FORBIDDEN_DEPENDENCY
            if rtype == "FORBIDDEN_DEPENDENCY":
                src_regex = rule.get("source_pattern")
                tgt_regex = rule.get("target_pattern")

                if src_regex and tgt_regex:
                    src_compiled = re.compile(src_regex, re.IGNORECASE)
                    tgt_compiled = re.compile(tgt_regex, re.IGNORECASE)

                    for edge in edges:
                        src = norm_path(edge.get("source") if isinstance(edge, dict) else getattr(edge, "source", ""))
                        tgt = norm_path(edge.get("target") if isinstance(edge, dict) else getattr(edge, "target", ""))

                        if src and tgt and src_compiled.search(src) and tgt_compiled.search(tgt):
                            violations.append({
                                "rule_id": rule["id"],
                                "rule_name": rule["name"],
                                "severity": rule["severity"],
                                "source_file": src,
                                "target_file": tgt,
                                "violating_value": f"{src} -> {tgt}",
                                "message": rule["message"],
                                "remediation": rule["remediation"]
                            })

            # 2. MAX_COMPLEXITY
            elif rtype == "MAX_COMPLEXITY":
                threshold = float(rule.get("threshold", 12.0))
                for r in risks:
                    src = norm_path(r.get("file", r.get("file_path", "")))
                    comp = float(r.get("complexity", 1.0) or 1.0)
                    if comp > threshold:
                        violations.append({
                            "rule_id": rule["id"],
                            "rule_name": rule["name"],
                            "severity": rule["severity"],
                            "source_file": src,
                            "target_file": None,
                            "violating_value": f"Complexity: {comp:.1f} (Threshold: {threshold:.1f})",
                            "message": rule["message"],
                            "remediation": rule["remediation"]
                        })

            # 3. MAX_COUPLING
            elif rtype == "MAX_COUPLING":
                threshold = float(rule.get("threshold", 8.0))
                for r in risks:
                    src = norm_path(r.get("file", r.get("file_path", "")))
                    coup = float(r.get("coupling_score", 0.0) or 0.0)
                    if coup > threshold:
                        violations.append({
                            "rule_id": rule["id"],
                            "rule_name": rule["name"],
                            "severity": rule["severity"],
                            "source_file": src,
                            "target_file": None,
                            "violating_value": f"Coupling: {coup:.1f} (Threshold: {threshold:.1f})",
                            "message": rule["message"],
                            "remediation": rule["remediation"]
                        })

        # Sort violations deterministically: HIGH -> MEDIUM -> LOW, then source_file
        sev_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        violations.sort(key=lambda v: (sev_rank.get(v["severity"], 3), v["source_file"] or ""))

        high_count = sum(1 for v in violations if v["severity"] == "HIGH")
        med_count = sum(1 for v in violations if v["severity"] == "MEDIUM")
        low_count = sum(1 for v in violations if v["severity"] == "LOW")

        return {
            "status": "COMPLIANT" if len(violations) == 0 else "VIOLATIONS_DETECTED",
            "total_rules_evaluated": len(self._rules),
            "total_violations": len(violations),
            "violations_by_severity": {
                "high": high_count,
                "medium": med_count,
                "low": low_count
            },
            "violations": violations
        }
