-- depends_on: 002_rkm_v1.1.0_upgrade.sql

-- 1. Create rkm_manifest singleton table
CREATE TABLE IF NOT EXISTS rkm_manifest (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    repository_uuid TEXT UNIQUE NOT NULL,
    schema_version TEXT NOT NULL,
    minimum_reader_version TEXT NOT NULL,
    maximum_writer_version TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    rule_pack_version TEXT NOT NULL,
    snapshot_version TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Alter rkm_analysis_runs table to add rule pack, semantic hash, and archived columns
ALTER TABLE rkm_analysis_runs ADD COLUMN rule_pack_version TEXT NOT NULL DEFAULT '1.0.0';
ALTER TABLE rkm_analysis_runs ADD COLUMN semantic_hash TEXT;
ALTER TABLE rkm_analysis_runs ADD COLUMN archived INTEGER NOT NULL DEFAULT 0;

-- 3. Populate manifest from metadata table
INSERT INTO rkm_manifest (id, repository_uuid, schema_version, minimum_reader_version, maximum_writer_version, engine_version, rule_pack_version, snapshot_version)
SELECT 1, repository_uuid, '1.2.0', '1.2.0', '1.x', '1.2.0', '1.0.0', '1.0.0'
FROM rkm_metadata LIMIT 1;

-- 4. Create rkm_event_logs table
CREATE TABLE IF NOT EXISTS rkm_event_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    event_action TEXT NOT NULL,
    target_id TEXT,
    correlation_id TEXT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. Create rkm_stage_cache table
CREATE TABLE IF NOT EXISTS rkm_stage_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_stage TEXT NOT NULL,
    stage_version TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    output_reference TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(analysis_stage, stage_version, input_hash)
);

-- 6. Create immutable triggers preventing update and delete on observation tables
-- rkm_files triggers
CREATE TRIGGER IF NOT EXISTS prevent_files_update BEFORE UPDATE ON rkm_files
BEGIN
    SELECT RAISE(FAIL, 'RKM files observations are immutable and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS prevent_files_delete BEFORE DELETE ON rkm_files
BEGIN
    SELECT RAISE(FAIL, 'RKM files observations are immutable and cannot be deleted.');
END;

-- rkm_symbols triggers
CREATE TRIGGER IF NOT EXISTS prevent_symbols_update BEFORE UPDATE ON rkm_symbols
BEGIN
    SELECT RAISE(FAIL, 'RKM symbols observations are immutable and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS prevent_symbols_delete BEFORE DELETE ON rkm_symbols
BEGIN
    SELECT RAISE(FAIL, 'RKM symbols observations are immutable and cannot be deleted.');
END;

-- rkm_dependencies triggers
CREATE TRIGGER IF NOT EXISTS prevent_dependencies_update BEFORE UPDATE ON rkm_dependencies
BEGIN
    SELECT RAISE(FAIL, 'RKM dependencies observations are immutable and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS prevent_dependencies_delete BEFORE DELETE ON rkm_dependencies
BEGIN
    SELECT RAISE(FAIL, 'RKM dependencies observations are immutable and cannot be deleted.');
END;

-- rkm_facts triggers
CREATE TRIGGER IF NOT EXISTS prevent_facts_update BEFORE UPDATE ON rkm_facts
BEGIN
    SELECT RAISE(FAIL, 'RKM facts observations are immutable and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS prevent_facts_delete BEFORE DELETE ON rkm_facts
BEGIN
    SELECT RAISE(FAIL, 'RKM facts observations are immutable and cannot be deleted.');
END;

-- rkm_interpretations triggers
CREATE TRIGGER IF NOT EXISTS prevent_interpretations_update BEFORE UPDATE ON rkm_interpretations
BEGIN
    SELECT RAISE(FAIL, 'RKM interpretations observations are immutable and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS prevent_interpretations_delete BEFORE DELETE ON rkm_interpretations
BEGIN
    SELECT RAISE(FAIL, 'RKM interpretations observations are immutable and cannot be deleted.');
END;

-- rkm_recommendations triggers
CREATE TRIGGER IF NOT EXISTS prevent_recommendations_update BEFORE UPDATE ON rkm_recommendations
BEGIN
    SELECT RAISE(FAIL, 'RKM recommendations observations are immutable and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS prevent_recommendations_delete BEFORE DELETE ON rkm_recommendations
BEGIN
    SELECT RAISE(FAIL, 'RKM recommendations observations are immutable and cannot be deleted.');
END;

-- rkm_metrics triggers
CREATE TRIGGER IF NOT EXISTS prevent_metrics_update BEFORE UPDATE ON rkm_metrics
BEGIN
    SELECT RAISE(FAIL, 'RKM metrics observations are immutable and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS prevent_metrics_delete BEFORE DELETE ON rkm_metrics
BEGIN
    SELECT RAISE(FAIL, 'RKM metrics observations are immutable and cannot be deleted.');
END;

-- rkm_architecture triggers
CREATE TRIGGER IF NOT EXISTS prevent_architecture_update BEFORE UPDATE ON rkm_architecture
BEGIN
    SELECT RAISE(FAIL, 'RKM architecture observations are immutable and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS prevent_architecture_delete BEFORE DELETE ON rkm_architecture
BEGIN
    SELECT RAISE(FAIL, 'RKM architecture observations are immutable and cannot be deleted.');
END;

-- rkm_provenance triggers
CREATE TRIGGER IF NOT EXISTS prevent_provenance_update BEFORE UPDATE ON rkm_provenance
BEGIN
    SELECT RAISE(FAIL, 'RKM provenance observations are immutable and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS prevent_provenance_delete BEFORE DELETE ON rkm_provenance
BEGIN
    SELECT RAISE(FAIL, 'RKM provenance observations are immutable and cannot be deleted.');
END;
