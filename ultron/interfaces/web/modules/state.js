/**
 * Ultron Web SPA — Authoritative UI State Machine & Store (v2.6.1)
 * Single Source of Truth for repository context, snapshot identity, objective progress,
 * request lifecycle tracking, and continuation readiness.
 */

export const STATES = {
    IDLE: 'IDLE',
    CONNECTING: 'CONNECTING',
    ANALYZING: 'ANALYZING',
    ATTACHING: 'ATTACHING',
    READY: 'READY',
    PARTIAL: 'PARTIAL',
    DEGRADED: 'DEGRADED',
    ERROR: 'ERROR',
    BLOCKED: 'BLOCKED',
    // Backward-compatibility aliases
    SELECTING_REPO: 'CONNECTING',
    CONNECTED: 'READY',
    SCANNING: 'ANALYZING',
    RENDERING: 'ANALYZING',
    REFRESHING: 'ANALYZING'
};

const VALID_TRANSITIONS = {
    [STATES.IDLE]: [STATES.CONNECTING, STATES.ANALYZING, STATES.ATTACHING, STATES.READY, STATES.PARTIAL, STATES.DEGRADED, STATES.ERROR],
    [STATES.CONNECTING]: [STATES.ANALYZING, STATES.ATTACHING, STATES.READY, STATES.PARTIAL, STATES.DEGRADED, STATES.ERROR, STATES.IDLE],
    [STATES.ANALYZING]: [STATES.READY, STATES.PARTIAL, STATES.DEGRADED, STATES.ERROR, STATES.IDLE, STATES.CONNECTING],
    [STATES.ATTACHING]: [STATES.ANALYZING, STATES.READY, STATES.PARTIAL, STATES.DEGRADED, STATES.ERROR, STATES.IDLE, STATES.CONNECTING],
    [STATES.READY]: [STATES.CONNECTED, STATES.CONNECTING, STATES.ANALYZING, STATES.ATTACHING, STATES.PARTIAL, STATES.DEGRADED, STATES.IDLE, STATES.ERROR, STATES.BLOCKED],
    [STATES.PARTIAL]: [STATES.CONNECTING, STATES.ANALYZING, STATES.ATTACHING, STATES.READY, STATES.IDLE, STATES.ERROR],
    [STATES.DEGRADED]: [STATES.CONNECTING, STATES.ANALYZING, STATES.ATTACHING, STATES.READY, STATES.IDLE, STATES.ERROR],
    [STATES.BLOCKED]: [STATES.READY, STATES.ANALYZING, STATES.CONNECTING, STATES.IDLE, STATES.ERROR],
    [STATES.ERROR]: [STATES.IDLE, STATES.CONNECTING, STATES.ANALYZING, STATES.ATTACHING, STATES.READY, STATES.PARTIAL, STATES.DEGRADED]
};

class StateStore {
    constructor() {
        this.currentState = STATES.IDLE;
        this.repoPath = '';
        this.workspace_id = '';
        this.repository_id = '';
        this.snapshot_id = '';
        this.model_hash = '';
        this.objective_id = '';
        this.objective_version = 0;
        this.active_objective = null;
        this.development_session = null;
        this.session_timeline = [];
        this.evolution_delta = null;
        this.projection_version = '2.7.0';
        this.active_request_keys = new Set();
        this.continuation_readiness = null;
        this.lastAnalysisData = null;
        this.lastError = null;
        this.activeTab = 'dashboard-tab';
        this.mode = 'creator'; // 'creator' or 'engineer'
        this.activePersona = 'developer';
        this.inspectedEntity = null;
        this.listeners = new Set();
        this.graphLayoutCache = new Map(); // Bounded to MAX_GRAPH_CACHE_ENTRIES
        this.MAX_GRAPH_CACHE_ENTRIES = 10;
        // Phase 1.9 & Phase 2.0 Canonical Mission State
        this.mission_intent = '';
        this.target_files = '';
        this.selected_provider = 'markdown';
        this.active_issue_id = '';
        this.reproduction_signature = '';
        this.why_it_matters = '';
    }

    setMissionContext({ intent = '', target_files = '', provider = 'markdown', issue_id = '', reproduction_signature = '', why_it_matters = '' }) {
        this.mission_intent = intent;
        this.target_files = target_files;
        this.selected_provider = provider;
        this.active_issue_id = issue_id;
        this.reproduction_signature = reproduction_signature;
        this.why_it_matters = why_it_matters;
        this.notifyListeners(this.currentState, { missionChange: true });
    }

    updateMissionIntent(intent) {
        this.mission_intent = intent || '';
        this.notifyListeners(this.currentState, { missionIntentChange: true, intent: this.mission_intent });
    }

    updateTargetFiles(target_files) {
        this.target_files = target_files || '';
        this.notifyListeners(this.currentState, { targetFilesChange: true, target_files: this.target_files });
    }

