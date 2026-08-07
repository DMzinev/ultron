import os
import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
from ultron.core.rkm.schema import (
    RepositoryMetadata, AnalysisRun, FileRecord, SymbolRecord,
    DependencyRecord, FactRecord, InterpretationRecord, RecommendationRecord,
    MetricRecord, ArchitectureRecord, ProvenanceRecord, RkmManifest,
    RkmRule, RkmRuleInstance, RkmEvaluation, RkmViolation, RkmViolationEvidence,
    EvaluationStatus, RKM_SCHEMA_VERSION, RKM_COMPATIBILITY, RkmEntityHistory
)

class AppliedMigration:
    def __init__(self, id: int, version: str, applied_at: str):
        self.id = id
        self.version = version
        self.applied_at = applied_at

class RepositoryStore:
    def __init__(self, db_path: str):
        self.db_path = db_path if db_path == ":memory:" else os.path.normpath(os.path.abspath(db_path))
        # Campaign 20: Integrity Check, Pre-Migration Backup & Corrupted DB Preservation
        from ultron.core.rkm.integrity import RKMDatabaseIntegrity
        RKMDatabaseIntegrity.verify_and_repair_database(self.db_path)
        
        if self.db_path != ":memory:":
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._run_migrations()
        self._check_compatibility()

    def parse_version(self, v_str: str) -> tuple[int, ...]:
        if not isinstance(v_str, str) or not v_str.strip():
            raise ValueError("Invalid version string")
        return tuple(int(x) for x in v_str.split("."))

    def _check_compatibility(self):
        if self.conn is None:
            raise ValueError("Database connection is closed")
        try:
            row = self.conn.execute(
                "SELECT minimum_reader_version FROM rkm_manifest WHERE id = 1"
            ).fetchone()
            if not row:
                row = self.conn.execute(
                    "SELECT minimum_reader_version FROM rkm_metadata LIMIT 1"
                ).fetchone()
            if row and row["minimum_reader_version"]:
                db_min_reader = self.parse_version(row["minimum_reader_version"])
                engine_ver = self.parse_version(RKM_SCHEMA_VERSION)
                if db_min_reader > engine_ver:
                    raise ValueError(
                        f"Incompatible database: minimum reader version is {row['minimum_reader_version']}, "
                        f"but current engine RKM schema version is {RKM_SCHEMA_VERSION}"
                    )
        except (sqlite3.OperationalError, ValueError, IndexError):
            return




    def _ensure_migrations_table_has_checksum(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS rkm_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT UNIQUE NOT NULL,
                applied_at TEXT NOT NULL
            );
        """)
        self.conn.commit()
        
        cursor = self.conn.execute("PRAGMA table_info(rkm_migrations)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "checksum" not in columns:
            self.conn.execute("ALTER TABLE rkm_migrations ADD COLUMN checksum TEXT;")
            self.conn.commit()

    def _run_migrations(self):
        import hashlib
        self._ensure_migrations_table_has_checksum()

        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
        if not os.path.exists(migrations_dir):
            return

        # 1. Read applied migrations from DB
        applied_rows = self.conn.execute("SELECT version, checksum FROM rkm_migrations").fetchall()
        applied_map = {row["version"]: row["checksum"] for row in applied_rows}

        # 2. Scan and parse all migrations in migrations directory
        migration_nodes = {}
        for filename in os.listdir(migrations_dir):
            if filename.endswith(".sql"):
                filepath = os.path.join(migrations_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    ddl = f.read()
                checksum = hashlib.sha256(ddl.replace("\r\n", "\n").encode("utf-8")).hexdigest()
                
                # Parse depends_on
                depends_on = []
                for line in ddl.splitlines():
                    line_strip = line.strip()
                    if line_strip.startswith("-- depends_on:"):
                        parts = line_strip.split("-- depends_on:", 1)[1].split(",")
                        for p in parts:
                            p_strip = p.strip()
                            if p_strip:
                                depends_on.append(p_strip)
                                
                migration_nodes[filename] = {
                    "filename": filename,
                    "filepath": filepath,
                    "ddl": ddl,
                    "checksum": checksum,
                    "depends_on": depends_on
                }

        # 3. Topological sort and circular dependency check
        visited = {}  # version -> state (0=unvisited, 1=visiting, 2=visited)
        order = []

        def visit(v):
            if visited.get(v, 0) == 1:
                raise ValueError(f"Circular dependency detected in migrations involving {v}")
            if visited.get(v, 0) == 2:
                return
            visited[v] = 1
            for dep in migration_nodes[v]["depends_on"]:
                if dep in migration_nodes:
                    visit(dep)
            visited[v] = 2
            order.append(v)

        for filename in sorted(migration_nodes.keys()):
            if filename not in visited:
                visit(filename)

        # 4. Apply migrations in order
        for filename in order:
            node = migration_nodes[filename]
            if filename in applied_map:
                stored_checksum = applied_map[filename]
                # If stored checksum is NULL (from old runs), backfill it only for legacy migrations
                if stored_checksum is None:
                    if filename in ("001_initial_schema.sql", "002_rkm_v1.1.0_upgrade.sql"):
                        with self.transaction():
                            self.conn.execute(
                                "UPDATE rkm_migrations SET checksum = ? WHERE version = ?",
                                (node["checksum"], filename)
                            )
                    else:
                        raise ValueError(
                            f"Migration '{filename}' has a NULL checksum in the database, which is "
                            f"prohibited for non-legacy migrations (version >= 003)."
                        )
                elif stored_checksum != node["checksum"]:
                    raise ValueError(
                        f"Migration file '{filename}' has been modified after execution! "
                        f"Stored checksum: {stored_checksum}, current file checksum: {node['checksum']}"
                    )
            else:
                # Apply migration
                correlation_id = f"mig-{int(datetime.now().timestamp())}"
                self.log_event("MIGRATION", "STARTED", filename, correlation_id, f"Applying migration {filename}")
                try:
                    with self.transaction():
                        self.conn.executescript(node["ddl"])
                        self.conn.execute(
                            "INSERT INTO rkm_migrations (version, checksum, applied_at) VALUES (?, ?, ?)",
                            (filename, node["checksum"], datetime.now().isoformat())
                        )
                    self.log_event("MIGRATION", "COMPLETED", filename, correlation_id, f"Successfully applied migration {filename}")
                except Exception as e:
                    self.log_event("MIGRATION", "FAILED", filename, correlation_id, f"Failed applying migration {filename}: {e}")
                    raise

    @contextmanager
    def transaction(self):
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def get_applied_migrations(self) -> list[AppliedMigration]:
        cursor = self.conn.execute("SELECT id, version, applied_at FROM rkm_migrations ORDER BY id")
        return [AppliedMigration(row["id"], row["version"], row["applied_at"]) for row in cursor]

    def schema_version(self) -> str:
        # For initial simple return: version of latest applied migration
        # or from RKM_SCHEMA_VERSION if table is populated
        row = self.conn.execute("SELECT rkm_version FROM rkm_metadata LIMIT 1").fetchone()
        if row:
            return row["rkm_version"]
        return RKM_SCHEMA_VERSION

    def get_compatibility_metadata(self) -> dict:
        manifest = self.get_manifest()
        if manifest:
            return {
                "minimum_reader_version": manifest.minimum_reader_version,
                "maximum_writer_version": manifest.maximum_writer_version
            }
        row = self.conn.execute("SELECT minimum_reader_version, maximum_writer_version FROM rkm_metadata LIMIT 1").fetchone()
        if row:
            return {
                "minimum_reader_version": row["minimum_reader_version"],
                "maximum_writer_version": row["maximum_writer_version"]
            }
        return RKM_COMPATIBILITY

    def save_manifest(self, manifest: RkmManifest):
        with self.transaction():
            existing = self.conn.execute(
                "SELECT repository_uuid, created_at FROM rkm_manifest WHERE id = 1"
            ).fetchone()
            if existing:
                raise RuntimeError("Manifest already initialized")
            
            cursor = self.conn.execute(
                """INSERT INTO rkm_manifest
                   (id, repository_uuid, schema_version, minimum_reader_version, maximum_writer_version, engine_version, rule_pack_version, snapshot_version)
                   VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
                (manifest.repository_uuid, manifest.schema_version, manifest.minimum_reader_version, manifest.maximum_writer_version,
                 manifest.engine_version, manifest.rule_pack_version, manifest.snapshot_version)
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Failed to insert manifest record")

    def update_manifest(self, engine_version: str, rule_pack_version: str, snapshot_version: str):
        with self.transaction():
            self.conn.execute(
                """UPDATE rkm_manifest SET 
                   engine_version = ?,
                   rule_pack_version = ?,
                   snapshot_version = ?
                   WHERE id = 1""",
                (engine_version, rule_pack_version, snapshot_version)
            )

    def get_manifest(self) -> RkmManifest:
        try:
            row = self.conn.execute("SELECT * FROM rkm_manifest WHERE id = 1").fetchone()
            if not row:
                return None
            return RkmManifest(
                repository_uuid=row["repository_uuid"],
                schema_version=row["schema_version"],
                minimum_reader_version=row["minimum_reader_version"],
                maximum_writer_version=row["maximum_writer_version"],
                engine_version=row["engine_version"],
                rule_pack_version=row["rule_pack_version"],
                snapshot_version=row["snapshot_version"],
                created_at=row["created_at"],
                id=row["id"]
            )
        except sqlite3.OperationalError:
            return None

    # --- Write queries ---
    def save_metadata(self, metadata: RepositoryMetadata) -> int:
        cursor = self.conn.execute(
            """INSERT OR REPLACE INTO rkm_metadata 
               (id, repository_uuid, name, root_path, language, size, rkm_version, minimum_reader_version, maximum_writer_version, latest_analysis_run_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (metadata.id, metadata.repository_uuid, metadata.name, metadata.root_path, metadata.language, metadata.size, 
            metadata.rkm_version, metadata.minimum_reader_version, metadata.maximum_writer_version, metadata.latest_analysis_run_id)
        )
        return cursor.lastrowid

    def save_analysis_run(self, run: AnalysisRun) -> int:
        cursor = self.conn.execute(
            """INSERT INTO rkm_analysis_runs 
               (repository_id, timestamp, duration, engine_version, rkm_version, content_hash, previous_run_id, rule_pack_version, semantic_hash, archived, semantic_hash_strategy)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run.repository_id, run.timestamp, run.duration, run.engine_version, run.rkm_version, run.content_hash, run.previous_run_id,
             run.rule_pack_version, run.semantic_hash, run.archived, run.semantic_hash_strategy)
        )
        return cursor.lastrowid


    def save_file(self, f: FileRecord) -> int:
        cursor = self.conn.execute(
            """INSERT OR REPLACE INTO rkm_files 
               (analysis_run_id, path, role, package, size, last_modified)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (f.analysis_run_id, f.path, f.role, f.package, f.size, f.last_modified)
        )
        return cursor.lastrowid

    def save_symbols(self, symbols: list[SymbolRecord]):
        self.conn.executemany(
            """INSERT INTO rkm_symbols (file_id, name, type, lineno) VALUES (?, ?, ?, ?)""",
            [(s.file_id, s.name, s.type, s.lineno) for s in symbols]
        )

    def save_dependencies(self, deps: list[DependencyRecord]):
        self.conn.executemany(
            """INSERT INTO rkm_dependencies (file_id, target_path) VALUES (?, ?)""",
            [(d.file_id, d.target_path) for d in deps]
        )

    def save_fact(self, fact: FactRecord) -> int:
        cursor = self.conn.execute(
            """INSERT INTO rkm_facts 
               (file_id, category, metric, value, value_type, source_type, source_reference)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (fact.file_id, fact.category, fact.metric, fact.value, fact.value_type, fact.source_type, fact.source_reference)
        )
        return cursor.lastrowid

    def save_interpretation(self, inter: InterpretationRecord) -> int:
        cursor = self.conn.execute(
            """INSERT INTO rkm_interpretations (fact_id, rule, result, confidence) VALUES (?, ?, ?, ?)""",
            (inter.fact_id, inter.rule, inter.result, inter.confidence)
        )
        return cursor.lastrowid

    def save_recommendations(self, recs: list[RecommendationRecord]):
        self.conn.executemany(
            """INSERT INTO rkm_recommendations (interpretation_id, action, confidence_type, confidence_value, status) 
               VALUES (?, ?, ?, ?, ?)""",
            [(r.interpretation_id, r.action, r.confidence_type, r.confidence_value, r.status) for r in recs]
        )

    def save_metrics(self, metrics: list[MetricRecord]):
        self.conn.executemany(
            """INSERT OR REPLACE INTO rkm_metrics (file_id, name, value) VALUES (?, ?, ?)""",
            [(m.file_id, m.name, m.value) for m in metrics]
        )

    def save_architecture(self, archs: list[ArchitectureRecord]):
        self.conn.executemany(
            """INSERT INTO rkm_architecture (file_id, layer, role) VALUES (?, ?, ?)""",
            [(a.file_id, a.layer, a.role) for a in archs]
        )

    def update_latest_analysis_run(self, metadata_id: int, run_id: int):
        self.conn.execute(
            "UPDATE rkm_metadata SET latest_analysis_run_id = ? WHERE id = ?",
            (run_id, metadata_id)
        )

    # --- Read queries ---
    def get_metadata(self) -> RepositoryMetadata:
        row = self.conn.execute("SELECT * FROM rkm_metadata LIMIT 1").fetchone()
        if not row:
            return None
        return RepositoryMetadata(
            id=row["id"],
            repository_uuid=row["repository_uuid"],
            name=row["name"],
            root_path=row["root_path"],
            language=row["language"],
            size=row["size"],
            rkm_version=row["rkm_version"],
            minimum_reader_version=row["minimum_reader_version"],
            maximum_writer_version=row["maximum_writer_version"],
            latest_analysis_run_id=row["latest_analysis_run_id"]
        )


    def get_files(self, include_archived: bool = False) -> list[FileRecord]:
        if not isinstance(include_archived, bool):
            raise TypeError("include_archived must be a boolean")
        if include_archived:
            cursor = self.conn.execute("SELECT * FROM rkm_files")
        else:
            cursor = self.conn.execute(
                """SELECT f.* FROM rkm_files f
                   JOIN rkm_analysis_runs r ON f.analysis_run_id = r.id
                   WHERE r.archived = 0"""
            )
        return [
            FileRecord(
                id=row["id"],
                analysis_run_id=row["analysis_run_id"],
                path=row["path"],
                role=row["role"],
                package=row["package"],
                size=row["size"],
                last_modified=row["last_modified"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in cursor
        ]

    def get_symbols(self, file_id: int) -> list[SymbolRecord]:
        cursor = self.conn.execute("SELECT * FROM rkm_symbols WHERE file_id = ?", (file_id,))
        return [
            SymbolRecord(
                id=row["id"],
                file_id=row["file_id"],
                name=row["name"],
                type=row["type"],
                lineno=row["lineno"]
            )
            for row in cursor
        ]

    def get_dependencies(self, file_id: int) -> list[DependencyRecord]:
        cursor = self.conn.execute("SELECT * FROM rkm_dependencies WHERE file_id = ?", (file_id,))
        return [
            DependencyRecord(
                id=row["id"],
                file_id=row["file_id"],
                target_path=row["target_path"]
            )
            for row in cursor
        ]

    def get_facts(self, file_id: int) -> list[FactRecord]:
        cursor = self.conn.execute("SELECT * FROM rkm_facts WHERE file_id = ?", (file_id,))
        return [
            FactRecord(
                id=row["id"],
                file_id=row["file_id"],
                category=row["category"],
                metric=row["metric"],
                value=row["value"],
                value_type=row["value_type"],
                source_type=row["source_type"],
                source_reference=row["source_reference"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in cursor
        ]

    def get_interpretations(self, fact_id: int) -> list[InterpretationRecord]:
        cursor = self.conn.execute("SELECT * FROM rkm_interpretations WHERE fact_id = ?", (fact_id,))
        return [
            InterpretationRecord(
                id=row["id"],
                fact_id=row["fact_id"],
                rule=row["rule"],
                result=row["result"],
                confidence=row["confidence"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in cursor
        ]

    def get_recommendations(self, interpretation_id: int) -> list[RecommendationRecord]:
        cursor = self.conn.execute("SELECT * FROM rkm_recommendations WHERE interpretation_id = ?", (interpretation_id,))
        return [
            RecommendationRecord(
                id=row["id"],
                interpretation_id=row["interpretation_id"],
                action=row["action"],
                confidence_type=row["confidence_type"],
                confidence_value=row["confidence_value"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in cursor
        ]

    def get_metrics(self, file_id: int) -> list[MetricRecord]:
        cursor = self.conn.execute("SELECT * FROM rkm_metrics WHERE file_id = ?", (file_id,))
        return [
            MetricRecord(
                id=row["id"],
                file_id=row["file_id"],
                name=row["name"],
                value=row["value"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in cursor
        ]

    def get_architecture(self, file_id: int) -> list[ArchitectureRecord]:
        cursor = self.conn.execute("SELECT * FROM rkm_architecture WHERE file_id = ?", (file_id,))
        return [
            ArchitectureRecord(
                id=row["id"],
                file_id=row["file_id"],
                layer=row["layer"],
                role=row["role"]
            )
            for row in cursor
        ]

    # --- AnalysisRun, Provenance, and Lineage Helpers ---
    def save_provenance(self, prov: ProvenanceRecord) -> int:
        cursor = self.conn.execute(
            """INSERT INTO rkm_provenance 
               (fact_id, generated_by, engine_version, rule_id, model_name, prompt_hash, configuration_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (prov.fact_id, prov.generated_by, prov.engine_version, prov.rule_id, prov.model_name, prov.prompt_hash, prov.configuration_hash)
        )
        return cursor.lastrowid

    def get_provenance(self, fact_id: int) -> list[ProvenanceRecord]:
        cursor = self.conn.execute("SELECT * FROM rkm_provenance WHERE fact_id = ?", (fact_id,))
        return [
            ProvenanceRecord(
                id=row["id"],
                fact_id=row["fact_id"],
                generated_by=row["generated_by"],
                engine_version=row["engine_version"],
                rule_id=row["rule_id"],
                model_name=row["model_name"],
                prompt_hash=row["prompt_hash"],
                configuration_hash=row["configuration_hash"],
                timestamp=row["timestamp"]
            )
            for row in cursor
        ]

    def _parse_analysis_run(self, row) -> AnalysisRun:
        if not row:
            return None
        keys = row.keys()
        return AnalysisRun(
            id=row["id"],
            repository_id=row["repository_id"],
            timestamp=row["timestamp"],
            duration=row["duration"],
            engine_version=row["engine_version"],
            rkm_version=row["rkm_version"],
            content_hash=row["content_hash"],
            previous_run_id=row["previous_run_id"],
            rule_pack_version=row["rule_pack_version"] if "rule_pack_version" in keys else "1.0.0",
            semantic_hash=row["semantic_hash"] if "semantic_hash" in keys else None,
            archived=row["archived"] if "archived" in keys else 0,
            semantic_hash_strategy=row["semantic_hash_strategy"] if "semantic_hash_strategy" in keys else "AST"
        )

    def get_analysis_runs(self, include_archived: bool = False) -> list[AnalysisRun]:
        if not isinstance(include_archived, bool):
            raise TypeError("include_archived must be a boolean")
        if include_archived:
            cursor = self.conn.execute("SELECT * FROM rkm_analysis_runs ORDER BY id ASC")
        else:
            cursor = self.conn.execute("SELECT * FROM rkm_analysis_runs WHERE archived = 0 ORDER BY id ASC")
        return [self._parse_analysis_run(row) for row in cursor]

    def get_analysis_run(self, run_id: int) -> AnalysisRun:
        row = self.conn.execute("SELECT * FROM rkm_analysis_runs WHERE id = ?", (run_id,)).fetchone()
        return self._parse_analysis_run(row)

    def get_analysis_run_by_hash(self, content_hash: str) -> AnalysisRun:
        # Cache reuse only considers active (non-archived) runs
        row = self.conn.execute("SELECT * FROM rkm_analysis_runs WHERE content_hash = ? AND archived = 0 LIMIT 1", (content_hash,)).fetchone()
        return self._parse_analysis_run(row)


    def get_file_records_for_run(self, run_id: int) -> list[FileRecord]:
        cursor = self.conn.execute("SELECT * FROM rkm_files WHERE analysis_run_id = ?", (run_id,))
        return [
            FileRecord(
                id=row["id"],
                analysis_run_id=row["analysis_run_id"],
                path=row["path"],
                role=row["role"],
                package=row["package"],
                size=row["size"],
                last_modified=row["last_modified"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in cursor
        ]

    def archive_analysis_run(self, run_id: int):
        with self.transaction():
            self.conn.execute(
                "UPDATE rkm_analysis_runs SET archived = 1 WHERE id = ?",
                (run_id,)
            )

    def log_event(self, event_type: str, event_action: str, target_id: str, correlation_id: str, message: str):
        try:
            with self.transaction():
                self.conn.execute(
                    """INSERT INTO rkm_event_logs (event_type, event_action, target_id, correlation_id, message)
                       VALUES (?, ?, ?, ?, ?)""",
                    (event_type, event_action, target_id, correlation_id, message)
                )
        except sqlite3.OperationalError:
            # During initial boot, table rkm_event_logs might not exist yet
            return

    def get_event_logs(self) -> list[dict]:
        try:
            cursor = self.conn.execute("SELECT * FROM rkm_event_logs ORDER BY id ASC")
            return [
                {
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "event_action": row["event_action"],
                    "target_id": row["target_id"],
                    "correlation_id": row["correlation_id"],
                    "message": row["message"],
                    "created_at": row["created_at"]
                }
                for row in cursor
            ]
        except sqlite3.OperationalError:
            return []

    def save_stage_cache(self, stage: str, stage_version: str, input_hash: str, output_ref: str):
        with self.transaction():
            self.conn.execute(
                """INSERT OR REPLACE INTO rkm_stage_cache (analysis_stage, stage_version, input_hash, output_reference)
                   VALUES (?, ?, ?, ?)""",
                (stage, stage_version, input_hash, output_ref)
            )

    def get_stage_cache(self, stage: str, stage_version: str, input_hash: str) -> str:
        try:
            row = self.conn.execute(
                """SELECT output_reference FROM rkm_stage_cache
                   WHERE analysis_stage = ? AND stage_version = ? AND input_hash = ?
                   LIMIT 1""",
                (stage, stage_version, input_hash)
            )
            res = row.fetchone()
            return res["output_reference"] if res else None
        except sqlite3.OperationalError:
            return None

    def prune_stage_cache(self) -> None:
        with self.transaction():
            # Get the timestamp of the 5th newest active run
            row = self.conn.execute(
                "SELECT timestamp FROM rkm_analysis_runs WHERE archived = 0 ORDER BY id DESC LIMIT 1 OFFSET 4"
            ).fetchone()
            if row and row["timestamp"]:
                self.conn.execute(
                    "DELETE FROM rkm_stage_cache WHERE created_at < ?",
                    (row["timestamp"],)
                )

    def save_rules(self, rules: list[RkmRule]):
        with self.transaction():
            self.conn.executemany(
                """INSERT OR REPLACE INTO rkm_rules 
                   (id, rule_pack_id, name, description, predicate_type, version) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [(r.id, r.rule_pack_id, r.name, r.description, r.predicate_type, r.version) for r in rules]
            )

    def get_rules(self) -> list[RkmRule]:
        cursor = self.conn.execute("SELECT * FROM rkm_rules")
        return [
            RkmRule(
                id=row["id"],
                rule_pack_id=row["rule_pack_id"],
                name=row["name"],
                description=row["description"],
                predicate_type=row["predicate_type"],
                version=row["version"]
            )
            for row in cursor
        ]

    def save_rule_instances(self, instances: list[RkmRuleInstance]):
        with self.transaction():
            self.conn.executemany(
                """INSERT OR REPLACE INTO rkm_rule_instances 
                   (rule_id, enabled, severity, predicate_config, version) 
                   VALUES (?, ?, ?, ?, ?)""",
                [(inst.rule_id, inst.enabled, inst.severity, json.dumps(inst.predicate_config), inst.version) for inst in instances]
            )

    def get_rule_instances(self) -> list[RkmRuleInstance]:
        cursor = self.conn.execute("SELECT * FROM rkm_rule_instances")
        return [
            RkmRuleInstance(
                id=row["id"],
                rule_id=row["rule_id"],
                enabled=row["enabled"],
                severity=row["severity"],
                predicate_config=json.loads(row["predicate_config"]),
                version=row["version"]
            )
            for row in cursor
        ]

    def save_evaluations(self, evals: list[RkmEvaluation]) -> list[int]:
        ids = []
        with self.transaction():
            for ev in evals:
                cursor = self.conn.execute(
                    """INSERT INTO rkm_evaluations 
                       (analysis_run_id, rule_id, status, started_at, finished_at, duration_ms, engine_version, rule_version) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (ev.analysis_run_id, ev.rule_id, ev.status.value if isinstance(ev.status, EvaluationStatus) else ev.status,
                     ev.started_at, ev.finished_at, ev.duration_ms, ev.engine_version, ev.rule_version)
                )
                ids.append(cursor.lastrowid)
        return ids

    def save_violations(self, violations: list[tuple[RkmViolation, list[RkmViolationEvidence]]]):
        with self.transaction():
            for vio, evidences in violations:
                cursor = self.conn.execute(
                    """INSERT INTO rkm_violations (evaluation_id, file_id, symbol_id, details) 
                       VALUES (?, ?, ?, ?)""",
                    (vio.evaluation_id, vio.file_id, vio.symbol_id, vio.details)
                )
                violation_id = cursor.lastrowid
                
                # Ingest violation evidence
                if evidences:
                    self.conn.executemany(
                        """INSERT INTO rkm_violation_evidence (violation_id, evidence_type, evidence_id) 
                           VALUES (?, ?, ?)""",
                        [(violation_id, ev.evidence_type, ev.evidence_id) for ev in evidences]
                    )

    def get_violations(self, analysis_run_id: int) -> list[tuple[RkmViolation, RkmRule, list[RkmViolationEvidence]]]:
        cursor = self.conn.execute(
            """SELECT v.*, r.id as rule_id, r.rule_pack_id, r.name as rule_name, r.description as rule_description, r.predicate_type, r.version as rule_version
               FROM rkm_violations v
               JOIN rkm_evaluations e ON v.evaluation_id = e.id
               JOIN rkm_rules r ON e.rule_id = r.id
               WHERE e.analysis_run_id = ?""",
            (analysis_run_id,)
        )
        
        results = []
        for row in cursor.fetchall():
            violation_id = row["id"]
            vio = RkmViolation(
                id=violation_id,
                evaluation_id=row["evaluation_id"],
                file_id=row["file_id"],
                symbol_id=row["symbol_id"],
                details=row["details"],
                created_at=row["created_at"]
            )
            rule = RkmRule(
                id=row["rule_id"],
                rule_pack_id=row["rule_pack_id"],
                name=row["rule_name"],
                description=row["rule_description"],
                predicate_type=row["predicate_type"],
                version=row["rule_version"]
            )
            
            # Fetch evidence for this violation
            ev_cursor = self.conn.execute(
                "SELECT * FROM rkm_violation_evidence WHERE violation_id = ?",
                (violation_id,)
            )
            evidences = [
                RkmViolationEvidence(
                    id=ev_row["id"],
                    violation_id=ev_row["violation_id"],
                    evidence_type=ev_row["evidence_type"],
                    evidence_id=ev_row["evidence_id"],
                    created_at=ev_row["created_at"]
                )
                for ev_row in ev_cursor
            ]
            results.append((vio, rule, evidences))
        return results

    def save_entity_history(self, history: list[RkmEntityHistory]):
        if not history:
            return
        
        seen = {}
        for h in history:
            key = (h.analysis_run_id, h.entity_type, h.entity_identifier)
            seen[key] = h
        deduplicated = list(seen.values())
        
        run_id = deduplicated[0].analysis_run_id
        
        with self.transaction():
            self.conn.execute(
                "DELETE FROM rkm_entity_history WHERE analysis_run_id = ?",
                (run_id,)
            )
            self.conn.executemany(
                """INSERT INTO rkm_entity_history
                   (entity_type, entity_identifier, analysis_run_id, action, signature)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (h.entity_type, h.entity_identifier, h.analysis_run_id, h.action, h.signature)
                    for h in deduplicated
                ]
            )

    def get_entity_history(self, run_id: int) -> list[RkmEntityHistory]:
        if not isinstance(run_id, int):
            raise TypeError("run_id must be an integer")
            
        cursor = self.conn.execute(
            "SELECT * FROM rkm_entity_history WHERE analysis_run_id = ?",
            (run_id,)
        )
        return [
            RkmEntityHistory(
                id=row["id"],
                entity_type=row["entity_type"],
                entity_identifier=row["entity_identifier"],
                analysis_run_id=row["analysis_run_id"],
                action=row["action"],
                signature=row["signature"],
                created_at=row["created_at"]
            )
            for row in cursor
        ]

    def close(self):
        self.conn.close()

