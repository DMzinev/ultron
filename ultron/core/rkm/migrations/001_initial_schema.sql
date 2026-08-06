CREATE TABLE IF NOT EXISTS rkm_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT UNIQUE NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rkm_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_uuid TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL,
    language TEXT,
    size INTEGER,
    rkm_version TEXT NOT NULL,
    minimum_reader_version TEXT NOT NULL DEFAULT '1.0.0',
    maximum_writer_version TEXT NOT NULL DEFAULT '1.x',
    latest_analysis_run_id INTEGER
);

CREATE TABLE IF NOT EXISTS rkm_analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    duration REAL NOT NULL,
    engine_version TEXT NOT NULL,
    rkm_version TEXT NOT NULL,
    analysis_hash TEXT NOT NULL,
    FOREIGN KEY(repository_id) REFERENCES rkm_metadata(id)
);

CREATE TABLE IF NOT EXISTS rkm_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_run_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    role TEXT NOT NULL,
    package TEXT,
    size INTEGER,
    last_modified TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(analysis_run_id) REFERENCES rkm_analysis_runs(id) ON DELETE CASCADE,
    UNIQUE(analysis_run_id, path)
);

CREATE TABLE IF NOT EXISTS rkm_symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    lineno INTEGER,
    FOREIGN KEY(file_id) REFERENCES rkm_files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rkm_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    target_path TEXT NOT NULL,
    FOREIGN KEY(file_id) REFERENCES rkm_files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rkm_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    metric TEXT NOT NULL,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_reference TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(file_id) REFERENCES rkm_files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rkm_interpretations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id INTEGER NOT NULL,
    rule TEXT NOT NULL,
    result TEXT NOT NULL,
    confidence REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(fact_id) REFERENCES rkm_facts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rkm_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interpretation_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    confidence_type TEXT NOT NULL,
    confidence_value REAL,
    status TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(interpretation_id) REFERENCES rkm_interpretations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rkm_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(file_id) REFERENCES rkm_files(id) ON DELETE CASCADE,
    UNIQUE(file_id, name)
);

CREATE TABLE IF NOT EXISTS rkm_architecture (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    layer TEXT NOT NULL,
    role TEXT NOT NULL,
    FOREIGN KEY(file_id) REFERENCES rkm_files(id) ON DELETE CASCADE
);