    setProvider(provider) {
        this.selected_provider = provider || 'markdown';
        this.notifyListeners(this.currentState, { providerChange: true, provider: this.selected_provider });
    }

    getMissionContext() {
        return {
            intent: this.mission_intent,
            target_files: this.target_files,
            provider: this.selected_provider,
            issue_id: this.active_issue_id,
            reproduction_signature: this.reproduction_signature || '',
            why_it_matters: this.why_it_matters || ''
        };
    }

    getSnapshot(snapshotId) {
        if (!snapshotId || snapshotId === this.snapshot_id) {
            return this.lastAnalysisData;
        }
        return this.lastAnalysisData?.snapshot_id === snapshotId ? this.lastAnalysisData : null;
    }

    getState() {
        return this.currentState;
    }

    getSnapshotContext() {
        return {
            repository: this.repoPath,
            workspace_id: this.workspace_id,
            repository_id: this.repository_id,
            snapshot_id: this.snapshot_id,
            model_hash: this.model_hash,
            objective_id: this.objective_id,
            objective_version: this.objective_version,
            continuation_readiness: this.continuation_readiness,
            development_session: this.development_session,
            projection_version: this.projection_version
        };
    }

    hydrateFromAnalysis(payload) {
        if (!payload) return false;
        const data = payload.data || payload;

        // Guard against cross-repo race: if repo_root is present and doesn't match active repo
        const incomingRepo = data.repository_root || (data.identity && data.identity.repository_root);
        if (incomingRepo && this.repoPath) {
            const normIncoming = String(incomingRepo).replace(/\\/g, '/').toLowerCase();
            const normCurrent = String(this.repoPath).replace(/\\/g, '/').toLowerCase();
            if (normIncoming !== normCurrent && !normIncoming.endsWith(normCurrent) && !normCurrent.endsWith(normIncoming)) {
                console.warn(`[Ultron State] Discarded late response for inactive repository: ${incomingRepo} (current: ${this.repoPath})`);
                return false;
            }
        }

        this.projection_version = data.projection_version || '2.6.5';
        this.payload_bytes = data.payload_bytes || (data.identity && data.identity.payload_bytes) || 0;
        this.payload_build_ms = data.payload_build_ms || (data.identity && data.identity.payload_build_ms) || 0;
        this.payload_serialize_ms = data.payload_serialize_ms || (data.identity && data.identity.payload_serialize_ms) || 0;
        this.snapshot_id = data.snapshot_id || '';
        this.model_hash = data.model_hash || data.repo_fingerprint || data.snapshot_id || '';
        this.repository_id = data.repository_id || (data.identity && data.identity.repository_id) || this.repository_id;
        this.lastAnalysisData = data;

        if (data.objective) {
            this.active_objective = data.objective;
            this.objective_id = data.objective.objective_id || '';
            this.objective_version = (this.objective_version || 0) + 1;
        }

        if (data.session) {
            this.development_session = data.session;
            this.session_timeline = data.session.timeline || [];
        }

        if (data.readiness) {
            // Snapshot-bound readiness check
            if (data.readiness.snapshot_id && data.readiness.snapshot_id !== this.snapshot_id && this.snapshot_id) {
                console.warn(`[Ultron State] Readiness snapshot mismatch (${data.readiness.snapshot_id} != ${this.snapshot_id}). Invalidating.`);
                this.continuation_readiness = null;
            } else {
                this.continuation_readiness = data.readiness;
            }
        }

        if (data.diff) {
            this.evolution_delta = data.diff;
        }

        this.setState(STATES.READY, {
            snapshot_id: this.snapshot_id,
            model_hash: this.model_hash,
            repository_id: this.repository_id,
            lastAnalysisData: data,
            active_objective: this.active_objective,
            continuation_readiness: this.continuation_readiness
        });
        return true;
    }

    setState(newState, payload = {}) {
        if (this.currentState === newState && Object.keys(payload).length === 0) return true;

        const allowed = VALID_TRANSITIONS[this.currentState] || [];
        if (this.currentState !== newState && !allowed.includes(newState)) {
            console.warn(`[Ultron State] Invalid transition blocked: ${this.currentState} -> ${newState}`);
            return false;
        }

        if (this.currentState !== newState) {
            console.log(`[Ultron State] Transition: ${this.currentState} -> ${newState}`);
            this.currentState = newState;
        }

        if (payload.repoPath !== undefined) this.repoPath = payload.repoPath;
        if (payload.workspace_id !== undefined) this.workspace_id = payload.workspace_id;
        if (payload.repository_id !== undefined) this.repository_id = payload.repository_id;
        if (payload.snapshot_id !== undefined) this.snapshot_id = payload.snapshot_id;
        if (payload.model_hash !== undefined) this.model_hash = payload.model_hash;
        if (payload.lastAnalysisData !== undefined) this.lastAnalysisData = payload.lastAnalysisData;
        if (payload.active_objective !== undefined) this.active_objective = payload.active_objective;
        if (payload.continuation_readiness !== undefined) this.continuation_readiness = payload.continuation_readiness;
        if (payload.lastError !== undefined) this.lastError = payload.lastError;

        this.notifyListeners(newState, payload);
        return true;
    }

