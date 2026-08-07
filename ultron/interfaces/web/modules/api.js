/**
 * Ultron Web SPA — Robust API Client
 * Campaign 9 & 13: Error Boundaries, Timeout & Response Envelope Unwrapper
 */

export class APIClient {
    static async request(endpoint, options = {}) {
        const controller = new AbortController();
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

            // Campaign 9: Robust Envelope Unwrapper
            // Handles both standardized envelope { success: true, data: { ... } } and raw legacy object payloads
            const isEnvelope = rawJson && typeof rawJson === 'object' && 'success' in rawJson;
            const success = isEnvelope ? Boolean(rawJson.success) : response.ok;
            const data = (isEnvelope && rawJson.data !== undefined && rawJson.data !== null) ? rawJson.data : rawJson;
            const error = (isEnvelope && rawJson.error) ? rawJson.error : (!response.ok ? (rawJson?.error || `HTTP ${response.status}`) : null);

            return {
                success,
                data,
                error,
                status: response.status
            };
        } catch (err) {
            clearTimeout(timer);
            const isAbort = err.name === 'AbortError';
            const errorMsg = isAbort ? 'Request timed out after 10s' : (err.message || 'Network connection failed');
            console.error(`[Ultron API Error] ${endpoint}:`, errorMsg);
            return {
                success: false,
                data: null,
                error: errorMsg,
                status: 0
            };
        }
    }

    static async get(endpoint, params = {}) {
        const url = new URL(endpoint, window.location.origin);
        Object.keys(params).forEach(key => {
            if (params[key] !== undefined && params[key] !== null) {
                url.searchParams.append(key, params[key]);
            }
        });
        return this.request(url.toString(), { method: 'GET' });
    }

    static async post(endpoint, body = {}) {
        return this.request(endpoint, { method: 'POST', body });
    }
}
