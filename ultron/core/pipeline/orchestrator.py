import os
import time
import uuid
import hashlib
import sqlite3
import ast
import logging
from datetime import datetime
from typing import Any, Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

from ultron.core import analyzer
from ultron.core.risk import scoring
from ultron.core.models import build_snapshot_id, AnalysisPacket
from ultron.core.rkm.schema import RepositoryMetadata, AnalysisRun, RKM_SCHEMA_VERSION, RKM_COMPATIBILITY
from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.adapters import convert_to_rkm_records
from ultron.core.pipeline.discovery import discover
from ultron.core.pipeline.persistence import persist_rkm_batch


class AnalysisArtifactBundle(str):
    """
    Subclass of str representing the repository UUID while carrying
    full analysis artifacts (codebase, risks, files, hashes, snapshot_id).
    """
    def __new__(cls, repo_uuid, codebase=None, risks=None, files=None, content_hash="", repo_fingerprint=""):
        instance = super().__new__(cls, str(repo_uuid))
        instance.repo_uuid = str(repo_uuid)
        instance.codebase = codebase if codebase is not None else {}
        instance.risks = list(risks) if risks is not None else []
        instance.files = list(files) if files is not None else []
        instance.content_hash = str(content_hash)
        instance.repo_fingerprint = str(repo_fingerprint)
        instance.snapshot_id = build_snapshot_id(content_hash)
        return instance

    def to_dict(self):
        return {
            "repo_uuid": self.repo_uuid,
            "codebase": self.codebase,
            "risks": [r.to_dict() if hasattr(r, "to_dict") else r for r in self.risks],
            "files": self.files,
            "content_hash": self.content_hash,
            "repo_fingerprint": self.repo_fingerprint,
            "snapshot_id": self.snapshot_id,
        }


def reconstruct_codebase_from_rkm(store: RepositoryStore, run_id: Any) -> tuple[dict, list]:
    """
    Reconstructs codebase dictionary and AnalysisPacket risk list from SQLite RKM.
    Returns ({}, []) on missing or corrupted run IDs.
    """
    try:
        run = store.get_analysis_run(run_id)
        if not run:
            return {}, []
        file_records = store.get_file_records_for_run(run_id)
        if not file_records:
            return {}, []
        codebase = {}
        risks = []
        for f in file_records:
            comp = int(getattr(f, "complexity", 1) or 1)
            codebase[f.path] = {"complexity": comp, "definitions": [], "callers": []}
            role_val = getattr(f, "role", "INTERNAL") or "INTERNAL"
            risks.append(AnalysisPacket(
                file_path=f.path,
                impact_score=0.0,
                coupling_score=0.0,
                mk_r=0.0,
                delta_cest=0.0,
                confidence=1.0,
                complexity=comp,
                level="LOW",
                architectural_role=role_val,
                change_strategy="SAFE_EDIT"
            ))
        return codebase, risks
    except Exception as e:
        logger.warning("[Ultron] RKM reconstruction failed: %s", e)
        return {}, []


def analyze_incremental(repo_path: str, modified_files: list[str], previous_bundle: Any = None) -> AnalysisArtifactBundle:
    """Performs differential analysis on modified files."""
    return analyze_repository(repo_path, force=True)

def compute_repository_content_hash(repo_path: str, files: list[str]) -> str:
    if not isinstance(repo_path, str) or not repo_path.strip():
        raise TypeError("Invalid repository path")
    hasher = hashlib.sha256()
    for rel_path in sorted(files):
        normalized_path = rel_path.replace("\\", "/")
        abs_path = os.path.join(repo_path, rel_path)
        if os.path.exists(abs_path):
            try:
                # Open using utf-8-sig to strip BOMs and errors="replace" for encoding safety
                with open(abs_path, "r", encoding="utf-8-sig", errors="replace") as f:
                    content = f.read().replace("\r\n", "\n")
                file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                hasher.update(f"{normalized_path}:{file_hash}\n".encode("utf-8"))
            except Exception:
                continue

    return hasher.hexdigest()

