// controllers/sessionController.js
(function() {
    window.Controllers = window.Controllers || {};
    window.Controllers.sessionController = window.Controllers.sessionController || {};

    function runRSIDiagnosticScan() {
        const counts = { concepts: 0, costing: 0, cvp: 0, abc: 0, variance: 0 };
        let totalMistakes = 0;
        if (stats.mistakesLog) {
            stats.mistakesLog.forEach(m => {
                if (counts[m.category] !== undefined) {
                    counts[m.category]++;
                    totalMistakes++;
                }
            });
        }

        let weakest = 'None';
        let maxMistakes = 0;
        for (const cat in counts) {
            if (counts[cat] > maxMistakes) {
                maxMistakes = counts[cat];
                weakest = cat;
            }
        }
        rsiState.weakestCategory = weakest;

        const accuracy = stats.totalAttempts > 0 ? ((stats.totalAttempts - totalMistakes) / stats.totalAttempts) : 1.0;
        if (stats.xp > 1500 && accuracy > 0.80) {
            rsiState.evolutionTier = 3;
        } else if (stats.xp > 600) {
            rsiState.evolutionTier = 2;
        } else {
            rsiState.evolutionTier = 1;
        }

        rsiState.activeMutations = [];
        rsiState.rangeMultiplier = 1.0 + (rsiState.evolutionTier - 1) * 0.25;

        if (rsiState.evolutionTier >= 2) {
            rsiState.activeMutations.push(`Numeric Range Expansion (+${Math.round((rsiState.rangeMultiplier - 1)*100)}% parameter spread)`);
        }
        if (weakest !== 'None') {
            rsiState.activeMutations.push(`Weakness Targeting: Over-weighting templates for "${getCategoryDisplayName(weakest)}"`);
        }
        if (stats.xp > 1000) {
            rsiState.activeMutations.push("Rounding Trap injection (forcing exact decimal precision)");
        }

        if (window.UI && window.UI.updateRSIUI) {
            window.UI.updateRSIUI();
        } else if (window.updateRSIUI) {
            window.updateRSIUI();
        }
        
        const summary = document.getElementById('rsi-diagnostic-summary');
        if (summary) {
            summary.innerHTML = `
                <div style="background-color: rgba(99, 102, 241, 0.1); border-left: 4px solid var(--accent-primary); padding: 8px 12px; border-radius: 4px; font-size: 13px; color: white;">
                    <strong>Diagnostic Scan Complete:</strong> Generator adjusted to target <strong>${weakest === 'None' ? 'All (Balanced)' : getCategoryDisplayName(weakest)}</strong>.
                </div>
            `;
        }
    }

    window.Controllers.sessionController.runRSIDiagnosticScan = runRSIDiagnosticScan;
    window.runRSIDiagnosticScan = runRSIDiagnosticScan;

    function updateCognitiveState(topic, isCorrect, attemptNum, errorVector) {
        if (topic === 'fifo') topic = 'costing';
        if (!stats.topicStats || !stats.topicStats[topic]) return;

        let ev = errorVector;
        if (!isCorrect && !ev) {
            ev = stats.beliefProfile[topic] || { slip: 0.333, procedural: 0.333, conceptual: 0.334 };
        }

        const event = {
            concept: topic,
            correct: isCorrect,
            attempt: attemptNum || 1,
            errorVector: ev,
            confidence: (window.currentPracProblem && window.currentPracProblem.confidence) || 0.7
        };

        // Transition through Concept State Machine
        window.ConceptStateMachine.transition(event);

        // Update highestDifficulty
        if (isCorrect) {
            let diffNum = 1;
            const prob = window.currentPracProblem || (typeof currentPracProblem !== 'undefined' ? currentPracProblem : null);
            if (prob && prob.difficulty) {
                const d = prob.difficulty;
                diffNum = d === 'easy' ? 1 : (d === 'intermediate' || d === 'medium' || d === 'hard' ? 2 : 3);
                if (d === 'hard') diffNum = 3;
            }
            stats.topicStats[topic].highestDifficulty = Math.max(stats.topicStats[topic].highestDifficulty || 1, diffNum);
        }
    }

    window.Controllers.sessionController.updateCognitiveState = updateCognitiveState;
    window.updateCognitiveState = updateCognitiveState;

    function updateTopicPerformance(topic, isCorrect) {
        updateCognitiveState(topic, isCorrect, isCorrect ? 1 : 2, null);
    }

    window.Controllers.sessionController.updateTopicPerformance = updateTopicPerformance;
    window.updateTopicPerformance = updateTopicPerformance;

})();