/**
 * Ultron Web SPA — UI State Machine & Store
 * Campaign 8: Explicit UI State Machine & State Transitions
 */

export const STATES = {
    IDLE: 'IDLE',
    SELECTING_REPO: 'SELECTING_REPO',
    CONNECTED: 'CONNECTED',
    SCANNING: 'SCANNING',
    ANALYZING: 'ANALYZING',
    RENDERING: 'RENDERING',
    READY: 'READY',
    REFRESHING: 'REFRESHING',
    ERROR: 'ERROR'
};

const VALID_TRANSITIONS = {
    [STATES.IDLE]: [STATES.SELECTING_REPO, STATES.CONNECTED, STATES.SCANNING, STATES.ERROR],
    [STATES.SELECTING_REPO]: [STATES.IDLE, STATES.CONNECTED, STATES.ERROR],
    [STATES.CONNECTED]: [STATES.SCANNING, STATES.IDLE, STATES.ERROR],
    [STATES.SCANNING]: [STATES.ANALYZING, STATES.ERROR, STATES.CONNECTED],
    [STATES.ANALYZING]: [STATES.RENDERING, STATES.ERROR, STATES.CONNECTED],
    [STATES.RENDERING]: [STATES.READY, STATES.ERROR],
    [STATES.READY]: [STATES.REFRESHING, STATES.SCANNING, STATES.IDLE, STATES.ERROR],
    [STATES.REFRESHING]: [STATES.ANALYZING, STATES.READY, STATES.ERROR],
    [STATES.ERROR]: [STATES.IDLE, STATES.CONNECTED, STATES.SCANNING, STATES.READY]
};

class StateStore {
    constructor() {
        this.currentState = STATES.IDLE;
        this.repoPath = '';
        this.activeTab = 'dashboard-tab';
        this.mode = 'creator'; // 'creator' or 'engineer'
        this.listeners = new Set();
        this.lastAnalysisData = null;
        this.lastError = null;
    }

    getState() {
        return this.currentState;
    }

    setState(newState, payload = {}) {
        if (this.currentState === newState) return true;

        const allowed = VALID_TRANSITIONS[this.currentState] || [];
        if (!allowed.includes(newState)) {
            console.warn(`[Ultron State] Invalid transition blocked: ${this.currentState} -> ${newState}`);
            return false;
        }

        console.log(`[Ultron State] Transition: ${this.currentState} -> ${newState}`);
        this.currentState = newState;

        if (payload.repoPath !== undefined) this.repoPath = payload.repoPath;
        if (payload.lastAnalysisData !== undefined) this.lastAnalysisData = payload.lastAnalysisData;
        if (payload.lastError !== undefined) this.lastError = payload.lastError;

        this.notifyListeners(newState, payload);
        return true;
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
