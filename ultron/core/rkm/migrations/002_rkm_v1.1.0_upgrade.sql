-- Migration 002: Upgrade RKM to version 1.1.0
-- Alter rkm_analysis_runs to add previous_run_id and rename analysis_hash to content_hash
-- Add rkm_provenance table

-- 1. Create table rkm_provenance with fact delete cascade
CREATE TABLE IF NOT EXISTS rkm_provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id INTEGER NOT NULL,
    generated_by TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    rule_id TEXT,
    model_name TEXT,
    prompt_hash TEXT,
    configuration_hash TEXT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(fact_id) REFERENCES rkm_facts(id) ON DELETE CASCADE
);

-- 2. Alter rkm_analysis_runs table to add previous_run_id with ON DELETE SET NULL
ALTER TABLE rkm_analysis_runs ADD COLUMN previous_run_id INTEGER REFERENCES rkm_analysis_runs(id) ON DELETE SET NULL;

-- 3. Rename analysis_hash to content_hash
ALTER TABLE rkm_analysis_runs RENAME COLUMN analysis_hash TO content_hash;

-- 4. Update reader compatibility and version info in existing metadata row
UPDATE rkm_metadata SET minimum_reader_version = '1.1.0', rkm_version = '1.1.0' WHERE id = 1;
