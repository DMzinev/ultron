/**
 * Ultron Web SPA — Robust API Client (v2.6.1)
 * Features:
 * 1. Contextual Request Sequencing (out-of-order stale response protection)
 * 2. AbortController cancellation with controller identity verification
 * 3. Distinct `stale: true` response envelope that is never treated as a failure error
 * 4. Automatic retry on transient network failures with exponential backoff
 */

export class APIClient {
    static activeControllers = new Map();
    static requestSequences = new Map();

    static deriveContextualKey(endpoint, options = {}) {
        if (options.cancelKey) return options.cancelKey;
        const repo = options.repo || (options.body && typeof options.body === 'object' ? options.body.repo : null) || '';
        const normRepo = repo ? String(repo).replace(/\\/g, '/').toLowerCase() : 'global';

        if (endpoint.includes("/workspace/watcher")) {
            return `watcher:${normRepo}`;
        }
        if (endpoint.includes("/progress") || endpoint.includes("/status")) {
            return `progress:${normRepo}`;
        }
        if (endpoint.includes("/analyze")) {
            return `analysis:${normRepo}`;
        }
        if (endpoint.includes("/objective")) {
            return `objective:${normRepo}`;
        }
        if (endpoint.includes("/agent/context") || endpoint.includes("/generate")) {
            const provider = options.provider || (options.body && options.body.provider) || 'md';
            return `context:${normRepo}:${provider}`;
        }
        if (endpoint.includes("/safety") || endpoint.includes("/run-tests")) {
            return `safety:${normRepo}`;
        }
        if (endpoint.includes("/health")) {
            return 'health:global';
        }
        return `default:${endpoint}`;
    }

    static cancelInFlight(key = 'default') {
        if (this.activeControllers.has(key)) {
            try {
                this.activeControllers.get(key).abort();
            } catch (e) {
                // Ignore abort errors
            }
            this.activeControllers.delete(key);
        }
    }

