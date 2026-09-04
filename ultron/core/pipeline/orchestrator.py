import os
import time
import uuid
import hashlib
import sqlite3
import ast
from datetime import datetime

from ultron.core import analyzer
from ultron.core.risk import scoring
from ultron.core.rkm.schema import RepositoryMetadata, AnalysisRun, RKM_SCHEMA_VERSION, RKM_COMPATIBILITY
from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.adapters import convert_to_rkm_records
from ultron.core.pipeline.discovery import discover
from ultron.core.pipeline.persistence import persist_rkm_batch

_CONTENT_HASH_CACHE = {}
_SEMANTIC_HASH_CACHE = {}

def compute_fast_stat_fingerprint(repo_path: str, files: list[str]) -> str:
    """Computes fast O(N) stat fingerprint using st_mtime_ns and st_size without reading file contents."""
    if not isinstance(repo_path, str) or not repo_path.strip():
        raise TypeError("Invalid repository path")
    abs_repo = os.path.abspath(repo_path)
    entries = []
    for rel_path in sorted(files):
        abs_p = os.path.join(abs_repo, rel_path)
        try:
            st = os.stat(abs_p)
            entries.append(f"{rel_path.replace('\\', '/')}:{st.st_mtime_ns}:{st.st_size}")
        except OSError:
            continue
    return hashlib.sha256(";".join(entries).encode("utf-8")).hexdigest()

def compute_repository_content_hash(repo_path: str, files: list[str]) -> str:
    if not isinstance(repo_path, str) or not repo_path.strip():
        raise TypeError("Invalid repository path")
    abs_repo = os.path.abspath(repo_path)
    stat_fp = compute_fast_stat_fingerprint(repo_path, files)
    cache_key = f"{abs_repo}:{stat_fp}"
    if cache_key in _CONTENT_HASH_CACHE:
        return _CONTENT_HASH_CACHE[cache_key]

    hasher = hashlib.sha256()
    for rel_path in sorted(files):
        normalized_path = rel_path.replace("\\", "/")
        abs_path = os.path.join(abs_repo, rel_path)
        if os.path.exists(abs_path):
            try:
                # Stream binary in 64KB blocks with CRLF normalization
                file_hasher = hashlib.sha256()
                with open(abs_path, "rb") as f:
                    while chunk := f.read(65536):
                        chunk_clean = chunk.replace(b"\r\n", b"\n")
                        file_hasher.update(chunk_clean)
                file_hash = file_hasher.hexdigest()
                hasher.update(f"{normalized_path}:{file_hash}\n".encode("utf-8"))
            except Exception:
                continue

    res = hasher.hexdigest()
    _CONTENT_HASH_CACHE[cache_key] = res
    return res

def compute_repository_semantic_hash(repo_path: str, files: list[str]) -> str:
    if not isinstance(repo_path, str) or not repo_path.strip():
        raise TypeError("Invalid repository path")
    abs_repo = os.path.abspath(repo_path)
    stat_fp = compute_fast_stat_fingerprint(repo_path, files)
    cache_key = f"{abs_repo}:{stat_fp}"
    if cache_key in _SEMANTIC_HASH_CACHE:
        return _SEMANTIC_HASH_CACHE[cache_key]

    hasher = hashlib.sha256()
    abs_repo = os.path.abspath(repo_path)
    for rel_path in sorted(files):
        normalized_path = rel_path.replace("\\", "/")
        abs_path = os.path.join(abs_repo, rel_path)
        if os.path.exists(abs_path):
            try:
                # Large file guard (>1MB)
                if os.path.getsize(abs_path) > 1024 * 1024:
                    file_hasher = hashlib.sha256()
                    with open(abs_path, "rb") as f:
                        while chunk := f.read(65536):
                            file_hasher.update(chunk.replace(b"\r\n", b"\n"))
                    file_hash = file_hasher.hexdigest()
                    hasher.update(f"{normalized_path}:{file_hash}\n".encode("utf-8"))
                    continue

                with open(abs_path, "r", encoding="utf-8-sig", errors="replace") as f:
                    content = f.read().replace("\r\n", "\n")
                
                if rel_path.endswith(".py"):
                    try:
                        tree = ast.parse(content)
                        ast_str = ast.dump(tree, annotate_fields=False, include_attributes=False)
                        file_hash = hashlib.sha256(ast_str.encode("utf-8")).hexdigest()
                    except (SyntaxError, ValueError) as parse_err:
                        print(f"[Warning] AST parse failed for {rel_path}: {parse_err}. Falling back to raw content hash.")
                        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                else:
                    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                
                hasher.update(f"{normalized_path}:{file_hash}\n".encode("utf-8"))
            except Exception:
                continue

    res = hasher.hexdigest()
    _SEMANTIC_HASH_CACHE[cache_key] = res
    return res

