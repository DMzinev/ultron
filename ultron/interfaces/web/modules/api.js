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

/* ---------------- Foundational DOM & API Helpers ---------------- */

export const $ = (id) => document.getElementById(id);

export function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => (
        { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
}

export function normPath(p) {
    return String(p || "").trim().replace(/\\/g, "/").replace(/^\.\//, "");
}

export function parseSeverity(s) {
    if (typeof s === "number" && Number.isFinite(s)) {
        return Math.max(1, Math.min(3, Math.round(s)));
    }
    if (!s) return 1;
    const str = String(s).toUpperCase().trim();
    if (str === "HIGH" || str === "CRITICAL" || str === "SEV 3" || str === "3") return 3;
    if (str === "MEDIUM" || str === "WARN" || str === "WARNING" || str === "SEV 2" || str === "2") return 2;
    return 1;
}

export async function api(path, body) {
    const opts = body === undefined
        ? { method: "GET" }
        : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
    const res = await fetch(path, opts);
    let data = null;
    try { data = await res.json(); } catch (_) { /* non-JSON body */ }
    if (!res.ok) {
        const msg = (data && (data.message || data.error)) || `Request failed (${res.status})`;
        throw new Error(msg);
    }
    return data || {};
}

export function show(view) {
    ["empty-state", "busy-state", "results", "error-state"].forEach((id) => {
        const el = $(id);
        if (el) el.hidden = id !== view;
    });
}

export function banner(text) {
    const b = $("banner");
    const bt = $("banner-text");
    if (!b || !bt) return;
    if (!text) { b.hidden = true; return; }
    bt.textContent = text;
    b.hidden = false;
}

export function showToast(msg) {
    const t = $("toast");
    if (!t) return;
    t.textContent = msg;
    t.hidden = false;
    setTimeout(() => { t.hidden = true; }, 2600);
}

export function splitPath(p) {
    const norm = String(p || "").replace(/\\/g, "/");
    const i = norm.lastIndexOf("/");
    return i === -1 ? { dir: "", base: norm } : { dir: norm.slice(0, i + 1), base: norm.slice(i + 1) };
}