    setRepositoryContext(repoPath, workspaceId = '', repositoryId = '') {
        this.repoPath = repoPath;
        this.workspace_id = workspaceId;
        this.repository_id = repositoryId || workspaceId;
        this.notifyListeners(this.currentState, { repoContextChange: true });
    }

    setSnapshot(snapshotId, modelHash = '', analysisData = null) {
        this.snapshot_id = snapshotId || '';
        this.model_hash = modelHash || '';
        if (analysisData) this.lastAnalysisData = analysisData;
        this.notifyListeners(this.currentState, { snapshotChange: true });
    }

    setObjective(objective) {
        if (!objective) return;
        this.active_objective = objective;
        this.objective_id = objective.objective_id || '';
        this.objective_version = (this.objective_version || 0) + 1;
        if (objective.repository_id) this.repository_id = objective.repository_id;
        if (objective.workspace_id) this.workspace_id = objective.workspace_id;
        this.notifyListeners(this.currentState, { objectiveChange: true, objective });
    }

    getObjective() {
        return this.active_objective;
    }

    setContinuationReadiness(readiness) {
        this.continuation_readiness = readiness;
        this.notifyListeners(this.currentState, { readinessChange: true, readiness });
    }

    registerRequest(key) {
        this.active_request_keys.add(key);
    }

    unregisterRequest(key) {
        this.active_request_keys.delete(key);
    }

    getGraphLayout(repository_id, snapshot_id, model_hash, layout_mode, svg_id) {
        const repo = repository_id || this.repository_id || this.repoPath || 'default';
        const snap = snapshot_id || this.snapshot_id || 'snap';
        const hash = model_hash || this.model_hash || 'hash';
        const mode = layout_mode || 'system';
        const svg = svg_id || 'main';
        const key = `${repo}::${snap}::${hash}::${mode}::${svg}`;
        return this.graphLayoutCache.get(key) || null;
    }

    setGraphLayout(repository_id, snapshot_id, model_hash, layout_mode, svg_id, layoutData) {
        if (!layoutData) return;
        const repo = repository_id || this.repository_id || this.repoPath || 'default';
        const snap = snapshot_id || this.snapshot_id || 'snap';
        const hash = model_hash || this.model_hash || 'hash';
        const mode = layout_mode || 'system';
        const svg = svg_id || 'main';
        const key = `${repo}::${snap}::${hash}::${mode}::${svg}`;

        // LRU Eviction if cache limit reached
        if (this.graphLayoutCache.size >= this.MAX_GRAPH_CACHE_ENTRIES && !this.graphLayoutCache.has(key)) {
            const oldestKey = this.graphLayoutCache.keys().next().value;
            if (oldestKey) this.graphLayoutCache.delete(oldestKey);
        }
        this.graphLayoutCache.set(key, layoutData);
    }

    clearGraphLayouts(repository_id = null) {
        if (!repository_id) {
            this.graphLayoutCache.clear();
            return;
        }
        const prefix = `${repository_id}::`;
        for (const key of Array.from(this.graphLayoutCache.keys())) {
            if (key.startsWith(prefix)) {
                this.graphLayoutCache.delete(key);
            }
        }
    }

    onRepositorySwitch(newRepo) {
        const startTime = Date.now();
        // 1. Invalidate graph layout caches for prior repositories
        this.clearGraphLayouts();

        // 2. Clear all active request registrations
        this.active_request_keys.clear();

        // 3. Reset repository state
        this.repoPath = newRepo;
        this.snapshot_id = '';
        this.model_hash = '';
        this.objective_id = '';
        this.objective_version = 0;
        this.active_objective = null;
        this.development_session = null;
        this.session_timeline = [];
        this.evolution_delta = null;
        this.continuation_readiness = null;
        this.lastAnalysisData = null;
        this.lastError = null;

        // 4. Update state machine
        this.setState(STATES.CONNECTING, { repoPath: newRepo, repoSwitched: true, elapsedMs: Date.now() - startTime });
        return { success: true, newRepo, elapsedMs: Date.now() - startTime };
    }

    resetForNewRepo(newRepo) {
        return this.onRepositorySwitch(newRepo);
    }

    subscribe(callback) {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }

    notifyListeners(newState, payload) {
        for (const cb of this.listeners) {
            try {
                cb(newState, payload, this);
            } catch (err) {
                console.error("[Ultron State] Listener error:", err);
            }
        }
    }

    setMode(mode) {
        this.mode = mode;
        this.notifyListeners(this.currentState, { modeChange: true });
    }

    setActiveTab(tabId) {
        this.activeTab = tabId;
        this.notifyListeners(this.currentState, { tabChange: true });
    }
}

export const stateStore = new StateStore();