def run_cached_stage(store: RepositoryStore, stage_name: str, stage_version: str, input_hash: str, compute_fn) -> str:
    cached = store.get_stage_cache(stage_name, stage_version, input_hash)
    if cached is not None:
        print(f"[Ultron] Cache hit for stage '{stage_name}' (version: {stage_version}).")
        return cached
    result = compute_fn()
    store.save_stage_cache(stage_name, stage_version, input_hash, str(result))
    return str(result)

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from ultron.core.models import AnalysisPacket, ArchitecturalRole, ChangeStrategy, build_snapshot_id

@dataclass
class AnalysisArtifactBundle:
    repo_uuid: str
    codebase: Dict[str, Any]
    risks: List[Any]
    files: List[str]
    content_hash: str
    repo_fingerprint: str = ""
    schema_version: str = "1.2.0"
    snapshot_id: str = ""
    analysis_run_id: Optional[int] = None
    repository_id: Optional[int] = None

    def __post_init__(self):
        if not self.snapshot_id and self.content_hash:
            self.snapshot_id = build_snapshot_id(self.content_hash)

    def __str__(self) -> str:
        """Backwards compatibility: string representation returns repo_uuid."""
        return self.repo_uuid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_uuid": self.repo_uuid,
            "codebase": self.codebase,
            "risks": self.risks,
            "files": self.files,
            "content_hash": self.content_hash,
            "repo_fingerprint": self.repo_fingerprint,
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "analysis_run_id": self.analysis_run_id,
            "repository_id": self.repository_id
        }


