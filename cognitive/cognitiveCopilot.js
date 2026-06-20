// cognitive/cognitiveCopilot.js
(function() {
    window.Cognitive = window.Cognitive || {};
    window.Cognitive.Copilot = window.Cognitive.Copilot || {};

    // Centroids for KNN classification of user learning state
    const CENTROIDS = [
        {
            label: "Arithmetic & Precision Slips",
            key: "arithmetic",
            vector: { entropy: 0.2, impasse: 0.1, accuracy: 0.7, mismatch: 0.8, decay: 0.2 },
            coaching: "Your conceptual understanding is solid, but you are experiencing calculation errors and overconfidence. Focus on double-checking intermediate math values and respecting rounding rules.",
            keywords: ["round", "decimal", "precision", "arithmetic", "calculator", "equals"]
        },
        {
            label: "Procedural & Formula Gaps",
            key: "procedural",
            vector: { entropy: 0.8, impasse: 0.5, accuracy: 0.5, mismatch: 0.3, decay: 0.4 },
            coaching: "You are mixing up different cost accounting steps or formulas (e.g. WA vs FIFO equivalent units). Re-study the structured sequence of rates and allocations.",
            keywords: ["equivalent", "allocation", "overhead", "rate", "fifo", "weighted", "average"]
        },
        {
            label: "Conceptual Misconceptions",
            key: "conceptual",
            vector: { entropy: 1.4, impasse: 0.9, accuracy: 0.3, mismatch: 0.6, decay: 0.5 },
            coaching: "There are fundamental concept barriers (e.g. flexible budgets volume variance, shelf space allocation priorities). Review slide definitions and Socratic walkthroughs.",
            keywords: ["constraint", "contribution", "margin", "fixed", "variable", "flexible", "budget"]
        },
        {
            label: "Memory Recall & Retention Decay",
            key: "decay",
            vector: { entropy: 0.5, impasse: 0.3, accuracy: 0.6, mismatch: 0.2, decay: 0.8 },
            coaching: "Your spacing intervals are collapsing due to long intervals between review sessions. Schedule active retrieval checkpoints to reactivate neural pathways.",
            keywords: ["spaced", "readiness", "decay", "retained", "retrieval", "days", "due"]
        }
    ];

    function calculateFeatures(activeTopic) {
        // 1. Calculate entropy of active topic belief
        let entropy = 0.0;
        let impasse = 0.5;
        if (window.Cognitive.beliefEngine && stats.beliefProfile && stats.beliefProfile[activeTopic]) {
            const belief = stats.beliefProfile[activeTopic];
            entropy = window.Cognitive.beliefEngine.calculateEntropy(belief);
            impasse = window.Cognitive.beliefEngine.calculateImpasseWeight(belief);
        }

        // 2. Calculate overall accuracy
        const total = stats.totalAttempts || 0;
        const correct = stats.correctAttempts || 0;
        const accuracy = total > 0 ? (correct / total) : 1.0;

        // 3. Calculate calibration mismatch
        let mismatch = 0.15;
        if (stats.calibrationStats) {
            const c = stats.calibrationStats;
            const totalCal = c.highConfidenceCorrect + c.highConfidenceIncorrect + c.lowConfidenceCorrect + c.lowConfidenceIncorrect;
            if (totalCal > 0) {
                mismatch = (c.highConfidenceIncorrect + c.lowConfidenceCorrect) / totalCal;
            }
        }

        // 4. Calculate average decay level across all topics
        let totalDecay = 0;
        const topics = ['concepts', 'costing', 'cvp', 'abc', 'variance'];
        topics.forEach(t => {
            const tStats = stats.topicStats[t];
            if (tStats && tStats.attempts > 0) {
                const dt = Date.now() - tStats.lastAttemptTime;
                const halfLife = tStats.tau || 5.0;
                totalDecay += Math.exp(-dt / (halfLife * 24 * 3600 * 1000));
            }
        });
        const avgRetention = topics.length > 0 ? (totalDecay / topics.length) : 1.0;
        const avgDecay = 1.0 - avgRetention;

        return { entropy, impasse, accuracy, mismatch, decay: avgDecay };
    }

    function classifyState(features) {
        let nearest = null;
        let minDistance = Infinity;

        // Euclidean Distance calculation
        CENTROIDS.forEach(c => {
            let sumSq = 0;
            // Normalize weights based on scale
            sumSq += Math.pow((features.entropy - c.vector.entropy) / 1.58, 2);
            sumSq += Math.pow(features.impasse - c.vector.impasse, 2);
            sumSq += Math.pow(features.accuracy - c.vector.accuracy, 2);
            sumSq += Math.pow(features.mismatch - c.vector.mismatch, 2);
            sumSq += Math.pow(features.decay - c.vector.decay, 2);
            const dist = Math.sqrt(sumSq);

            if (dist < minDistance) {
                minDistance = dist;
                nearest = c;
            }
        });

        return {
            barrier: nearest.label,
            key: nearest.key,
            coaching: nearest.coaching,
            distance: minDistance,
            keywords: nearest.keywords
        };
    }

    // TF-IDF inspired score to match keyword queries to PDF text
    function getRecommendedPages(keywords, weakestTopic, maxResults = 3) {
        if (!window.Storage.knowledgeBase || !window.Storage.knowledgeBase.rawPages) return [];
        
        const topicsMap = {
            "concepts": [1],
            "costing": [2],
            "cvp": [3],
            "abc": [4],
            "variance": [5]
        };
        const activeSessions = topicsMap[weakestTopic] || [1, 2, 3, 4, 5];

        let results = [];
        
        window.Storage.knowledgeBase.rawPages.forEach(page => {
            // Priority boost if matching the user's weakest session topic
            let score = activeSessions.includes(page.session) ? 5.0 : 0.0;
            
            const textLower = page.text.toLowerCase();
            
            // Keyword frequency matching
            keywords.forEach(keyword => {
                const regex = new RegExp("\\b" + keyword.toLowerCase() + "\\b", "g");
                const matches = textLower.match(regex);
                if (matches) {
                    score += matches.length * 2.0; // Term frequency weight
                }
            });

            // Specific formulas boosts
            if (weakestTopic === 'fifo' || weakestTopic === 'costing') {
                if (textLower.includes("equivalent") || textLower.includes("units")) score += 3.0;
            }
            if (weakestTopic === 'cvp') {
                if (textLower.includes("breakeven") || textLower.includes("contribution")) score += 3.0;
            }
            if (weakestTopic === 'variance') {
                if (textLower.includes("flexible") || textLower.includes("variance")) score += 3.0;
            }

            if (score > 0) {
                results.push({
                    session: page.session,
                    sessionTitle: page.sessionTitle,
                    page: page.page,
                    snippet: page.text.slice(0, 180) + "...",
                    score: score
                });
            }
        });

        // Sort by highest matching score
        results.sort((a, b) => b.score - a.score);
        return results.slice(0, maxResults);
    }

    window.Cognitive.Copilot.runDiagnostic = function(activeTopic, weakestTopic) {
        const features = calculateFeatures(activeTopic);
        const classification = classifyState(features);
        const recommendations = getRecommendedPages(classification.keywords, weakestTopic);
        
        return {
            features: features,
            classification: classification,
            recommendations: recommendations
        };
    };

})();
