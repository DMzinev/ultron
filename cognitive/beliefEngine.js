// cognitive/beliefEngine.js
(function() {
    window.Cognitive = window.Cognitive || {};
    
    // Cognitive configuration constants
    window.Cognitive.Config = {
        BELIEF_BETA: 0.3,
        TAU_BASE: 5.0,
        TAU_MIN: 3.0,
        TAU_MAX: 7.0,
        TARGET_VELOCITY: 0.5,
        GAIN: 2.0,
        DAMPING: 0.25
    };

    window.Cognitive.beliefEngine = {
        updateBelief: function(topic, errorVector) {
            if (topic === 'fifo') topic = 'costing';
            if (!stats.beliefProfile) stats.beliefProfile = {};
            const belief = stats.beliefProfile[topic] || { slip: 0.333, procedural: 0.333, conceptual: 0.334 };
            
            if (errorVector) {
                const beta = window.Cognitive.Config.BELIEF_BETA;
                // Exponential belief update
                belief.slip = (1 - beta) * belief.slip + beta * (errorVector.slip || 0);
                belief.procedural = (1 - beta) * belief.procedural + beta * (errorVector.procedural || 0);
                belief.conceptual = (1 - beta) * belief.conceptual + beta * (errorVector.conceptual || 0);
                
                // Re-normalize to sum to exactly 1.0
                const sum = belief.slip + belief.procedural + belief.conceptual;
                if (sum > 0) {
                    belief.slip /= sum;
                    belief.procedural /= sum;
                    belief.conceptual /= sum;
                }
                stats.beliefProfile[topic] = belief;

                // Log update to system event log
                if (!stats.systemLog) stats.systemLog = [];
                stats.systemLog.unshift({
                    timestamp: Date.now(),
                    topic: topic,
                    event: "belief_update",
                    details: {
                        slip: Math.round(belief.slip * 100) / 100,
                        procedural: Math.round(belief.procedural * 100) / 100,
                        conceptual: Math.round(belief.conceptual * 100) / 100
                    }
                });
                if (stats.systemLog.length > 50) stats.systemLog.pop();
            }
            return belief;
        },

        calculateEntropy: function(belief) {
            if (!belief) return 0.0;
            let entropy = 0.0;
            const p_slip = Math.max(0.0001, belief.slip || 0);
            const p_proc = Math.max(0.0001, belief.procedural || 0);
            const p_concept = Math.max(0.0001, belief.conceptual || 0);
            
            // Shannon Entropy = -sum(p * log2(p))
            entropy -= p_slip * Math.log2(p_slip);
            entropy -= p_proc * Math.log2(p_proc);
            entropy -= p_concept * Math.log2(p_concept);
            return Math.round(entropy * 100) / 100;
        },

        calculateImpasseWeight: function(belief) {
            if (!belief) return 0.5;
            // Impasse weight: conceptual confusion has highest weight (1.0), procedural (0.5), slip (0.0)
            const w = 0.0 * (belief.slip || 0) + 0.5 * (belief.procedural || 0) + 1.0 * (belief.conceptual || 0);
            return Math.round(w * 100) / 100;
        }
    };

})();