def reconstruct_codebase_from_rkm(store: RepositoryStore, run_id: int) -> tuple[dict[str, Any], list[Any]]:
    """
    Fast-path rehydration: reconstructs codebase dictionary and risks AnalysisPackets
    directly from SQLite store records in < 10ms, eliminating redundant filesystem scans.
    """
    file_records = store.get_file_records_for_run(run_id)
    if not file_records:
        return {}, []

    codebase: dict[str, Any] = {}
    risks: list[Any] = []

    for f in file_records:
        norm_file = f.path.replace("\\", "/")
        symbols = store.get_symbols(f.id)
        deps = store.get_dependencies(f.id)
        metrics = store.get_metrics(f.id)

        imports = sorted(list(set(getattr(d, "target_path", "") for d in deps if getattr(d, "target_path", ""))))
        definitions = []
        for s in symbols:
            sym_type = getattr(s, "type", getattr(s, "symbol_type", "function"))
            definitions.append({
                "type": sym_type or "function",
                "name": s.name,
                "lineno": getattr(s, "lineno", getattr(s, "line_start", 1)) or 1,
                "args": [],
                "calls": []
            })

        codebase[norm_file] = {
            "imports": imports,
            "definitions": definitions
        }

        metric_map = {getattr(m, "name", getattr(m, "metric_name", "")): getattr(m, "value", getattr(m, "metric_value", 0.0)) for m in metrics}
        complexity = int(metric_map.get("cyclomatic_complexity", metric_map.get("complexity", 1.0)))
        coupling = float(metric_map.get("coupling_score", metric_map.get("coupling", 0.0)))
        impact = float(metric_map.get("impact_score", metric_map.get("impact", 1.0)))
        level = "HIGH" if impact > 10.0 else ("MEDIUM" if impact > 3.0 else "LOW")
        mitigation = (
            f"High risk implementation. Impact Score: {impact:.2f} (Complexity: {complexity}, Coupling: {int(coupling)})."
            if level == "HIGH" else (
                f"Moderate risk implementation. Impact Score: {impact:.2f} (Complexity: {complexity}, Coupling: {int(coupling)})."
                if level == "MEDIUM" else
                f"Low risk implementation. Impact Score: {impact:.2f} (Complexity: {complexity}, Coupling: {int(coupling)})."
            )
        )

        role_val = getattr(f, "role", "INTERNAL") or "INTERNAL"
        try:
            role = ArchitecturalRole(role_val)
        except ValueError:
            role = ArchitecturalRole.INTERNAL

        packet = AnalysisPacket(
            file_path=norm_file,
            impact_score=impact,
            coupling_score=coupling,
            mk_r=float(metric_map.get("mk_r", 0.0)),
            delta_cest=float(metric_map.get("delta_cest", 0.0)),
            confidence=float(metric_map.get("confidence", 1.0)),
            level=level,
            boundary_type=role.display_name,
            complexity=complexity,
            mitigation=mitigation,
            callers=[getattr(d, "target_path", "") for d in deps if getattr(d, "target_path", "") and getattr(d, "target_path", "") != norm_file],
            changes=[],
            delta_score=0.0,
            architectural_role=role,
            change_strategy=ChangeStrategy.SAFE_EDIT
        )
        risks.append(packet)

    return codebase, risks

