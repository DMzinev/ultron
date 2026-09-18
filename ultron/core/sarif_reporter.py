"""
ultron.core.sarif_reporter
Native OASIS SARIF (Static Analysis Results Interchange Format) 2.1.0 Static Analysis Exporter.
Conforms strictly to SARIF 2.1.0 schema for GitHub Advanced Security Code Scanning,
GitLab SAST, Azure DevOps, and SonarQube ingestion.
"""

import hashlib
import json
import os
import tempfile
from typing import Any, Dict, List, Optional, Set

SARIF_SCHEMA_URI = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
)
SARIF_VERSION = "2.1.0"


def normalize_sarif_uri(file_path: Any, repo_path: Optional[str] = None) -> str:
    """
    Normalizes file path to clean relative POSIX path suitable for SARIF %SRCROOT% resolution.
    Strips leading slashes, Windows backslashes, and './' prefixes.
    """
    raw_str = str(file_path or "").replace("\\", "/").strip()
    if not raw_str:
        return "unknown"

    if repo_path and os.path.isabs(raw_str):
        try:
            norm_repo = os.path.abspath(os.path.normpath(repo_path))
            raw_str = os.path.relpath(raw_str, norm_repo).replace("\\", "/")
        except (ValueError, OSError):
            pass

    # Clean leading ./ and /
    while raw_str.startswith("./"):
        raw_str = raw_str[2:]
    raw_str = raw_str.lstrip("/")

    return raw_str or "unknown"


def map_severity_to_sarif_level(severity: Any) -> str:
    """
    Maps Ultron severity string to strict SARIF 2.1.0 level ('error', 'warning', 'note', 'none').
    """
    sev_upper = str(severity or "LOW").upper().strip()
    if sev_upper in ("CRITICAL", "HIGH", "ERROR"):
        return "error"
    elif sev_upper in ("MEDIUM", "WARN", "WARNING"):
        return "warning"
    elif sev_upper in ("LOW", "INFO", "HEALTHY", "NOTE"):
        return "note"
    return "note"


