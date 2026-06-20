// storage/statsStore.js

// Global persistent state (survives page reloads)
var stats = {
    schemaVersion: 4,
    xp: 0,
    streak: 0,
    totalAttempts: 0,
    correctAttempts: 0,
    masteryConcepts: 0,
    masteryCosting: 0,
    masteryCvp: 0,
    masteryAbc: 0,
    masteryVariance: 0,
    spacedRepQueue: [],
    calibrationStats: {
        highConfidenceCorrect: 0,
        highConfidenceIncorrect: 0,
        lowConfidenceCorrect: 0,
        lowConfidenceIncorrect: 0
    },
    reflectionStats: {
        reflectionAttempts: 0,
        reflectionCorrect: 0
    },
    consecutiveStats: {
        concepts: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true },
        costing: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true },
        cvp: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true },
        abc: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true },
        variance: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true }
    },
    topicStats: {
        concepts: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 },
        costing: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 },
        cvp: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 },
        abc: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 },
        variance: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 }
    },
    masteryPeaks: {
        concepts: 0, costing: 0, cvp: 0, abc: 0, variance: 0
    },
    rsiSettings: {
        tauDelta: 0, tauBase: 5.0, targetVelocity: 0.5, gain: 2.0, damping: 0.25, promotionStreak: 3
    },
    beliefProfile: {
        concepts: { slip: 0.333, procedural: 0.333, conceptual: 0.334 },
        costing: { slip: 0.333, procedural: 0.333, conceptual: 0.334 },
        cvp: { slip: 0.333, procedural: 0.333, conceptual: 0.334 },
        abc: { slip: 0.333, procedural: 0.333, conceptual: 0.334 },
        variance: { slip: 0.333, procedural: 0.333, conceptual: 0.334 }
    },
    mistakesLog: [],
    systemLog: [], // Capped event log for debugging state traces
    answeredQuizzes: {} // Slide quizzes completed (prevents XP farming)
};

// Global RSI in-memory configuration
var rsiState = {
    evolutionTier: 1,
    activeMutations: [],
    weakestCategory: 'None',
    rangeMultiplier: 1.0
};