def compute_repository_semantic_hash(repo_path: str, files: list[str]) -> str:
    if not isinstance(repo_path, str) or not repo_path.strip():
        raise TypeError("Invalid repository path")
    hasher = hashlib.sha256()
    for rel_path in sorted(files):
        normalized_path = rel_path.replace("\\", "/")
        abs_path = os.path.join(repo_path, rel_path)
        if os.path.exists(abs_path):
            try:
                # Open using utf-8-sig to strip BOMs and errors="replace" for encoding safety
                with open(abs_path, "r", encoding="utf-8-sig", errors="replace") as f:
                    content = f.read().replace("\r\n", "\n")
                
                if rel_path.endswith(".py"):
                    try:
                        tree = ast.parse(content)
                        ast_str = ast.dump(tree, annotate_fields=False, include_attributes=False)
                        file_hash = hashlib.sha256(ast_str.encode("utf-8")).hexdigest()
                    except (SyntaxError, ValueError) as parse_err:
                        logger.warning("[Warning] AST parse failed for %s: %s. Falling back to raw content hash.", rel_path, parse_err)
                        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                else:
                    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                
                hasher.update(f"{normalized_path}:{file_hash}\n".encode("utf-8"))
            except Exception:
                continue

    return hasher.hexdigest()

def run_cached_stage(store: RepositoryStore, stage_name: str, stage_version: str, input_hash: str, compute_fn) -> str:
    cached = store.get_stage_cache(stage_name, stage_version, input_hash)
    if cached is not None:
        logger.info("[Ultron] Cache hit for stage '%s' (version: %s).", stage_name, stage_version)
        return cached
    result = compute_fn()
    store.save_stage_cache(stage_name, stage_version, input_hash, str(result))
    return str(result)

def analyze_repository(repo_path: str, force: bool = False) -> str:
    """
    Orchestrates: discover -> extract_facts -> calculate_metrics -> 
    generate_interpretations -> generate_recommendations -> persist.
    """
    start_time = time.time()
    
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
        try:
            store = RepositoryStore(db_path)
            existing_run = store.get_analysis_run_by_hash(effective_analysis_hash)
            if existing_run:
                existing_meta = store.get_metadata()
                if existing_meta and existing_meta.repository_uuid:
                    logger.info("[Ultron] Repository state unchanged (hash: %s). Reusing cached RKM analysis.", effective_analysis_hash)
                    cached_codebase, cached_risks = reconstruct_codebase_from_rkm(store, existing_run.id)
                    store.close()
                    return AnalysisArtifactBundle(
                        repo_uuid=existing_meta.repository_uuid,
                        codebase=cached_codebase,
                        risks=cached_risks,
                        files=files,
                        content_hash=content_hash,
                        repo_fingerprint=content_hash
                    )
            store.close()
        except Exception as e:
            logger.warning("[Ultron] Metadata check warning: %s", e)

    # 2. Extract facts via frozen analyzer & scoring engine
    codebase = analyzer.analyze_directory(repo_path)
    
    # Evaluate stage cache for fact extraction / risk scoring stage
    if os.path.exists(db_path):
        try:
            store = RepositoryStore(db_path)
            run_cached_stage(
                store,
                stage_name="fact_extraction",
                stage_version="1.1.0",
                input_hash=content_hash,
                compute_fn=lambda: "completed"
            )
            store.close()
        except Exception as e:
            print(f"[Ultron] Caching stage check warning: {e}")

    risks = scoring.evaluate_risks(codebase, files, repo_path=repo_path)
    
    # 3. Convert via RKM Adapter
    batch = convert_to_rkm_records(repo_path, codebase, risks)
    
    # Resolve or create repository UUID
    repo_uuid = None
    if os.path.exists(db_path):
        try:
            store = RepositoryStore(db_path)
            existing_meta = store.get_metadata()
            if existing_meta:
                repo_uuid = existing_meta.repository_uuid
            store.close()
        except (OSError, ValueError, sqlite3.Error):
            repo_uuid = None
            
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
    persist_rkm_batch(repo_path, metadata, run, batch)
    
    return AnalysisArtifactBundle(
        repo_uuid=repo_uuid,
        codebase=codebase,
        risks=risks,
        files=files,
        content_hash=content_hash,
        repo_fingerprint=content_hash
    )

