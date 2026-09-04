/**
 * Ultron Web SPA — Asynchronous IndexedDB Storage Engine
 * High-Scale Snapshot & Architecture Persistence Adapter (v0.2.0)
 */

const DB_NAME = "ultron_db";
const DB_VERSION = 1;
const STORE_NAME = "snapshots";

export class UltronStorage {
    static _db = null;
    static _fallbackStore = new Map();

    static async initDB() {
        if (this._db) return this._db;
        if (typeof indexedDB === "undefined") {
            console.warn("[UltronStorage] IndexedDB not available, using in-memory store.");
            return null;
        }

        return new Promise((resolve) => {
            try {
                const req = indexedDB.open(DB_NAME, DB_VERSION);
                req.onupgradeneeded = (e) => {
                    const db = e.target.result;
                    if (!db.objectStoreNames.contains(STORE_NAME)) {
                        db.createObjectStore(STORE_NAME, { keyPath: "repoPath" });
                    }
                };
                req.onsuccess = (e) => {
                    this._db = e.target.result;
                    resolve(this._db);
                };
                req.onerror = (e) => {
                    console.warn("[UltronStorage] IndexedDB open error, falling back:", e);
                    resolve(null);
                };
            } catch (err) {
                console.warn("[UltronStorage] IndexedDB initialization failed:", err);
                resolve(null);
            }
        });
    }

    static async saveSnapshot(repoPath, data) {
        const normKey = String(repoPath || ".").replace(/\\/g, '/');
        const envelope = {
            repoPath: normKey,
            schemaVersion: "v0.2.0",
            timestamp: Date.now(),
            data: data
        };

        const db = await this.initDB();
        if (!db) {
            this._fallbackStore.set(normKey, envelope);
            try {
                // Also mirror lightweight metadata in localStorage for backup
                localStorage.setItem("ultron_cached_repo", normKey);
            } catch (_) {}
            return;
        }

        return new Promise((resolve) => {
            try {
                const tx = db.transaction(STORE_NAME, "readwrite");
                const store = tx.objectStore(STORE_NAME);
                store.put(envelope);
                tx.oncomplete = () => resolve();
                tx.onerror = () => {
                    this._fallbackStore.set(normKey, envelope);
                    resolve();
                };
            } catch (err) {
                this._fallbackStore.set(normKey, envelope);
                resolve();
            }
        });
    }

    static async getLatestSnapshot(repoPath) {
        const normKey = String(repoPath || ".").replace(/\\/g, '/');
        const db = await this.initDB();
        if (!db) {
            const mem = this._fallbackStore.get(normKey);
            return mem ? mem.data : null;
        }

        return new Promise((resolve) => {
            try {
                const tx = db.transaction(STORE_NAME, "readonly");
                const store = tx.objectStore(STORE_NAME);
                const req = store.get(normKey);
                req.onsuccess = (e) => {
                    const record = e.target.result;
                    resolve(record ? record.data : null);
                };
                req.onerror = () => {
                    const mem = this._fallbackStore.get(normKey);
                    resolve(mem ? mem.data : null);
                };
            } catch (err) {
                const mem = this._fallbackStore.get(normKey);
                resolve(mem ? mem.data : null);
            }
        });
    }

    static async clearSnapshots(repoPath) {
        const normKey = String(repoPath || ".").replace(/\\/g, '/');
        this._fallbackStore.delete(normKey);
        const db = await this.initDB();
        if (!db) return;

        return new Promise((resolve) => {
            try {
                const tx = db.transaction(STORE_NAME, "readwrite");
                const store = tx.objectStore(STORE_NAME);
                store.delete(normKey);
                tx.oncomplete = () => resolve();
                tx.onerror = () => resolve();
            } catch (_) {
                resolve();
            }
        });
    }
}
