import os
import time
from datetime import datetime
from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.schema import RepositoryMetadata, AnalysisRun, ProvenanceRecord, RkmEvaluation, EvaluationStatus
from ultron.core.rkm.adapters import RKMRecordBatch

def seed_default_rules(store: RepositoryStore):
    import json
    from ultron.core.rkm.schema import RkmRule, RkmRuleInstance
    
    rules_path = os.path.join(os.path.dirname(__file__), "..", "rkm", "rulepacks", "default", "rules.json")
    if not os.path.exists(rules_path):
        return
        
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            pack = json.load(f)
            
        rule_pack_id = pack.get("rule_pack_id", "default")
        rules_to_save = []
        instances_to_save = []
        
        for r_dict in pack.get("rules", []):
            rule = RkmRule(
                id=r_dict["id"],
                rule_pack_id=rule_pack_id,
                name=r_dict["name"],
                description=r_dict["description"],
                predicate_type=r_dict["predicate_type"],
                version=r_dict.get("version", "1.0.0")
            )
            rules_to_save.append(rule)
            
            instance = RkmRuleInstance(
                id=None,
                rule_id=r_dict["id"],
                enabled=r_dict.get("enabled", 1),
                severity=r_dict.get("severity", "warning"),
                predicate_config=r_dict.get("predicate_config", {}),
                version=r_dict.get("version", "1.0.0")
            )
            instances_to_save.append(instance)
            
        if rules_to_save:
            store.save_rules(rules_to_save)
        if instances_to_save:
            store.save_rule_instances(instances_to_save)
    except Exception as e:
        print(f"Warning: failed to seed default rules: {e}")

