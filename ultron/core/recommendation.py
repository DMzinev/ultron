"""
core/recommendation.py — Consequence-Driven Recommendation & Decision Quality Engine.
Gate A: Consumes canonical EvidenceBundle, enforces epistemic hierarchy, and discloses limitations.
"""
import os
import re
import math
from typing import List, Dict, Any, Optional
from ultron.core.models import FileCategory, RecommendationAction, RecommendationPacket
from ultron.core.evidence import (
    EvidenceClassification, ConfidenceTier, EvidenceBundle, EvidenceRecord,
    compile_repository_evidence
)

POLICY_VERSION = "consequence_v1"
RECOMMENDATION_ENGINE_VERSION = "1.0.0"


def classify_file(path: str, repo_root: str = "") -> FileCategory:
    """Single authoritative file category classifier across the entire Ultron system."""
    if not path:
        return FileCategory.UNKNOWN
    norm = path.replace("\\", "/").strip().lower()

    # 1. Test code
    if (re.search(r'(^|/)(tests?|fixtures|testing)(/|$)', norm) or
        re.search(r'(^|/)test_[^/]+\.py$', norm) or
        re.search(r'[^/]+_test\.py$', norm) or
        norm.endswith("conftest.py") or (norm.startswith("test/") and norm.endswith(".py"))):
        return FileCategory.TEST_CODE

    # 2. Configuration & Build files
    base = os.path.basename(norm)
    if (base in ("setup.py", "setup.cfg", "pyproject.toml", "tox.ini", "makefile", "gemfile",
                 "conf.py", ".coveragerc", "dockerfile", "vagrantfile") or
        base.startswith((".git", "requirements")) or base.endswith(".lock")):
        return FileCategory.CONFIGURATION

    # 3. Documentation
    if (re.search(r'(^|/)(docs?|documentation)(/|$)', norm) or
        norm.endswith((".md", ".rst", ".txt", ".adoc")) or "license" in base or "readme" in base):
        return FileCategory.DOCUMENTATION

    # 4. Generated code / vendored / migrations
    if (norm.endswith(("_pb2.py", "_pb2_grpc.py", ".min.js", ".min.css")) or
        "/migrations/" in norm or "/vendor/" in norm or "/node_modules/" in norm):
        return FileCategory.GENERATED

    # 5. Tooling & Scratch scripts
    if re.search(r'(^|/)(extras|scripts|tools|scratch|bin)(/|$)', norm) and not norm.startswith("src/"):
        return FileCategory.TOOLING

    # 6. Production code
    if norm.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
        return FileCategory.PRODUCTION_CODE

    return FileCategory.UNKNOWN


def compute_priority(
    packet_dict: Dict[str, Any], callers: List[str], objective: str = "",
    policy: str = POLICY_VERSION, evidence_tier: str = "OBSERVED"
) -> float:
    """Policy-based continuous priority scoring with active objective weighting."""
    category = packet_dict.get("category", FileCategory.PRODUCTION_CODE)
    if category != FileCategory.PRODUCTION_CODE or evidence_tier == "INSUFFICIENT_EVIDENCE":
        return 0.0

    callers_count = len(callers)
    role = packet_dict.get("architectural_role", "INTERNAL")

    public_weight = 2.0 if role in ("PUBLIC_MODULE", "PACKAGE_INITIALIZER") else (1.5 if role == "CLI" else 1.0)
    centrality = 1.5 if role in ("CLI", "SERVER") else (1.3 if role == "CORE_ENGINE" else (0.5 if "util" in packet_dict.get("file_path", "").lower() else 1.0))

    consequence_base = (1.0 + callers_count) * math.log(math.e + public_weight) * centrality

    # Objective relevance multiplier: direct keyword matching or mitigation match
    objective_mult = 1.0
    if objective:
        words = [w.lower() for w in re.findall(r'[a-zA-Z0-9_]+', objective) if len(w) >= 3]
        f_lower = packet_dict.get("file_path", "").lower()
        if any(w in f_lower or (len(w) >= 4 and w[:4] in f_lower) or any(part.startswith(w[:4]) for part in f_lower.split('/')) for w in words):
            objective_mult = 3.5
        elif any(w in str(packet_dict.get("mitigation", "")).lower() for w in words):
            objective_mult = 1.8
        else:
            # When an active objective exists and doesn't match this subsystem, de-prioritize background hubs
            objective_mult = 0.5

    evidence_mult = {"OBSERVED": 1.0, "DERIVED": 0.8, "INFERRED": 0.5, "UNKNOWN": 0.1, "INSUFFICIENT_EVIDENCE": 0.0}.get(evidence_tier, 0.0)
    return round(consequence_base * objective_mult * evidence_mult, 3)


