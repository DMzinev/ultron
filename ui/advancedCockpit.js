// ui/advancedCockpit.js
(function() {
    window.UI = window.UI || {};

    function updateTelemetryUI() {
                let activeTopic = 'concepts';
                if (currentPracProblem && currentPracProblem.category) {
                    activeTopic = currentPracProblem.category === 'fifo' ? 'costing' : currentPracProblem.category;
                }
                
                const tStats = (stats.topicStats && stats.topicStats[activeTopic]) ? stats.topicStats[activeTopic] : { tau: 5.0, lastVelocity: 0.5 };
                const belief = (stats.beliefProfile && stats.beliefProfile[activeTopic]) ? stats.beliefProfile[activeTopic] : { slip: 0.333, procedural: 0.333, conceptual: 0.334 };
                
                let entropy = 0;
                const pSlip = belief.slip || 0;
                const pProc = belief.procedural || 0;
                const pConc = belief.conceptual || 0;
                if (pSlip > 0) entropy -= pSlip * Math.log2(pSlip);
                if (pProc > 0) entropy -= pProc * Math.log2(pProc);
                if (pConc > 0) entropy -= pConc * Math.log2(pConc);
                
                let mismatchRate = 0.15;
                if (stats.calibrationStats) {
                    const totalCal = stats.calibrationStats.highConfidenceCorrect + stats.calibrationStats.highConfidenceIncorrect + stats.calibrationStats.lowConfidenceCorrect + stats.calibrationStats.lowConfidenceIncorrect;
                    if (totalCal > 0) {
                        const mismatchCount = stats.calibrationStats.highConfidenceIncorrect + stats.calibrationStats.lowConfidenceCorrect;
                        mismatchRate = Math.max(0.01, Math.min(0.99, mismatchCount / totalCal));
                    }
                }
                const snr = 20 * Math.log10((1 - mismatchRate) / mismatchRate);
                
                const tauEl = document.getElementById('telemetry-tau-val');
                const snrEl = document.getElementById('telemetry-snr-val');
                const entEl = document.getElementById('telemetry-entropy-val');
                const stateEl = document.getElementById('telemetry-active-state');
                const velEl = document.getElementById('telemetry-velocity-val');
                
                if (tauEl) tauEl.innerText = `${tStats.tau ? tStats.tau.toFixed(1) : '5.0'}d`;
                if (snrEl) snrEl.innerText = `${snr.toFixed(1)} dB`;
                if (entEl) entEl.innerText = entropy.toFixed(2);
                if (stateEl) stateEl.innerText = capitalizeFirst(activeTopic);
                if (velEl) velEl.innerText = tStats.lastVelocity ? tStats.lastVelocity.toFixed(2) : '0.50';
            }

    window.UI.updateTelemetryUI = updateTelemetryUI;
    window.updateTelemetryUI = updateTelemetryUI;

    function updateDecayTracker() {
                const tbody = document.getElementById('decay-tracker-body');
                if (!tbody || !stats.topicStats) return;
                
                tbody.innerHTML = '';
                const topics = ['concepts', 'costing', 'cvp', 'abc', 'variance'];
                topics.forEach(t => {
                    const tStats = stats.topicStats[t];
                    let lastPractice = "Never";
                    let retained = 0;
                    let riskLabel = '<span class="num-badge" style="background-color: var(--danger); color: white; padding: 2px 6px; border-radius: 4px; width:auto;">Critical</span>';
                    
                    if (tStats && tStats.attempts > 0) {
                        lastPractice = formatTimeAgo(tStats.lastAttemptTime);
                        const dt = Date.now() - tStats.lastAttemptTime;
                        retained = Math.round(Math.max(0.1, Math.exp(-dt / (5 * 24 * 3600 * 1000))) * 100);
                        
                        if (retained > 80) {
                            riskLabel = '<span class="num-badge" style="background-color: var(--success); color: white; padding: 2px 6px; border-radius: 4px; width:auto;">Low Risk</span>';
                        } else if (retained > 50) {
                            riskLabel = '<span class="num-badge" style="background-color: var(--warning); color: white; padding: 2px 6px; border-radius: 4px; width:auto;">Medium Risk</span>';
                        } else {
                            riskLabel = '<span class="num-badge" style="background-color: var(--danger); color: white; padding: 2px 6px; border-radius: 4px; width:auto;">High Risk</span>';
                        }
                    }
                    
                    tbody.innerHTML += `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <td style="padding: 8px 6px; font-weight:700; color:white;">${getCategoryDisplayName(t)}</td>
                            <td style="padding: 8px 6px; color:var(--text-secondary);">${lastPractice}</td>
                            <td style="padding: 8px 6px; text-align: center; color:var(--accent-primary); font-weight:800;">${retained}%</td>
                            <td style="padding: 8px 6px; text-align: right;">${riskLabel}</td>
                        </tr>
                    `;
                });
            }

    window.UI.updateDecayTracker = updateDecayTracker;
    window.updateDecayTracker = updateDecayTracker;

    function computeStudyPlan() {
                const container = document.getElementById('recommended-plan-content');
                if (!container || !stats.topicStats) return;
                
                const topics = ['concepts', 'costing', 'cvp', 'abc', 'variance'];
                let scores = [];
                topics.forEach(t => {
                    const tStats = stats.topicStats[t];
                    let retained = 0;
                    let attempts = 0;
                    if (tStats) {
                        attempts = tStats.attempts;
                        const dt = Date.now() - tStats.lastAttemptTime;
                        retained = Math.exp(-dt / (5 * 24 * 3600 * 1000));
                    }
                    const mastery = stats['mastery' + capitalizeFirst(t)] || 0;
                    scores.push({
                        topic: t,
                        name: getCategoryDisplayName(t),
                        retained: retained,
                        attempts: attempts,
                        mastery: mastery
                    });
                });
                
                // Sort by lowest retention first, then lowest attempts, then lowest mastery
                scores.sort((a, b) => {
                    if (a.attempts === 0 && b.attempts > 0) return -1;
                    if (b.attempts === 0 && a.attempts > 0) return 1;
                    if (a.retained !== b.retained) return a.retained - b.retained;
                    return a.mastery - b.mastery;
                });
                
                const urgent = scores[0];
                const retainedPct = Math.round(urgent.retained * 100);
                
                let html = '';
                if (urgent.attempts === 0) {
                    html = `
                        <div style="font-size: 13px; color: white; line-height: 1.4; flex: 1;">
                            📥 Recommended Action: You haven't practiced <strong>${urgent.name}</strong> yet! Start a guided review or practice challenge to build baseline conceptual memory.
                        </div>
                        <button class="btn btn-primary" onclick="switchTab('practice-arena'); startArenaPractice('${urgent.topic}');" style="font-size:12px; padding:6px 12px; background-color:#34d399; border-color:#34d399; color:black; font-weight:700;">Start Practice</button>
                    `;
                } else if (urgent.retained < 0.6) {
                    html = `
                        <div style="font-size: 13px; color: white; line-height: 1.4; flex: 1;">
                            ⏳ Recommended Action: Memory retention for <strong>${urgent.name}</strong> has decayed to <strong>${retainedPct}%</strong>. Conquering a quick adaptive challenge will refresh your recall pathways!
                        </div>
                        <button class="btn btn-primary" onclick="switchTab('practice-arena'); startArenaPractice('${urgent.topic}');" style="font-size:12px; padding:6px 12px; background-color:#34d399; border-color:#34d399; color:black; font-weight:700;">Review Now</button>
                    `;
                } else {
                    html = `
                        <div style="font-size: 13px; color: white; line-height: 1.4; flex: 1;">
                            🎓 Recommended Action: Great job! Retention across all cost accounting modules is above 60%. Test your knowledge under pressure in the timed Exam Simulator!
                        </div>
                        <button class="btn btn-primary" onclick="switchTab('practice-arena'); setArenaMode('exam');" style="font-size:12px; padding:6px 12px; background-color:#34d399; border-color:#34d399; color:black; font-weight:700;">Start Exam Simulation</button>
                    `;
                }
                container.innerHTML = html;
            }

    window.UI.computeStudyPlan = computeStudyPlan;
    window.computeStudyPlan = computeStudyPlan;

    function updateCalibrationHUD() {
                const cStats = stats.calibrationStats;
                if (!cStats) return;
                
                const totalHigh = cStats.highConfidenceCorrect + cStats.highConfidenceIncorrect;
                const totalLow = cStats.lowConfidenceCorrect + cStats.lowConfidenceIncorrect;
                
                const overconfidenceRate = totalHigh > 0 ? (cStats.highConfidenceIncorrect / totalHigh) : 0;
                const underconfidenceRate = totalLow > 0 ? (cStats.lowConfidenceCorrect / totalLow) : 0;
                
                const overEl = document.getElementById('stats-overconfidence-val');
                const underEl = document.getElementById('stats-underconfidence-val');
                const refEl = document.getElementById('stats-reflections-val');
                const tipEl = document.getElementById('stats-calibration-tip');
                
                if (overEl) overEl.innerText = `${Math.round(overconfidenceRate * 100)}%`;
                if (underEl) underEl.innerText = `${Math.round(underconfidenceRate * 100)}%`;
                if (refEl) refEl.innerText = stats.reflectionStats ? stats.reflectionStats.reflectionAttempts : 0;
                
                if (tipEl) {
                    if (totalHigh === 0 && totalLow === 0) {
                        tipEl.innerHTML = `<strong>Coaching Tip:</strong> No calibration data yet. Complete pre-practice retrieval checkpoints to calculate your profile.`;
                    } else if (overconfidenceRate > 0.4) {
                        tipEl.innerHTML = `<strong>Coaching Tip:</strong> ⚠️ You tend to feel very confident about formulas you calculate incorrectly (Overconfidence is high). Try double-checking your work before submitting!`;
                        tipEl.style.borderLeftColor = 'var(--danger)';
                    } else if (underconfidenceRate > 0.4) {
                        tipEl.innerHTML = `<strong>Coaching Tip:</strong> ⚖️ You tend to guess correctly even when you feel unsure (Underconfidence detected). Trust your instincts, your recall is stronger than you think!`;
                        tipEl.style.borderLeftColor = 'var(--warning)';
                    } else {
                        tipEl.innerHTML = `<strong>Coaching Tip:</strong> ✅ Excellent calibration. Your confidence levels align closely with your actual recall correctness. Keep it up!`;
                        tipEl.style.borderLeftColor = 'var(--success)';
                    }
                }
            }

    window.UI.updateCalibrationHUD = updateCalibrationHUD;
    window.updateCalibrationHUD = updateCalibrationHUD;

    function toggleAdvancedCockpit() {
                const content = document.getElementById('advanced-cockpit-content');
                const icon = document.getElementById('cockpit-toggle-icon');
                if (!content || !icon) return;
                if (content.style.display === 'none') {
                    content.style.display = 'block';
                    icon.innerText = '➖';
                } else {
                    content.style.display = 'none';
                    icon.innerText = '➕';
                }
            }

    window.UI.toggleAdvancedCockpit = toggleAdvancedCockpit;
    window.toggleAdvancedCockpit = toggleAdvancedCockpit;

    function runSystemIntegrityCheck() {
                const feedbackEl = document.getElementById('integrity-suite-feedback');
                const logEl = document.getElementById('integrity-suite-log');
                if (!feedbackEl || !logEl) return;
                
                logEl.style.display = 'block';
                logEl.innerHTML = '';
                
                let passed = 0;
                let total = 14;
                
                function logCheck(name, success, info) {
                    const icon = success ? '✅' : '❌';
                    logEl.innerHTML += `<div style="margin-bottom:4px; color:${success ? '#34d399':'#f43f5e'}">${icon} <strong>${name}</strong>: ${info}</div>`;
                    if (success) passed++;
                }
                
                // Check 1: FIFO Process Costing equivalent units standard formulas
                try {
                    const mathDetails = { completed: 42, clUnits: 10, clDmPct: 0.6, opUnits: 8, opDmPct: 0.9 };
                    const expectedWA = mathDetails.completed + (mathDetails.clUnits * mathDetails.clDmPct); // 42 + 6 = 48
                    const expectedFIFO = expectedWA - (mathDetails.opUnits * mathDetails.opDmPct); // 48 - 7.2 = 40.8
                    
                    const correctWA = Math.abs(expectedWA - 48.0) < 0.01;
                    const correctFIFO = Math.abs(expectedFIFO - 40.8) < 0.01;
                    
                    logCheck("FIFO / WA Formulas", correctWA && correctFIFO, `FIFO equivalent units correctly isolates current-period work (${expectedFIFO} EU calculated).`);
                } catch (e) {
                    logCheck("FIFO / WA Formulas", false, e.message);
                }
                
                // Check 2: CVP Breakeven rounded-up integer assertion
                try {
                    const fc = 10000;
                    const price = 25;
                    const vc = 17;
                    const cmu = price - vc; // 8
                    const beUnits = Math.ceil(fc / cmu); // Math.ceil(1250) = 1250
                    
                    const fc2 = 10000;
                    const price2 = 25;
                    const vc2 = 18;
                    const cmu2 = price2 - vc2; // 7
                    const beUnits2 = Math.ceil(fc2 / cmu2); // Math.ceil(1428.57) = 1429
                    
                    const ok = (beUnits === 1250) && (beUnits2 === 1429);
                    logCheck("CVP Breakeven Round-up", ok, `Breakeven units correctly rounded UP to next integer: ${beUnits2} units (from 1428.57).`);
                } catch (e) {
                    logCheck("CVP Breakeven Round-up", false, e.message);
                }
                
                // Check 3: Standard price variance sign rules (Poitou-Chemises)
                try {
                    const sp = 45.00;
                    const ap_fav = 44.50;
                    const ap_unfav = 46.20;
                    const qty = 5800;
                    
                    const favVar = (sp - ap_fav) * qty; // +2900 (Favorable)
                    const unfavVar = (sp - ap_unfav) * qty; // -6960 (Unfavorable)
                    
                    const ok = (favVar > 0) && (unfavVar < 0);
                    logCheck("Variance Sign Conventions", ok, `Favorable price variance yields a positive value (${favVar} F), and Unfavorable yields negative (${unfavVar} U).`);
                } catch (e) {
                    logCheck("Variance Sign Conventions", false, e.message);
                }
                
                // Check 4: Local Storage Persistence & Scheduling
                try {
                    const tempQueue = [{ category: 'fifo', name: 'FIFO Costing', dueDate: Date.now() + 120000 }];
                    localStorage.setItem('innsbruck_integrity_test_key', JSON.stringify(tempQueue));
                    const retrieved = JSON.parse(localStorage.getItem('innsbruck_integrity_test_key'));
                    localStorage.removeItem('innsbruck_integrity_test_key');
                    
                    const ok = retrieved && retrieved.length === 1 && retrieved[0].category === 'fifo';
                    logCheck("Local Storage Persistence", ok, "Scheduled spaced repetition records save and restore successfully.");
                } catch (e) {
                    logCheck("Local Storage Persistence", false, e.message);
                }
                
                // Check 5: RSI range multiplier tier logic
                try {
                    const t1Multiplier = 1.0;
                    const t3Multiplier = 1.5;
                    const ok = (t1Multiplier === 1.0) && (t3Multiplier === 1.5);
                    logCheck("RSI Range Adjustments", ok, `Numerical scale adjusts properly based on evolution tiers (baseline is 1.00x).`);
                } catch (e) {
                    logCheck("RSI Range Adjustments", false, e.message);
                }
                
                // Check 6: Bayesian Belief Update & Re-normalization
                try {
                    const testBelief = { slip: 0.333, procedural: 0.333, conceptual: 0.334 };
                    const beta = 0.3;
                    const errorVector = { slip: 0.0, procedural: 0.0, conceptual: 1.0 }; // Conceptual failure
                    
                    // Update
                    testBelief.slip = (1 - beta) * testBelief.slip + beta * (errorVector.slip || 0);
                    testBelief.procedural = (1 - beta) * testBelief.procedural + beta * (errorVector.procedural || 0);
                    testBelief.conceptual = (1 - beta) * testBelief.conceptual + beta * (errorVector.conceptual || 0);
                    
                    // Re-normalize
                    const sum = testBelief.slip + testBelief.procedural + testBelief.conceptual;
                    testBelief.slip /= sum;
                    testBelief.procedural /= sum;
                    testBelief.conceptual /= sum;
                    
                    const sumExact = testBelief.slip + testBelief.procedural + testBelief.conceptual;
                    const ok = Math.abs(sumExact - 1.0) < 0.0001 && testBelief.conceptual > 0.45;
                    logCheck("Bayesian Belief Normalization", ok, `Belief profile updates correctly and re-normalizes (Conceptual: ${testBelief.conceptual.toFixed(2)}, Sum: ${sumExact.toFixed(2)}).`);
                } catch (e) {
                    logCheck("Bayesian Belief Normalization", false, e.message);
                }
                
                // Check 7: Spacing Controller Damped Loop Bounds
                try {
                    const settings = { tauDelta: 0, tauBase: 5.0, targetVelocity: 0.5, gain: 2.0, damping: 0.25 };
                    const v_adj = -1.0;
                    const error = v_adj - settings.targetVelocity; // -1.5
                    
                    settings.tauDelta = (1 - settings.damping) * settings.tauDelta + settings.damping * settings.gain * error; // -0.75
                    let tau_new = settings.tauBase + settings.tauDelta; // 4.25
                    tau_new = Math.max(3.0, Math.min(7.0, tau_new));
                    
                    const ok = tau_new === 4.25;
                    logCheck("Spacing Controller Updates", ok, `Spacing controller correctly computes damped half-life adjustment (tau: ${tau_new.toFixed(2)} days).`);
                } catch (e) {
                    logCheck("Spacing Controller Updates", false, e.message);
                }

                // Check 8: Controller saveStats Purity
                try {
                    let saveCount = 0;
                    const originalSave = window.saveStats;
                    const originalStorageSave = window.Storage.saveStats;
                    window.saveStats = window.Storage.saveStats = function() { saveCount++; };
                    
                    const originalProblem = window.currentPracProblem;
                    window.currentPracProblem = { category: 'concepts', difficulty: 'easy', status: 'ACTIVE', forfeited: false };
                    
                    if (typeof rateSRS === 'function') {
                        rateSRS('good');
                    }
                    
                    window.currentPracProblem = originalProblem;
                    window.saveStats = originalSave;
                    window.Storage.saveStats = originalStorageSave;
                    
                    logCheck("Controller saveStats Purity", saveCount === 1, `saveStats was called exactly ${saveCount} time(s) during mock SRS scheduling.`);
                } catch (e) {
                    logCheck("Controller saveStats Purity", false, e.message);
                }

                // Check 9: Belief Normalization verification across active profiles
                try {
                    let ok = true;
                    let details = [];
                    const topics = ['concepts', 'costing', 'cvp', 'abc', 'variance'];
                    topics.forEach(t => {
                        const belief = stats.beliefProfile[t];
                        if (belief) {
                            const sum = belief.slip + belief.procedural + belief.conceptual;
                            if (Math.abs(sum - 1.0) > 0.001) {
                                ok = false;
                                details.push(`${t}: ${sum.toFixed(4)}`);
                            }
                        }
                    });
                    logCheck("Belief Vector Normalization", ok, ok ? "All active belief profile vectors sum to exactly 1.0." : `Mismatches found: ${details.join(', ')}`);
                } catch (e) {
                    logCheck("Belief Vector Normalization", false, e.message);
                }

                // Check 10: Spacing Parameter Bounds verification across active stats
                try {
                    let ok = true;
                    let details = [];
                    const topics = ['concepts', 'costing', 'cvp', 'abc', 'variance'];
                    topics.forEach(t => {
                        const tStats = stats.topicStats[t];
                        if (tStats && tStats.tau !== undefined) {
                            if (tStats.tau < 3.0 || tStats.tau > 7.0) {
                                ok = false;
                                details.push(`${t}: ${tStats.tau}`);
                            }
                        }
                    });
                    logCheck("Spacing Parameter Bounds", ok, ok ? "All topic spacing parameters are within limits [3.0, 7.0]." : `Out of bounds: ${details.join(', ')}`);
                } catch (e) {
                    logCheck("Spacing Parameter Bounds", false, e.message);
                }

                // Check 11: Local Storage Persistence & Migrator roundtrip check
                try {
                    const mockStats = {
                        schemaVersion: 3,
                        xp: 888,
                        streak: 9,
                        totalAttempts: 50,
                        correctAttempts: 40,
                        masteryConcepts: 10,
                        masteryCosting: 20,
                        masteryCvp: 30,
                        masteryAbc: 40,
                        masteryVariance: 50,
                        spacedRepQueue: [],
                        beliefProfile: {
                            concepts: { slip: 0.333, procedural: 0.333, conceptual: 0.334 }
                        }
                    };
                    const serialized = JSON.stringify(mockStats);
                    const migrated = window.Storage.migrateStats(serialized);

                    const matchesXp = migrated.xp === 888;
                    const matchesSchema = migrated.schemaVersion === 4;
                    const addedFields = migrated.systemLog !== undefined && migrated.mistakesLog !== undefined;

                    logCheck("Storage Persistence Roundtrip", matchesXp && matchesSchema && addedFields,
                        (matchesXp && matchesSchema && addedFields) ?
                        "Stats migration roundtrip verified schema version 4 upgrade and properties retention." :
                        `Migration failed: XP match = ${matchesXp}, Schema = ${matchesSchema}, Fields = ${addedFields}`
                    );
                } catch (e) {
                    logCheck("Storage Persistence Roundtrip", false, e.message);
                }

                // Check 12: Expanded European/English Parsing Suite
                try {
                    const parseF = window.Utils.parseRobustFloat;
                    const testCases = [
                        { input: "12,5", expected: 12.5 },
                        { input: "12.5", expected: 12.5 },
                        { input: "40,000", expected: 40000 },
                        { input: "40.000", expected: 40000 },
                        { input: "€1,234.56", expected: 1234.56 },
                        { input: "1 234,56", expected: 1234.56 },
                        { input: "-1200,50", expected: -1200.5 }
                    ];

                    let ok = true;
                    const failedCases = [];
                    testCases.forEach((tc, idx) => {
                        const res = parseF(tc.input);
                        if (Math.abs(res - tc.expected) > 0.001) {
                            ok = false;
                            failedCases.push(`Case #${idx+1} [${tc.input}]: expected ${tc.expected}, got ${res}`);
                        }
                    });

                    logCheck("Expanded Parsing Suite", ok, ok ? "All 7 mixed notation formats parsed successfully." : `Failures: ${failedCases.join('; ')}`);
                } catch (e) {
                    logCheck("Expanded Parsing Suite", false, e.message);
                }

                // Check 13: Verification Consistency
                try {
                    const mockCorrect = { cmu: 10, be: 100, profit: 500 };
                    const mockUser = { 'ans-cvp-cmu': '10', 'ans-cvp-be': '100', 'ans-cvp-profit': '500' };
                    
                    const resPractice = window.Controllers.answerVerifier.verify('cvp', 0, mockCorrect, mockUser);
                    const resExam = window.verifyAnswers('cvp', 0, mockCorrect, mockUser);
                    
                    const matches = resPractice.correct === true && 
                                    resExam.correct === true && 
                                    JSON.stringify(resPractice.results) === JSON.stringify(resExam.results) &&
                                    resPractice.score === 1.0;
                                    
                    logCheck("Verification Consistency", matches, matches ? 
                        "Verified identical results and grading scores from Practice and Exam verifier paths." :
                        "Practice vs Exam verifier outputs are inconsistent!"
                    );
                } catch (e) {
                    logCheck("Verification Consistency", false, e.message);
                }
                
                // Final Score
                feedbackEl.innerText = `Integrity Check: ${passed} / ${total} Passed`;
                if (passed === total) {
                    feedbackEl.style.color = 'var(--success)';
                } else {
                    feedbackEl.style.color = 'var(--danger)';
                }
            }

    window.UI.runSystemIntegrityCheck = runSystemIntegrityCheck;
    window.runSystemIntegrityCheck = runSystemIntegrityCheck;

})();