(function() {
    window.Storage = window.Storage || {};
    window.Storage.stats = stats;
    window.Storage.rsiState = rsiState;

    function migrateStats(raw) {
        let loaded = null;
        if (raw) {
            try {
                loaded = JSON.parse(raw);
            } catch (e) {
                console.error("Failed to parse local storage stats:", e);
            }
        }
        
        if (!loaded) {
            return stats;
        }

        let version = loaded.schemaVersion || 0;

        // Sequential versioned upgrades
        if (version === 0) {
            loaded.schemaVersion = 1;
            version = 1;
        }
        if (version === 1) {
            if (!loaded.calibrationStats) {
                loaded.calibrationStats = { highConfidenceCorrect: 0, highConfidenceIncorrect: 0, lowConfidenceCorrect: 0, lowConfidenceIncorrect: 0 };
            }
            if (!loaded.reflectionStats) {
                loaded.reflectionStats = { reflectionAttempts: 0, reflectionCorrect: 0 };
            }
            if (!loaded.consecutiveStats) {
                loaded.consecutiveStats = {
                    concepts: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true },
                    costing: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true },
                    cvp: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true },
                    abc: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true },
                    variance: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true }
                };
            }
            if (!loaded.topicStats) {
                loaded.topicStats = {
                    concepts: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 },
                    costing: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 },
                    cvp: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 },
                    abc: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 },
                    variance: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 }
                };
            }
            if (!loaded.masteryPeaks) {
                loaded.masteryPeaks = { concepts: 0, costing: 0, cvp: 0, abc: 0, variance: 0 };
            }
            loaded.schemaVersion = 2;
            version = 2;
        }
        if (version === 2) {
            if (!loaded.rsiSettings) {
                loaded.rsiSettings = { tauDelta: 0, tauBase: 5.0, targetVelocity: 0.5, gain: 2.0, damping: 0.25, promotionStreak: 3 };
            }
            if (!loaded.beliefProfile) {
                loaded.beliefProfile = {};
            }
            const topics = ['concepts', 'costing', 'cvp', 'abc', 'variance'];
            topics.forEach(t => {
                if (!loaded.beliefProfile[t]) {
                    loaded.beliefProfile[t] = { slip: 0.333, procedural: 0.333, conceptual: 0.334 };
                }
                if (loaded.topicStats && loaded.topicStats[t]) {
                    if (loaded.topicStats[t].tau === undefined) loaded.topicStats[t].tau = 5.0;
                    if (loaded.topicStats[t].lastVelocity === undefined) loaded.topicStats[t].lastVelocity = 0.5;
                }
            });
            loaded.schemaVersion = 3;
            version = 3;
        }
        if (version === 3) {
            if (!loaded.systemLog) loaded.systemLog = [];
            if (!loaded.mistakesLog) loaded.mistakesLog = [];
            if (!loaded.answeredQuizzes) loaded.answeredQuizzes = {};
            loaded.schemaVersion = 4;
            version = 4;
        }

        // Structural validation & deep repair (Layer 1 Test C recovery)
        const defaults = {
            schemaVersion: 4,
            xp: 0,
            streak: 0,
            totalAttempts: 0,
            correctAttempts: 0,
            masteryConcepts: 0,
            masteryCosting: 0,
            masteryCvp: 0,
            masteryAbc: 0,
            masteryVariance: 0,
            spacedRepQueue: [],
            calibrationStats: {
                highConfidenceCorrect: 0,
                highConfidenceIncorrect: 0,
                lowConfidenceCorrect: 0,
                lowConfidenceIncorrect: 0
            },
            reflectionStats: {
                reflectionAttempts: 0,
                reflectionCorrect: 0
            },
            consecutiveStats: {
                concepts: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true },
                costing: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true },
                cvp: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true },
                abc: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true },
                variance: { correct: 0, incorrect: 0, activeDifficulty: 'easy', hintsEnabled: true }
            },
            topicStats: {
                concepts: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 },
                costing: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 },
                cvp: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 },
                abc: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 },
                variance: { attempts: 0, correct: 0, highestDifficulty: 1, lastAttemptTime: Date.now(), tau: 5.0, lastVelocity: 0.5 }
            },
            masteryPeaks: {
                concepts: 0, costing: 0, cvp: 0, abc: 0, variance: 0
            },
            rsiSettings: {
                tauDelta: 0, tauBase: 5.0, targetVelocity: 0.5, gain: 2.0, damping: 0.25, promotionStreak: 3
            },
            beliefProfile: {
                concepts: { slip: 0.333, procedural: 0.333, conceptual: 0.334 },
                costing: { slip: 0.333, procedural: 0.333, conceptual: 0.334 },
                cvp: { slip: 0.333, procedural: 0.333, conceptual: 0.334 },
                abc: { slip: 0.333, procedural: 0.333, conceptual: 0.334 },
                variance: { slip: 0.333, procedural: 0.333, conceptual: 0.334 }
            },
            mistakesLog: [],
            systemLog: [],
            answeredQuizzes: {}
        };

        // Deep repair missing or corrupt keys
        for (const key in defaults) {
            if (loaded[key] === undefined || loaded[key] === null) {
                loaded[key] = JSON.parse(JSON.stringify(defaults[key]));
            } else if (typeof defaults[key] === 'object' && !Array.isArray(defaults[key])) {
                // Check sub-properties for objects
                for (const subKey in defaults[key]) {
                    if (loaded[key][subKey] === undefined || loaded[key][subKey] === null) {
                        loaded[key][subKey] = JSON.parse(JSON.stringify(defaults[key][subKey]));
                    } else if (typeof defaults[key][subKey] === 'object') {
                        // Check sub-sub-properties
                        for (const ssubKey in defaults[key][subKey]) {
                            if (loaded[key][subKey][ssubKey] === undefined || loaded[key][subKey][ssubKey] === null) {
                                loaded[key][subKey][ssubKey] = defaults[key][subKey][ssubKey];
                            }
                        }
                    }
                }
            }
        }

        return loaded;
    }
    window.Storage.migrateStats = migrateStats;

    const defaultStatsStr = JSON.stringify(stats);

    function loadStats() {
        let saved = null;
        try {
            saved = localStorage.getItem('innsbruck_gamification_stats_v3');
            if (saved) {
                JSON.parse(saved);
            }
        } catch (e) {
            console.error("LocalStorage corruption detected inside loadStats. Rebuilding defaults...", e);
            localStorage.removeItem('innsbruck_gamification_stats_v3');
            stats = JSON.parse(defaultStatsStr);
            localStorage.setItem('innsbruck_gamification_stats_v3', defaultStatsStr);
            window.Storage.stats = stats;
            return stats;
        }
        stats = migrateStats(saved);
        window.Storage.stats = stats;
        return stats;
    }
    window.Storage.loadStats = loadStats;
    window.loadStats = loadStats;

    function saveStats() {
        localStorage.setItem('innsbruck_gamification_stats_v3', JSON.stringify(stats));
    }
    window.Storage.saveStats = saveStats;
    window.saveStats = saveStats;

})();