def resolve_action(
    category: FileCategory, priority_score: float, risk_level: str, callers_count: int,
    confidence_tier: str = "HIGH", has_sufficient_evidence: bool = True
) -> RecommendationAction:
    """Resolve actionable recommendation with epistemic uncertainty gating."""
    if category != FileCategory.PRODUCTION_CODE or confidence_tier in ("INSUFFICIENT_EVIDENCE", "NOT_ASSESSED") or not has_sufficient_evidence:
        return RecommendationAction.DO_NOT_RECOMMEND
    if callers_count > 8 and risk_level == "HIGH" and priority_score < 5.0:
        return RecommendationAction.PROTECT
    if priority_score >= 10.0:
        return RecommendationAction.INVESTIGATE if risk_level != "HIGH" else RecommendationAction.REFACTOR
    if priority_score >= 3.0:
        return RecommendationAction.INVESTIGATE
    return RecommendationAction.DEFER


def generate_explainability(
    target: str, callers: List[str], role: str, complexity: int, impact: float,
    objective: str, evidence_tier: str, limitations: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Generates the 7-question plain-English explainability contract with disclosed limitations."""
    base_name = os.path.basename(target)
    c_count = len(callers)
    callers_sample = ", ".join([os.path.basename(c) for c in callers[:3]]) if callers else "none"

    why_this = f"'{base_name}' functions as a {role.replace('_', ' ').lower()} module with {c_count} inbound dependent(s)."
    obj_words = [w.lower() for w in re.findall(r'[a-zA-Z0-9_]+', objective) if len(w) >= 3] if objective else []
    why_now = f"Matches active objective '{objective}' with high architectural reach." if obj_words and any(w in target.lower() for w in obj_words) else (
        f"Central architectural hub with {c_count} downstream dependents requiring review." if c_count > 3 else "Local component with contained scope."
    )
    what_could_break = (
        f"Modifying this file risks breaking runtime behavior in: {callers_sample}." if c_count > 0 else "Isolated file; low risk of external breakage."
    )
    conf_reason = "Direct AST call-graph and import verification" if evidence_tier == "OBSERVED" else "Deterministic derivation from observed AST"
    next_action = (
        f"Inspect caller contracts in {callers_sample} and prepare a bounded mission." if c_count > 0 else f"Safe for direct local edits; verify unit tests for {base_name}."
    )

    return {
        "why_this": why_this, "why_now": why_now, "what_it_affects": callers,
        "what_could_break": what_could_break, "evidence_tier": evidence_tier,
        "confidence_reason": conf_reason, "next_action": next_action,
        "limitations": list(limitations or [])
    }


def generate_comparative_alternatives(
    top_rec: RecommendationPacket, candidates: List[RecommendationPacket], limit: int = 2
) -> List[Dict[str, Any]]:
    """Synthesizes non-circular 'Why this, not X?' structural comparisons for alternatives."""
    if len(candidates) <= 1:
        return [{"file": "none", "why_not": "Single production module in repository; no competing alternatives."}]

    alternatives = []
    top_base = os.path.basename(top_rec.target_file)
    top_callers = top_rec.coupling

    for alt in candidates[1:limit + 1]:
        alt_base = os.path.basename(alt.target_file)
        if alt.coupling < top_callers:
            why_not = f"Higher local complexity (CC {alt.complexity}), but fewer inbound callers ({alt.coupling} vs {top_callers} in {top_base})."
        elif alt.public_surface == "HIGH" and alt.coupling <= top_callers:
            why_not = f"Important interface surface, but lower immediate downstream consequence ({alt.coupling} callers)."
        elif "util" in alt.target_file.lower():
            why_not = f"Utility drawer with isolated functions; changes do not drive system-wide control flow."
        else:
            why_not = f"Lower architectural centrality and lower active objective relevance compared to {top_base}."

        alternatives.append({"file": alt.target_file, "why_not": why_not})

    return alternatives


def build_consequence_recommendations(
    codebase: Dict[str, Any], risks: Optional[List[Any]] = None, objective: str = "", limit: int = 10,
    policy: str = POLICY_VERSION, repo_path: str = "",
    evidence_bundle: Optional[EvidenceBundle] = None
) -> List[RecommendationPacket]:
    """Compiles consequence-driven recommendations consuming canonical EvidenceBundle."""
    risks_list = risks if isinstance(risks, list) else []
    if isinstance(codebase, str):
        if not repo_path:
            repo_path = codebase
        codebase = {r.get("file_path", r.get("file", "")): r for r in risks_list if isinstance(r, dict)}
    elif not isinstance(codebase, dict):
        codebase = {}

    bundle = evidence_bundle or compile_repository_evidence(repo_path, codebase, risks_list)

    risk_lookup = {}
    for r in risks_list:
        if isinstance(r, dict):
            risk_lookup[r.get("file_path", r.get("file", ""))] = r
        elif hasattr(r, "file_path"):
            risk_lookup[getattr(r, "file_path", "")] = r
    candidates = []
    for rel_path, analysis in codebase.items():
        cat = classify_file(rel_path, repo_path)
        r_item = risk_lookup.get(rel_path)

        callers = []
        comp = 1
        imp = 0.0
        role = "INTERNAL"
        if r_item:
            callers = r_item.callers if hasattr(r_item, "callers") else r_item.get("callers", [])
            comp = r_item.complexity if hasattr(r_item, "complexity") else r_item.get("complexity", 1)
            imp = r_item.impact_score if hasattr(r_item, "impact_score") else r_item.get("impact_score", 0.0)
            role_val = r_item.architectural_role if hasattr(r_item, "architectural_role") else r_item.get("architectural_role", "INTERNAL")
            role = role_val.value if hasattr(role_val, "value") else str(role_val)
        else:
            callers = analysis.get("callers", analysis.get("inbound_callers", []))
            comp = analysis.get("complexity", analysis.get("mccabe_complexity", 1))

        packet_dict = {
            "file_path": rel_path, "category": cat, "architectural_role": role,
            "complexity": comp, "impact_score": imp
        }

        # Evidence query from canonical bundle
        target_records = bundle.get_records_for_target(rel_path)
        target_limitations = bundle.get_target_limitations(rel_path)
        target_confidence = bundle.get_target_confidence(rel_path)
        
        evidence_tier = "OBSERVED" if rel_path in codebase else "UNKNOWN"
        has_sufficient = len(target_records) > 0 and evidence_tier != "UNKNOWN"
        
        p_score = compute_priority(packet_dict, callers, objective=objective, policy=policy, evidence_tier=evidence_tier)
        p_level = "HIGH" if p_score >= 10.0 else ("MEDIUM" if p_score >= 3.0 else "LOW")
        action = resolve_action(cat, p_score, "HIGH" if imp >= 10.0 else "LOW", len(callers), confidence_tier=target_confidence, has_sufficient_evidence=has_sufficient)

        if cat == FileCategory.PRODUCTION_CODE and action != RecommendationAction.DO_NOT_RECOMMEND:
            expl = generate_explainability(rel_path, callers, role, comp, imp, objective, evidence_tier, target_limitations)
            candidates.append(RecommendationPacket(
                target_file=rel_path, category=cat.value, priority_score=p_score, priority_level=p_level,
                confidence_tier=target_confidence, recommendation_action=action.value, why_this=expl["why_this"],
                why_now=expl["why_now"], what_it_affects=expl["what_it_affects"], what_could_break=expl["what_could_break"],
                evidence_tier=expl["evidence_tier"], confidence_reason=expl["confidence_reason"],
                next_action=expl["next_action"], complexity=comp, coupling=len(callers),
                impact_score=round(imp, 2), public_surface="HIGH" if role in ("PUBLIC_MODULE", "PACKAGE_INITIALIZER") else "INTERNAL",
                evidence_records=[r.to_dict() for r in target_records],
                limitations=target_limitations,
                policy_version=policy, engine_version=RECOMMENDATION_ENGINE_VERSION
            ))

    candidates.sort(key=lambda r: (-r.priority_score, -r.impact_score, r.target_file))

    # Populate comparative alternatives on the top recommendation
    if candidates:
        top_alt = generate_comparative_alternatives(candidates[0], candidates, limit=2)
        candidates[0].alternatives_compared = top_alt

    return candidates[:limit]
