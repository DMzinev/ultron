// cognitive/conceptStateMachine.js
(function() {
    window.ConceptStateMachine = window.ConceptStateMachine || {};

    function getPrereqs(c) {
        if (c === 'concepts') return [];
        if (c === 'costing') return ['concepts'];
        if (c === 'cvp') return ['concepts'];
        if (c === 'abc') return ['costing', 'cvp'];
        if (c === 'variance') return ['abc'];
        return [];
    }

    function getLeadsTo(c) {
        if (c === 'concepts') return ['costing', 'cvp'];
        if (c === 'costing') return ['abc'];
        if (c === 'cvp') return ['abc'];
        if (c === 'abc') return ['variance'];
        if (c === 'variance') return [];
        return [];
    }



    function mirrorToLegacy(conceptId) {
        if (!window.stats || !window.stats.csmState || !window.stats.csmState[conceptId]) return;
        const node = window.stats.csmState[conceptId];
        
        // 1. Mastery
        window.stats['mastery' + window.capitalizeFirst(conceptId)] = Math.round(node.state.mastery * 100);
        
        // 2. Peaks
        if (!window.stats.masteryPeaks) window.stats.masteryPeaks = {};
        window.stats.masteryPeaks[conceptId] = Math.max(window.stats.masteryPeaks[conceptId] || 0, Math.round(node.state.mastery * 100));
        
        // 3. Belief Profile
        if (!window.stats.beliefProfile) window.stats.beliefProfile = {};
        window.stats.beliefProfile[conceptId] = {
            slip: node.state.belief.slip,
            procedural: node.state.belief.procedural,
            conceptual: node.state.belief.conceptual
        };
        
        // 4. Topic Stats
        if (!window.stats.topicStats) window.stats.topicStats = {};
        if (!window.stats.topicStats[conceptId]) {
            window.stats.topicStats[conceptId] = {
                attempts: 0,
                correct: 0,
                highestDifficulty: 1,
                lastAttemptTime: Date.now(),
                tau: 5.0,
                lastVelocity: 0.5
            };
        }
        window.stats.topicStats[conceptId].attempts = node.history.attempts;
        window.stats.topicStats[conceptId].correct = node.history.correct;
        window.stats.topicStats[conceptId].tau = node.state.tau;
        window.stats.topicStats[conceptId].lastVelocity = node.state.velocity;
        window.stats.topicStats[conceptId].lastAttemptTime = node.history.lastUpdated;
    }

    window.ConceptStateMachine = {
        get concepts() {
            if (!window.stats) return {};
            if (!window.stats.csmState) {
                window.stats.csmState = {};
            }
            const topics = ['concepts', 'costing', 'cvp', 'abc', 'variance'];
            topics.forEach(t => {
                if (!window.stats.csmState[t]) {
                    window.stats.csmState[t] = {
                        id: t,
                        state: {
                            mastery: (window.stats['mastery' + window.capitalizeFirst(t)] !== undefined) ? window.stats['mastery' + window.capitalizeFirst(t)] / 100.0 : 0.0,
                            memoryStrength: 0.5,
                            tau: (window.stats.topicStats && window.stats.topicStats[t] && window.stats.topicStats[t].tau !== undefined) ? window.stats.topicStats[t].tau : 5.0,
                            velocity: (window.stats.topicStats && window.stats.topicStats[t] && window.stats.topicStats[t].lastVelocity !== undefined) ? window.stats.topicStats[t].lastVelocity : 0.0,
                            entropy: 1.58,
                            belief: (window.stats.beliefProfile && window.stats.beliefProfile[t]) ? {
                                slip: window.stats.beliefProfile[t].slip || 0.333,
                                procedural: window.stats.beliefProfile[t].procedural || 0.333,
                                conceptual: window.stats.beliefProfile[t].conceptual || 0.334
                            } : { slip: 0.333, procedural: 0.333, conceptual: 0.334 }
                        },
                        history: {
                            attempts: (window.stats.topicStats && window.stats.topicStats[t] && window.stats.topicStats[t].attempts !== undefined) ? window.stats.topicStats[t].attempts : 0,
                            correct: (window.stats.topicStats && window.stats.topicStats[t] && window.stats.topicStats[t].correct !== undefined) ? window.stats.topicStats[t].correct : 0,
                            lastSignal: 0.0,
                            lastUpdated: (window.stats.topicStats && window.stats.topicStats[t] && window.stats.topicStats[t].lastAttemptTime !== undefined) ? window.stats.topicStats[t].lastAttemptTime : Date.now()
                        },
                        graph: {
                            prerequisites: getPrereqs(t),
                            leadsTo: getLeadsTo(t)
                        }
                    };
                } else {
                    // Ensure mandatory fields exist inside loaded csmState nodes
                    const node = window.stats.csmState[t];
                    node.id = t;
                    if (!node.state) node.state = {};
                    if (node.state.mastery === undefined) node.state.mastery = 0.0;
                    if (node.state.memoryStrength === undefined) node.state.memoryStrength = 0.5;
                    if (node.state.tau === undefined) node.state.tau = 5.0;
                    if (node.state.velocity === undefined) node.state.velocity = 0.0;
                    if (node.state.entropy === undefined) node.state.entropy = 1.58;
                    if (!node.state.belief) node.state.belief = { slip: 0.333, procedural: 0.333, conceptual: 0.334 };
                    if (!node.history) node.history = {};
                    if (node.history.attempts === undefined) node.history.attempts = 0;
                    if (node.history.correct === undefined) node.history.correct = 0;
                    if (node.history.lastSignal === undefined) node.history.lastSignal = 0.0;
                    if (node.history.lastUpdated === undefined) node.history.lastUpdated = Date.now();
                    if (!node.graph) node.graph = {};
                    node.graph.prerequisites = getPrereqs(t);
                    node.graph.leadsTo = getLeadsTo(t);
                }
            });
            return window.stats.csmState;
        },

        decay: function(node) {
            const now = Date.now();
            const dt = now - node.history.lastUpdated;
            if (dt > 0) {
                const halfLife = node.state.tau || 5.0;
                const decayFactor = Math.exp(-dt / (halfLife * 24 * 3600 * 1000));
                node.state.memoryStrength = Math.max(0.1, node.state.memoryStrength * decayFactor);
            }
        },

        transition: function(event) {
            const conceptId = event.concept;
            const node = this.concepts[conceptId];
            if (!node) return;

            // Apply decay first
            this.decay(node);

            // 1. Compute learning signal v
            let v;
            if (event.correct && event.attempt === 1) v = 1.0;
            else if (event.correct && event.attempt === 2) v = 0.5;
            else v = -1.0;

            node.history.attempts++;
            if (event.correct) {
                node.history.correct++;
            }
            node.history.lastSignal = v;
            node.history.lastUpdated = Date.now();

            // 2. Entropy
            const b = node.state.belief;
            const entropy = -(
                b.slip * Math.log2(b.slip + 1e-9) +
                b.procedural * Math.log2(b.procedural + 1e-9) +
                b.conceptual * Math.log2(b.conceptual + 1e-9)
            );
            node.state.entropy = entropy;

            // 3. Impasse Weight
            const W = 0.0 * b.slip + 0.5 * b.procedural + 1.0 * b.conceptual;

            // 4. Velocity Update
            const adjSignal = v < 0 ? v * (1 - W) : v;
            node.state.velocity = 0.75 * node.state.velocity + 0.25 * adjSignal;

            // 5. Tau Control (adaptive spacing)
            const target = 0.5;
            const error = node.state.velocity - target;
            node.state.tau = Math.max(3.0, Math.min(7.0, 5.0 + 2.0 * error));

            // 6. Belief Update (Bayesian posterior smoothing, beta = 0.3)
            if (event.errorVector) {
                const beta = 0.3;
                const obs = event.errorVector;
                for (let k of ["slip", "procedural", "conceptual"]) {
                    b[k] = (1 - beta) * b[k] + beta * (obs[k] || 0);
                }

                // Normalize
                const sum = b.slip + b.procedural + b.conceptual;
                if (sum > 0) {
                    b.slip /= sum;
                    b.procedural /= sum;
                    b.conceptual /= sum;
                } else {
                    b.slip = 0.333;
                    b.procedural = 0.333;
                    b.conceptual = 0.334;
                }
            }

            // 7. Mastery Update
            node.state.mastery = 0.6 * node.state.mastery + 0.4 * Math.max(0, node.state.velocity);
            node.state.mastery = Math.max(0.0, Math.min(1.0, node.state.mastery));

            // 8. Graph Propagation
            const delta = event.correct ? +0.02 : -0.05;
            this.propagate(node, delta);

            // Mirror to legacy stats
            mirrorToLegacy(conceptId);
            node.graph.prerequisites.forEach(p => mirrorToLegacy(p));
            node.graph.leadsTo.forEach(l => mirrorToLegacy(l));
        },

        propagate: function(conceptNode, delta) {
            // Prerequisites
            for (let dep of conceptNode.graph.prerequisites) {
                const depNode = this.concepts[dep];
                if (depNode) {
                    depNode.state.mastery = Math.max(0.0, Math.min(1.0, depNode.state.mastery + delta * 0.5));
                }
            }

            // LeadsTo
            for (let lead of conceptNode.graph.leadsTo) {
                const leadNode = this.concepts[lead];
                if (leadNode) {
                    this.decay(leadNode);
                    leadNode.state.memoryStrength = Math.max(0.1, Math.min(1.0, leadNode.state.memoryStrength + delta));
                }
            }
        },

        getState: function(conceptId) {
            return this.concepts[conceptId];
        },

        getDashboard: function() {
            const summary = {};
            const topics = ['concepts', 'costing', 'cvp', 'abc', 'variance'];
            topics.forEach(t => {
                const c = this.concepts[t];
                summary[t] = {
                    mastery: c.state.mastery,
                    memoryStrength: c.state.memoryStrength,
                    tau: c.state.tau,
                    velocity: c.state.velocity,
                    entropy: c.state.entropy,
                    belief: c.state.belief,
                    attempts: c.history.attempts,
                    correct: c.history.correct
                };
            });
            return summary;
        },

        getGlobalState: function() {
            return this;
        }
    };

    // Ensure we trigger initialization mirror on load
    const topics = ['concepts', 'costing', 'cvp', 'abc', 'variance'];
    topics.forEach(t => {
        const c = window.ConceptStateMachine.concepts; // force creation
        mirrorToLegacy(t);
    });

})();