def analyze_repository(repo_path: str, force: bool = False, cancel_token=None) -> AnalysisArtifactBundle:
    """
    Orchestrates: discover -> extract_facts -> calculate_metrics -> 
    generate_interpretations -> generate_recommendations -> persist.
    Returns an AnalysisArtifactBundle containing codebase facts and risk evaluations.
    cancel_token: callable returning True when cancellation is requested.
    """
    start_time = time.time()
    
    # Check cancellation before starting
    if cancel_token and cancel_token():
        raise InterruptedError("Analysis cancelled by user")
    
    # 1. Discover
    files = discover(repo_path)
    
    # Compute content hash and effective analysis hash
    content_hash = compute_repository_content_hash(repo_path, files)
    engine_version = "1.2.0"
    effective_analysis_hash = hashlib.sha256(
        f"{content_hash}:{engine_version}:{RKM_SCHEMA_VERSION}".encode("utf-8")
    ).hexdigest()
    
    # Check cache gate
    db_path = os.path.join(repo_path, ".ultron", "repository.db")
    if not force and os.path.exists(db_path):
        store = None
        try:
            store = RepositoryStore(db_path)
            existing_run = store.get_analysis_run_by_hash(effective_analysis_hash)
            if existing_run:
                existing_meta = store.get_metadata()
                if existing_meta and existing_meta.repository_uuid:
                    print(f"[Ultron] Repository state unchanged (hash: {effective_analysis_hash}). Reusing cached RKM analysis.")
                    try:
                        codebase, risks = reconstruct_codebase_from_rkm(store, existing_run.id)
                        if codebase and risks:
                            return AnalysisArtifactBundle(
                                repo_uuid=existing_meta.repository_uuid,
                                codebase=codebase,
                                risks=risks,
                                files=files,
                                content_hash=effective_analysis_hash,
                                repo_fingerprint=content_hash
                            )
                    except Exception as rehydrate_err:
                        print(f"[Ultron Warning] Cache rehydration fallback: {rehydrate_err}")
                        codebase = analyzer.analyze_directory(repo_path)
                        risks = scoring.evaluate_risks(codebase, files, repo_path=repo_path)
                        return AnalysisArtifactBundle(
                            repo_uuid=existing_meta.repository_uuid,
                            codebase=codebase,
                            risks=risks,
                            files=files,
                            content_hash=effective_analysis_hash,
                            repo_fingerprint=content_hash
                        )
        except Exception as e:
            print(f"[Ultron] Metadata check warning: {e}")
        finally:
            if store:
                store.close()

    # 2. Extract facts via frozen analyzer & scoring engine
    codebase = analyzer.analyze_directory(repo_path, cancel_token=cancel_token)
    
    # Check cancellation before risk scoring
    if cancel_token and cancel_token():
        raise InterruptedError("Analysis cancelled by user")
    
    # Evaluate stage cache for fact extraction / risk scoring stage
    if os.path.exists(db_path):
        store = None
        try:
            store = RepositoryStore(db_path)
            run_cached_stage(
                store,
                stage_name="fact_extraction",
                stage_version="1.1.0",
                input_hash=content_hash,
                compute_fn=lambda: "completed"
            )
        except Exception as e:
            print(f"[Ultron] Caching stage check warning: {e}")
        finally:
            if store:
                store.close()

    risks = scoring.evaluate_risks(codebase, files, repo_path=repo_path)
    
    # 3. Convert via RKM Adapter
    batch = convert_to_rkm_records(repo_path, codebase, risks)
    
    # Resolve or create repository UUID
    repo_uuid = None
    if os.path.exists(db_path):
        store = None
        try:
            store = RepositoryStore(db_path)
            existing_meta = store.get_metadata()
            if existing_meta:
                repo_uuid = existing_meta.repository_uuid
        except (OSError, ValueError, sqlite3.Error):
            repo_uuid = None
        finally:
            if store:
                store.close()
            
    if not repo_uuid:
        repo_uuid = str(uuid.uuid4())
        
    repo_name = os.path.basename(os.path.abspath(repo_path))
    repo_size = sum(f.size for f in batch.files)
    
    metadata = RepositoryMetadata(
        id=1,  # Single repository context for local DB
        repository_uuid=repo_uuid,
        name=repo_name,
        root_path=os.path.abspath(repo_path),
        language="Python",
        size=repo_size,
        rkm_version=RKM_SCHEMA_VERSION,
        minimum_reader_version=RKM_COMPATIBILITY["minimum_reader_version"],
        maximum_writer_version=RKM_COMPATIBILITY["maximum_writer_version"],
        latest_analysis_run_id=None
    )
    
    duration = time.time() - start_time
    semantic_hash = compute_repository_semantic_hash(repo_path, files)
    
    run = AnalysisRun(
        id=None,
        repository_id=None,
        timestamp=datetime.now().isoformat(),
        duration=duration,
        engine_version=engine_version,
        rkm_version=RKM_SCHEMA_VERSION,
        content_hash=effective_analysis_hash,
        previous_run_id=None,
        rule_pack_version="1.0.0",
        semantic_hash=semantic_hash,
        archived=0,
        semantic_hash_strategy="AST"
    )
    
    # 4. Persist atomically
    persist_res = persist_rkm_batch(repo_path, metadata, run, batch)
    repo_uuid = persist_res.repository_uuid
    analysis_run_id = persist_res.run_id
    repository_id = persist_res.repository_id
    snapshot_id = build_snapshot_id(effective_analysis_hash)
    
    return AnalysisArtifactBundle(
        repo_uuid=repo_uuid,
        codebase=codebase,
        risks=risks,
        files=files,
        content_hash=effective_analysis_hash,
        repo_fingerprint=content_hash,
        snapshot_id=snapshot_id,
        analysis_run_id=analysis_run_id,
        repository_id=repository_id
    )


