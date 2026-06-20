// cognitive/masteryEngine.js
(function() {
    window.Cognitive = window.Cognitive || {};

    window.Cognitive.masteryEngine = {
        updateDecayedMastery: function() {
            if (!stats.topicStats) return;
            const topics = ['concepts', 'costing', 'cvp', 'abc', 'variance'];
            topics.forEach(t => {
                const tStats = stats.topicStats[t];
                if (!tStats || tStats.attempts === 0) return;
                
                const Accuracy = tStats.correct / tStats.attempts;
                const diffNum = tStats.highestDifficulty || 1;
                const Difficulty = 0.6 + (diffNum * 0.2); // 1->0.8, 2->1.0, 3->1.2
                
                const dt = Date.now() - tStats.lastAttemptTime;
                const halfLife = tStats.tau || 5.0;
                const recency = Math.max(0.1, Math.exp(-dt / (halfLife * 24 * 3600 * 1000))); // Dynamic decay half-life parameter
                
                const repetition = Math.min(1.0, 0.2 + 0.8 * Math.log2(tStats.attempts + 1) / Math.log2(10));
                
                const calculatedMastery = Math.round(Accuracy * Difficulty * recency * repetition * 100);
                const mVal = Math.min(100, Math.max(0, calculatedMastery));
                stats['mastery' + capitalizeFirst(t)] = mVal;
                
                if (!stats.masteryPeaks) stats.masteryPeaks = { concepts: 0, costing: 0, cvp: 0, abc: 0, variance: 0 };
                stats.masteryPeaks[t] = Math.max(stats.masteryPeaks[t] || 0, mVal);
            });
        },

        getMilestone: function(peak) {
            if (peak >= 90) {
                return { level: "Master", color: "#10b981", bg: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)" };
            } else if (peak >= 70) {
                return { level: "Proficient", color: "#3b82f6", bg: "rgba(59, 130, 246, 0.1)", border: "1px solid rgba(59, 130, 246, 0.3)" };
            } else if (peak >= 40) {
                return { level: "Competent", color: "#f59e0b", bg: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)" };
            } else {
                return { level: "Novice", color: "#9ca3af", bg: "rgba(156, 163, 175, 0.1)", border: "1px solid rgba(156, 163, 175, 0.3)" };
            }
        }
    };

    // Keep global alias for compatibility
    window.updateDecayedMastery = window.Cognitive.masteryEngine.updateDecayedMastery;

})();