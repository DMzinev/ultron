/**
 * Ultron Web SPA — Robust API Client
 * Campaign 9 & 13: Error Boundaries, Timeout, Request Cancellation & Envelope Unwrapper
 */

export class APIClient {
    static activeControllers = new Map();

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
        const cancelKey = options.cancelKey || 'default';
        if (options.cancelPrevious !== false) {
            this.cancelInFlight(cancelKey);
        }

        const controller = new AbortController();
        this.activeControllers.set(cancelKey, controller);

        const timeoutMs = options.timeout || 10000;
        const timer = setTimeout(() => controller.abort(), timeoutMs);

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
            this.activeControllers.delete(cancelKey);

            let rawJson = null;
            try {
                rawJson = await response.json();
            } catch (jsonErr) {
                console.warn(`[Ultron API] Failed to parse JSON response from ${endpoint}:`, jsonErr);
                return {
                    success: false,
                    error: `Server error (${response.status}): Non-JSON response`,
                    status: response.status
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
                success,
                data,
                error,
                status: response.status
            };
        } catch (err) {
            clearTimeout(timer);
            this.activeControllers.delete(cancelKey);

            const isAbort = err.name === 'AbortError';
            const errorMsg = isAbort ? 'Request cancelled or timed out after 10s' : (err.message || 'Network connection failed');
            if (!isAbort) console.error(`[Ultron API Error] ${endpoint}:`, errorMsg);
            return {
                success: false,
                data: null,
                error: errorMsg,
                status: 0
            };
        }
    }

    static async get(endpoint, params = {}, options = {}) {
        const url = new URL(endpoint, window.location.origin);
        Object.keys(params).forEach(key => {
            if (params[key] !== undefined && params[key] !== null) {
                url.searchParams.append(key, params[key]);
            }
        });
        return this.request(url.toString(), { method: 'GET', ...options });
    }

    static async post(endpoint, body = {}, options = {}) {
        return this.request(endpoint, { method: 'POST', body, ...options });
    }
}
