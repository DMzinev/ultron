// cognitive/conceptPolicyController.js
(function() {
    window.Cognitive = window.Cognitive || {};

    let lastDecisionType = null;
    let cooldownCounter = 0; // cooldown of 2 checks to avoid oscillation

    window.Cognitive.PolicyController = {
        computeGlobalState: function(csm) {
            if (!csm || !csm.concepts) return [];
            const concepts = Object.entries(csm.concepts);

            const vector = concepts.map(([id, c]) => {
                const v = c.state.velocity || 0.0;
                const e = c.state.entropy || 0.0;
                const m = c.state.mastery || 0.0;
                return {
                    id: id,
                    velocity: v,
                    entropy: e,
                    mastery: m,
                    pressure: (1.0 - m) * e - v
                };
            });

            return vector;
        },

        selectTargets: function(vector) {
            if (vector.length === 0) return { weakest: null, mostStable: null };
            const sorted = [...vector].sort((a, b) => b.pressure - a.pressure);
            return {
                weakest: sorted[0],
                mostStable: sorted[sorted.length - 1]
            };
        },

        decide: function(csm, active) {
            if (!csm) return { type: "NORMAL", target: active };
            const vector = this.computeGlobalState(csm);
            if (vector.length === 0) return { type: "NORMAL", target: active };

            // GUARD: Don't intervene until the student has at least 3 total practice attempts.
            // Before that, the CSM state (entropy, velocity) is not meaningful enough to drive interventions.
            const totalAttempts = csm.concepts ? Object.values(csm.concepts).reduce((sum, c) => {
                return sum + ((c.history && c.history.attempts) ? c.history.attempts : 0);
            }, 0) : 0;
            if (totalAttempts < 3) return { type: "NORMAL", target: active };

            const { weakest } = this.selectTargets(vector);

            const systemVelocity = vector.reduce((s, c) => s + c.velocity, 0) / vector.length;

            let decision = { type: "NORMAL", target: active };

            // CASE 1 — collapse zone (local failure, requires at least 2 attempts on the failing concept)
            const weakestAttempts = (weakest && csm.concepts[weakest.id] && csm.concepts[weakest.id].history) ? csm.concepts[weakest.id].history.attempts : 0;
            if (weakest && weakest.pressure > 0.8 && weakestAttempts >= 2) {
                decision = {
                    type: "SHOW_SLIDES",
                    target: weakest.id,
                    reason: "local_instability"
                };
            }
            // CASE 2 — low learning momentum (requires at least 2 attempts on weakest)
            else if (systemVelocity < -0.3 && weakest && weakestAttempts >= 2) {
                decision = {
                    type: "WORKED_EXAMPLE",
                    target: weakest.id
                };
            }
            // CASE 3 — high mastery stability
            else if (vector.every(v => v.mastery > 0.8)) {
                decision = {
                    type: "HARD_PROBLEM",
                    target: active
                };
            }

            // Apply hysteresis cooldown logic (prevents thrashing between interventions)
            if (cooldownCounter > 0 && lastDecisionType && lastDecisionType !== decision.type) {
                // If it is a critical collapse (pressure > 1.2), override cooldown!
                const isCriticalCollapse = (weakest && weakest.pressure > 1.2 && decision.type === "SHOW_SLIDES");
                if (!isCriticalCollapse) {
                    cooldownCounter--;
                    return { type: lastDecisionType, target: lastDecisionType === "SHOW_SLIDES" || lastDecisionType === "WORKED_EXAMPLE" ? weakest.id : active };
                }
            }

            // Reset cooldown on new decision type
            if (lastDecisionType !== decision.type) {
                lastDecisionType = decision.type;
                cooldownCounter = 2; // lock this decision type for 2 iterations
            }

            return decision;
        },

        resetCooldown: function() {
            lastDecisionType = null;
            cooldownCounter = 0;
        }
    };
})();