class SARIFReporter:
    """
    Compiles Ultron architecture analysis findings, policy violations, circular dependencies,
    and high-risk hotspots into standard-compliant OASIS SARIF 2.1.0 documents.
    """

    CANONICAL_RULES: List[Dict[str, Any]] = [
        {
            "id": "ULTRON-CIRCULAR-DEP",
            "name": "CircularDependency",
            "shortDescription": {
                "text": "Circular import dependency cycle detected"
            },
            "fullDescription": {
                "text": "Two or more modules form a cyclic import dependency chain, impairing architectural decoupling and testability."
            },
            "defaultConfiguration": {
                "level": "error"
            },
            "properties": {
                "tags": ["architecture", "maintainability", "dependencies"]
            }
        },
        {
            "id": "ULTRON-RISK-CRITICAL",
            "name": "CriticalArchitecturalRisk",
            "shortDescription": {
                "text": "Critical architectural risk hotspot"
            },
            "fullDescription": {
                "text": "Module exhibits critical cyclomatic complexity and structural coupling, representing an extreme risk of cascading regressions."
            },
            "defaultConfiguration": {
                "level": "error"
            },
            "properties": {
                "tags": ["architecture", "risk", "complexity"]
            }
        },
        {
            "id": "ULTRON-RISK-HIGH",
            "name": "HighArchitecturalRisk",
            "shortDescription": {
                "text": "High architectural risk hotspot"
            },
            "fullDescription": {
                "text": "Module exhibits high cyclomatic complexity or heavy inbound coupling, posing elevated risk for shotgun surgery."
            },
            "defaultConfiguration": {
                "level": "error"
            },
            "properties": {
                "tags": ["architecture", "risk", "complexity"]
            }
        },
        {
            "id": "ULTRON-COMPLEXITY-HOTSPOT",
            "name": "HighCyclomaticComplexity",
            "shortDescription": {
                "text": "Module cyclomatic complexity exceeds policy threshold"
            },
            "fullDescription": {
                "text": "Module exceeds the maximum McCabe cyclomatic complexity limit, hindering maintainability and unit test verification."
            },
            "defaultConfiguration": {
                "level": "warning"
            },
            "properties": {
                "tags": ["maintainability", "complexity"]
            }
        },
        {
            "id": "ULTRON-COUPLING-BOTTLENECK",
            "name": "ExcessiveCoupling",
            "shortDescription": {
                "text": "Module inbound coupling ceiling breached"
            },
            "fullDescription": {
                "text": "Module has excessive inbound dependent callers, creating a bottleneck and severe architectural rigidity."
            },
            "defaultConfiguration": {
                "level": "error"
            },
            "properties": {
                "tags": ["architecture", "coupling", "maintainability"]
            }
        },
    ]

    @classmethod
    def generate_sarif_report(
        cls,
        analysis_dict: Dict[str, Any],
        repo_path: str = ".",
        driver_version: str = "1.5.0"
    ) -> Dict[str, Any]:
        """
        Generates a complete, OASIS SARIF 2.1.0 compliant JSON dictionary.
        Dynamic rule registration ensures every result has an associated driver rule descriptor.
        """
        registered_rules: Dict[str, Dict[str, Any]] = {}
        for r in cls.CANONICAL_RULES:
            registered_rules[r["id"]] = dict(r)

        results: List[Dict[str, Any]] = []
        emitted_fingerprints: Set[str] = set()

        abs_repo = os.path.abspath(os.path.normpath(repo_path))

        # 1. Process Policy Violations
        policy_violations = analysis_dict.get("policy_violations", [])
        for v in policy_violations:
            rule_id = str(v.get("rule_id") or "ULTRON-POLICY-BREACH").strip()
            rule_name = str(v.get("rule_name") or rule_id).strip()
            severity = v.get("severity", "MEDIUM")
            level = map_severity_to_sarif_level(severity)

            # Dynamically register rule if not present (Directive 1)
            if rule_id not in registered_rules:
                registered_rules[rule_id] = {
                    "id": rule_id,
                    "name": rule_name.replace(" ", ""),
                    "shortDescription": {
                        "text": rule_name
                    },
                    "fullDescription": {
                        "text": v.get("message") or f"Architectural governance violation for rule {rule_name}."
                    },
                    "defaultConfiguration": {
                        "level": level
                    },
                    "properties": {
                        "tags": ["architecture", "governance", "policy"]
                    }
                }

            source_file = normalize_sarif_uri(
                v.get("source_file") or v.get("file") or v.get("file_path"),
                repo_path=abs_repo
            )
            line = int(v.get("line") or v.get("lineno") or 1)

            message_text = v.get("message") or f"Policy breach: {rule_name}"
            remediation = v.get("remediation")
            if remediation:
                message_text = f"{message_text} Remediation: {remediation}"

            fp = hashlib.sha256(f"{rule_id}:{source_file}:{line}".encode("utf-8")).hexdigest()[:16]
            if fp in emitted_fingerprints:
                continue
            emitted_fingerprints.add(fp)

            result_item: Dict[str, Any] = {
                "ruleId": rule_id,
                "level": level,
                "message": {
                    "text": message_text
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": source_file,
                                "uriBaseId": "%SRCROOT%"
                            },
                            "region": {
                                "startLine": max(1, line),
                                "startColumn": 1
                            }
                        }
                    }
                ],
                "partialFingerprints": {
                    "primaryLocationHash": fp
                },
                "properties": {
                    "severity": severity,
                    "remediation": remediation or "",
                    "violatingValue": str(v.get("violating_value") or "")
                }
            }
            results.append(result_item)

        # 2. Process Circular Dependencies
        cycles = analysis_dict.get("circular_dependencies") or analysis_dict.get("cycles") or []
        for cycle in cycles:
            cycle_nodes = []
            if isinstance(cycle, dict):
                cycle_nodes = cycle.get("nodes") or cycle.get("cycle") or []
            elif isinstance(cycle, (list, tuple)):
                cycle_nodes = list(cycle)

            if not cycle_nodes:
                continue

            first_file = normalize_sarif_uri(cycle_nodes[0], repo_path=abs_repo)
            cycle_chain = " -> ".join(normalize_sarif_uri(n, repo_path=abs_repo) for n in cycle_nodes)
            rule_id = "ULTRON-CIRCULAR-DEP"

            fp = hashlib.sha256(f"{rule_id}:{cycle_chain}".encode("utf-8")).hexdigest()[:16]
            if fp in emitted_fingerprints:
                continue
            emitted_fingerprints.add(fp)

            result_item = {
                "ruleId": rule_id,
                "level": "error",
                "message": {
                    "text": f"Circular import dependency cycle detected: {cycle_chain}."
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": first_file,
                                "uriBaseId": "%SRCROOT%"
                            },
                            "region": {
                                "startLine": 1,
                                "startColumn": 1
                            }
                        }
                    }
                ],
                "partialFingerprints": {
                    "primaryLocationHash": fp
                },
                "properties": {
                    "cycleChain": cycle_chain,
                    "cycleLength": len(cycle_nodes)
                }
            }
            results.append(result_item)

        # 3. Process High and Critical Architectural Risk Hotspots
        risks = analysis_dict.get("risks", [])
        for r in risks:
            level_str = str(r.get("level", "LOW")).upper()
            if level_str not in ("CRITICAL", "HIGH"):
                continue

            rule_id = f"ULTRON-RISK-{level_str}"
            file_path = normalize_sarif_uri(
                r.get("file_path") or r.get("file"),
                repo_path=abs_repo
            )
            comp = r.get("complexity", 1)
            coup = r.get("coupling_score", 0.0)
            impact = r.get("impact_score", 0.0)
            mitigation = r.get("mitigation", "")

            msg = (
                f"{level_str} architectural risk in {file_path} "
                f"(Complexity: {comp}, Coupling: {coup:.1f}, Impact Score: {impact:.1f})."
            )
            if mitigation:
                msg = f"{msg} Mitigation: {mitigation}"

            fp = hashlib.sha256(f"{rule_id}:{file_path}".encode("utf-8")).hexdigest()[:16]
            if fp in emitted_fingerprints:
                continue
            emitted_fingerprints.add(fp)

            result_item = {
                "ruleId": rule_id,
                "level": "error",
                "message": {
                    "text": msg
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": file_path,
                                "uriBaseId": "%SRCROOT%"
                            },
                            "region": {
                                "startLine": 1,
                                "startColumn": 1
                            }
                        }
                    }
                ],
                "partialFingerprints": {
                    "primaryLocationHash": fp
                },
                "properties": {
                    "complexity": comp,
                    "couplingScore": coup,
                    "impactScore": impact,
                    "mitigation": mitigation
                }
            }
            results.append(result_item)

        # Sort results deterministically by ruleId, file uri, line
        results.sort(
            key=lambda item: (
                item.get("ruleId", ""),
                item.get("locations", [{}])[0].get("physicalLocation", {}).get("artifactLocation", {}).get("uri", ""),
                item.get("locations", [{}])[0].get("physicalLocation", {}).get("region", {}).get("startLine", 1)
            )
        )

        # Sort rules list deterministically
        sorted_rules = sorted(registered_rules.values(), key=lambda r: r["id"])

        sarif_document = {
            "$schema": SARIF_SCHEMA_URI,
            "version": SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Ultron",
                            "version": driver_version,
                            "semanticVersion": driver_version,
                            "informationUri": "https://github.com/DMzinev/ultron",
                            "rules": sorted_rules
                        }
                    },
                    "results": results
                }
            ]
        }

        return sarif_document

    @classmethod
    def write_sarif_file(cls, sarif_payload: Dict[str, Any], output_path: str) -> str:
        """
        Atomically writes SARIF JSON report to output_path.
        Creates parent directories if necessary and ensures file handle closure before replacement (Directive 4).
        """
        abs_output = os.path.abspath(os.path.normpath(output_path))
        parent_dir = os.path.dirname(abs_output)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # Windows-safe atomic replacement: close handle before os.replace
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=parent_dir or None,
            prefix=".ultron_sarif_",
            suffix=".tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(sarif_payload, f, indent=2)
            # Temporary file handle is now closed, safe to replace on Windows
            os.replace(tmp_path, abs_output)
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise

        return abs_output