    static async request(endpoint, options = {}) {
        const cancelKey = this.deriveContextualKey(endpoint, options);
        
        // Increment sequence counter for this specific contextual key
        const seq = (this.requestSequences.get(cancelKey) || 0) + 1;
        this.requestSequences.set(cancelKey, seq);

        if (options.cancelPrevious === true) {
            this.cancelInFlight(cancelKey);
        }

        const controller = new AbortController();
        this.activeControllers.set(cancelKey, controller);

        // Timeout budget: 90s for /analyze, 30s for other endpoints
        const timeoutMs = options.timeout || (endpoint.includes("/analyze") ? 90000 : 30000);

        let isTimedOut = false;
        const timer = setTimeout(() => {
            isTimedOut = true;
            controller.abort();
        }, timeoutMs);

        try {
            const fetchOptions = {
                method: options.method || 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    ...(options.headers || {})
                },
                signal: controller.signal
            };

            if (options.body) {
                fetchOptions.body = typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
            }

            const response = await fetch(endpoint, fetchOptions);
            clearTimeout(timer);

            // Guard controller cleanup by instance identity
            if (this.activeControllers.get(cancelKey) === controller) {
                this.activeControllers.delete(cancelKey);
            }

            // Sequence validation check: if a newer request for this context started, discard as stale
            const latestSeq = this.requestSequences.get(cancelKey) || 0;
            if (seq < latestSeq) {
                console.warn(`[Ultron API] Discarding stale response for key '${cancelKey}' (seq: ${seq} < latest: ${latestSeq})`);
                return {
                    stale: true,
                    success: false,
                    data: null,
                    error: null,
                    status: response.status
                };
            }

            let rawJson = null;
            try {
                rawJson = await response.json();
            } catch (jsonErr) {
                console.warn(`[Ultron API] Failed to parse JSON response from ${endpoint}:`, jsonErr);
                return {
                    stale: false,
                    success: false,
                    error: `Server error (${response.status}): Non-JSON response`,
                    status: response.status,
                    data: null
                };
            }

            // Envelope Unwrapper
            let success = response.ok;
            if (rawJson && typeof rawJson === 'object') {
                if ('success' in rawJson) {
                    success = Boolean(rawJson.success);
                } else if ('status' in rawJson) {
                    success = response.ok && rawJson.status !== 'error' && rawJson.status !== 'failed';
                }
            }

            const data = (rawJson && typeof rawJson === 'object' && rawJson.data !== undefined && rawJson.data !== null) ? rawJson.data : rawJson;
            const error = (rawJson && typeof rawJson === 'object' && rawJson.error)
                ? rawJson.error
                : (rawJson && typeof rawJson === 'object' && rawJson.message && !success ? rawJson.message : (!response.ok ? `HTTP ${response.status}` : null));

            return {
                stale: false,
                success,
                data,
                error,
                status: response.status
            };
        } catch (err) {
            clearTimeout(timer);

            if (this.activeControllers.get(cancelKey) === controller) {
                this.activeControllers.delete(cancelKey);
            }

            const latestSeq = this.requestSequences.get(cancelKey) || 0;
            if (seq < latestSeq) {
                return {
                    stale: true,
                    success: false,
                    data: null,
                    error: null
                };
            }

            const isAbort = err.name === 'AbortError';
            let errorMsg;
            if (isAbort && isTimedOut) {
                errorMsg = `Request timed out after ${Math.round(timeoutMs / 1000)}s`;
            } else if (isAbort) {
                errorMsg = 'Request cancelled by user';
            } else {
                errorMsg = err.message || 'Network connection failed';
            }

            return {
                stale: false,
                success: false,
                isCancel: isAbort && !isTimedOut,
                isTimeout: isTimedOut,
                error: errorMsg,
                data: null
            };
        }
    }

    static abortAll() {
        for (const controller of this.activeControllers.values()) {
            try {
                controller.abort();
            } catch (_) {
                // Ignore abort errors
            }
        }
        this.activeControllers.clear();
    }

    static buildUrl(endpoint, params = {}) {
        if (!params || typeof params !== 'object' || Object.keys(params).length === 0) {
            return endpoint;
        }
        const filteredParams = {};
        for (const [key, value] of Object.entries(params)) {
            if (value !== undefined && value !== null) {
                filteredParams[key] = value;
            }
        }
        const qs = new URLSearchParams(filteredParams).toString();
        if (!qs) return endpoint;
        return endpoint + (endpoint.includes('?') ? '&' : '?') + qs;
    }

    static _normalizeGetArgs(paramsOrOptions = {}, options = {}) {
        const optionKeys = new Set(['cancelKey', 'cancelPrevious', 'timeout', 'headers', 'signal']);
        const finalParams = {};
        const finalOptions = { ...options };

        if (paramsOrOptions && typeof paramsOrOptions === 'object') {
            for (const [k, v] of Object.entries(paramsOrOptions)) {
                if (optionKeys.has(k)) {
                    if (!(k in finalOptions)) finalOptions[k] = v;
                } else {
                    finalParams[k] = v;
                }
            }
        }
        return { finalParams, finalOptions };
    }

    static async requestWithRetry(endpoint, options = {}, retries = 2, delayMs = 1000) {
        let lastResult = null;
        const cancelKey = this.deriveContextualKey(endpoint, options);

        for (let i = 0; i <= retries; i++) {
            const reqOpts = i === 0 ? options : { ...options, cancelPrevious: false };
            lastResult = await this.request(endpoint, reqOpts);
            if (lastResult.stale || lastResult.success || (lastResult.isCancel && !lastResult.isTimeout)) {
                return lastResult;
            }
            if (lastResult.status && lastResult.status >= 400 && lastResult.status < 500) {
                return lastResult; // Do not retry client 4xx errors
            }
            if (i < retries) {
                console.warn(`[Ultron API] Request failed (${lastResult.error}), retrying ${i + 1}/${retries} after ${delayMs}ms...`);
                await new Promise(r => setTimeout(r, delayMs));
                delayMs *= 2;
            }
        }
        return lastResult;
    }

    static get(endpoint, paramsOrOptions = {}, options = {}) {
        const { finalParams, finalOptions } = this._normalizeGetArgs(paramsOrOptions, options);
        const url = this.buildUrl(endpoint, finalParams);
        return this.request(url, { ...finalOptions, method: 'GET', repo: finalParams?.repo || finalOptions?.repo });
    }

    static getWithRetry(endpoint, paramsOrOptions = {}, options = {}, retries = 2, delayMs = 1000) {
        const { finalParams, finalOptions } = this._normalizeGetArgs(paramsOrOptions, options);
        const url = this.buildUrl(endpoint, finalParams);
        return this.requestWithRetry(url, { ...finalOptions, method: 'GET', repo: finalParams?.repo || finalOptions?.repo }, retries, delayMs);
    }

    static post(endpoint, body = {}, options = {}) {
        return this.request(endpoint, { ...options, method: 'POST', body });
    }
}
