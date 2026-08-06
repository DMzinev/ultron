from abc import ABC, abstractmethod
from typing import Any
import fnmatch
from ultron.core.rkm.schema import RkmRule, RkmViolation, RkmViolationEvidence, RkmRuleInstance

class Constraint(ABC):
    """
    Abstract interface for stateless, side-effect free constraint plugins.
    Constraint plugins are pure functions over repository observations.
    """
    @abstractmethod
    def evaluate(self, store: Any, run_id: int, rule: RkmRule, config: dict[str, Any]) -> list[tuple[RkmViolation, list[RkmViolationEvidence]]]:
        pass

class ComplexityConstraint(Constraint):
    def evaluate(self, store: Any, run_id: int, rule: RkmRule, config: dict[str, Any]) -> list[tuple[RkmViolation, list[RkmViolationEvidence]]]:
        max_limit = config.get("max")
        if max_limit is None:
            return []
        
        violations = []
        files = store.get_file_records_for_run(run_id)
        for f in files:
            metrics = store.get_metrics(f.id)
            for m in metrics:
                if m.name == "complexity" and m.value > max_limit:
                    vio = RkmViolation(
                        id=None,
                        evaluation_id=None,
                        file_id=f.id,
                        symbol_id=None,
                        details=f"File '{f.path}' complexity is {m.value}, exceeding the maximum limit of {max_limit}."
                    )
                    ev = RkmViolationEvidence(
                        id=None,
                        violation_id=None,
                        evidence_type="metric",
                        evidence_id=m.id
                    )
                    violations.append((vio, [ev]))
        return violations

class CouplingConstraint(Constraint):
    def evaluate(self, store: Any, run_id: int, rule: RkmRule, config: dict[str, Any]) -> list[tuple[RkmViolation, list[RkmViolationEvidence]]]:
        max_limit = config.get("max")
        if max_limit is None:
            return []
        
        violations = []
        files = store.get_file_records_for_run(run_id)
        for f in files:
            metrics = store.get_metrics(f.id)
            for m in metrics:
                if m.name == "coupling" and m.value > max_limit:
                    vio = RkmViolation(
                        id=None,
                        evaluation_id=None,
                        file_id=f.id,
                        symbol_id=None,
                        details=f"File '{f.path}' coupling is {m.value}, exceeding the maximum limit of {max_limit}."
                    )
                    ev = RkmViolationEvidence(
                        id=None,
                        violation_id=None,
                        evidence_type="metric",
                        evidence_id=m.id
                    )
                    violations.append((vio, [ev]))
        return violations

class LayerConstraint(Constraint):
    def evaluate(self, store: Any, run_id: int, rule: RkmRule, config: dict[str, Any]) -> list[tuple[RkmViolation, list[RkmViolationEvidence]]]:
        source_pattern = config.get("source_pattern")
        target_pattern = config.get("target_pattern")
        if not source_pattern or not target_pattern:
            return []
        
        violations = []
        files = store.get_file_records_for_run(run_id)
        for f in files:
            # Check if source file matches pattern (e.g. 'ultron/core/*')
            if fnmatch.fnmatch(f.path, source_pattern):
                deps = store.get_dependencies(f.id)
                for d in deps:
                    # check target dependency path against target pattern
                    # dependencies are stored as module names or paths; normalize back to paths if needed
                    target = d.target_path.replace(".", "/")
                    if fnmatch.fnmatch(target, target_pattern) or fnmatch.fnmatch(d.target_path, target_pattern):
                        vio = RkmViolation(
                            id=None,
                            evaluation_id=None,
                            file_id=f.id,
                            symbol_id=None,
                            details=f"Dependency boundary violation: File '{f.path}' (matching '{source_pattern}') "
                                    f"imports '{d.target_path}' (matching '{target_pattern}')."
                        )
                        ev = RkmViolationEvidence(
                            id=None,
                            violation_id=None,
                            evidence_type="dependency",
                            evidence_id=d.id
                        )
                        violations.append((vio, [ev]))
        return violations

class ConstraintEngine:
    def __init__(self):
        self.plugins = {
            "complexity_limit": ComplexityConstraint(),
            "coupling_limit": CouplingConstraint(),
            "layer_restriction": LayerConstraint()
        }

    def register_plugin(self, predicate_type: str, constraint: Constraint):
        self.plugins[predicate_type] = constraint

    def evaluate_rules(self, store: Any, run_id: int, rules: list[RkmRule], instances: list[RkmRuleInstance]) -> list[tuple[RkmViolation, list[RkmViolationEvidence], RkmRule]]:
        # Match instances to rules
        instance_map = {inst.rule_id: inst for inst in instances if inst.enabled}
        
        results = []
        for r in rules:
            inst = instance_map.get(r.id)
            if not inst:
                continue
            
            plugin = self.plugins.get(r.predicate_type)
            if not plugin:
                # Unsupported predicate type
                continue
            
            try:
                violations = plugin.evaluate(store, run_id, r, inst.predicate_config)
                for vio, evidences in violations:
                    results.append((vio, evidences, r))
            except Exception:
                # Engine/plugin runtime crash would produce an ERROR evaluation, handled at pipeline level
                raise
        return results