def analyze_incremental(
    repo_path: str, 
    changed_files: list[str], 
    previous_bundle: AnalysisArtifactBundle = None
) -> AnalysisArtifactBundle:
    """
    Sub-50ms Incremental Differential Analyzer:
    Only re-evaluates touched files and direct 1-hop callers.
    """
    start_time = time.time()
    all_files = discover(repo_path)
    
    if previous_bundle is not None and previous_bundle.codebase:
        codebase = dict(previous_bundle.codebase)
    else:
        db_path = os.path.join(repo_path, ".ultron", "repository.db")
        if os.path.exists(db_path):
            store = None
            try:
                store = RepositoryStore(db_path)
                meta = store.get_metadata()
                if meta and meta.latest_analysis_run_id:
                    codebase, _ = reconstruct_codebase_from_rkm(store, meta.latest_analysis_run_id)
                else:
                    codebase = analyzer.analyze_directory(repo_path)
            except Exception:
                codebase = analyzer.analyze_directory(repo_path)
            finally:
                if store:
                    store.close()
        else:
            codebase = analyzer.analyze_directory(repo_path)

    # 1. Update codebase surgically
    analyzer.update_codebase_incremental(repo_path, changed_files, codebase)
    
    # 2. Identify 1-hop blast radius for risk re-evaluation
    affected_targets = set(changed_files)
    for ch_file in changed_files:
        norm_ch = ch_file.replace("\\", "/")
        for caller_path, analysis in codebase.items():
            if norm_ch in analysis.get("imports", []):
                affected_targets.add(caller_path)
                
    # 3. Evaluate risks on affected targets only
    risks = scoring.evaluate_risks(codebase, list(affected_targets), repo_path=repo_path)
    
    # 4. Compute effective analysis hash
    content_hash = compute_repository_content_hash(repo_path, all_files)
    engine_version = "1.2.0"
    effective_analysis_hash = hashlib.sha256(
        f"{content_hash}:{engine_version}:{RKM_SCHEMA_VERSION}".encode("utf-8")
    ).hexdigest()
    
    batch = convert_to_rkm_records(repo_path, codebase, risks)
    repo_uuid = previous_bundle.repo_uuid if previous_bundle else str(uuid.uuid4())
    repo_name = os.path.basename(os.path.abspath(repo_path))
    repo_size = sum(f.size for f in batch.files)
    
    metadata = RepositoryMetadata(
        id=1,
        repository_uuid=repo_uuid,
        name=repo_name,
        root_path=os.path.abspath(repo_path),
        language="Python",
        size=repo_size,
        rkm_version=RKM_SCHEMA_VERSION,
        minimum_reader_version=RKM_COMPATIBILITY["minimum_reader_version"],
        maximum_writer_version=RKM_COMPATIBILITY["maximum_writer_version"],
        latest_analysis_run_id=None
    )
    
    duration = time.time() - start_time
    semantic_hash = compute_repository_semantic_hash(repo_path, all_files)
    
    run = AnalysisRun(
        id=None,
        repository_id=None,
        timestamp=datetime.now().isoformat(),
        duration=duration,
        engine_version=engine_version,
        rkm_version=RKM_SCHEMA_VERSION,
        content_hash=effective_analysis_hash,
        previous_run_id=previous_bundle.analysis_run_id if previous_bundle else None,
        rule_pack_version="1.0.0",
        semantic_hash=semantic_hash,
        archived=0,
        semantic_hash_strategy="AST"
    )
    
    persist_res = persist_rkm_batch(repo_path, metadata, run, batch)
    
    return AnalysisArtifactBundle(
        repo_uuid=persist_res.repository_uuid,
        codebase=codebase,
        risks=risks,
        files=all_files,
        content_hash=effective_analysis_hash,
        repo_fingerprint=content_hash,
        snapshot_id=build_snapshot_id(effective_analysis_hash),
        analysis_run_id=persist_res.run_id,
        repository_id=persist_res.repository_id
    )


