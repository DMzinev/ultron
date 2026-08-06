import os
from datetime import datetime
from ultron.core.rkm.schema import (
    FileRecord, SymbolRecord, DependencyRecord, FactRecord,
    InterpretationRecord, RecommendationRecord, MetricRecord, ArchitectureRecord
)
from ultron.core.risk import scoring

class RKMRecordBatch:
    def __init__(self):
        self.files = []
        self.symbols = {}         # rel_path -> list[SymbolRecord]
        self.dependencies = {}    # rel_path -> list[DependencyRecord]
        self.facts = {}           # rel_path -> list[FactRecord]
        self.interpretations = {} # rel_path -> list[tuple[FactRecord, InterpretationRecord]]
        self.recommendations = {} # rel_path -> list[tuple[InterpretationRecord, RecommendationRecord]]
        self.metrics = {}         # rel_path -> list[MetricRecord]
        self.architecture = {}    # rel_path -> list[ArchitectureRecord]

def convert_to_rkm_records(repo_path: str, codebase: dict, risks: list) -> RKMRecordBatch:
    batch = RKMRecordBatch()
    risk_map = {p.file_path: p for p in risks}

    for rel_path, analysis in codebase.items():
        abs_path = os.path.join(repo_path, rel_path)
        
        # Get file metadata
        size = 0
        last_modified = ""
        if os.path.exists(abs_path):
            try:
                size = os.path.getsize(abs_path)
                last_modified = datetime.fromtimestamp(os.path.getmtime(abs_path)).isoformat()
            except (OSError, ValueError) as e:
                size = 0
                last_modified = ""

        packet = risk_map.get(rel_path)
        if packet:
            role = packet.architectural_role.value
            complexity = packet.complexity
            coupling = int(packet.coupling_score)
            impact_score = packet.impact_score
            confidence = packet.confidence
            mitigation = packet.mitigation
            level = packet.level
        else:
            role = scoring.determine_architectural_role(rel_path, abs_path).value
            complexity = scoring.get_file_complexity(abs_path)
            coupling = len(analysis.get("imports", []))
            impact_score = float(complexity)
            confidence = 1.0
            mitigation = ""
            level = "LOW"

        package = os.path.dirname(rel_path)

        # FileRecord
        file_rec = FileRecord(
            id=None,
            analysis_run_id=None,
            path=rel_path,
            role=role,
            package=package,
            size=size,
            last_modified=last_modified,
            created_at=None,
            updated_at=None
        )
        batch.files.append(file_rec)

        # SymbolRecord
        batch.symbols[rel_path] = []
        for defn in analysis.get("definitions", []):
            batch.symbols[rel_path].append(SymbolRecord(
                id=None,
                file_id=None,
                name=defn.get("name", ""),
                type=defn.get("type", "function"),
                lineno=defn.get("lineno", 1)
            ))

        # DependencyRecord
        batch.dependencies[rel_path] = []
        for imp in analysis.get("imports", []):
            batch.dependencies[rel_path].append(DependencyRecord(
                id=None,
                file_id=None,
                target_path=imp
            ))

        # Facts (complexity, coupling)
        batch.facts[rel_path] = []
        fact_complexity = FactRecord(
            id=None,
            file_id=None,
            category="complexity",
            metric="cyclomatic_complexity",
            value=str(complexity),
            value_type="integer",
            source_type="ast_parser",
            source_reference="analyzer.py:16",
            created_at=None,
            updated_at=None
        )
        batch.facts[rel_path].append(fact_complexity)

        fact_coupling = FactRecord(
            id=None,
            file_id=None,
            category="coupling",
            metric="coupling_count",
            value=str(coupling),
            value_type="integer",
            source_type="dependency_analyzer",
            source_reference="scoring.py:214",
            created_at=None,
            updated_at=None
        )
        batch.facts[rel_path].append(fact_coupling)

        # Interpretations and Recommendations
        batch.interpretations[rel_path] = []
        batch.recommendations[rel_path] = []
        if packet and level in ("MEDIUM", "HIGH"):
            inter = InterpretationRecord(
                id=None,
                fact_id=None,
                rule="coupling_count >= 3",
                result="Instability / high coupling detected",
                confidence=confidence,
                created_at=None,
                updated_at=None
            )
            batch.interpretations[rel_path].append((fact_coupling, inter))

            if mitigation:
                rec = RecommendationRecord(
                    id=None,
                    interpretation_id=None,
                    action=mitigation,
                    confidence_type="heuristic",
                    confidence_value=confidence,
                    status="active",
                    created_at=None,
                    updated_at=None
                )
                batch.recommendations[rel_path].append((inter, rec))

        # MetricRecord
        batch.metrics[rel_path] = []
        batch.metrics[rel_path].append(MetricRecord(
            id=None,
            file_id=None,
            name="complexity",
            value=float(complexity),
            created_at=None,
            updated_at=None
        ))
        batch.metrics[rel_path].append(MetricRecord(
            id=None,
            file_id=None,
            name="coupling",
            value=float(coupling),
            created_at=None,
            updated_at=None
        ))
        batch.metrics[rel_path].append(MetricRecord(
            id=None,
            file_id=None,
            name="hotspot_score",
            value=impact_score,
            created_at=None,
            updated_at=None
        ))

        # ArchitectureRecord
        batch.architecture[rel_path] = []
        parts = os.path.normpath(package).split(os.sep) if package else ["root"]
        layer = parts[0] if parts else "root"
        batch.architecture[rel_path].append(ArchitectureRecord(
            id=None,
            file_id=None,
            layer=layer,
            role=role
        ))

    return batch