def persist_rkm_batch(repo_path: str, metadata: RepositoryMetadata, run: AnalysisRun, batch: RKMRecordBatch) -> str:
    db_path = os.path.join(repo_path, ".ultron", "repository.db")
    store = RepositoryStore(db_path)

    try:
        # Check existing metadata to preserve lineage
        existing_meta = store.get_metadata()
        previous_run_id = None
        if existing_meta:
            previous_run_id = existing_meta.latest_analysis_run_id
            metadata.latest_analysis_run_id = previous_run_id

        with store.transaction():
            # Initialize singleton RkmManifest if not exists
            manifest = store.get_manifest()
            if not manifest:
                from ultron.core.rkm.schema import RkmManifest, RKM_SCHEMA_VERSION, RKM_COMPATIBILITY
                manifest = RkmManifest(
                    repository_uuid=metadata.repository_uuid,
                    schema_version=RKM_SCHEMA_VERSION,
                    minimum_reader_version=RKM_COMPATIBILITY["minimum_reader_version"],
                    maximum_writer_version=RKM_COMPATIBILITY["maximum_writer_version"],
                    engine_version=run.engine_version,
                    rule_pack_version=run.rule_pack_version,
                    snapshot_version="1.0.0"
                )
                store.save_manifest(manifest)
            
            # Seed rules and rule instances from default pack
            seed_default_rules(store)

            # 1. Save metadata
            metadata_id = store.save_metadata(metadata)
            
            # 2. Save run
            run.repository_id = metadata_id
            run.previous_run_id = previous_run_id
            run_id = store.save_analysis_run(run)
            
            # 3. Save files and build mapping from path -> file_id
            file_id_map = {}
            for f in batch.files:
                f.analysis_run_id = run_id
                f_id = store.save_file(f)
                file_id_map[f.path] = f_id

            # 4. Save symbols
            all_symbols = []
            for path, symbols in batch.symbols.items():
                f_id = file_id_map.get(path)
                if f_id:
                    for s in symbols:
                        s.file_id = f_id
                        all_symbols.append(s)
            if all_symbols:
                store.save_symbols(all_symbols)

            # 5. Save dependencies
            all_deps = []
            for path, deps in batch.dependencies.items():
                f_id = file_id_map.get(path)
                if f_id:
                    for d in deps:
                        d.file_id = f_id
                        all_deps.append(d)
            if all_deps:
                store.save_dependencies(all_deps)

            # 6. Save facts and provenance
            fact_id_map = {}  # (path, category, metric) -> fact_id
            for path, facts in batch.facts.items():
                f_id = file_id_map.get(path)
                if f_id:
                    for fact in facts:
                        fact.file_id = f_id
                        fact_id = store.save_fact(fact)
                        fact_id_map[(path, fact.category, fact.metric)] = fact_id
                        
                        # Save provenance record
                        prov = ProvenanceRecord(
                            id=None,
                            fact_id=fact_id,
                            generated_by=fact.source_type,
                            engine_version=run.engine_version
                        )
                        store.save_provenance(prov)


            # 7. Save interpretations
            inter_id_map = {}  # id(InterpretationRecord) -> interpretation_id
            for path, inter_tuples in batch.interpretations.items():
                for fact_record, inter_record in inter_tuples:
                    fact_id = fact_id_map.get((path, fact_record.category, fact_record.metric))
                    if fact_id:
                        inter_record.fact_id = fact_id
                        inter_id = store.save_interpretation(inter_record)
                        inter_id_map[id(inter_record)] = inter_id

            # 8. Save recommendations
            all_recs = []
            for path, rec_tuples in batch.recommendations.items():
                for inter_record, rec_record in rec_tuples:
                    inter_id = inter_id_map.get(id(inter_record))
                    if inter_id:
                        rec_record.interpretation_id = inter_id
                        all_recs.append(rec_record)
            if all_recs:
                store.save_recommendations(all_recs)

            # 9. Save metrics
            all_metrics = []
            for path, metrics in batch.metrics.items():
                f_id = file_id_map.get(path)
                if f_id:
                    for m in metrics:
                        m.file_id = f_id
                        all_metrics.append(m)
            if all_metrics:
                store.save_metrics(all_metrics)

            # 10. Save architecture
            all_archs = []
            for path, archs in batch.architecture.items():
                f_id = file_id_map.get(path)
                if f_id:
                    for a in archs:
                        a.file_id = f_id
                        all_archs.append(a)
            if all_archs:
                store.save_architecture(all_archs)

            # 11. Run constraint engine evaluations
            from ultron.core.rkm.engine import ConstraintEngine
            engine = ConstraintEngine()
            rules = store.get_rules()
            instances = store.get_rule_instances()
            correlation_id = f"run-{run_id}"

            for r in rules:
                inst = next((i for i in instances if i.rule_id == r.id), None)
                if not inst or not inst.enabled:
                    continue
                
                started_at = datetime.now().isoformat()
                start_ticks = time.perf_counter()
                
                status = EvaluationStatus.PENDING
                try:
                    plugin = engine.plugins.get(r.predicate_type)
                    if not plugin:
                        status = EvaluationStatus.SKIPPED
                        violations_with_evidence = []
                    else:
                        status = EvaluationStatus.RUNNING
                        # plugins return list of (vio, list[evidence])
                        violations_with_evidence = plugin.evaluate(store, run_id, r, inst.predicate_config)
                        status = EvaluationStatus.FAILED if violations_with_evidence else EvaluationStatus.PASSED
                except Exception as e:
                    status = EvaluationStatus.ERROR
                    violations_with_evidence = []
                    store.log_event("RULE_EVALUATION", "ERROR", r.id, correlation_id, f"Error evaluating rule {r.id}: {e}")
                    
                finished_at = datetime.now().isoformat()
                duration_ms = int((time.perf_counter() - start_ticks) * 1000)
                
                ev = RkmEvaluation(
                    id=None,
                    analysis_run_id=run_id,
                    rule_id=r.id,
                    status=status,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                    engine_version=run.engine_version,
                    rule_version=r.version
                )
                
                # Save evaluation
                ev_id = store.save_evaluations([ev])[0]
                
                # Save violations for this evaluation
                if status == EvaluationStatus.FAILED:
                    violations_to_save = []
                    for vio, evidences in violations_with_evidence:
                        vio.evaluation_id = ev_id
                        violations_to_save.append((vio, evidences))
                    if violations_to_save:
                        store.save_violations(violations_to_save)

            # Compute and save entity history
            if previous_run_id:
                try:
                    from ultron.core.rkm.evolution.engine import EvolutionEngine
                    from ultron.core.rkm.schema import RkmEntityHistory
                    
                    deltas = EvolutionEngine.compare_runs(store, previous_run_id, run_id)
                    history_records = []
                    for d in deltas:
                        if d.entity_type in ('file', 'symbol'):
                            action = 'modified'
                            if d.delta_type.endswith('_added') or d.delta_type == 'file_added':
                                action = 'added'
                            elif d.delta_type.endswith('_removed') or d.delta_type == 'file_removed':
                                action = 'removed'
                            
                            history_records.append(
                                RkmEntityHistory(
                                    id=None,
                                    entity_type=d.entity_type,
                                    entity_identifier=d.entity_identifier,
                                    analysis_run_id=run_id,
                                    action=action,
                                    signature=None
                                )
                            )
                    if history_records:
                        store.save_entity_history(history_records)
                except Exception as e:
                    store.log_event("EVOLUTION", "ERROR", metadata.repository_uuid, correlation_id, f"Failed to compute entity history: {e}")
            else:
                try:
                    from ultron.core.rkm.schema import RkmEntityHistory
                    history_records = []
                    for path in file_id_map.keys():
                        history_records.append(
                            RkmEntityHistory(
                                id=None,
                                entity_type="file",
                                entity_identifier=path,
                                analysis_run_id=run_id,
                                action="added",
                                signature=None
                            )
                        )
                    if history_records:
                        store.save_entity_history(history_records)
                except Exception as e:
                    store.log_event("EVOLUTION", "ERROR", metadata.repository_uuid, correlation_id, f"Failed to compute initial entity history: {e}")

            # 12. Update latest analysis run
            store.update_latest_analysis_run(metadata_id, run_id)
            
            # 13. Prune stage cache (keep newest 5 runs)
            store.prune_stage_cache()
            
            # 14. Log completion event
            store.log_event("ANALYSIS", "COMPLETED", metadata.repository_uuid, correlation_id, f"Successfully completed analysis run {run_id}")
            
    finally:
        store.close()
        
    return metadata.repository_uuid
