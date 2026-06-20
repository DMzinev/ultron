// cognitive/stateController.js
(function() {
    window.Cognitive = window.Cognitive || {};

    window.Cognitive.stateController = {
        updateSpacingState: function(topic, velocity, impasseWeight) {
            if (topic === 'fifo') topic = 'costing';
            if (!stats.topicStats || !stats.topicStats[topic]) return { tau: 5.0, deltaTau: 0.0 };
            
            const tStats = stats.topicStats[topic];
            
            // Adjust velocity based on impasse weight if failure occurred
            let v_adj = velocity;
            if (velocity < 0) {
                // Scaling negative velocity by impasse weight (conceptual error scales it fully, slip has zero scaling)
                v_adj = velocity * impasseWeight;
            }
            
            const cfg = window.Cognitive.Config || { TAU_BASE: 5.0, TAU_MIN: 3.0, TAU_MAX: 7.0, TARGET_VELOCITY: 0.5, GAIN: 2.0, DAMPING: 0.25 };
            const settings = stats.rsiSettings || { tauDelta: 0, tauBase: 5.0, targetVelocity: 0.5, gain: 2.0, damping: 0.25 };
            
            const error = v_adj - cfg.TARGET_VELOCITY;
            
            // Proportional feedback loop with damping (low-pass filter)
            settings.tauDelta = (1 - cfg.DAMPING) * settings.tauDelta + cfg.DAMPING * cfg.GAIN * error;
            
            let tau_new = cfg.TAU_BASE + settings.tauDelta;
            
            // Enforce bounds [3.0, 7.0]
            tau_new = Math.max(cfg.TAU_MIN, Math.min(cfg.TAU_MAX, tau_new));
            
            tStats.tau = Math.round(tau_new * 10) / 10;
            tStats.lastVelocity = velocity; // track base velocity
            
            // Log update to system event log
            if (!stats.systemLog) stats.systemLog = [];
            stats.systemLog.unshift({
                timestamp: Date.now(),
                topic: topic,
                event: "spacing_update",
                details: {
                    velocity: velocity,
                    v_adj: v_adj,
                    impasseWeight: impasseWeight,
                    error: error,
                    tauDelta: settings.tauDelta,
                    tau: tStats.tau
                }
            });
            // Cap at 50 logs
            if (stats.systemLog.length > 50) stats.systemLog.pop();
            
            return {
                tau: tStats.tau,
                deltaTau: settings.tauDelta
            };
        }
    };

})();
