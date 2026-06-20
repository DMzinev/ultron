// ui/appUI.js
(function() {
    window.UI = window.UI || {};
    window.UI.appUI = {};

    let currentArenaMode = 'learn';

    const s1Items = [
        { id: 'c-q1', name: "A. Annual retainer paid to film distributor" },
        { id: 'c-q2', name: "B. Electricity costs of store (single bill)" },
        { id: 'c-q3', name: "C. Costs of films purchased for sale" },
        { id: 'c-q4', name: "D. Subscription to Video-Novo magazine" },
        { id: 'c-q5', name: "E. Leasing of budgeting computer software" },
        { id: 'c-q6', name: "F. Cost of popcorn provided free to customers" },
        { id: 'c-q7', name: "G. Earthquake insurance policy for store" },
        { id: 'c-q8', name: "H. Freight-in costs of films purchased" }
    ];
    let s1UserAnswers = {};

    const parseFloat = window.Utils.parseRobustFloat || window.parseRobustFloat;

    function updateRSIUI() {
                const tierEl = document.getElementById('rsi-evolution-tier-val');
                const multiplierEl = document.getElementById('rsi-range-multiplier-val');
                const targetEl = document.getElementById('rsi-target-focus-val');
                const listEl = document.getElementById('rsi-active-mutations-list');
    
                if (tierEl) tierEl.innerText = rsiState.evolutionTier === 3 ? "Tier 3: Evolving Master" : (rsiState.evolutionTier === 2 ? "Tier 2: Adaptive Core" : "Tier 1: Standard Baseline");
                if (multiplierEl) multiplierEl.innerText = `${rsiState.rangeMultiplier.toFixed(2)}x`;
                if (targetEl) targetEl.innerText = rsiState.weakestCategory === 'None' ? 'All (Balanced)' : getCategoryDisplayName(rsiState.weakestCategory);
    
                if (listEl) {
                    if (rsiState.activeMutations.length === 0) {
                        listEl.innerHTML = `<li style="color: var(--text-muted); font-size:12px;">No mutations currently active. Complete practices to initialize adaptive settings.</li>`;
                    } else {
                        listEl.innerHTML = rsiState.activeMutations.map(m => `
                            <li style="color: #60a5fa; font-size: 12px; display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                                <span style="display:inline-block; width: 6px; height: 6px; border-radius:50%; background-color:#60a5fa;"></span>
                                ${m}
                            </li>
                        `).join('');
                    }
                }
            }

    window.UI.updateRSIUI = updateRSIUI;
    window.updateRSIUI = updateRSIUI;

    function selectRetrievalConfidence(conf) {
                currentRetrievalConfidence = conf;
                document.querySelectorAll('.btn-confidence').forEach(btn => {
                    btn.style.borderColor = 'var(--border-color)';
                    btn.style.backgroundColor = 'var(--bg-primary)';
                    btn.style.color = 'var(--text-secondary)';
                });
                const activeBtn = document.getElementById('conf-btn-' + conf);
                if (activeBtn) {
                    activeBtn.style.borderColor = 'var(--accent-primary)';
                    activeBtn.style.backgroundColor = 'rgba(99, 102, 241, 0.2)';
                    activeBtn.style.color = 'white';
                }
            }

    window.UI.selectRetrievalConfidence = selectRetrievalConfidence;
    window.selectRetrievalConfidence = selectRetrievalConfidence;

    function submitRetrievalAnswer() {
                if (currentRetrievalConfidence === null) {
                    alert("Please rate your confidence in this recall before submitting!");
                    return;
                }
                
                const ans = document.getElementById('retrieval-answer-input').value.trim();
                if (!ans) {
                    alert("Please write down your formula or concept answer first!");
                    return;
                }
                
                const q = currentRetrievalQuestion;
                const match = q.r.test(ans);
                const feedbackEl = document.getElementById('retrieval-regex-feedback');
                const correctEl = document.getElementById('retrieval-correct-solution');
                const feedbackPanel = document.getElementById('retrieval-feedback-panel');
                
                if (match) {
                    feedbackEl.innerHTML = `<span style="color: var(--success);">Automated Check: Match Found ✅ (Likely Correct)</span>`;
                } else {
                    feedbackEl.innerHTML = `<span style="color: var(--warning);">Automated Check: Review Suggested 🔍 (Please verify with the solution below)</span>`;
                }
                
                correctEl.innerText = q.sol;
                feedbackPanel.style.display = 'block';
                
                // Disable inputs during self-grade
                document.getElementById('retrieval-answer-input').disabled = true;
                document.getElementById('retrieval-submit-btn').disabled = true;
                document.querySelectorAll('.btn-confidence').forEach(btn => btn.style.pointerEvents = 'none');
            }

    window.UI.submitRetrievalAnswer = submitRetrievalAnswer;
    window.submitRetrievalAnswer = submitRetrievalAnswer;

    function confirmRetrievalCheck(isMatch) {
                // Track calibration statistics
                const conf = currentRetrievalConfidence;
                const cStats = stats.calibrationStats;
                if (isMatch) {
                    stats.xp += 5; // Award 5 XP for retrieval
                    if (conf === 3) cStats.highConfidenceCorrect++;
                    else if (conf === 1) cStats.lowConfidenceCorrect++;
                } else {
                    if (conf === 3) cStats.highConfidenceIncorrect++;
                    else if (conf === 1) cStats.lowConfidenceIncorrect++;
                }
                
                // Record confidence on current practice problem
                if (currentPracProblem) {
                    currentPracProblem.retrievalConfidence = conf;
                }
                
                saveStats();
                
                // Reset panel & Transition to practice problem
                document.getElementById('retrieval-pretest-panel').style.display = 'none';
                document.getElementById('prac-question-prompt').style.display = 'block';
                
                const diagPanel = document.getElementById('prac-diagram-panel');
                if (diagPanel && currentPracProblem.mathDetails) {
                    diagPanel.style.display = 'block';
                }
                
                // Adaptive Scaffolding Check
                const sel = currentPracProblem.category;
                const hintsEnabled = !stats.consecutiveStats || !stats.consecutiveStats[sel] || stats.consecutiveStats[sel].hintsEnabled !== false;
                if (hintsEnabled) {
                    document.getElementById('prac-scaffold-panel').style.display = 'block';
                } else {
                    document.getElementById('prac-scaffold-panel').style.display = 'none';
                }
                
                document.getElementById('prac-active-buttons').style.display = 'flex';
            }

    window.UI.confirmRetrievalCheck = confirmRetrievalCheck;
    window.confirmRetrievalCheck = confirmRetrievalCheck;

    function updateDashboardMistakes() {
                const card = document.getElementById('dash-mistakes-card');
                const list = document.getElementById('dash-mistakes-list');
                if (!card || !list) return;
                if (!stats.mistakesLog || stats.mistakesLog.length === 0) {
                    card.style.display = 'none';
                    return;
                }
                card.style.display = 'block';
                list.innerHTML = '';
                stats.mistakesLog.forEach(m => {
                    list.innerHTML += `
                        <div class="mistake-card-item">
                            <div class="mistake-title">⚠️ ${m.title}</div>
                            <div class="mistake-desc">${m.desc}</div>
                            <div class="mistake-remedy">💡 Remedy: ${m.remedy}</div>
                        </div>
                    `;
                });
            }

    window.UI.updateDashboardMistakes = updateDashboardMistakes;
    window.updateDashboardMistakes = updateDashboardMistakes;

    function updateStatsHUD() {
                const level = Math.floor(stats.xp / 500) + 1;
                const prevLevelXp = (level - 1) * 500;
                const levelProgress = ((stats.xp - prevLevelXp) / 500) * 100;
                let rank = 'Novice Controller';
                if (stats.xp > 300 && stats.xp <= 800) rank = 'Junior Controller';
                else if (stats.xp > 800 && stats.xp <= 1500) rank = 'Senior Controller';
                else if (stats.xp > 1500 && stats.xp <= 2500) rank = 'Lead Auditor';
                else if (stats.xp > 2500) rank = 'Innsbruck Legend 🎓';
    
                const values = {
                    'dash-rank': rank, 'dash-level-text': `Level ${level} | ${stats.xp - prevLevelXp} / 500 XP to Level ${level+1}`,
                    'dash-xp-val': stats.xp, 'dash-streak-val': `${stats.streak}🔥`,
                    'prac-rank': rank, 'prac-level-text': `Level ${level} | ${stats.xp - prevLevelXp} / 500 XP`,
                    'prac-xp-val': stats.xp, 'prac-streak-val': `${stats.streak}🔥`
                };
                for (const id in values) {
                    const el = document.getElementById(id);
                    if (el) el.innerText = values[id];
                }
                const fill1 = document.getElementById('dash-progress-fill');
                if (fill1) fill1.style.width = `${levelProgress}%`;
                const fill2 = document.getElementById('prac-progress-fill');
                if (fill2) fill2.style.width = `${levelProgress}%`;
                
                let accuracy = 0;
                if (stats.totalAttempts > 0) accuracy = Math.round((stats.correctAttempts / stats.totalAttempts) * 100);
                const accVal = document.getElementById('arena-accuracy-val');
                if (accVal) accVal.innerText = `${accuracy}%`;
            }

    window.UI.updateStatsHUD = updateStatsHUD;
    window.updateStatsHUD = updateStatsHUD;

    function updateMasteryUI() {
                updateDecayedMastery();
                const topics = ['concepts', 'costing', 'cvp', 'abc', 'variance'];
                topics.forEach(t => {
                    const val = stats['mastery' + capitalizeFirst(t)] || 0;
                    const textEl = document.getElementById(`mastery-${t}-val`);
                    const fillEl = document.getElementById(`mastery-${t}-fill`);
                    if (textEl) textEl.innerText = `${val}%`;
                    if (fillEl) fillEl.style.width = `${val}%`;
                    
                    // Update competency badge
                    const peak = (stats.masteryPeaks && stats.masteryPeaks[t] !== undefined) ? stats.masteryPeaks[t] : 0;
                    const badgeEl = document.getElementById(`competency-${t}-badge`);
                    if (badgeEl) {
                        let level = "Novice";
                        let color = "#9ca3af";
                        let bg = "rgba(156, 163, 175, 0.1)";
                        let border = "1px solid rgba(156, 163, 175, 0.3)";
                        
                        if (peak >= 90) {
                            level = "Master";
                            color = "#10b981";
                            bg = "rgba(16, 185, 129, 0.1)";
                            border = "1px solid rgba(16, 185, 129, 0.3)";
                        } else if (peak >= 70) {
                            level = "Proficient";
                            color = "#3b82f6";
                            bg = "rgba(59, 130, 246, 0.1)";
                            border = "1px solid rgba(59, 130, 246, 0.3)";
                        } else if (peak >= 40) {
                            level = "Competent";
                            color = "#f59e0b";
                            bg = "rgba(245, 158, 11, 0.1)";
                            border = "1px solid rgba(245, 158, 11, 0.3)";
                        }
                        
                        badgeEl.innerText = level;
                        badgeEl.style.color = color;
                        badgeEl.style.backgroundColor = bg;
                        badgeEl.style.border = border;
                    }
                });
            }

    window.UI.updateMasteryUI = updateMasteryUI;
    window.updateMasteryUI = updateMasteryUI;

    function switchTab(tabId) {
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                document.getElementById('tab-' + tabId).classList.add('active');
                
                const items = document.querySelectorAll('.nav-item');
                const titles = {
                    'dashboard': ['University Innsbruck Cost Accounting', 'Welcome to the study companion portal designed for Winter Term 2025/26.'],
                    'session1': ['Session 1: Cost Concepts', 'Identify direct vs. indirect, variable vs. fixed cost behaviors.'],
                    'session2': ['Session 2: Costing Systems', 'Calculations for rates, overhead allocations, and FIFO equivalent units.'],
                    'session3': ['Session 3: CVP & Bottlenecks', 'Break-even limits, CVP graph structures, and capacity constraint decisions.'],
                    'session4': ['Session 4: Activity-Based Costing', 'Trace activity overhead pools to products to resolve cost distortions.'],
                    'session5': ['Session 5: Budgeting & Variances', 'Construct flexible budgets to analyze price and efficiency deviations.'],
                    'practice-arena': ['The Practice Arena', 'Separating Learn mode tutorials, Practice mode scaffolds, and timed Exams.'],
                    'ml-copilot': ['ML Cognitive Copilot', 'KNN performance classifier & PDF keyword slide recommender.']
                };
    
                let index = ['dashboard', 'session1', 'session2', 'session3', 'session4', 'session5', 'practice-arena', 'ml-copilot'].indexOf(tabId);
                if (index !== -1) items[index].classList.add('active');
                
                document.getElementById('tab-header-title').innerText = titles[tabId][0];
                
                // Trigger local computations
                if (tabId === 'session1') renderClassifierHTML();
                else if (tabId === 'session2') { calculateS2Rates(); calculateS2OH(); calculateS2EU(); }
                else if (tabId === 'session3') { updateCVP(); updateBottleneck(); }
                else if (tabId === 'session4') { calculateABC(); calculateS4Distribution(); }
                else if (tabId === 'session5') { calculateVariances(); }
                else if (tabId === 'practice-arena') { setArenaMode(currentArenaMode); }
                else if (tabId === 'ml-copilot') { updateCopilotUI(); }
            }

    window.UI.switchTab = switchTab;
    window.switchTab = switchTab;

    function updateCopilotUI() {
        let activeTopic = 'concepts';
        if (window.currentPracProblem && window.currentPracProblem.category) {
            activeTopic = window.currentPracProblem.category === 'fifo' ? 'costing' : window.currentPracProblem.category;
        } else if (typeof currentPracProblem !== 'undefined' && currentPracProblem && currentPracProblem.category) {
            activeTopic = currentPracProblem.category === 'fifo' ? 'costing' : currentPracProblem.category;
        }

        const weakest = (window.Storage && window.Storage.stats && window.Storage.stats.weakestCategory) || (rsiState && rsiState.weakestCategory) || 'concepts';
        
        if (!window.Cognitive || !window.Cognitive.Copilot || !window.Cognitive.Copilot.runDiagnostic) return;
        
        const diag = window.Cognitive.Copilot.runDiagnostic(activeTopic, weakest);
        
        // Render classifier results
        const barrierTitle = document.getElementById('copilot-barrier-title');
        const coachingText = document.getElementById('copilot-coaching-text');
        
        if (barrierTitle) barrierTitle.innerText = diag.classification.barrier;
        if (coachingText) coachingText.innerText = diag.classification.coaching;
        
        // Render features
        const fEntropy = document.getElementById('copilot-feat-entropy');
        const fImpasse = document.getElementById('copilot-feat-impasse');
        const fAccuracy = document.getElementById('copilot-feat-accuracy');
        const fMismatch = document.getElementById('copilot-feat-mismatch');
        const fDecay = document.getElementById('copilot-feat-decay');
        
        if (fEntropy) fEntropy.innerText = diag.features.entropy.toFixed(2);
        if (fImpasse) fImpasse.innerText = diag.features.impasse.toFixed(2);
        if (fAccuracy) fAccuracy.innerText = `${Math.round(diag.features.accuracy * 100)}%`;
        if (fMismatch) fMismatch.innerText = `${Math.round(diag.features.mismatch * 100)}%`;
        if (fDecay) fDecay.innerText = `${Math.round(diag.features.decay * 100)}%`;
        
        // Render recommendations list
        const recList = document.getElementById('copilot-recommendations-list');
        if (recList) {
            if (diag.recommendations.length === 0) {
                recList.innerHTML = `<p style="color:var(--text-muted); font-size:12px; font-style:italic;">No recommendations found yet. Complete practices to collect data.</p>`;
            } else {
                recList.innerHTML = diag.recommendations.map(r => `
                    <div style="background: rgba(59, 130, 246, 0.04); border: 1px solid rgba(59, 130, 246, 0.15); padding: 10px; border-radius: 6px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <strong style="color:#60a5fa; font-size:12px;">${r.sessionTitle}</strong>
                            <span class="num-badge" style="background:rgba(96,165,250,0.15); color:#60a5fa; padding:2px 6px; border-radius:4px; font-size:10px; border: 1px solid rgba(96,165,250,0.3);">Slide Page ${r.page}</span>
                        </div>
                        <div style="font-size:11.5px; color:var(--text-secondary); line-height:1.4; font-style:italic;">"${r.snippet}"</div>
                    </div>
                `).join('');
            }
        }
    }

    function reRunCopilotDiagnostic() {
        updateCopilotUI();
    }

    function searchPdfDatabase() {
        const query = document.getElementById('pdf-search-input').value.trim();
        const resultsEl = document.getElementById('pdf-search-results');
        if (!resultsEl) return;
        if (!query) {
            resultsEl.innerHTML = `<p style="color:var(--text-muted); font-size:12px; font-style:italic;">Please enter a search query.</p>`;
            return;
        }

        if (!window.Storage || !window.Storage.knowledgeBase || !window.Storage.knowledgeBase.rawPages) {
            resultsEl.innerHTML = `<p style="color:var(--danger); font-size:12px;">Knowledge base not found.</p>`;
            return;
        }

        const queryLower = query.toLowerCase();
        let matches = [];

        window.Storage.knowledgeBase.rawPages.forEach(page => {
            const idx = page.text.toLowerCase().indexOf(queryLower);
            if (idx !== -1) {
                let start = Math.max(0, idx - 40);
                let end = Math.min(page.text.length, idx + 100);
                let snippet = page.text.slice(start, end);
                if (start > 0) snippet = "..." + snippet;
                if (end < page.text.length) snippet = snippet + "...";

                // Highlight keyword
                const regex = new RegExp(queryLower, 'gi');
                snippet = snippet.replace(regex, match => `<strong style="color:var(--warning);">${match}</strong>`);

                matches.push({
                    sessionTitle: page.sessionTitle,
                    page: page.page,
                    snippet: snippet
                });
            }
        });

        if (matches.length === 0) {
            resultsEl.innerHTML = `<p style="color:var(--text-muted); font-size:12px; font-style:italic;">No matches found for "${query}".</p>`;
        } else {
            resultsEl.innerHTML = matches.slice(0, 10).map(m => `
                <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); padding:8px; border-radius:6px; font-size:11.5px; line-height:1.4;">
                    <div style="font-weight:700; color:white; margin-bottom:2px; display:flex; justify-content:space-between;">
                        <span>${m.sessionTitle}</span>
                        <span style="color:var(--accent-primary);">Slide ${m.page}</span>
                    </div>
                    <div style="color:var(--text-secondary); font-style:italic;">${m.snippet}</div>
                </div>
            `).join('');
        }
    }

    window.UI.updateCopilotUI = updateCopilotUI;
    window.updateCopilotUI = updateCopilotUI;
    window.UI.reRunCopilotDiagnostic = reRunCopilotDiagnostic;
    window.reRunCopilotDiagnostic = reRunCopilotDiagnostic;
    window.UI.searchPdfDatabase = searchPdfDatabase;
    window.searchPdfDatabase = searchPdfDatabase;

    function renderClassifierHTML() {
                const container = document.getElementById('s1-classifier-inputs');
                if (!container || container.children.length > 0) return;
                let html = `
                    <div class="classifier-grid classifier-header">
                        <div class="classifier-row">Cost Item</div>
                        <div class="classifier-row" style="text-align: center;">D / I</div>
                        <div class="classifier-row" style="text-align: center;">V / F</div>
                    </div>
                `;
                s1Items.forEach(item => {
                    html += `
                        <div class="classifier-grid">
                            <div>${item.name}</div>
                            <div class="select-btn-group">
                                <button class="select-btn" id="${item.id}-d" onclick="setS1Classifier('${item.id}', 'di', 'D')">Direct</button>
                                <button class="select-btn" id="${item.id}-i" onclick="setS1Classifier('${item.id}', 'di', 'I')">Indirect</button>
                            </div>
                            <div class="select-btn-group">
                                <button class="select-btn" id="${item.id}-v" onclick="setS1Classifier('${item.id}', 'vf', 'V')">Variable</button>
                                <button class="select-btn" id="${item.id}-f" onclick="setS1Classifier('${item.id}', 'vf', 'F')">Fixed</button>
                            </div>
                        </div>
                    `;
                });
                container.innerHTML = html;
            }

    window.UI.renderClassifierHTML = renderClassifierHTML;
    window.renderClassifierHTML = renderClassifierHTML;

    function setS1Classifier(rowId, colType, value) {
                const diBtn = [document.getElementById(rowId + '-d'), document.getElementById(rowId + '-i')];
                const vfBtn = [document.getElementById(rowId + '-v'), document.getElementById(rowId + '-f')];
                if (colType === 'di') {
                    diBtn.forEach(btn => btn.classList.remove('active', 'correct', 'incorrect'));
                    document.getElementById(rowId + '-' + value.toLowerCase()).classList.add('active');
                    s1UserAnswers[rowId + '-di'] = value;
                } else {
                    vfBtn.forEach(btn => btn.classList.remove('active', 'correct', 'incorrect'));
                    document.getElementById(rowId + '-' + value.toLowerCase()).classList.add('active');
                    s1UserAnswers[rowId + '-vf'] = value;
                }
            }

    window.UI.setS1Classifier = setS1Classifier;
    window.setS1Classifier = setS1Classifier;

    function checkClassifications() {
                let correct = 0;
                let total = 16;
                for (const key in s1ClassifierCorrect) {
                    const parts = key.split('-');
                    const rowId = parts[0] + '-' + parts[1];
                    const userVal = s1UserAnswers[key];
                    if (userVal) {
                        const btn = document.getElementById(rowId + '-' + userVal.toLowerCase());
                        btn.classList.remove('active');
                        if (userVal === s1ClassifierCorrect[key]) {
                            btn.classList.add('correct'); correct++;
                        } else {
                            btn.classList.add('incorrect');
                        }
                    }
                }
                const fb = document.getElementById('classifier-feedback');
                fb.innerText = `Score: ${correct}/${total} correct.`;
                fb.style.color = correct === total ? 'var(--success)' : 'var(--warning)';
                
                // Add to mastery
                stats.masteryConcepts = Math.min(100, stats.masteryConcepts + Math.floor((correct/total)*20));
                saveStats();
            }

    window.UI.checkClassifications = checkClassifications;
    window.checkClassifications = checkClassifications;

    function resetClassifications() {
                s1UserAnswers = {};
                document.querySelectorAll('.select-btn').forEach(b => b.classList.remove('active', 'correct', 'incorrect'));
                document.getElementById('classifier-feedback').innerText = '';
            }

    window.UI.resetClassifications = resetClassifications;
    window.resetClassifications = resetClassifications;

    function checkEx211() {
                const t500 = parseFloat(document.getElementById('ex211-tot500').value) || 0;
                const u500 = parseFloat(document.getElementById('ex211-unit500').value) || 0;
                const t2000 = parseFloat(document.getElementById('ex211-tot2000').value) || 0;
                const u2000 = parseFloat(document.getElementById('ex211-unit2000').value) || 0;
                const lesson = document.getElementById('ex211-lesson').value;
    
                const isCorrect = (t500 === 40000 && u500 === 80 && t2000 === 40000 && u2000 === 20 && lesson === 'B');
                const fb = document.getElementById('ex211-feedback');
                if (isCorrect) {
                    fb.innerText = "Correct! Fixed cost in total remains €40,000, while unit cost varies.";
                    fb.className = "alert alert-success";
                    fb.style.marginTop = "10px";
                    stats.xp += 20;
                    stats.masteryConcepts = Math.min(100, stats.masteryConcepts + 10);
                    saveStats();
                } else {
                    fb.innerText = "Incorrect. Recall that music cost is fixed. Per-person cost = Total / Attendance.";
                    fb.className = "alert alert-warning";
                    fb.style.marginTop = "10px";
                }
            }

    window.UI.checkEx211 = checkEx211;
    window.checkEx211 = checkEx211;

    function checkEx116() {
                const q1 = document.getElementById('ex116-q1').value;
                const q2 = document.getElementById('ex116-q2').value;
                const q3 = document.getElementById('ex116-q3').value;
                const q4 = document.getElementById('ex116-q4').value;
    
                const isCorrect = (q1 === 'SK' && q2 === 'AD' && q3 === 'PS' && q4 === 'SK');
                const fb = document.getElementById('ex116-feedback');
                if (isCorrect) {
                    fb.innerText = "Correct! Scorekeeping (monthly sales/scrap reports), Attention Directing (budget performance reports), and Problem Solving (purchasing decision analysis).";
                    fb.className = "alert alert-success";
                    fb.style.marginTop = "10px";
                    stats.xp += 20;
                    stats.masteryConcepts = Math.min(100, stats.masteryConcepts + 10);
                    saveStats();
                } else {
                    fb.innerText = "Incorrect. Check definitions: Scorekeeping is raw data, Attention Directing is performance reporting, Problem Solving is decision making.";
                    fb.className = "alert alert-warning";
                    fb.style.marginTop = "10px";
                }
            }

    window.UI.checkEx116 = checkEx116;
    window.checkEx116 = checkEx116;

    function calculateS2Rates() {
                const dir = parseFloat(document.getElementById('s2-calc-director').value) || 0;
                const part = parseFloat(document.getElementById('s2-calc-partner').value) || 0;
                const assoc = parseFloat(document.getElementById('s2-calc-associate').value) || 0;
                const assist = parseFloat(document.getElementById('s2-calc-assistant').value) || 0;
                const billable = parseFloat(document.getElementById('s2-calc-billable').value) || 1;
                const total = parseFloat(document.getElementById('s2-calc-total').value) || 1;
    
                const roles = [{n: 'Director', c: dir}, {n: 'Partner', c: part}, {n: 'Associate', c: assoc}, {n: 'Assistant', c: assist}];
                const tbody = document.getElementById('s2-rates-table').querySelector('tbody');
                tbody.innerHTML = '';
    
                roles.forEach(r => {
                    const r1 = r.c / billable;
                    const r2 = r.c / total;
                    tbody.innerHTML += `
                        <tr><td><strong>${r.n}</strong> (€${r.c.toLocaleString()})</td><td>€${r1.toFixed(2)}/hr</td><td>€${r2.toFixed(2)}/hr</td><td style="color:var(--warning);">+€${(r1-r2).toFixed(2)}/hr</td></tr>
                    `;
                });
            }

    window.UI.calculateS2Rates = calculateS2Rates;
    window.calculateS2Rates = calculateS2Rates;

    function calculateS2OH() {
                const budgetedCost = parseFloat(document.getElementById('s2-oh-budget').value) || 0;
                const budgetedHours = parseFloat(document.getElementById('s2-oh-hours').value) || 1;
                const actualCost = parseFloat(document.getElementById('s2-oh-actual-cost').value) || 0;
                const actualHours = parseFloat(document.getElementById('s2-oh-actual-hours').value) || 0;
    
                const rate = budgetedCost / budgetedHours;
                const allocated = rate * actualHours;
                const diff = allocated - actualCost;
    
                document.getElementById('s2-oh-rate-result').innerText = `€${rate.toFixed(2)} / MH`;
                document.getElementById('s2-oh-allocated-result').innerText = `€${allocated.toLocaleString()}`;
    
                const status = document.getElementById('s2-oh-status-result');
                const explanation = document.getElementById('s2-oh-explanation-result');
    
                if (diff >= 0) {
                    status.innerText = `Overallocated by €${diff.toLocaleString()}`;
                    status.className = 'num-badge correct';
                    explanation.innerHTML = `Overhead is <strong>overallocated</strong> because allocation exceeds actual costs. Decreases COGS on adjustment.`;
                } else {
                    status.innerText = `Underallocated by €${Math.abs(diff).toLocaleString()}`;
                    status.className = 'num-badge incorrect';
                    explanation.innerHTML = `Overhead is <strong>underallocated</strong> because actual costs exceed allocation. Increases COGS on adjustment.`;
                }
            }

    window.UI.calculateS2OH = calculateS2OH;
    window.calculateS2OH = calculateS2OH;

    function calculateS2EU() {
                const opUnits = parseFloat(document.getElementById('s2-eu-op-units').value) || 0;
                const started = parseFloat(document.getElementById('s2-eu-started').value) || 0;
                const completed = parseFloat(document.getElementById('s2-eu-completed').value) || 0;
                const clUnits = parseFloat(document.getElementById('s2-eu-cl-units').value) || 0;
    
                const opDmPct = (parseFloat(document.getElementById('s2-eu-op-dm').value) || 0) / 100;
                const opConvPct = (parseFloat(document.getElementById('s2-eu-op-conv').value) || 0) / 100;
                const clDmPct = (parseFloat(document.getElementById('s2-eu-cl-dm').value) || 0) / 100;
                const clConvPct = (parseFloat(document.getElementById('s2-eu-cl-conv').value) || 0) / 100;
    
                const opDmCost = parseFloat(document.getElementById('s2-eu-op-dm-cost').value) || 0;
                const opConvCost = parseFloat(document.getElementById('s2-eu-op-conv-cost').value) || 0;
                const addDmCost = parseFloat(document.getElementById('s2-eu-add-dm-cost').value) || 0;
                const addConvCost = parseFloat(document.getElementById('s2-eu-add-conv-cost').value) || 0;
    
                const clDmEU = clUnits * clDmPct;
                const clConvEU = clUnits * clConvPct;
                const opDmEU = opUnits * opDmPct;
                const opConvEU = opUnits * opConvPct;
    
                const totalAccountedDm = completed + clDmEU;
                const totalAccountedConv = completed + clConvEU;
    
                const currDmEU = totalAccountedDm - opDmEU;
                const currConvEU = totalAccountedConv - opConvEU;
    
                document.getElementById('s2-res-phys-comp').innerText = completed;
                document.getElementById('s2-res-dm-comp').innerText = completed.toFixed(1);
                document.getElementById('s2-res-conv-comp').innerText = completed.toFixed(1);
    
                document.getElementById('s2-res-phys-cl').innerText = clUnits;
                document.getElementById('s2-res-dm-cl').innerText = clDmEU.toFixed(1);
                document.getElementById('s2-res-conv-cl').innerText = clConvEU.toFixed(1);
    
                document.getElementById('s2-res-phys-total').innerText = (completed + clUnits);
                document.getElementById('s2-res-dm-total').innerText = totalAccountedDm.toFixed(1);
                document.getElementById('s2-res-conv-total').innerText = totalAccountedConv.toFixed(1);
    
                document.getElementById('s2-res-phys-op').innerText = -opUnits;
                document.getElementById('s2-res-dm-op').innerText = (-opDmEU).toFixed(1);
                document.getElementById('s2-res-conv-op').innerText = (-opConvEU).toFixed(1);
    
                document.getElementById('s2-res-phys-current').innerText = started;
                document.getElementById('s2-res-dm-current').innerText = currDmEU.toFixed(1);
                document.getElementById('s2-res-conv-current').innerText = currConvEU.toFixed(1);
    
                const opDmRate = opDmCost / (opDmEU || 1);
                const opConvRate = opConvCost / (opConvEU || 1);
                const currDmRate = addDmCost / (currDmEU || 1);
                const currConvRate = addConvCost / (currConvEU || 1);
    
                document.getElementById('s2-res-op-dm-rate').innerText = `€${opDmRate.toLocaleString(undefined, {maximumFractionDigits:2})} / EU`;
                document.getElementById('s2-res-op-conv-rate').innerText = `€${opConvRate.toLocaleString(undefined, {maximumFractionDigits:2})} / EU`;
                document.getElementById('s2-res-curr-dm-rate').innerText = `€${currDmRate.toLocaleString(undefined, {maximumFractionDigits:2})} / EU`;
                document.getElementById('s2-res-curr-conv-rate').innerText = `€${currConvRate.toLocaleString(undefined, {maximumFractionDigits:2})} / EU`;
    
                const isDefault = opUnits === 8 && started === 50 && completed === 46 && clUnits === 12 && 
                                  opDmPct === 0.9 && opConvPct === 0.4 && clDmPct === 0.6 && clConvPct === 0.3;
                document.getElementById('s2-slide-typo-alert').style.display = isDefault ? 'inline-flex' : 'none';
            }

    window.UI.calculateS2EU = calculateS2EU;
    window.calculateS2EU = calculateS2EU;

    function updateCVP() {
                const price = parseFloat(document.getElementById('s3-cvp-price').value);
                const vc = parseFloat(document.getElementById('s3-cvp-vc').value);
                const fc = parseFloat(document.getElementById('s3-cvp-fc').value);
                const volume = parseFloat(document.getElementById('s3-cvp-volume').value);
    
                document.getElementById('s3-cvp-price-val').innerText = `€${price.toFixed(2)}`;
                document.getElementById('s3-cvp-vc-val').innerText = `€${vc.toFixed(2)}`;
                document.getElementById('s3-cvp-fc-val').innerText = `€${fc.toFixed(2)}`;
                document.getElementById('s3-cvp-volume-val').innerText = volume;
    
                const cmu = price - vc;
                document.getElementById('s3-cvp-cmu').innerText = `€${cmu.toFixed(2)}`;
    
                let be = 0;
                if (cmu > 0) {
                    be = fc / cmu;
                    document.getElementById('s3-cvp-be').innerText = `${Math.ceil(be)} units (€${(be * price).toFixed(0)})`;
                } else {
                    document.getElementById('s3-cvp-be').innerText = `N/A`;
                }
    
                const profit = (volume * price) - (volume * vc) - fc;
                const profitEl = document.getElementById('s3-cvp-profit');
                profitEl.innerText = profit >= 0 ? `€${profit.toFixed(2)}` : `(€${Math.abs(profit).toFixed(2)})`;
                profitEl.style.color = profit >= 0 ? 'var(--success)' : 'var(--danger)';
    
                drawCVPChart(price, vc, fc, volume, be);
            }

    window.UI.updateCVP = updateCVP;
    window.updateCVP = updateCVP;

    function drawCVPChart(price, vc, fc, volume, be) {
                const svg = document.getElementById('cvp-chart');
                const width = 400, height = 300, padding = 40;
                const maxUnits = 300;
                const maxCost = Math.max(maxUnits * price, fc + maxUnits * vc, fc) * 1.1;
    
                const getX = (u) => padding + (u / maxUnits) * (width - 2 * padding);
                const getY = (c) => height - padding - (c / maxCost) * (height - 2 * padding);
    
                let html = `
                    <line x1="${getX(0)}" y1="${getY(0)}" x2="${getX(maxUnits)}" y2="${getY(0)}" class="cvp-axis" />
                    <line x1="${getX(0)}" y1="${getY(0)}" x2="${getX(0)}" y2="${getY(maxCost)}" class="cvp-axis" />
                    <text x="${width - padding}" y="${height - 10}" class="cvp-text" text-anchor="end">Volume</text>
                    <text x="10" y="30" class="cvp-text">€</text>
                `;
    
                if (price - vc > 0 && be <= maxUnits) {
                    html += `
                        <polygon points="${getX(0)},${getY(fc)} ${getX(be)},${getY(be * price)} ${getX(0)},${getY(0)}" class="cvp-loss-area" />
                        <polygon points="${getX(be)},${getY(be * price)} ${getX(maxUnits)},${getY(maxUnits * price)} ${getX(maxUnits)},${getY(fc + maxUnits * vc)}" class="cvp-profit-area" />
                    `;
                } else {
                    html += `<polygon points="${getX(0)},${getY(fc)} ${getX(maxUnits)},${getY(fc + maxUnits * vc)} ${getX(maxUnits)},${getY(maxUnits * price)} ${getX(0)},${getY(0)}" class="cvp-loss-area" />`;
                }
    
                html += `
                    <line x1="${getX(0)}" y1="${getY(fc)}" x2="${getX(maxUnits)}" y2="${getY(fc)}" class="cvp-fixed-cost" />
                    <line x1="${getX(0)}" y1="${getY(fc)}" x2="${getX(maxUnits)}" y2="${getY(fc + maxUnits * vc)}" class="cvp-total-cost" />
                    <line x1="${getX(0)}" y1="${getY(0)}" x2="${getX(maxUnits)}" y2="${getY(maxUnits * price)}" class="cvp-revenue" />
                    <text x="${getX(maxUnits) - 10}" y="${getY(fc) - 6}" class="cvp-text" style="fill:#f59e0b;">FC</text>
                    <text x="${width - padding - 30}" y="${getY(fc + maxUnits * vc) - 10}" class="cvp-text" style="fill:#3b82f6;">TC</text>
                    <text x="${width - padding - 30}" y="${getY(maxUnits * price) - 10}" class="cvp-text" style="fill:#10b981;">TR</text>
                `;
    
                if (price - vc > 0 && be > 0 && be <= maxUnits) {
                    html += `
                        <circle cx="${getX(be)}" cy="${getY(be * price)}" r="5" class="cvp-point-be" />
                        <text x="${getX(be) + 8}" y="${getY(be * price) + 12}" class="cvp-text" style="fill:var(--warning); font-weight:bold;">BEP</text>
                    `;
                }
                svg.innerHTML = html;
            }

    window.UI.drawCVPChart = drawCVPChart;
    window.drawCVPChart = drawCVPChart;

    function updateBottleneck() {
                const cola = parseFloat(document.getElementById('s3-alloc-cola').value) || 0;
                const lemonade = parseFloat(document.getElementById('s3-alloc-lemonade').value) || 0;
                const punch = parseFloat(document.getElementById('s3-alloc-punch').value) || 0;
                const oj = parseFloat(document.getElementById('s3-alloc-oj').value) || 0;
    
                const total = cola + lemonade + punch + oj;
                const spaceLabel = document.getElementById('s3-alloc-total');
                spaceLabel.innerText = `${total} m / 12 m`;
    
                const cmCola = cola * 675;
                const cmLemon = lemonade * 576;
                const cmPunch = punch * 151.2;
                const cmOJ = oj * 246;
    
                document.getElementById('s3-cm-cola').innerText = `€${cmCola.toFixed(2)}`;
                document.getElementById('s3-cm-lemonade').innerText = `€${cmLemon.toFixed(2)}`;
                document.getElementById('s3-cm-punch').innerText = `€${cmPunch.toFixed(2)}`;
                document.getElementById('s3-cm-oj').innerText = `€${cmOJ.toFixed(2)}`;
    
                const totalCM = cmCola + cmLemon + cmPunch + cmOJ;
                document.getElementById('s3-cm-total').innerText = `€${totalCM.toFixed(2)}`;
    
                const feedback = document.getElementById('s3-bottleneck-feedback');
                if (total > 12) {
                    spaceLabel.style.color = 'var(--danger)';
                    feedback.innerText = "Allocated shelf space exceeds 12m limit!";
                    feedback.style.backgroundColor = 'var(--danger-glow)';
                    feedback.style.color = 'var(--danger)';
                } else {
                    spaceLabel.style.color = total === 12 ? 'var(--success)' : 'var(--warning)';
                    if (total === 12 && cola === 6 && lemonade === 4 && punch === 1 && oj === 1) {
                        feedback.innerText = "Optimal Allocation! CM maximized at €6,751.20/day.";
                        feedback.style.backgroundColor = 'var(--success-glow)';
                        feedback.style.color = 'var(--success)';
                    } else {
                        feedback.innerText = "Sub-optimal. Place maximum space to higher CM/meter products (Cola, Lemonade).";
                        feedback.style.backgroundColor = 'var(--warning-glow)';
                        feedback.style.color = 'var(--warning)';
                    }
                }
            }

    window.UI.updateBottleneck = updateBottleneck;
    window.updateBottleneck = updateBottleneck;

    function calculateABC() {
                const prod = parseFloat(document.getElementById('s4-pool-prod').value) || 0;
                const del = parseFloat(document.getElementById('s4-pool-del').value) || 0;
    
                const tVol = 4800, aVol = 10200;
                const totalVol = tVol + aVol;
                const tDM = 650000/tVol, aDM = 860000/aVol;
                const tDL = 480000/tVol, aDL = 600000/aVol;
    
                // Traditional
                const tradRate = (prod + del) / totalVol;
                const tradT = tDM + tDL + tradRate;
                const tradA = aDM + aDL + tradRate;
    
                // ABC
                const rProd = prod / 10800; // machine hours
                const rDel = del / 290; // shipments
                const abcT = tDM + tDL + ((3000 * rProd) + (40 * rDel)) / tVol;
                const abcA = aDM + aDL + ((7800 * rProd) + (250 * rDel)) / aVol;
    
                const tbody = document.getElementById('s4-abc-table').querySelector('tbody');
                tbody.innerHTML = `
                    <tr><td>Titan Throne</td><td>€${tradT.toFixed(2)}</td><td>€${abcT.toFixed(2)}</td><td style="color:var(--success);">+€${(tradT-abcT).toFixed(2)}</td><td>Over-costed Traditionally</td></tr>
                    <tr><td>Arena X</td><td>€${tradA.toFixed(2)}</td><td>€${abcA.toFixed(2)}</td><td style="color:var(--danger);">€${(tradA-abcA).toFixed(2)}</td><td>Under-costed Traditionally</td></tr>
                `;
            }

    window.UI.calculateABC = calculateABC;
    window.calculateABC = calculateABC;

    function calculateS4Distribution() {
                const o = parseFloat(document.getElementById('s4-plan-orders').value) || 0;
                const oc = parseFloat(document.getElementById('s4-plan-order-cost').value) || 0;
                const l = parseFloat(document.getElementById('s4-plan-loads').value) || 0;
                const lc = parseFloat(document.getElementById('s4-plan-load-cost').value) || 0;
    
                const rev22 = 1000000, cogs22 = 750000, opex22 = 245000;
                const prof22 = rev22 - cogs22 - opex22;
    
                const rev23 = 950000, cogs23 = 720000;
                const opex23 = (o*oc) + (l*lc) + (1500*40) + 40000;
                const prof23 = rev23 - cogs23 - opex23;
                const unitProf = prof23 / 250000;
    
                const tbody = document.getElementById('s4-dist-table').querySelector('tbody');
                tbody.innerHTML = `
                    <tr><td>2022 Audited</td><td>€${rev22.toLocaleString()}</td><td>€${cogs22.toLocaleString()}</td><td>€${opex22.toLocaleString()}</td><td>€${prof22.toLocaleString()}</td><td>€0.02</td></tr>
                    <tr><td>2023 Restructured (Plan)</td><td>€${rev23.toLocaleString()}</td><td>€${cogs23.toLocaleString()}</td><td>€${opex23.toLocaleString()}</td><td style="color:${prof23 >= 0 ? 'var(--success)' : 'var(--danger)'};">€${prof23.toLocaleString()}</td><td>€${unitProf.toFixed(2)}</td></tr>
                `;
    
                const fb = document.getElementById('s4-dist-feedback');
                if (unitProf >= 0.30) {
                    fb.innerHTML = `Plan successfully achieves <strong>€${unitProf.toFixed(2)}/unit profit</strong>, meeting target.`;
                    fb.style.color = 'var(--success)';
                } else {
                    fb.innerHTML = `Plan yields <strong>€${unitProf.toFixed(2)}/unit profit</strong>, failing to meet €0.30 target. Reduce orders/load costs further.`;
                    fb.style.color = 'var(--warning)';
                }
            }

    window.UI.calculateS4Distribution = calculateS4Distribution;
    window.calculateS4Distribution = calculateS4Distribution;

    function calculateVariances() {
                const bpDM = parseFloat(document.getElementById('s5-bp-dm').value) || 0;
                const apDM = parseFloat(document.getElementById('s5-ap-dm').value) || 0;
                const sqDM = parseFloat(document.getElementById('s5-sq-dm').value) || 0;
                const aqDM = parseFloat(document.getElementById('s5-aq-dm').value) || 0;
    
                const bpDL = parseFloat(document.getElementById('s5-bp-dl').value) || 0;
                const apDL = parseFloat(document.getElementById('s5-ap-dl').value) || 0;
                const sqDL = parseFloat(document.getElementById('s5-sq-dl').value) || 0;
                const aqDL = parseFloat(document.getElementById('s5-aq-dl').value) || 0;
    
                const volBudget = parseFloat(document.getElementById('s5-vol-budget').value) || 0;
                const volActual = parseFloat(document.getElementById('s5-vol-actual').value) || 0;
    
                const dmPrice = (bpDM - apDM) * aqDM;
                const dmEff = (volActual * sqDM - aqDM) * bpDM;
                const dlPrice = (bpDL - apDL) * aqDL;
                const dlEff = (volActual * sqDL - aqDL) * bpDL;
    
                const render = (id, val) => {
                    const el = document.getElementById(id);
                    el.innerText = `€${Math.abs(val).toFixed(2)} ${val >= 0 ? 'F' : 'U'}`;
                    el.style.color = val >= 0 ? 'var(--success)' : 'var(--danger)';
                };
    
                render('s5-res-dm-price', dmPrice);
                render('s5-res-dm-eff', dmEff);
                render('s5-res-dm-total', dmPrice + dmEff);
                render('s5-res-dl-price', dlPrice);
                render('s5-res-dl-eff', dlEff);
                render('s5-res-dl-total', dlPrice + dlEff);
    
                const fbv = (dmPrice + dmEff) + (dlPrice + dlEff);
                const svv = (volBudget - volActual) * ((sqDM * bpDM) + (sqDL * bpDL));
                render('s5-res-fbv', fbv);
                render('s5-res-svv', svv);
                render('s5-res-sbv', fbv + svv);
            }

    window.UI.calculateVariances = calculateVariances;
    window.calculateVariances = calculateVariances;

    function setArenaMode(mode) {
        currentArenaMode = mode;
        document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.mode-content-container').forEach(c => c.style.display = 'none');
        document.getElementById('mode-tab-' + mode).classList.add('active');
        document.getElementById('arena-' + mode + '-mode').style.display = 'block';

        if (mode === 'learn') loadLearnTopic();
        else if (mode === 'practice' && window.exitActivePractice) window.exitActivePractice();
        else if (mode === 'exam' && window.exitExamReview) window.exitExamReview();
    }

    window.UI.setArenaMode = setArenaMode;
    window.setArenaMode = setArenaMode;

    function setLearnFlowStep(step) {
                currentLearnStep = step;
                document.querySelectorAll('.lesson-step-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.lesson-step-content').forEach(c => c.classList.remove('active'));
                document.getElementById('lst-' + step).classList.add('active');
                document.getElementById('lsc-' + step).classList.add('active');
                renderLearnStep();
            }

    window.UI.setLearnFlowStep = setLearnFlowStep;
    window.setLearnFlowStep = setLearnFlowStep;

    var currentLearnSlideIdx = 0;
    var currentSlideQuiz = null;
    // Slide quiz completion state is read from/written to stats.answeredQuizzes to survive reloads and prevent XP farming



    function generateHeuristicQuiz(session, page, text) {
        const textLower = text.toLowerCase();
        
        if (textLower.includes("fifo") || textLower.includes("process costing")) {
            return {
                q: "Based on this slide, what is a key focus of process costing or FIFO equivalent units?",
                opts: [
                    "Isolating current-period work separate from opening WIP.",
                    "Tracking individual custom job orders separately.",
                    "Applying overhead using a single storewide rate."
                ],
                correct: 0,
                reason: "Process costing applies costs to homogeneous products, with FIFO specifically isolating current work."
            };
        }
        if (textLower.includes("variance") || textLower.includes("budget")) {
            return {
                q: "According to this slide's budget and variance principles, why do we analyze variances?",
                opts: [
                    "To match financial accounting compliance regulations.",
                    "To isolate performance differences and identify pricing/efficiency deviations.",
                    "To guarantee profit levels are always met."
                ],
                correct: 1,
                reason: "Variance analysis isolates deviations between actual and standard costs to pinpoint areas of concern."
            };
        }
        if (textLower.includes("overhead") || textLower.includes("rate") || textLower.includes("allocation")) {
            return {
                q: "What is a main purpose of cost allocation bases and rates described here?",
                opts: [
                    "To assign indirect costs to products in a reasonable, systematic manner.",
                    "To eliminate fixed costs entirely.",
                    "To trace direct costs physically."
                ],
                correct: 0,
                reason: "Allocation bases are used to distribute indirect costs (overhead) to products based on cause-and-effect drivers."
            };
        }
        if (textLower.includes("breakeven") || textLower.includes("cvp")) {
            return {
                q: "What is a core objective of Cost-Volume-Profit (CVP) analysis on this slide?",
                opts: [
                    "To calculate total actual overhead spending.",
                    "To understand how profit behaves under different prices, volumes, and cost structures.",
                    "To comply with corporate tax guidelines."
                ],
                correct: 1,
                reason: "CVP analysis models the relationships between costs, volume, selling prices, and operating profit."
            };
        }
        if (textLower.includes("abc") || textLower.includes("activity-based")) {
            return {
                q: "What represents a fundamental difference of Activity-Based Costing (ABC) over traditional systems?",
                opts: [
                    "ABC traces costs to activities first, and then to products using multiple drivers.",
                    "ABC simplifies overhead into a single volume-based rate.",
                    "ABC focuses solely on direct materials."
                ],
                correct: 0,
                reason: "ABC traces overhead to individual activity cost pools and allocates them via cost drivers, reducing distortion."
            };
        }
        
        return {
            q: "Which of the following describes the cost management principle discussed on this page?",
            opts: [
                "Calculating costs accurately to support manager decision-making.",
                "Filing historical financial statements for external audit review.",
                "Using static budgets exclusively without adjustments."
            ],
            correct: 0,
            reason: "Management cost systems focus on providing timely, accurate details to support internal decision-making."
        };
    }

    function highlightKeyPhrases(text) {
        const terms = [
            "direct material", "direct labour", "flexible budget", "price variance", "efficiency variance",
            "process costing", "equivalent units", "contribution margin", "breakeven", "activity-based",
            "cross-subsidization", "allocation rate", "indirect cost", "fixed cost", "variable cost"
        ];
        let highlighted = text;
        terms.forEach(t => {
            const regex = new RegExp("\\b" + t + "\\b", "gi");
            highlighted = highlighted.replace(regex, match => `<strong style="color:var(--accent-primary); border-bottom: 1px dotted var(--accent-primary);">${match}</strong>`);
        });
        return highlighted;
    }

    function renderInteractiveSlideViewer(container) {
        if (!container) return;
        
        const sessionMap = {
            's1-concepts': 1,
            's2-fifo': 2,
            's3-cvp': 3,
            's4-abc': 4,
            's5-variance': 5
        };
        const sNum = sessionMap[currentLearnTopic] || 1;
        
        if (!window.Storage || !window.Storage.knowledgeBase || !window.Storage.knowledgeBase.rawPages) {
            container.innerHTML = `<p style="color:var(--danger);">Error: PDF Slide Database not loaded.</p>`;
            return;
        }
        
        const pages = window.Storage.knowledgeBase.rawPages.filter(p => p.session === sNum);
        if (pages.length === 0) {
            container.innerHTML = `<p style="color:var(--danger);">Error: No slides found for Session ${sNum}.</p>`;
            return;
        }
        
        if (currentLearnSlideIdx >= pages.length) {
            currentLearnSlideIdx = 0;
        }
        
        const slide = pages[currentLearnSlideIdx];
        const quizKey = `${sNum}_${slide.page}`;
        const quizzes = (window.Storage && window.Storage.knowledgeBase) ? window.Storage.knowledgeBase.slideQuizzes : {};
        currentSlideQuiz = quizzes[quizKey] || generateHeuristicQuiz(sNum, slide.page, slide.text);
        
        let quizHTML = "";
        stats.answeredQuizzes = stats.answeredQuizzes || {};
        const quizCompleted = stats.answeredQuizzes[quizKey] && (stats.answeredQuizzes[quizKey] === true || stats.answeredQuizzes[quizKey].completed);
        
        if (quizCompleted) {
            quizHTML = `
                <div style="background-color: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.2); padding: 12px; border-radius: 6px; margin-top: 15px;">
                    <div style="color:#10b981; font-weight:700; font-size:12px; margin-bottom:4px;">✓ Quiz Completed (+5 XP Awarded)</div>
                    <div style="color:white; font-size:12px; font-weight:600; margin-bottom:4px;">${currentSlideQuiz.q}</div>
                    <div style="font-size:11.5px; color:var(--text-secondary); font-style:italic;"><strong>Correct Answer:</strong> ${currentSlideQuiz.opts[currentSlideQuiz.correct]}</div>
                    <div style="font-size:11.5px; color:var(--text-secondary); margin-top:4px;"><strong>Explanation:</strong> ${currentSlideQuiz.reason}</div>
                </div>
            `;
        } else {
            quizHTML = `
                <div id="learn-slide-quiz-panel" style="display:none; background-color: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.2); padding: 12px; border-radius: 6px; margin-top: 15px;">
                    <h4 style="color:white; font-size:12px; margin-top:0; margin-bottom:8px;" id="lsq-question">${currentSlideQuiz.q}</h4>
                    <div style="display:flex; flex-direction:column; gap:8px;" id="lsq-options">
                        ${currentSlideQuiz.opts.map((opt, oIdx) => `
                            <label style="font-size:11.5px; color:var(--text-secondary); display:flex; align-items:center; gap:6px; cursor:pointer;">
                                <input type="radio" name="slide-quiz-opt" value="${oIdx}"> ${opt}
                            </label>
                        `).join('')}
                    </div>
                    <button class="btn btn-primary" onclick="submitSlideQuiz()" style="font-size:11px; padding:4px 10px; margin-top:10px; background-color:#10b981; border-color:#10b981; color:white; font-weight:700;">Submit Answer</button>
                    <div id="lsq-feedback" style="margin-top:8px; font-size:11px; font-weight:600;"></div>
                </div>
            `;
        }

        container.innerHTML = `
            <div class="slide-deck-container" style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 16px; border-radius: 8px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:8px;">
                    <span style="font-weight:700; color:var(--accent-primary);" id="learn-slide-title">${slide.sessionTitle} | Slide Page</span>
                    <span style="font-size:11px; color:var(--text-secondary);" id="learn-slide-pages">${slide.page} / ${pages.length}</span>
                </div>
                
                <div style="min-height:120px; font-size:12.5px; color:white; line-height:1.6; margin-bottom:16px;" id="learn-slide-text">
                    ${highlightKeyPhrases(slide.text)}
                </div>
                
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <button class="btn btn-secondary" onclick="prevLearnSlide()" style="font-size:11px; padding:5px 10px;" ${currentLearnSlideIdx === 0 ? 'disabled' : ''}>Previous</button>
                    ${!quizCompleted ? `<button class="btn btn-primary" id="lsq-quiz-btn" onclick="showSlideQuiz()" style="font-size:11px; padding:5px 10px; background-color:#3b82f6; border-color:#3b82f6; color:white; font-weight:700;">Quiz Me</button>` : ''}
                    <button class="btn btn-secondary" onclick="nextLearnSlide()" style="font-size:11px; padding:5px 10px;" ${currentLearnSlideIdx === pages.length - 1 ? 'disabled' : ''}>Next</button>
                </div>
                
                <div id="lsq-quiz-container">
                    ${quizHTML}
                </div>
            </div>
        `;
    }

    function prevLearnSlide() {
        if (currentLearnSlideIdx > 0) {
            currentLearnSlideIdx--;
            const concept = document.getElementById('lsc-concept');
            renderInteractiveSlideViewer(concept);
        }
    }

    function nextLearnSlide() {
        const sessionMap = {
            's1-concepts': 1,
            's2-fifo': 2,
            's3-cvp': 3,
            's4-abc': 4,
            's5-variance': 5
        };
        const sNum = sessionMap[currentLearnTopic] || 1;
        const pages = window.Storage.knowledgeBase.rawPages.filter(p => p.session === sNum);
        
        if (currentLearnSlideIdx < pages.length - 1) {
            currentLearnSlideIdx++;
            const concept = document.getElementById('lsc-concept');
            renderInteractiveSlideViewer(concept);
        }
    }

    function showSlideQuiz() {
        const panel = document.getElementById('learn-slide-quiz-panel');
        const btn = document.getElementById('lsq-quiz-btn');
        if (panel) panel.style.display = 'block';
        if (btn) btn.style.display = 'none';
    }

    function submitSlideQuiz() {
        const selected = document.querySelector('input[name="slide-quiz-opt"]:checked');
        const feedback = document.getElementById('lsq-feedback');
        if (!selected) {
            alert("Please select an option before submitting!");
            return;
        }
        const userVal = parseInt(selected.value);
        if (userVal === currentSlideQuiz.correct) {
            feedback.innerHTML = `<span style="color:var(--success);">Correct! ✓ ${currentSlideQuiz.reason}</span>`;
            feedback.style.color = 'var(--success)';
            
            const sessionMap = {
                's1-concepts': 1,
                's2-fifo': 2,
                's3-cvp': 3,
                's4-abc': 4,
                's5-variance': 5
            };
            const sNum = sessionMap[currentLearnTopic] || 1;
            const pages = window.Storage.knowledgeBase.rawPages.filter(p => p.session === sNum);
            const slide = pages[currentLearnSlideIdx];
            const quizKey = `${sNum}_${slide.page}`;
            
            stats.answeredQuizzes = stats.answeredQuizzes || {};
            const completedState = stats.answeredQuizzes[quizKey];
            const isAlreadyCompleted = completedState && (completedState === true || completedState.completed);
            if (!isAlreadyCompleted) {
                stats.answeredQuizzes[quizKey] = {
                    completed: true,
                    timestamp: Date.now()
                };
                stats.xp += 5;
                if (window.UI && window.UI.appUI && window.UI.appUI.updateAllUI) {
                    window.UI.appUI.updateAllUI();
                } else if (window.updateAllUI) {
                    window.updateAllUI();
                }
                saveStats();
            }
        } else {
            feedback.innerHTML = `<span style="color:var(--danger);">Incorrect. Try again!</span>`;
            feedback.style.color = 'var(--danger)';
        }
    }

    window.UI.prevLearnSlide = prevLearnSlide;
    window.prevLearnSlide = prevLearnSlide;
    window.UI.nextLearnSlide = nextLearnSlide;
    window.nextLearnSlide = nextLearnSlide;
    window.UI.showSlideQuiz = showSlideQuiz;
    window.showSlideQuiz = showSlideQuiz;
    window.UI.submitSlideQuiz = submitSlideQuiz;
    window.submitSlideQuiz = submitSlideQuiz;

    function goToLearnSlide(sessionKey, pageNum) {
        switchTab('practice-arena');
        setArenaMode('learn');
        const select = document.getElementById('learn-session-select');
        if (select) {
            select.value = sessionKey;
            loadLearnTopic();
            currentLearnSlideIdx = pageNum - 1;
            setLearnFlowStep('concept');
            renderInteractiveSlideViewer(document.getElementById('lsc-concept'));
        }
    }
    window.UI.goToLearnSlide = goToLearnSlide;
    window.goToLearnSlide = goToLearnSlide;

    function loadWorkedExample(topic) {
        const sessionMap = {
            'concepts': 's1-concepts',
            'costing': 's2-fifo',
            'fifo': 's2-fifo',
            'cvp': 's3-cvp',
            'abc': 's4-abc',
            'variance': 's5-variance',
            's1-concepts': 's1-concepts',
            's2-fifo': 's2-fifo',
            's3-cvp': 's3-cvp',
            's4-abc': 's4-abc',
            's5-variance': 's5-variance'
        };
        const key = sessionMap[topic] || topic;
        const lesson = (window.Storage && window.Storage.knowledgeBase && window.Storage.knowledgeBase.lessons) ? window.Storage.knowledgeBase.lessons[key] : null;
        if (!lesson) return;

        const prompt = document.getElementById('prac-question-prompt');
        if (prompt) {
            prompt.style.display = 'block';
            prompt.innerHTML = `
                <div class="card" style="background-color: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.2); padding: 16px; border-radius: 8px;">
                    <h3 style="color: var(--accent-primary); font-size: 15px; margin-top: 0; margin-bottom: 8px;">Worked Example: ${lesson.title}</h3>
                    <div style="font-size: 13px; color: white; line-height: 1.5; margin-bottom: 12px;">
                        ${lesson.worked}
                    </div>
                    <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4; border-top: 1px solid var(--border-color); padding-top: 10px;">
                        <strong>Concept Note:</strong> ${lesson.concept}
                    </div>
                </div>
            `;
        }

        const diagPanel = document.getElementById('prac-diagram-panel');
        if (diagPanel) diagPanel.style.display = 'none';

        const scaffoldPanel = document.getElementById('prac-scaffold-panel');
        if (scaffoldPanel) scaffoldPanel.style.display = 'none';

        const pretestPanel = document.getElementById('retrieval-pretest-panel');
        if (pretestPanel) pretestPanel.style.display = 'none';

        const activeButtons = document.getElementById('prac-active-buttons');
        if (activeButtons) {
            activeButtons.style.display = 'flex';
            activeButtons.innerHTML = `
                <button class="btn btn-primary" onclick="exitActivePractice()" style="font-size:12px; padding:6px 12px;">Return to Practice Lobby</button>
            `;
        }
    }
    window.UI.loadWorkedExample = loadWorkedExample;
    window.loadWorkedExample = loadWorkedExample;

    function renderCpcSlides(topic) {
        const sessionMap = {
            'concepts': 1,
            'costing': 2,
            'fifo': 2,
            'cvp': 3,
            'abc': 4,
            'variance': 5
        };
        const sessionNum = sessionMap[topic] || 1;
        const pages = (window.Storage && window.Storage.knowledgeBase && window.Storage.knowledgeBase.rawPages) ?
            window.Storage.knowledgeBase.rawPages.filter(p => p.session === sessionNum) : [];

        const prompt = document.getElementById('prac-question-prompt');
        if (prompt) {
            prompt.style.display = 'block';
            let slidesHtml = pages.map(p => `
                <div style="background-color: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-color); padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--accent-primary); margin-bottom: 4px;">Page ${p.page}: ${p.sessionTitle}</div>
                    <div style="font-size: 12px; color: white; line-height: 1.4;">${p.text}</div>
                </div>
            `).join('');

            prompt.innerHTML = `
                <div class="card" style="background-color: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.2); padding: 16px; border-radius: 8px;">
                    <h3 style="color: var(--danger); font-size: 15px; margin-top: 0; margin-bottom: 8px;">Concept Review: ${topic.toUpperCase()}</h3>
                    <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">This concept is currently unstable. Please review the slides below to stabilize your knowledge before practicing.</p>
                    <div style="max-height: 350px; overflow-y: auto; padding-right: 6px; margin-bottom: 12px; border: 1px solid var(--border-color); padding: 8px; border-radius: 6px; background-color: var(--bg-primary);">
                        ${slidesHtml}
                    </div>
                </div>
            `;
        }

        const diagPanel = document.getElementById('prac-diagram-panel');
        if (diagPanel) diagPanel.style.display = 'none';

        const scaffoldPanel = document.getElementById('prac-scaffold-panel');
        if (scaffoldPanel) scaffoldPanel.style.display = 'none';

        const pretestPanel = document.getElementById('retrieval-pretest-panel');
        if (pretestPanel) pretestPanel.style.display = 'none';

        const activeButtons = document.getElementById('prac-active-buttons');
        if (activeButtons) {
            activeButtons.style.display = 'flex';
            activeButtons.innerHTML = `
                <button class="btn btn-primary" onclick="exitActivePractice()" style="font-size:12px; padding:6px 12px;">Return to Practice Lobby</button>
            `;
        }
    }
    window.UI.renderCpcSlides = renderCpcSlides;
    window.renderCpcSlides = renderCpcSlides;

    function revealGuidedSolution(topic, step) {
        if (topic === 's1-concepts') {
            if (step === 1) {
                document.getElementById('gc-s1-di').value = 'D';
                document.getElementById('gc-s1-fv').value = 'F';
                verifyGC(1);
            } else if (step === 2) {
                document.getElementById('gc-s2-di').value = 'I';
                document.getElementById('gc-s2-fv').value = 'V';
                verifyGC(2);
            } else if (step === 3) {
                document.getElementById('gc-s3-di').value = 'D';
                document.getElementById('gc-s3-fv').value = 'F';
                verifyGC(3);
            }
        } else if (topic === 's2-fifo') {
            if (step === 1) {
                document.getElementById('gf-s1-dm').value = 7.2;
                document.getElementById('gf-s1-conv').value = 3.6;
                verifyGF(1);
            } else if (step === 2) {
                document.getElementById('gf-s2-dm').value = 46;
                document.getElementById('gf-s2-conv').value = 46.4;
                verifyGF(2);
            } else if (step === 3) {
                document.getElementById('gf-s3-dm').value = 700000;
                document.getElementById('gf-s3-conv').value = 300000;
                verifyGF(3);
            }
        } else if (topic === 's3-cvp') {
            if (step === 1) {
                document.getElementById('gcvp-s1').value = 1.8;
                verifyGCVP(1);
            } else if (step === 2) {
                document.getElementById('gcvp-s2').value = 100;
                verifyGCVP(2);
            } else if (step === 3) {
                document.getElementById('gcvp-s3').value = 90;
                verifyGCVP(3);
            }
        } else if (topic === 's4-abc') {
            if (step === 1) {
                document.getElementById('gabc-s1').value = 43.33;
                verifyGABC(1);
            } else if (step === 2) {
                document.getElementById('gabc-s2').value = 41.67;
                verifyGABC(2);
            } else if (step === 3) {
                document.getElementById('gabc-s3').value = 31.79;
                verifyGABC(3);
            }
        } else if (topic === 's5-variance') {
            if (step === 1) {
                document.getElementById('g-s1').value = 6000;
                verifyGVariance(1);
            } else if (step === 2) {
                document.getElementById('g-s2').value = 2900;
                document.getElementById('g-s2-eff').value = 'F';
                verifyGVariance(2);
            } else if (step === 3) {
                document.getElementById('g-s3').value = 3000;
                document.getElementById('g-s3-eff').value = 'F';
                verifyGVariance(3);
            }
        }
    }
    window.UI.revealGuidedSolution = revealGuidedSolution;
    window.revealGuidedSolution = revealGuidedSolution;

    function loadLearnTopic() {
        currentLearnTopic = document.getElementById('learn-session-select').value;
        currentLearnSlideIdx = 0; // Reset slide index when changing session topic
        setLearnFlowStep('concept');
    }

    window.UI.loadLearnTopic = loadLearnTopic;
    window.loadLearnTopic = loadLearnTopic;

    function renderLearnStep() {
        const concept = document.getElementById('lsc-concept');
        const diagram = document.getElementById('lsc-diagram');
        const worked = document.getElementById('lsc-worked');
        const guided = document.getElementById('lsc-guided');

        const data = (window.Storage && window.Storage.knowledgeBase && window.Storage.knowledgeBase.lessons) ? window.Storage.knowledgeBase.lessons[currentLearnTopic] : null;
        if (!data) return;

        // Render Slide deck viewer for theory
        renderInteractiveSlideViewer(concept);
        
        diagram.innerHTML = data.diagram;
        worked.innerHTML = data.worked;

        if (currentLearnStep === 'guided') {
            if (currentLearnTopic === 's1-concepts') initializeGuidedConcepts(guided);
            else if (currentLearnTopic === 's2-fifo') initializeGuidedFifo(guided);
            else if (currentLearnTopic === 's3-cvp') initializeGuidedCvp(guided);
            else if (currentLearnTopic === 's4-abc') initializeGuidedAbc(guided);
            else if (currentLearnTopic === 's5-variance') initializeGuidedVariance(guided);
        }
    }

    window.UI.renderLearnStep = renderLearnStep;
    window.renderLearnStep = renderLearnStep;

    function initializeGuidedConcepts(container) {
                guidedState = { step: 1 };
                renderGuidedConcepts(container);
            }

    window.UI.initializeGuidedConcepts = initializeGuidedConcepts;
    window.initializeGuidedConcepts = initializeGuidedConcepts;

    function renderGuidedConcepts(container) {
                let html = `
                    <h3 style="font-size:15px; color:white; margin-bottom:8px;">Guided Practice: Cost Classification</h3>
                    <p>Let's classify costs for Crescendo Store's film section step-by-step.</p>
                    <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                        <div style="font-size:13px; font-weight:600; margin-bottom:4px;">1) Annual retainer paid to film distributor:</div>
                        <div style="display:flex; flex-direction:column; gap:8px;">
                            <div>
                                Direct or Indirect?
                                <select class="form-input" id="gc-s1-di" style="width:auto; display:inline-block; margin-left:8px;" ${guidedState.step > 1 ? 'disabled' : ''}>
                                    <option value="">--</option><option value="D" ${guidedState.step > 1 ? 'selected' : ''}>Direct (D)</option><option value="I">Indirect (I)</option>
                                </select>
                            </div>
                            <div>
                                Fixed or Variable?
                                <select class="form-input" id="gc-s1-fv" style="width:auto; display:inline-block; margin-left:8px;" ${guidedState.step > 1 ? 'disabled' : ''}>
                                    <option value="">--</option><option value="F" ${guidedState.step > 1 ? 'selected' : ''}>Fixed (F)</option><option value="V">Variable (V)</option>
                                </select>
                                ${guidedState.step === 1 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px; margin-left:8px;" onclick="verifyGC(1)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s1-concepts\', 1)">Reveal Solution</button>' : '✅'}
                            </div>
                        </div>
                    </div>
                `;
                if (guidedState.step >= 2) {
                    html += `
                        <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                            <div style="font-size:13px; font-weight:600; margin-bottom:4px;">2) Electricity costs of the entire store (single bill):</div>
                            <div style="display:flex; flex-direction:column; gap:8px;">
                                <div>
                                    Direct or Indirect?
                                    <select class="form-input" id="gc-s2-di" style="width:auto; display:inline-block; margin-left:8px;" ${guidedState.step > 2 ? 'disabled' : ''}>
                                        <option value="">--</option><option value="D">Direct (D)</option><option value="I" ${guidedState.step > 2 ? 'selected' : ''}>Indirect (I)</option>
                                    </select>
                                </div>
                                <div>
                                    Fixed or Variable?
                                    <select class="form-input" id="gc-s2-fv" style="width:auto; display:inline-block; margin-left:8px;" ${guidedState.step > 2 ? 'disabled' : ''}>
                                        <option value="">--</option><option value="F">Fixed (F)</option><option value="V" ${guidedState.step > 2 ? 'selected' : ''}>Variable (V)</option>
                                    </select>
                                    ${guidedState.step === 2 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px; margin-left:8px;" onclick="verifyGC(2)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s1-concepts\', 2)">Reveal Solution</button>' : '✅'}
                                </div>
                            </div>
                        </div>
                    `;
                }
                if (guidedState.step >= 3) {
                    html += `
                        <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                            <div style="font-size:13px; font-weight:600; margin-bottom:4px;">3) Subscription to Video-Novo magazine (for film section):</div>
                            <div style="display:flex; flex-direction:column; gap:8px;">
                                <div>
                                    Direct or Indirect?
                                    <select class="form-input" id="gc-s3-di" style="width:auto; display:inline-block; margin-left:8px;" ${guidedState.step > 3 ? 'disabled' : ''}>
                                        <option value="">--</option><option value="D" ${guidedState.step > 3 ? 'selected' : ''}>Direct (D)</option><option value="I">Indirect (I)</option>
                                    </select>
                                </div>
                                <div>
                                    Fixed or Variable?
                                    <select class="form-input" id="gc-s3-fv" style="width:auto; display:inline-block; margin-left:8px;" ${guidedState.step > 3 ? 'disabled' : ''}>
                                        <option value="">--</option><option value="F" ${guidedState.step > 3 ? 'selected' : ''}>Fixed (F)</option><option value="V">Variable (V)</option>
                                    </select>
                                    ${guidedState.step === 3 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px; margin-left:8px;" onclick="verifyGC(3)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s1-concepts\', 3)">Reveal Solution</button>' : '✅'}
                                </div>
                            </div>
                        </div>
                    `;
                }
                if (guidedState.step === 4) {
                    html += `<div class="alert alert-success">Cost Classification Tutorial completed! +50 XP unlocked. Mastery concepts increased by +20%!</div>`;
                }
                container.innerHTML = html;
            }

    window.UI.renderGuidedConcepts = renderGuidedConcepts;
    window.renderGuidedConcepts = renderGuidedConcepts;

    function verifyGC(step) {
                if (step === 1) {
                    const di = document.getElementById('gc-s1-di').value;
                    const fv = document.getElementById('gc-s1-fv').value;
                    if (di === 'D' && fv === 'F') { guidedState.step = 2; }
                    else alert("Incorrect. Distributor retainer is direct to movie section and fixed.");
                } else if (step === 2) {
                    const di = document.getElementById('gc-s2-di').value;
                    const fv = document.getElementById('gc-s2-fv').value;
                    if (di === 'I' && fv === 'V') { guidedState.step = 3; }
                    else alert("Incorrect. Store electricity bill is shared (indirect) and varies with usage.");
                } else if (step === 3) {
                    const di = document.getElementById('gc-s3-di').value;
                    const fv = document.getElementById('gc-s3-fv').value;
                    if (di === 'D' && fv === 'F') {
                        guidedState.step = 4;
                        stats.xp += 50; stats.masteryConcepts = Math.min(100, stats.masteryConcepts + 20);
                        saveStats();
                    } else alert("Incorrect. Department magazine is direct and subscription fee is fixed.");
                }
                renderGuidedConcepts(document.getElementById('lsc-guided'));
            }

    window.UI.verifyGC = verifyGC;
    window.verifyGC = verifyGC;

    function initializeGuidedFifo(container) {
                guidedState = { step: 1 };
                renderGuidedFifo(container);
            }

    window.UI.initializeGuidedFifo = initializeGuidedFifo;
    window.initializeGuidedFifo = initializeGuidedFifo;

    function renderGuidedFifo(container) {
                let html = `
                    <h3 style="font-size:15px; color:white; margin-bottom:8px;">Guided Practice: Aéro-France FIFO Process Costing</h3>
                    <p>Let's calculate the Equivalent Units and cost/EU step-by-step.</p>
                    <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                        <div style="font-size:13px; font-weight:600; margin-bottom:4px;">1) Calculate Closing WIP Equivalent Units:</div>
                        <p>Closing WIP has 12 physical units (60% DM completed, 30% Conversion completed).</p>
                        <div style="display:flex; flex-direction:column; gap:8px;">
                            <div>
                                Closing WIP DM EU (12 × 0.6) = 
                                <input type="number" class="form-input" id="gf-s1-dm" style="max-width:80px; display:inline-block;" step="0.1" ${guidedState.step > 1 ? 'disabled value="7.2"' : ''}>
                            </div>
                            <div>
                                Closing WIP Conversion EU (12 × 0.3) = 
                                <input type="number" class="form-input" id="gf-s1-conv" style="max-width:80px; display:inline-block;" step="0.1" ${guidedState.step > 1 ? 'disabled value="3.6"' : ''}>
                                ${guidedState.step === 1 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px; margin-left:8px;" onclick="verifyGF(1)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s2-fifo\', 1)">Reveal Solution</button>' : '✅'}
                            </div>
                        </div>
                    </div>
                `;
                if (guidedState.step >= 2) {
                    html += `
                        <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                            <div style="font-size:13px; font-weight:600; margin-bottom:4px;">2) Calculate work done in current period (FIFO Equivalent Units):</div>
                            <p>Formula: Current Work EU = Units Completed (46) + Closing WIP EU - Opening WIP EU (8 units: 90% DM, 40% Conversion).</p>
                            <div style="display:flex; flex-direction:column; gap:8px;">
                                <div>
                                    Current DM EU = 46 + 7.2 - (8 × 0.9 = 7.2) = 
                                    <input type="number" class="form-input" id="gf-s2-dm" style="max-width:80px; display:inline-block;" step="0.1" ${guidedState.step > 2 ? 'disabled value="46"' : ''}>
                                </div>
                                <div>
                                    Current Conversion EU = 46 + 3.6 - (8 × 0.4 = 3.2) = 
                                    <input type="number" class="form-input" id="gf-s2-conv" style="max-width:80px; display:inline-block;" step="0.1" ${guidedState.step > 2 ? 'disabled value="46.4"' : ''}>
                                    ${guidedState.step === 2 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px; margin-left:8px;" onclick="verifyGF(2)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s2-fifo\', 2)">Reveal Solution</button>' : '✅'}
                                </div>
                            </div>
                        </div>
                    `;
                }
                if (guidedState.step >= 3) {
                    html += `
                        <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                            <div style="font-size:13px; font-weight:600; margin-bottom:4px;">3) Calculate Current Period Cost per EU:</div>
                            <p>Costs added: DM €32,200,000 | Conversion €13,920,000. Divide by current period EUs from step 2.</p>
                            <div style="display:flex; flex-direction:column; gap:8px;">
                                <div>
                                    Cost per DM EU = €32,200,000 / 46 = €
                                    <input type="number" class="form-input" id="gf-s3-dm" style="max-width:100px; display:inline-block;" ${guidedState.step > 3 ? 'disabled value="700000"' : ''}>
                                </div>
                                <div>
                                    Cost per Conversion EU = €13,920,000 / 46.4 = €
                                    <input type="number" class="form-input" id="gf-s3-conv" style="max-width:100px; display:inline-block;" ${guidedState.step > 3 ? 'disabled value="300000"' : ''}>
                                    ${guidedState.step === 3 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px; margin-left:8px;" onclick="verifyGF(3)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s2-fifo\', 3)">Reveal Solution</button>' : '✅'}
                                </div>
                            </div>
                        </div>
                    `;
                }
                if (guidedState.step === 4) {
                    html += `<div class="alert alert-success">FIFO Process Costing Tutorial completed! +50 XP unlocked. Job & Process Costing mastery increased by +20%!</div>`;
                }
                container.innerHTML = html;
            }

    window.UI.renderGuidedFifo = renderGuidedFifo;
    window.renderGuidedFifo = renderGuidedFifo;

    function verifyGF(step) {
                if (step === 1) {
                    const dm = parseFloat(document.getElementById('gf-s1-dm').value);
                    const conv = parseFloat(document.getElementById('gf-s1-conv').value);
                    if (Math.abs(dm - 7.2) < 0.1 && Math.abs(conv - 3.6) < 0.1) { guidedState.step = 2; }
                    else alert("Incorrect. DM WIP EU = 12 * 0.6 = 7.2. Conv WIP EU = 12 * 0.3 = 3.6.");
                } else if (step === 2) {
                    const dm = parseFloat(document.getElementById('gf-s2-dm').value);
                    const conv = parseFloat(document.getElementById('gf-s2-conv').value);
                    if (Math.abs(dm - 46) < 0.1 && Math.abs(conv - 46.4) < 0.1) { guidedState.step = 3; }
                    else alert("Incorrect. DM = 46 + 7.2 - 7.2 = 46. Conv = 46 + 3.6 - 3.2 = 46.4.");
                } else if (step === 3) {
                    const dm = parseFloat(document.getElementById('gf-s3-dm').value);
                    const conv = parseFloat(document.getElementById('gf-s3-conv').value);
                    if (Math.abs(dm - 700000) < 1 && Math.abs(conv - 300000) < 1) {
                        guidedState.step = 4;
                        stats.xp += 50; stats.masteryCosting = Math.min(100, stats.masteryCosting + 20);
                        saveStats();
                    } else alert("Incorrect. Cost/DM EU = 32,200,000 / 46 = €700,000. Cost/Conv EU = 13,920,000 / 46.4 = €300,000.");
                }
                renderGuidedFifo(document.getElementById('lsc-guided'));
            }

    window.UI.verifyGF = verifyGF;
    window.verifyGF = verifyGF;

    function initializeGuidedCvp(container) {
                guidedState = { step: 1 };
                renderGuidedCvp(container);
            }

    window.UI.initializeGuidedCvp = initializeGuidedCvp;
    window.initializeGuidedCvp = initializeGuidedCvp;

    function renderGuidedCvp(container) {
                let html = `
                    <h3 style="font-size:15px; color:white; margin-bottom:8px;">Guided Practice: CVP & Bottlenecks</h3>
                    <p>Let's calculate CVP and capacity constraints step-by-step.</p>
                    <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                        <div style="font-size:13px; font-weight:600; margin-bottom:4px;">1) Calculate Contribution Margin per Unit:</div>
                        <p>Selling price = €3.00, Variable Cost = €1.20, Fixed Costs = €180.00.</p>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span>CM per unit = Price - VC = €</span>
                            <input type="number" class="form-input" id="gcvp-s1" style="max-width:80px; display:inline-block;" step="0.01" ${guidedState.step > 1 ? 'disabled value="1.80"' : ''}>
                            ${guidedState.step === 1 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px;" onclick="verifyGCVP(1)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s3-cvp\', 1)">Reveal Solution</button>' : '✅'}
                        </div>
                    </div>
                `;
                if (guidedState.step >= 2) {
                    html += `
                        <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                            <div style="font-size:13px; font-weight:600; margin-bottom:4px;">2) Calculate Breakeven Volume:</div>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span>Breakeven = Fixed Costs / CM per unit = </span>
                                <input type="number" class="form-input" id="gcvp-s2" style="max-width:80px; display:inline-block;" step="1" ${guidedState.step > 2 ? 'disabled value="100"' : ''}><span>units</span>
                                ${guidedState.step === 2 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px;" onclick="verifyGCVP(2)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s3-cvp\', 2)">Reveal Solution</button>' : '✅'}
                            </div>
                        </div>
                    `;
                }
                if (guidedState.step >= 3) {
                    html += `
                        <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                            <div style="font-size:13px; font-weight:600; margin-bottom:4px;">3) Calculate Operating Profit at 150 units sales:</div>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span>Profit = (Sales × CM) - Fixed Costs = €</span>
                                <input type="number" class="form-input" id="gcvp-s3" style="max-width:100px; display:inline-block;" step="0.01" ${guidedState.step > 3 ? 'disabled value="90"' : ''}>
                                ${guidedState.step === 3 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px;" onclick="verifyGCVP(3)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s3-cvp\', 3)">Reveal Solution</button>' : '✅'}
                            </div>
                        </div>
                    `;
                }
                if (guidedState.step === 4) {
                    html += `<div class="alert alert-success">CVP & Bottlenecks Tutorial completed! +50 XP unlocked. CVP mastery increased by +20%!</div>`;
                }
                container.innerHTML = html;
            }

    window.UI.renderGuidedCvp = renderGuidedCvp;
    window.renderGuidedCvp = renderGuidedCvp;

    function verifyGCVP(step) {
                if (step === 1) {
                    const val = parseFloat(document.getElementById('gcvp-s1').value);
                    if (Math.abs(val - 1.8) < 0.05) { guidedState.step = 2; }
                    else alert("Incorrect. CM per unit = €3.00 - €1.20 = €1.80.");
                } else if (step === 2) {
                    const val = parseFloat(document.getElementById('gcvp-s2').value);
                    if (Math.abs(val - 100) < 0.1) { guidedState.step = 3; }
                    else alert("Incorrect. Breakeven volume = €180.00 / €1.80 = 100 units.");
                } else if (step === 3) {
                    const val = parseFloat(document.getElementById('gcvp-s3').value);
                    if (Math.abs(val - 90) < 0.1) {
                        guidedState.step = 4;
                        stats.xp += 50; stats.masteryCvp = Math.min(100, stats.masteryCvp + 20);
                        saveStats();
                    } else alert("Incorrect. Profit = (150 * €1.80) - €180 = €90.00.");
                }
                renderGuidedCvp(document.getElementById('lsc-guided'));
            }

    window.UI.verifyGCVP = verifyGCVP;
    window.verifyGCVP = verifyGCVP;

    function initializeGuidedAbc(container) {
                guidedState = { step: 1 };
                renderGuidedAbc(container);
            }

    window.UI.initializeGuidedAbc = initializeGuidedAbc;
    window.initializeGuidedAbc = initializeGuidedAbc;

    function renderGuidedAbc(container) {
                let html = `
                    <h3 style="font-size:15px; color:white; margin-bottom:8px;">Guided Practice: Activity-Based Costing</h3>
                    <p>Let's compute traditional vs. ABC unit costs step-by-step.</p>
                    <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                        <div style="font-size:13px; font-weight:600; margin-bottom:4px;">1) Calculate Traditional Overhead allocation rate:</div>
                        <p>Total overhead = Setup pool €450,000 + Delivery pool €200,000 = €650,000. Total units = 15,000 units.</p>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span>Rate per unit = €650,000 / 15,000 = €</span>
                            <input type="number" class="form-input" id="gabc-s1" style="max-width:80px; display:inline-block;" step="0.01" ${guidedState.step > 1 ? 'disabled value="43.33"' : ''}>
                            ${guidedState.step === 1 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px;" onclick="verifyGABC(1)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s4-abc\', 1)">Reveal Solution</button>' : '✅'}
                        </div>
                    </div>
                `;
                if (guidedState.step >= 2) {
                    html += `
                        <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                            <div style="font-size:13px; font-weight:600; margin-bottom:4px;">2) Calculate Setup Cost Driver rate (ABC):</div>
                            <p>Setup pool = €450,000. Total machine hours = 10,800 hours.</p>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span>Rate per machine hour = €450,000 / 10,800 = €</span>
                                <input type="number" class="form-input" id="gabc-s2" style="max-width:80px; display:inline-block;" step="0.01" ${guidedState.step > 2 ? 'disabled value="41.67"' : ''}>
                                ${guidedState.step === 2 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px; margin-left:8px;" onclick="verifyGABC(2)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s4-abc\', 2)">Reveal Solution</button>' : '✅'}
                            </div>
                        </div>
                    `;
                }
                if (guidedState.step >= 3) {
                    html += `
                        <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                            <div style="font-size:13px; font-weight:600; margin-bottom:4px;">3) Calculate ABC Overhead per unit for Titan Throne:</div>
                            <p>Titan Throne uses 3,000 machine hours, 40 shipments. Delivery rate = €689.66/shipment. Titan Throne volume = 4,800 units.</p>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span>ABC OH/unit = ((3,000 × 41.67) + (40 × 689.66)) / 4,800 = €</span>
                                <input type="number" class="form-input" id="gabc-s3" style="max-width:100px; display:inline-block;" step="0.01" ${guidedState.step > 3 ? 'disabled value="31.79"' : ''}>
                                ${guidedState.step === 3 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px; margin-left:8px;" onclick="verifyGABC(3)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s4-abc\', 3)">Reveal Solution</button>' : '✅'}
                            </div>
                        </div>
                    `;
                }
                if (guidedState.step === 4) {
                    html += `<div class="alert alert-success">ABC Costing Tutorial completed! +50 XP unlocked. ABC mastery increased by +20%!</div>`;
                }
                container.innerHTML = html;
            }

    window.UI.renderGuidedAbc = renderGuidedAbc;
    window.renderGuidedAbc = renderGuidedAbc;

    function verifyGABC(step) {
                if (step === 1) {
                    const val = parseFloat(document.getElementById('gabc-s1').value);
                    if (Math.abs(val - 43.33) < 0.05) { guidedState.step = 2; }
                    else alert("Incorrect. Traditional rate = €650,000 / 15,000 = €43.33.");
                } else if (step === 2) {
                    const val = parseFloat(document.getElementById('gabc-s2').value);
                    if (Math.abs(val - 41.67) < 0.05) { guidedState.step = 3; }
                    else alert("Incorrect. Setup rate = €450,000 / 10,800 = €41.67.");
                } else if (step === 3) {
                    const val = parseFloat(document.getElementById('gabc-s3').value);
                    if (Math.abs(val - 31.79) < 0.05) {
                        guidedState.step = 4;
                        stats.xp += 50; stats.masteryAbc = Math.min(100, stats.masteryAbc + 20);
                        saveStats();
                    } else alert("Incorrect. ABC Overhead = (3,000 * 41.67 + 40 * 689.66) / 4,800 = €31.79.");
                }
                renderGuidedAbc(document.getElementById('lsc-guided'));
            }

    window.UI.verifyGABC = verifyGABC;
    window.verifyGABC = verifyGABC;

    function initializeGuidedVariance(container) {
                guidedState = { step: 1, vol: 3000, sq: 2, sp: 15, aq: 5800, ap: 14.50 };
                renderGuidedVariance(container);
            }

    window.UI.initializeGuidedVariance = initializeGuidedVariance;
    window.initializeGuidedVariance = initializeGuidedVariance;

    function renderGuidedVariance(container) {
                let html = `
                    <h3 style="font-size:15px; color:white; margin-bottom:8px;">Guided intermediate steps: DM price & efficiency variances</h3>
                    <p>Standard allowed inputs: 2.0 kg/unit at €15/kg. Actual: 3,000 units made. Used 5,800 kg costing €14.50/kg.</p>
                    <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                        <div style="font-size:13px; font-weight:600; margin-bottom:4px;">1) Calculate Standard Quantity Allowed ($SQ$)</div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span>3,000 units × 2.0 kg = </span>
                            <input type="number" class="form-input" id="g-s1" style="max-width:100px;" ${guidedState.step > 1 ? 'disabled value="6000"' : ''}><span>kg</span>
                            ${guidedState.step === 1 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px;" onclick="verifyGVariance(1)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s5-variance\', 1)">Reveal Solution</button>' : '✅'}
                        </div>
                    </div>
                `;
                if (guidedState.step >= 2) {
                    html += `
                        <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                            <div style="font-size:13px; font-weight:600; margin-bottom:4px;">2) DM Price Variance: $(SP - AP) \times AQ$</div>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span>(€15.00 - €14.50) × 5,800 kg = €</span>
                                <input type="number" class="form-input" id="g-s2" style="max-width:100px;" ${guidedState.step > 2 ? 'disabled value="2900"' : ''}>
                                <select class="form-input" id="g-s2-eff" style="width:auto;" ${guidedState.step > 2 ? 'disabled' : ''}>
                                    <option value="">--</option><option value="F" ${guidedState.step > 2 ? 'selected' : ''}>F</option><option value="U">U</option>
                                </select>
                                ${guidedState.step === 2 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px;" onclick="verifyGVariance(2)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s5-variance\', 2)">Reveal Solution</button>' : '✅'}
                            </div>
                        </div>
                    `;
                }
                if (guidedState.step >= 3) {
                    html += `
                        <div class="card" style="background-color:var(--bg-primary); margin-bottom:10px;">
                            <div style="font-size:13px; font-weight:600; margin-bottom:4px;">3) DM Efficiency Variance: $(SQ - AQ) \times SP$</div>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span>(6,000 kg - 5,800 kg) × €15.00 = €</span>
                                <input type="number" class="form-input" id="g-s3" style="max-width:100px;" ${guidedState.step > 3 ? 'disabled value="3000"' : ''}>
                                <select class="form-input" id="g-s3-eff" style="width:auto;" ${guidedState.step > 3 ? 'disabled' : ''}>
                                    <option value="">--</option><option value="F" ${guidedState.step > 3 ? 'selected' : ''}>F</option><option value="U">U</option>
                                </select>
                                ${guidedState.step === 3 ? '<button class="btn btn-primary" style="padding:4px 8px; font-size:11px;" onclick="verifyGVariance(3)">Check</button><button class="btn btn-secondary" style="padding:4px 8px; font-size:11px; margin-left:4px; border-color:var(--warning); color:var(--warning);" onclick="revealGuidedSolution(\'s5-variance\', 3)">Reveal Solution</button>' : '✅'}
                            </div>
                        </div>
                    `;
                }
                if (guidedState.step === 4) {
                    html += `<div class="alert alert-success">Variance Analysis Tutorial completed! +50 XP unlocked. Variance mastery increased by +20%!</div>`;
                }
                container.innerHTML = html;
            }

    window.UI.renderGuidedVariance = renderGuidedVariance;
    window.renderGuidedVariance = renderGuidedVariance;

    function verifyGVariance(step) {
                if (step === 1) {
                    if (parseFloat(document.getElementById('g-s1').value) === 6000) guidedState.step = 2;
                    else alert("Incorrect. 3,000 units * 2 kg = 6,000 kg.");
                } else if (step === 2) {
                    const val = parseFloat(document.getElementById('g-s2').value);
                    const eff = document.getElementById('g-s2-eff').value;
                    if (val === 2900 && eff === 'F') guidedState.step = 3;
                    else alert("Incorrect. Price variance = €0.50 savings/kg * 5,800 kg = €2,900 F.");
                } else if (step === 3) {
                    const val = parseFloat(document.getElementById('g-s3').value);
                    const eff = document.getElementById('g-s3-eff').value;
                    if (val === 3000 && eff === 'F') {
                        guidedState.step = 4;
                        stats.xp += 50; stats.masteryVariance = Math.min(100, stats.masteryVariance + 20);
                        saveStats();
                    } else alert("Incorrect. Efficiency variance = 200 kg saved * €15/kg = €3,000 F.");
                }
                renderGuidedVariance(document.getElementById('lsc-guided'));
            }

    window.UI.verifyGVariance = verifyGVariance;
    window.verifyGVariance = verifyGVariance;

    function renderDynamicDiagram(category, templateId, mathDetails, containerId, correctAnswers) {
                const container = document.getElementById(containerId);
                if (!container) return;
                if (!mathDetails) {
                    container.style.display = 'none';
                    return;
                }
                container.style.display = 'block';
                let svg = '';
                const cAnswers = correctAnswers || (currentPracProblem ? currentPracProblem.correctAnswers : {});
                
                if (category === 'concepts') {
                    if (templateId === 0) {
                        const isDirect = cAnswers.q1_di === 'D';
                        const isFixed = cAnswers.q1_vf === 'F';
                        svg = `
                            <h4 style="color: white; font-size:12px; margin-bottom:10px;">Visual Coding: 2x2 Cost Classification Matrix</h4>
                            <p style="font-size:11px; margin-bottom:8px;">Item: <strong>"${mathDetails.itemName}"</strong> is highlighted in the correct quadrant:</p>
                            <svg width="320" height="180" viewBox="0 0 320 180" class="diagram-svg">
                                <text x="110" y="20" fill="var(--text-secondary)" font-size="10" text-anchor="middle">Variable</text>
                                <text x="230" y="20" fill="var(--text-secondary)" font-size="10" text-anchor="middle">Fixed</text>
                                <text x="30" y="65" fill="var(--text-secondary)" font-size="10" text-anchor="end">Direct</text>
                                <text x="30" y="130" fill="var(--text-secondary)" font-size="10" text-anchor="end">Indirect</text>
                                <rect x="50" y="35" width="120" height="55" fill="${isDirect && !isFixed ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255,255,255,0.02)'}" stroke="${isDirect && !isFixed ? 'var(--accent-primary)' : 'var(--border-color)'}" stroke-width="${isDirect && !isFixed ? 2 : 1}" rx="4"/>
                                <text x="110" y="65" fill="${isDirect && !isFixed ? 'white' : 'var(--text-muted)'}" font-size="9" text-anchor="middle">Direct & Variable</text>
                                <rect x="180" y="35" width="120" height="55" fill="${isDirect && isFixed ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255,255,255,0.02)'}" stroke="${isDirect && isFixed ? 'var(--accent-primary)' : 'var(--border-color)'}" stroke-width="${isDirect && isFixed ? 2 : 1}" rx="4"/>
                                <text x="240" y="65" fill="${isDirect && isFixed ? 'white' : 'var(--text-muted)'}" font-size="9" text-anchor="middle">Direct & Fixed</text>
                                <rect x="50" y="100" width="120" height="55" fill="${!isDirect && !isFixed ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255,255,255,0.02)'}" stroke="${!isDirect && !isFixed ? 'var(--accent-primary)' : 'var(--border-color)'}" stroke-width="${!isDirect && !isFixed ? 2 : 1}" rx="4"/>
                                <text x="110" y="130" fill="${!isDirect && !isFixed ? 'white' : 'var(--text-muted)'}" font-size="9" text-anchor="middle">Indirect & Variable</text>
                                <rect x="180" y="100" width="120" height="55" fill="${!isDirect && isFixed ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255,255,255,0.02)'}" stroke="${!isDirect && isFixed ? 'var(--accent-primary)' : 'var(--border-color)'}" stroke-width="${!isDirect && isFixed ? 2 : 1}" rx="4"/>
                                <text x="240" y="130" fill="${!isDirect && isFixed ? 'white' : 'var(--text-muted)'}" font-size="9" text-anchor="middle">Indirect & Fixed</text>
                            </svg>
                        `;
                    } else if (templateId === 1) {
                        const ff = mathDetails.fixedFee;
                        const p1 = mathDetails.p1;
                        const p2 = mathDetails.p2;
                        const u1 = (ff / p1).toFixed(2);
                        const u2 = (ff / p2).toFixed(2);
                        svg = `
                            <h4 style="color: white; font-size:12px; margin-bottom:10px;">Visual Coding: Fixed Cost Behavior Graph</h4>
                            <p style="font-size:11px; margin-bottom:8px;">Flat gold line is Total Cost. Blue curve is Unit Cost per person.</p>
                            <svg width="340" height="180" viewBox="0 0 340 180" class="diagram-svg">
                                <line x1="40" y1="20" x2="320" y2="20" stroke="var(--border-color)" stroke-dasharray="2,2"/>
                                <line x1="40" y1="75" x2="320" y2="75" stroke="var(--border-color)" stroke-dasharray="2,2"/>
                                <line x1="40" y1="130" x2="320" y2="130" stroke="var(--border-color)" stroke-dasharray="2,2"/>
                                <line x1="40" y1="15" x2="40" y2="150" stroke="var(--text-muted)" stroke-width="1.5"/>
                                <line x1="40" y1="150" x2="320" y2="150" stroke="var(--text-muted)" stroke-width="1.5"/>
                                <text x="320" y="165" fill="var(--text-secondary)" font-size="9" text-anchor="end">Attendance</text>
                                <text x="35" y="25" fill="var(--text-secondary)" font-size="9" text-anchor="end">Cost (€)</text>
                                <line x1="40" y1="50" x2="300" y2="50" stroke="var(--warning)" stroke-width="2"/>
                                <text x="305" y="48" fill="var(--warning)" font-size="9" font-weight="700">Total: €${ff.toLocaleString()}</text>
                                <path d="M 50 140 Q 100 85 290 60" fill="none" stroke="var(--accent-primary)" stroke-width="2.5"/>
                                <circle cx="100" cy="95" r="4.5" fill="var(--success)" stroke="white" stroke-width="1"/>
                                <text x="105" y="90" fill="white" font-size="8" font-weight="700">S1: ${p1} people (€${u1}/ea)</text>
                                <circle cx="240" cy="65" r="4.5" fill="var(--success)" stroke="white" stroke-width="1"/>
                                <text x="245" y="60" fill="white" font-size="8" font-weight="700">S2: ${p2} people (€${u2}/ea)</text>
                            </svg>
                        `;
                    } else if (templateId === 2) {
                        const ans = cAnswers.func;
                        svg = `
                            <h4 style="color: white; font-size:12px; margin-bottom:10px;">Visual Coding: Information Flow & Accountant Roles</h4>
                            <svg width="340" height="100" viewBox="0 0 340 100" class="diagram-svg">
                                <line x1="90" y1="45" x2="120" y2="45" stroke="var(--border-color)" stroke-width="2"/>
                                <line x1="210" y1="45" x2="240" y2="45" stroke="var(--border-color)" stroke-width="2"/>
                                <rect x="10" y="25" width="80" height="40" fill="${ans === 'SK' ? 'rgba(99, 102, 241, 0.25)' : 'rgba(255,255,255,0.02)'}" stroke="${ans === 'SK' ? 'var(--accent-primary)' : 'var(--border-color)'}" stroke-width="${ans === 'SK' ? 2 : 1}" rx="4"/>
                                <text x="50" y="44" fill="${ans === 'SK' ? 'white' : 'var(--text-muted)'}" font-size="9" font-weight="700" text-anchor="middle">Scorekeeping</text>
                                <text x="50" y="55" fill="var(--text-muted)" font-size="7" text-anchor="middle">Record Data</text>
                                <rect x="130" y="25" width="80" height="40" fill="${ans === 'AD' ? 'rgba(99, 102, 241, 0.25)' : 'rgba(255,255,255,0.02)'}" stroke="${ans === 'AD' ? 'var(--accent-primary)' : 'var(--border-color)'}" stroke-width="${ans === 'AD' ? 2 : 1}" rx="4"/>
                                <text x="170" y="44" fill="${ans === 'AD' ? 'white' : 'var(--text-muted)'}" font-size="9" font-weight="700" text-anchor="middle">Attention Directing</text>
                                <text x="170" y="55" fill="var(--text-muted)" font-size="7" text-anchor="middle">Spot Anomalies</text>
                                <rect x="250" y="25" width="80" height="40" fill="${ans === 'PS' ? 'rgba(99, 102, 241, 0.25)' : 'rgba(255,255,255,0.02)'}" stroke="${ans === 'PS' ? 'var(--accent-primary)' : 'var(--border-color)'}" stroke-width="${ans === 'PS' ? 2 : 1}" rx="4"/>
                                <text x="290" y="44" fill="${ans === 'PS' ? 'white' : 'var(--text-muted)'}" font-size="9" font-weight="700" text-anchor="middle">Problem Solving</text>
                                <text x="290" y="55" fill="var(--text-muted)" font-size="7" text-anchor="middle">Make Decisions</text>
                            </svg>
                        `;
                    }
                } else if (category === 'fifo') {
                    if (templateId === 0) {
                        const op = mathDetails.opUnits;
                        const comp = mathDetails.completed;
                        const cl = mathDetails.clUnits;
                        svg = `
                            <h4 style="color: white; font-size:12px; margin-bottom:10px;">Visual Coding: FIFO Work Distribution Pipeline</h4>
                            <p style="font-size:11px; margin-bottom:8px;">FIFO counts only current period work. We complete opening WIP, do started/completed, and start closing WIP.</p>
                            <svg width="340" height="150" viewBox="0 0 340 150" class="diagram-svg">
                                <rect x="10" y="25" width="90" height="60" fill="rgba(245, 158, 11, 0.08)" stroke="var(--warning)" stroke-width="1" rx="4"/>
                                <text x="55" y="45" fill="white" font-size="9" font-weight="700" text-anchor="middle">Opening WIP (${op} u)</text>
                                <text x="55" y="60" fill="var(--text-secondary)" font-size="8" text-anchor="middle">DM Work: ${(100 - mathDetails.opDmPct*100)}%</text>
                                <text x="55" y="72" fill="var(--text-secondary)" font-size="8" text-anchor="middle">Conv Work: ${(100 - mathDetails.opConvPct*100)}%</text>
                                <rect x="115" y="25" width="110" height="60" fill="rgba(16, 185, 129, 0.08)" stroke="var(--success)" stroke-width="1.5" rx="4"/>
                                <text x="170" y="45" fill="white" font-size="9" font-weight="700" text-anchor="middle">Started & Comp (${comp - op} u)</text>
                                <text x="170" y="60" fill="var(--text-secondary)" font-size="8" text-anchor="middle">DM Work: 100%</text>
                                <text x="170" y="72" fill="var(--text-secondary)" font-size="8" text-anchor="middle">Conv Work: 100%</text>
                                <rect x="240" y="25" width="90" height="60" fill="rgba(99, 102, 241, 0.08)" stroke="var(--accent-primary)" stroke-width="1" rx="4"/>
                                <text x="285" y="45" fill="white" font-size="9" font-weight="700" text-anchor="middle">Closing WIP (${cl} u)</text>
                                <text x="285" y="60" fill="var(--text-secondary)" font-size="8" text-anchor="middle">DM Work: ${mathDetails.clDmPct*100}%</text>
                                <text x="285" y="72" fill="var(--text-secondary)" font-size="8" text-anchor="middle">Conv Work: ${mathDetails.clConvPct*100}%</text>
                                <path d="M 55 95 L 55 110 L 285 110 L 285 95" fill="none" stroke="var(--text-muted)" stroke-width="1"/>
                                <text x="170" y="130" fill="white" font-size="9.5" font-weight="700" text-anchor="middle">
                                    DM EU: ${(comp - op)} + (${cl} × ${mathDetails.clDmPct}) + (${op} × ${(1 - mathDetails.opDmPct).toFixed(1)}) = ${mathDetails.currDmEU.toFixed(1)} EU
                                </text>
                            </svg>
                        `;
                    } else if (templateId === 1) {
                        const rB = mathDetails.rateBillable;
                        const rT = mathDetails.rateTotal;
                        const ratio = (rT / rB * 100).toFixed(0);
                        svg = `
                            <h4 style="color: white; font-size:12px; margin-bottom:10px;">Visual Coding: Billing Rate Comparison (Denominator Choices)</h4>
                            <svg width="340" height="120" viewBox="0 0 340 120" class="diagram-svg">
                                <text x="10" y="25" fill="white" font-size="9" font-weight="700">Scenario 1 (Billable Hours only)</text>
                                <rect x="10" y="30" width="200" height="15" fill="var(--accent-primary)" rx="3"/>
                                <text x="215" y="42" fill="white" font-size="10" font-weight="700">€${rB.toFixed(2)}/hr</text>
                                <text x="10" y="65" fill="white" font-size="9" font-weight="700">Scenario 2 (Total Budgeted Hours)</text>
                                <rect x="10" y="70" width="${ratio * 2}" height="15" fill="var(--text-muted)" rx="3"/>
                                <text x="${ratio * 2 + 25}" y="82" fill="white" font-size="10" font-weight="700">€${rT.toFixed(2)}/hr</text>
                                <text x="10" y="105" fill="var(--warning)" font-size="8">Scenario 1 is higher because non-billable overhead is loaded onto client hours.</text>
                            </svg>
                        `;
                    } else if (templateId === 2) {
                        const rate = mathDetails.ohRate;
                        const allocated = mathDetails.ohAllocated;
                        const actual = mathDetails.actualOH;
                        const diff = mathDetails.ohDiff;
                        const isOver = diff >= 0;
                        svg = `
                            <h4 style="color: white; font-size:12px; margin-bottom:10px;">Visual Coding: Overhead Allocation Balance Scale</h4>
                            <svg width="340" height="140" viewBox="0 0 340 140" class="diagram-svg">
                                <line x1="80" y1="${isOver ? 70 : 50}" x2="260" y2="${isOver ? 50 : 70}" stroke="white" stroke-width="3"/>
                                <line x1="170" y1="40" x2="170" y2="100" stroke="var(--text-muted)" stroke-width="2"/>
                                <polygon points="160,100 180,100 170,85" fill="var(--text-muted)"/>
                                <line x1="80" y1="${isOver ? 70 : 50}" x2="80" y2="${isOver ? 100 : 80}" stroke="var(--border-color)"/>
                                <rect x="40" y="${isOver ? 100 : 80}" width="80" height="20" fill="var(--bg-secondary)" stroke="var(--danger)" rx="3"/>
                                <text x="80" y="${isOver ? 113 : 93}" fill="white" font-size="8.5" text-anchor="middle">Actual: €${actual.toLocaleString()}</text>
                                <line x1="260" y1="${isOver ? 50 : 70}" x2="260" y2="${isOver ? 80 : 100}" stroke="var(--border-color)"/>
                                <rect x="220" y="${isOver ? 80 : 100}" width="80" height="20" fill="var(--bg-secondary)" stroke="var(--success)" rx="3"/>
                                <text x="260" y="${isOver ? 93 : 113}" fill="white" font-size="8.5" text-anchor="middle">Alloc: €${Math.round(allocated).toLocaleString()}</text>
                                <text x="170" y="130" fill="${isOver ? 'var(--success)' : 'var(--danger)'}" font-size="10.5" font-weight="700" text-anchor="middle">
                                    ${isOver ? 'OVER-ALLOCATED' : 'UNDER-ALLOCATED'} by €${Math.abs(Math.round(diff)).toLocaleString()}
                                </text>
                            </svg>
                        `;
                    }
                } else if (category === 'cvp') {
                    if (templateId === 0) {
                        const price = mathDetails.price;
                        const vc = mathDetails.vc;
                        const fc = mathDetails.fc;
                        const be = mathDetails.be;
                        svg = `
                            <h4 style="color: white; font-size:12px; margin-bottom:10px;">Visual Coding: Dynamic CVP Breakeven Graph</h4>
                            <svg width="340" height="180" viewBox="0 0 340 180" class="diagram-svg">
                                <line x1="35" y1="10" x2="35" y2="150" stroke="var(--text-muted)" stroke-width="1.5"/>
                                <line x1="35" y1="150" x2="310" y2="150" stroke="var(--text-muted)" stroke-width="1.5"/>
                                <text x="310" y="165" fill="var(--text-secondary)" font-size="8.5" text-anchor="end">Volume (Units)</text>
                                <text x="30" y="15" fill="var(--text-secondary)" font-size="8.5" text-anchor="end">Revenue/Costs (€)</text>
                                <line x1="35" y1="110" x2="280" y2="110" stroke="var(--warning)" stroke-width="1.5" stroke-dasharray="3,3"/>
                                <text x="285" y="113" fill="var(--warning)" font-size="7.5">FC: €${fc.toLocaleString()}</text>
                                <line x1="35" y1="110" x2="260" y2="40" stroke="#3b82f6" stroke-width="2"/>
                                <line x1="35" y1="150" x2="260" y2="20" stroke="#10b981" stroke-width="2"/>
                                <circle cx="140" cy="89" r="4.5" fill="var(--warning)" stroke="white" stroke-width="1.5"/>
                                <line x1="140" y1="89" x2="140" y2="150" stroke="var(--text-muted)" stroke-dasharray="2,2"/>
                                <text x="140" y="162" fill="var(--warning)" font-size="8.5" font-weight="700" text-anchor="middle">BEP: ${be}</text>
                                <text x="265" y="22" fill="#10b981" font-size="8.5" font-weight="700">Revenue</text>
                                <text x="265" y="42" fill="#3b82f6" font-size="8.5" font-weight="700">Total Cost</text>
                            </svg>
                        `;
                    } else if (templateId === 1) {
                        svg = `
                            <h4 style="color: white; font-size:12px; margin-bottom:10px;">Visual Coding: Constrained Bottleneck Analysis</h4>
                            <p style="font-size:11px; margin-bottom:8px;">Cola capacity is <strong>${mathDetails.casesPerMeter} cases/meter</strong>, yielding <strong>€${mathDetails.cmMeter.toFixed(2)} CM</strong> per daily meter.</p>
                            <svg width="340" height="90" viewBox="0 0 340 90" class="diagram-svg">
                                <rect x="20" y="20" width="300" height="30" fill="rgba(255,255,255,0.02)" stroke="white" stroke-width="1" rx="3"/>
                                <rect x="25" y="25" width="30" height="20" fill="var(--accent-primary)" rx="2"/>
                                <rect x="60" y="25" width="30" height="20" fill="var(--accent-primary)" rx="2"/>
                                <rect x="95" y="25" width="30" height="20" fill="var(--accent-primary)" rx="2"/>
                                <text x="145" y="38" fill="var(--text-secondary)" font-size="8">...</text>
                                <rect x="250" y="25" width="30" height="20" fill="var(--accent-primary)" rx="2"/>
                                <rect x="285" y="25" width="30" height="20" fill="var(--accent-primary)" rx="2"/>
                                <text x="170" y="38" fill="white" font-size="9.5" font-weight="700" text-anchor="middle">${mathDetails.casesPerMeter} Cases/meter</text>
                                <text x="170" y="70" fill="var(--success)" font-size="10.5" font-weight="700" text-anchor="middle">
                                    CM: €${mathDetails.cmCase.toFixed(2)}/case × ${mathDetails.casesPerMeter} cases = €${mathDetails.cmMeter.toFixed(2)}/meter/day
                                </text>
                            </svg>
                        `;
                    }
                } else if (category === 'abc') {
                    if (templateId === 0) {
                        svg = `
                            <h4 style="color: white; font-size:12px; margin-bottom:10px;">Visual Coding: Traditional (Single Pool) vs. ABC (Traced Drivers)</h4>
                            <svg width="340" height="150" viewBox="0 0 340 150" class="diagram-svg">
                                <rect x="10" y="25" width="85" height="30" fill="rgba(99, 102, 241, 0.15)" stroke="var(--accent-primary)" rx="3"/>
                                <text x="52.5" y="43" fill="white" font-size="8" font-weight="700" text-anchor="middle">Setups: €${mathDetails.setupPool.toLocaleString()}</text>
                                <rect x="10" y="85" width="85" height="30" fill="rgba(99, 102, 241, 0.15)" stroke="var(--accent-primary)" rx="3"/>
                                <text x="52.5" y="103" fill="white" font-size="8" font-weight="700" text-anchor="middle">Delivery: €${mathDetails.delPool.toLocaleString()}</text>
                                <text x="165" y="33" fill="var(--text-secondary)" font-size="7.5" text-anchor="middle">Setup Hours</text>
                                <text x="165" y="42" fill="white" font-size="7" text-anchor="middle">(${mathDetails.setupsA + mathDetails.setupsB} hrs)</text>
                                <line x1="95" y1="40" x2="135" y2="40" stroke="var(--border-color)" stroke-width="1"/>
                                <text x="165" y="93" fill="var(--text-secondary)" font-size="7.5" text-anchor="middle">Shipments</text>
                                <text x="165" y="102" fill="white" font-size="7" text-anchor="middle">(${mathDetails.delA + mathDetails.delB} ships)</text>
                                <line x1="95" y1="100" x2="135" y2="100" stroke="var(--border-color)" stroke-width="1"/>
                                <rect x="235" y="25" width="90" height="30" fill="rgba(16, 185, 129, 0.1)" stroke="var(--success)" rx="3"/>
                                <text x="280" y="43" fill="white" font-size="8" font-weight="700" text-anchor="middle">Premium (Titan)</text>
                                <rect x="235" y="85" width="90" height="30" fill="rgba(16, 185, 129, 0.1)" stroke="var(--success)" rx="3"/>
                                <text x="280" y="103" fill="white" font-size="8" font-weight="700" text-anchor="middle">Basic (Arena)</text>
                                <line x1="195" y1="40" x2="235" y2="40" stroke="var(--accent-primary)" stroke-width="1.5"/>
                                <line x1="195" y1="40" x2="235" y2="95" stroke="var(--border-color)" stroke-width="1" stroke-dasharray="2,2"/>
                                <line x1="195" y1="100" x2="235" y2="45" stroke="var(--border-color)" stroke-width="1" stroke-dasharray="2,2"/>
                                <line x1="195" y1="100" x2="235" y2="100" stroke="var(--accent-primary)" stroke-width="1.5"/>
                                <text x="170" y="137" fill="var(--warning)" font-size="7.5" text-anchor="middle">ABC traces overhead based on usage, avoiding traditional volume distortion.</text>
                            </svg>
                        `;
                    } else if (templateId === 1) {
                        svg = `
                            <h4 style="color: white; font-size:12px; margin-bottom:10px;">Visual Coding: Logistics Restructuring Cost Structure</h4>
                            <svg width="340" height="110" viewBox="0 0 340 110" class="diagram-svg">
                                <text x="10" y="20" fill="white" font-size="9" font-weight="700">Budget Structure (€${mathDetails.rev.toLocaleString()} Revenue)</text>
                                <rect x="20" y="30" width="${(mathDetails.cogs/mathDetails.rev * 300).toFixed(0)}" height="20" fill="var(--danger)" rx="2"/>
                                <rect x="${(20 + mathDetails.cogs/mathDetails.rev * 300).toFixed(0)}" y="30" width="${(mathDetails.opex/mathDetails.rev * 300).toFixed(0)}" height="20" fill="var(--warning)" rx="2"/>
                                <rect x="${(20 + (mathDetails.cogs + mathDetails.opex)/mathDetails.rev * 300).toFixed(0)}" y="30" width="${(mathDetails.profit/mathDetails.rev * 300).toFixed(0)}" height="20" fill="var(--success)" rx="2"/>
                                <rect x="20" y="65" width="8" height="8" fill="var(--danger)"/>
                                <text x="32" y="72" fill="var(--text-secondary)" font-size="8">COGS: €${mathDetails.cogs.toLocaleString()}</text>
                                <rect x="120" y="65" width="8" height="8" fill="var(--warning)"/>
                                <text x="132" y="72" fill="var(--text-secondary)" font-size="8">OPEX: €${mathDetails.opex.toLocaleString()}</text>
                                <rect x="220" y="65" width="8" height="8" fill="var(--success)"/>
                                <text x="232" y="72" fill="var(--text-secondary)" font-size="8">Profit: €${mathDetails.profit.toLocaleString()}</text>
                                <text x="20" y="95" fill="white" font-size="8.5" font-weight="700">Profit Per Tile: €${(mathDetails.profit / mathDetails.tiles).toFixed(3)}</text>
                            </svg>
                        `;
                    }
                } else if (category === 'variance') {
                    if (templateId === 0) {
                        const actCost = Math.round(mathDetails.actDM_qty * mathDetails.actDM_price);
                        const splitCost = Math.round(mathDetails.actDM_qty * mathDetails.stdDM_price);
                        const flexCost = Math.round(mathDetails.actualVol * mathDetails.stdDM_qty * mathDetails.stdDM_price);
                        const pVal = Math.round(Math.abs(mathDetails.dmPriceVar));
                        const pEff = mathDetails.dmPriceVar >= 0 ? 'F' : 'U';
                        const eVal = Math.round(Math.abs(mathDetails.dmEffVar));
                        const eEff = mathDetails.dmEffVar >= 0 ? 'F' : 'U';
                        svg = `
                            <h4 style="color: white; font-size:12px; margin-bottom:10px;">Visual Coding: 3-Column Variance Bridge (Direct Materials)</h4>
                            <svg width="340" height="150" viewBox="0 0 340 150" class="diagram-svg">
                                <rect x="10" y="25" width="85" height="50" fill="rgba(255,255,255,0.02)" stroke="var(--border-color)" rx="3"/>
                                <text x="52.5" y="42" fill="white" font-size="8.5" font-weight="700" text-anchor="middle">Actual Cost</text>
                                <text x="52.5" y="55" fill="var(--text-secondary)" font-size="7.5" text-anchor="middle">AQ × AP</text>
                                <text x="52.5" y="67" fill="white" font-size="8" font-weight="700" text-anchor="middle">€${actCost.toLocaleString()}</text>
                                <rect x="127.5" y="25" width="85" height="50" fill="rgba(255,255,255,0.02)" stroke="var(--border-color)" rx="3"/>
                                <text x="170" y="42" fill="white" font-size="8.5" font-weight="700" text-anchor="middle">Split Point</text>
                                <text x="170" y="55" fill="var(--text-secondary)" font-size="7.5" text-anchor="middle">AQ × SP</text>
                                <text x="170" y="67" fill="white" font-size="8" font-weight="700" text-anchor="middle">€${splitCost.toLocaleString()}</text>
                                <rect x="245" y="25" width="85" height="50" fill="rgba(255,255,255,0.02)" stroke="var(--border-color)" rx="3"/>
                                <text x="287.5" y="42" fill="white" font-size="8.5" font-weight="700" text-anchor="middle">Flex Budget</text>
                                <text x="287.5" y="55" fill="var(--text-secondary)" font-size="7.5" text-anchor="middle">SQ × SP</text>
                                <text x="287.5" y="67" fill="white" font-size="8" font-weight="700" text-anchor="middle">€${flexCost.toLocaleString()}</text>
                                <path d="M 52.5 80 L 52.5 95 L 170 95 L 170 80" fill="none" stroke="var(--text-muted)" stroke-width="1"/>
                                <rect x="75" y="87" width="70" height="15" fill="${pEff === 'F' ? 'var(--success-glow)' : 'var(--danger-glow)'}" stroke="${pEff === 'F' ? 'var(--success)' : 'var(--danger)'}" rx="2"/>
                                <text x="110" y="97" fill="white" font-size="8" font-weight="700" text-anchor="middle">Price: €${pVal.toLocaleString()} ${pEff}</text>
                                <path d="M 170 80 L 170 110 L 287.5 110 L 287.5 80" fill="none" stroke="var(--text-muted)" stroke-width="1"/>
                                <rect x="190" y="102" width="85" height="15" fill="${eEff === 'F' ? 'var(--success-glow)' : 'var(--danger-glow)'}" stroke="${eEff === 'F' ? 'var(--success)' : 'var(--danger)'}" rx="2"/>
                                <text x="232.5" y="112" fill="white" font-size="8" font-weight="700" text-anchor="middle">Efficiency: €${eVal.toLocaleString()} ${eEff}</text>
                            </svg>
                        `;
                    } else if (templateId === 1) {
                        svg = `
                            <h4 style="color: white; font-size:12px; margin-bottom:10px;">Visual Coding: Master Budget Prep Sequence</h4>
                            <svg width="340" height="110" viewBox="0 0 340 110" class="diagram-svg">
                                <rect x="10" y="30" width="55" height="25" fill="rgba(99, 102, 241, 0.15)" stroke="var(--accent-primary)" rx="2"/>
                                <text x="37.5" y="42" fill="white" font-size="8" font-weight="700" text-anchor="middle">1. Sales</text>
                                <line x1="65" y1="42" x2="75" y2="42" stroke="var(--border-color)" stroke-width="1.5"/>
                                <rect x="75" y="30" width="55" height="25" fill="rgba(99, 102, 241, 0.15)" stroke="var(--accent-primary)" rx="2"/>
                                <text x="102.5" y="42" fill="white" font-size="8" font-weight="700" text-anchor="middle">2. Prod</text>
                                <line x1="130" y1="42" x2="140" y2="42" stroke="var(--border-color)" stroke-width="1.5"/>
                                <rect x="140" y="30" width="55" height="25" fill="rgba(99, 102, 241, 0.15)" stroke="var(--accent-primary)" rx="2"/>
                                <text x="167.5" y="42" fill="white" font-size="8" font-weight="700" text-anchor="middle">3. DM Purch</text>
                                <line x1="195" y1="42" x2="205" y2="42" stroke="var(--border-color)" stroke-width="1.5"/>
                                <rect x="205" y="30" width="60" height="25" fill="rgba(99, 102, 241, 0.15)" stroke="var(--accent-primary)" rx="2"/>
                                <text x="235" y="42" fill="white" font-size="7.5" font-weight="700" text-anchor="middle">4. Operating</text>
                                <line x1="265" y1="42" x2="275" y2="42" stroke="var(--border-color)" stroke-width="1.5"/>
                                <rect x="275" y="30" width="55" height="25" fill="rgba(99, 102, 241, 0.15)" stroke="var(--accent-primary)" rx="2"/>
                                <text x="302.5" y="42" fill="white" font-size="8" font-weight="700" text-anchor="middle">5. Bal Sheet</text>
                                <text x="170" y="80" fill="var(--warning)" font-size="7.5" text-anchor="middle">We begin with Sales because demand dictates all downstream procurement and financing.</text>
                            </svg>
                        `;
                    }
                }
                container.innerHTML = svg;
            }

    window.UI.renderDynamicDiagram = renderDynamicDiagram;
    window.renderDynamicDiagram = renderDynamicDiagram;

    function getWalkthroughHTML(category, templateId, md, c) {
                if (!md) return "";
                let html = "";
                if (category === 'concepts') {
                    if (templateId === 0) {
                        html = `
                            <div style="display: inline-flex; align-items: center; gap: 4px; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a78bfa; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:12px; height:12px; stroke:#a78bfa;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>Seminar Reference: Session 1 Ex 2.15</div>
                            <p><strong>Cost Classification Walkthrough:</strong></p>
                            <p>Item analyzed: <strong>"${md.itemName}"</strong></p>
                            <p>Correct classifications: Assignment: <strong>${c.q1_di === 'D' ? 'Direct' : 'Indirect'}</strong> | Behavior: <strong>${c.q1_vf === 'F' ? 'Fixed' : 'Variable'}</strong>.</p>
                            <p><strong>Rationale:</strong> ${md.desc}</p>
                        `;
                    } else if (templateId === 1) {
                        html = `
                            <div style="display: inline-flex; align-items: center; gap: 4px; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a78bfa; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:12px; height:12px; stroke:#a78bfa;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.247 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>Seminar Reference: Session 1 Ex 2.11</div>
                            <p><strong>Music Group Cost Behavior Steps:</strong></p>
                            <ul>
                                <li>The fee of €${md.fixedFee.toLocaleString()} paid to the music group is a <strong>fixed cost</strong>. Therefore, total costs in both scenarios are equal to €${md.fixedFee.toLocaleString()}.</li>
                                <li>For Scenario 1 (${md.p1} people): unit cost = €${md.fixedFee.toLocaleString()} / ${md.p1} = €${c.unit500.toFixed(2)} per person.</li>
                                <li>For Scenario 2 (${md.p2} people): unit cost = €${md.fixedFee.toLocaleString()} / ${md.p2} = €${c.unit2000.toFixed(2)} per person.</li>
                                <li><strong>Takeaway:</strong> Total fixed costs remain constant, but per-unit fixed costs decrease dynamically as volume increases.</li>
                            </ul>
                        `;
                    } else if (templateId === 2) {
                        html = `
                            <div style="display: inline-flex; align-items: center; gap: 4px; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a78bfa; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:12px; height:12px; stroke:#a78bfa;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.247 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>Seminar Reference: Session 1 Ex 1.16</div>
                            <p><strong>Accountant Functions Walkthrough:</strong></p>
                            <p>Activity analyzed: <strong>"${md.text}"</strong></p>
                            <p>Correct function: <strong>${md.ansName}</strong></p>
                            <p><strong>Rationale:</strong> ${md.desc}</p>
                        `;
                    }
                } else if (category === 'abc') {
                    if (templateId === 0) {
                        html = `
                            <div style="display: inline-flex; align-items: center; gap: 4px; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a78bfa; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:12px; height:12px; stroke:#a78bfa;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.247 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>Seminar Reference: Session 4 Ex 4.2</div>
                            <p><strong>Traditional vs. ABC Allocation Walkthrough:</strong></p>
                            <ul>
                                <li>Total Overhead = €${md.setupPool.toLocaleString()} (Setup) + €${md.delPool.toLocaleString()} (Delivery) = €${md.totalOH.toLocaleString()}.</li>
                                <li>Total Volume = ${md.volA.toLocaleString()} (Premium) + ${md.volB.toLocaleString()} (Basic) = ${md.totalVol.toLocaleString()} units.</li>
                                <li>Traditional overhead rate = €${md.totalOH.toLocaleString()} / ${md.totalVol.toLocaleString()} units = €${md.tradRate.toFixed(2)}/unit.</li>
                                <li>Traditional cost Premium = DM + DL + Trad OH = €${md.dmA} + €${md.dlA} + €${md.tradRate.toFixed(2)} = €${c.tradCostA.toFixed(2)}.</li>
                                <li>Traditional cost Basic = DM + DL + Trad OH = €${md.dmB} + €${md.dlB} + €${md.tradRate.toFixed(2)} = €${c.tradCostB.toFixed(2)}.</li>
                                <li>Setup Activity Driver Rate = Setup Pool €${md.setupPool.toLocaleString()} / (${md.setupsA} + ${md.setupsB} hrs) = €${md.setupRate.toFixed(2)}/setup hour.</li>
                                <li>Delivery Activity Driver Rate = Delivery Pool €${md.delPool.toLocaleString()} / (${md.delA} + ${md.delB} shipments) = €${md.delRate.toFixed(2)}/shipment.</li>
                                <li>ABC Overhead allocated to Premium = (${md.setupsA} hrs × €${md.setupRate.toFixed(2)}) + (${md.delA} shipments × €${md.delRate.toFixed(2)}) = €${((md.setupsA * md.setupRate) + (md.delA * md.delRate)).toLocaleString()}.</li>
                                <li>ABC Overhead per Premium unit = €${((md.setupsA * md.setupRate) + (md.delA * md.delRate)).toLocaleString()} / ${md.volA.toLocaleString()} units = €${(((md.setupsA * md.setupRate) + (md.delA * md.delRate)) / md.volA).toFixed(2)}.</li>
                                <li>ABC Cost Premium = DM + DL + ABC OH/unit = €${md.dmA} + €${md.dlA} + €${(((md.setupsA * md.setupRate) + (md.delA * md.delRate)) / md.volA).toFixed(2)} = €${c.abcCostA.toFixed(2)}.</li>
                                <li>ABC Overhead allocated to Basic = (${md.setupsB} hrs × €${md.setupRate.toFixed(2)}) + (${md.delB} shipments × €${md.delRate.toFixed(2)}) = €${((md.setupsB * md.setupRate) + (md.delB * md.delRate)).toLocaleString()}.</li>
                                <li>ABC Overhead per Basic unit = €${((md.setupsB * md.setupRate) + (md.delB * md.delRate)).toLocaleString()} / ${md.volB.toLocaleString()} units = €${(((md.setupsB * md.setupRate) + (md.delB * md.delRate)) / md.volB).toFixed(2)}.</li>
                                <li>ABC Cost Basic = DM + DL + ABC OH/unit = €${md.dmB} + €${md.dlB} + €${(((md.setupsB * md.setupRate) + (md.delB * md.delRate)) / md.volB).toFixed(2)} = €${c.abcCostB.toFixed(2)}.</li>
                            </ul>
                        `;
                    } else {
                        html = `
                            <div style="display: inline-flex; align-items: center; gap: 4px; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a78bfa; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:12px; height:12px; stroke:#a78bfa;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.247 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>Seminar Reference: Session 4 Ex 12.12</div>
                            <p><strong>Logistics Restructuring Steps:</strong></p>
                            <ul>
                                <li>Calculate budgeted OPEX:
                                    <ul>
                                         <li>Ordering costs: ${md.orders} orders × €${md.orderCost} = €${(md.orders * md.orderCost).toLocaleString()}</li>
                                         <li>Loading costs: ${md.loads.toLocaleString()} loads × €${md.loadCost} = €${(md.loads * md.loadCost).toLocaleString()}</li>
                                         <li>Setup costs: ${md.setups.toLocaleString()} setups × €${md.setupCost} = €${(md.setups * md.setupCost).toLocaleString()}</li>
                                         <li>Fixed administration costs: €${md.adminFixed.toLocaleString()}</li>
                                         <li><strong>Total OPEX:</strong> €${(md.orders * md.orderCost).toLocaleString()} + €${(md.loads * md.loadCost).toLocaleString()} + €${(md.setups * md.setupCost).toLocaleString()} + €${md.adminFixed.toLocaleString()} = €${md.opex.toLocaleString()}</li>
                                    </ul>
                                </li>
                                <li>Budgeted Operating Profit = Revenue (€${md.rev.toLocaleString()}) - COGS (€${md.cogs.toLocaleString()}) - OPEX (€${md.opex.toLocaleString()}) = €${md.profit.toLocaleString()}.</li>
                                <li>Operating Profit per Tile = €${md.profit.toLocaleString()} / ${md.tiles.toLocaleString()} tiles = €${c.perTile.toFixed(3)} per tile.</li>
                            </ul>
                        `;
                    }
                } else if (category === 'variance') {
                    if (templateId === 0) {
                        html = `
                            <div style="display: inline-flex; align-items: center; gap: 4px; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a78bfa; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:12px; height:12px; stroke:#a78bfa;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.247 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>Seminar Reference: Session 5 Ex 15.23</div>
                            <p><strong>Standard Cost Variance Walkthrough:</strong></p>
                            <ul>
                                <li><strong>DM Price Variance:</strong> (Std Price - Act Price) × Act Qty = (€${md.stdDM_price.toFixed(2)} - €${md.actDM_price.toFixed(2)}) × ${md.actDM_qty.toLocaleString()} = €${Math.abs(md.dmPriceVar).toFixed(2)} ${md.dmPriceVar >= 0 ? 'Favorable (F)' : 'Unfavorable (U)'}.</li>
                                <li>Standard DM Quantity allowed for actual production = ${md.actualVol.toLocaleString()} units × ${md.stdDM_qty} rolls = ${(md.actualVol * md.stdDM_qty).toFixed(1)} rolls.</li>
                                <li><strong>DM Efficiency Variance:</strong> (Std Qty allowed - Act Qty used) × Std Price = (${(md.actualVol * md.stdDM_qty).toFixed(1)} - ${md.actDM_qty.toLocaleString()}) × €${md.stdDM_price.toFixed(2)} = €${Math.abs(md.dmEffVar).toFixed(2)} ${md.dmEffVar >= 0 ? 'Favorable (F)' : 'Unfavorable (U)'}.</li>
                                <li><strong>DL Price Variance:</strong> (Std Rate - Act Rate) × Act Hours = (€${md.stdDL_rate.toFixed(2)} - €${md.actDL_rate.toFixed(2)}) × ${md.actDL_hours.toLocaleString()} = €${Math.abs(md.dlPriceVar).toFixed(2)} ${md.dlPriceVar >= 0 ? 'Favorable (F)' : 'Unfavorable (U)'}.</li>
                                <li>Standard DL Hours allowed for actual production = ${md.actualVol.toLocaleString()} units × ${md.stdDL_hours} = ${(md.actualVol * md.stdDL_hours).toFixed(1)} hours.</li>
                                <li><strong>DL Efficiency Variance:</strong> (Std Hours allowed - Act Hours worked) × Std Rate = (${(md.actualVol * md.stdDL_hours).toFixed(1)} - ${md.actDL_hours.toLocaleString()}) × €${md.stdDL_rate.toFixed(2)} = €${Math.abs(md.dlEffVar).toFixed(2)} ${md.dlEffVar >= 0 ? 'Favorable (F)' : 'Unfavorable (U)'}.</li>
                            </ul>
                        `;
                    } else {
                        html = `
                            <div style="display: inline-flex; align-items: center; gap: 4px; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a78bfa; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:12px; height:12px; stroke:#a78bfa;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.247 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>Seminar Reference: Session 5 Ex 5.2</div>
                            <p><strong>Master Budget Sequencing Steps:</strong></p>
                            <ol>
                                <li><strong>Sales Budget (1):</strong> The starting point because sales dictate production requirements.</li>
                                <li><strong>Production Budget (2):</strong> Budgeting quantities to produce to satisfy sales demand and ending inventory targets.</li>
                                <li><strong>Direct Materials Purchases Budget (3):</strong> Computed from production requirements and raw materials inventory plans.</li>
                                <li><strong>Budgeted Operating Income Statement (4):</strong> Created by consolidating revenue, COGS, and operating expenses.</li>
                                <li><strong>Budgeted Balance Sheet (5):</strong> Created last since it relies on budgeted cash flows, earnings, and working capital details from all prior budgets.</li>
                            </ol>
                        `;
                    }
                } else if (category === 'fifo') {
                    if (templateId === 0) {
                        html = `
                            <div style="display: inline-flex; align-items: center; gap: 4px; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a78bfa; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:12px; height:12px; stroke:#a78bfa;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.247 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>Seminar Reference: Session 2 FIFO Ex 4.13</div>
                            <p><strong>FIFO Costing Steps Walkthrough:</strong></p>
                            <ul>
                                <li>Equivalent units represent work performed in the current period under FIFO.</li>
                                <li><strong>DM Equivalent Units of work done:</strong> Units Completed (${md.completed}) + Closing WIP EU (${md.clUnits} units × ${md.clDmPct*100}%) - Opening WIP EU (${md.opUnits} units × ${md.opDmPct*100}%) = ${md.completed} + ${md.clUnits * md.clDmPct} - ${md.opUnits * md.opDmPct} = <strong>${c.currDmEU.toFixed(1)} EU</strong>.</li>
                                <li><strong>Conversion Equivalent Units of work done:</strong> Units Completed (${md.completed}) + Closing WIP EU (${md.clUnits} units × ${md.clConvPct*100}%) - Opening WIP EU (${md.opUnits} units × ${md.opConvPct*100}%) = ${md.completed} + ${md.clUnits * md.clConvPct} - ${md.opUnits * md.opConvPct} = <strong>${c.currConvEU.toFixed(1)} EU</strong>.</li>
                                <li><strong>Cost per DM Equivalent Unit:</strong> Current DM Cost Added €${md.addDmCost.toLocaleString()} / ${c.currDmEU.toFixed(1)} DM EU = <strong>€${c.rateDM.toFixed(2)}/EU</strong>.</li>
                                <li><strong>Cost per Conversion Equivalent Unit:</strong> Current Conversion Cost Added €${md.addConvCost.toLocaleString()} / ${c.currConvEU.toFixed(1)} Conv EU = <strong>€${c.rateConv.toFixed(2)}/EU</strong>.</li>
                            </ul>
                        `;
                    } else if (templateId === 1) {
                        html = `
                            <div style="display: inline-flex; align-items: center; gap: 4px; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a78bfa; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:12px; height:12px; stroke:#a78bfa;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.247 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>Seminar Reference: Session 2 Ex 3.12</div>
                            <p><strong>Zimmermann Billing Rate Walkthrough:</strong></p>
                            <ul>
                                <li><strong>Scenario (1) Client Billable Hours:</strong> labor rate = €${md.salary.toLocaleString()} / ${md.billableHours.toLocaleString()} hrs = <strong>€${c.rateBillable.toFixed(2)}/hr</strong>.</li>
                                <li><strong>Scenario (2) Total Budgeted Hours:</strong> labor rate = €${md.salary.toLocaleString()} / (${md.billableHours.toLocaleString()} + ${md.leaveHours} + ${md.devHours} = ${md.totalHours.toLocaleString()} hrs) = <strong>€${c.rateTotal.toFixed(2)}/hr</strong>.</li>
                                <li>Note: Denominator choices drastically affect billing rates. Scenario 1 ensures all labor costs are recovered from billable client hours alone, loading leave and training overhead onto client rates.</li>
                            </ul>
                        `;
                    } else {
                        html = `
                            <div style="display: inline-flex; align-items: center; gap: 4px; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a78bfa; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:12px; height:12px; stroke:#a78bfa;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.247 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>Seminar Reference: Session 2 Ex 3.13</div>
                            <p><strong>Overhead Allocation Walkthrough:</strong></p>
                            <ul>
                                <li><strong>Predetermined Overhead Rate:</strong> Budgeted Overhead €${md.budgetedOH.toLocaleString()} / Budgeted Machine Hours ${md.budgetedMH.toLocaleString()} MH = <strong>€${c.ohRate.toFixed(2)}/MH</strong>.</li>
                                <li><strong>Total Overhead Allocated:</strong> Overhead Rate €${c.ohRate.toFixed(2)} × Actual Machine Hours ${md.actualMH.toLocaleString()} MH = <strong>€${c.ohAllocated.toLocaleString()}</strong>.</li>
                                <li><strong>Over- or Under-allocation Amount:</strong> Total Allocated €${c.ohAllocated.toLocaleString()} - Actual Overhead incurred €${md.actualOH.toLocaleString()} = <strong>€${c.ohDiff.toLocaleString()}</strong>. (A positive value indicates overhead is over-allocated, a negative value indicates underallocated).</li>
                            </ul>
                        `;
                    }
                } else if (category === 'cvp') {
                    if (templateId === 0) {
                        html = `
                            <div style="display: inline-flex; align-items: center; gap: 4px; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a78bfa; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:12px; height:12px; stroke:#a78bfa;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.247 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>Seminar Reference: Session 3 Ex 3.2</div>
                            <p><strong>CVP Walkthrough:</strong></p>
                            <ul>
                                <li><strong>Unit Contribution Margin (CM):</strong> Price €${md.price.toFixed(2)} - VC €${md.vc.toFixed(2)} = <strong>€${c.cmu.toFixed(2)}</strong>.</li>
                                <li><strong>Breakeven Quantity:</strong> Fixed Costs €${md.fc.toLocaleString()} / Unit CM €${c.cmu.toFixed(2)} = <strong>${c.be} units</strong> (rounded up).</li>
                                <li><strong>Operating Profit above Breakeven:</strong> Since fixed costs are fully recovered at the Breakeven Point, operating profit for sales volume above breakeven is simply: ${md.extraVol.toLocaleString()} units × Unit CM €${c.cmu.toFixed(2)} = <strong>€${c.profit.toLocaleString()}</strong>.</li>
                            </ul>
                        `;
                    } else {
                        html = `
                            <div style="display: inline-flex; align-items: center; gap: 4px; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a78bfa; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-bottom: 10px; font-family: 'Outfit', sans-serif;"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:12px; height:12px; stroke:#a78bfa;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.247 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>Seminar Reference: Session 3 Ex 10.11</div>
                            <p><strong>Shelf-Space Constraint Walkthrough:</strong></p>
                            <ul>
                                <li><strong>CM per case:</strong> Selling Price €${md.price.toFixed(2)} - Variable Cost €${md.vc.toFixed(2)} = <strong>€${c.cmCase.toFixed(2)}/case</strong>.</li>
                                <li><strong>Daily CM per shelf-meter:</strong> CM per case €${c.cmCase.toFixed(2)} × Capacity ${md.casesPerMeter} cases/meter/day = <strong>€${c.cmMeter.toFixed(2)}/meter/day</strong>.</li>
                                <li><strong>Decision Rule:</strong> When shelf space is the bottleneck resource, products should be prioritized and allocated shelf space based on contribution margin per shelf-meter rather than contribution margin per case.</li>
                            </ul>
                        `;
                    }
                }
                return html;
            }

    window.UI.getWalkthroughHTML = getWalkthroughHTML;
    window.getWalkthroughHTML = getWalkthroughHTML;

    function getCategoryDisplayName(c) {
                return { concepts: 'Cost Concepts', abc: 'Activity-Based Costing', variance: 'Variance Analysis', fifo: 'FIFO Process Costing', cvp: 'CVP & Constraints' }[c] || c;
            }

    window.UI.getCategoryDisplayName = getCategoryDisplayName;
    window.getCategoryDisplayName = getCategoryDisplayName;

    function updateDashboardSpacedRep() {
                const container = document.getElementById('spaced-rep-list-container');
                if (!container) return;
                if (!stats.spacedRepQueue || stats.spacedRepQueue.length === 0) {
                    container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">All topics fully mastered! Your review queue is currently empty.</div>`;
                    return;
                }
                container.innerHTML = '';
                stats.spacedRepQueue.forEach(item => {
                    const diffMs = item.dueDate - Date.now();
                    const due = diffMs <= 0;
                    let dueText = 'DUE NOW';
                    if (!due) {
                        const diffMins = Math.ceil(diffMs / 60000);
                        if (diffMins < 60) {
                            dueText = `Due in ${diffMins} min${diffMins > 1 ? 's':''}`;
                        } else {
                            const diffHrs = Math.ceil(diffMins / 60);
                            if (diffHrs < 24) {
                                dueText = `Due in ${diffHrs} hr${diffHrs > 1 ? 's':''}`;
                            } else {
                                const diffDays = Math.ceil(diffHrs / 24);
                                dueText = `Due in ${diffDays} day${diffDays > 1 ? 's':''}`;
                            }
                        }
                    }
                    const btnStyle = due ? 'background-color: var(--warning); border-color: var(--warning); color: black; font-weight:700;' : '';
                    container.innerHTML += `
                        <div class="rep-card">
                            <div><strong>${item.name}</strong><div style="font-size:11px; color:${due ? 'var(--warning)':'var(--text-muted)'}; font-weight:${due ? '700':'400'};">${dueText}</div></div>
                            <button class="btn btn-primary" style="padding:4px 8px; font-size:11px; ${btnStyle}" onclick="switchTab('practice-arena'); startArenaPractice('${item.category}');">Review Now</button>
                        </div>
                    `;
                });
            }

    window.UI.updateDashboardSpacedRep = updateDashboardSpacedRep;
    window.updateDashboardSpacedRep = updateDashboardSpacedRep;

    function startArenaPractice(category) {
        currentArenaMode = 'practice';
        setArenaMode('practice');
        document.getElementById('prac-category-select').value = category;
        if (window.startPracticeChallenge) window.startPracticeChallenge();
    }

    window.UI.startArenaPractice = startArenaPractice;
    window.startArenaPractice = startArenaPractice;

    function startExamSimulation() {
                window.examSubmitted = false;
                document.getElementById('exam-intro-card').style.display = 'none';
                document.getElementById('exam-active-panel').style.display = 'block';
                
                examQuestions = []; examAnswers = Array(5).fill(null); examCurrentIdx = 0;
                const cats = ['concepts', 'abc', 'variance', 'fifo', 'cvp'];
                cats.forEach(cat => {
                    const div = document.createElement('div');
                    currentPracProblem = { category: cat, difficulty: 'intermediate', status: 'ACTIVE', forfeited: false };
                    if (cat === 'concepts') generateConceptsProblemPrac(div);
                    else if (cat === 'abc') generateABCProblemPrac(div);
                    else if (cat === 'variance') generateVarianceProblemPrac(div);
                    else if (cat === 'fifo') generateFIFOProblemPrac(div);
                    else if (cat === 'cvp') generateCVPProblemPrac(div);
    
                    examQuestions.push({
                        category: cat,
                        promptHTML: div.innerHTML,
                        correctAnswers: currentPracProblem.correctAnswers,
                        templateId: currentPracProblem.templateId,
                        mathDetails: currentPracProblem.mathDetails
                    });
                });
    
                examTimeRemaining = 900;
                clearInterval(examTimer);
                examTimer = setInterval(() => {
                    examTimeRemaining--;
                    const m = Math.floor(examTimeRemaining / 60); const s = examTimeRemaining % 60;
                    document.getElementById('exam-timer-clock').innerText = `${m}:${s < 10 ? '0' : ''}${s}`;
                    if (examTimeRemaining <= 0) { clearInterval(examTimer); submitExam(); }
                }, 1000);
    
                renderExamQuestion();
            }

    window.UI.startExamSimulation = startExamSimulation;
    window.startExamSimulation = startExamSimulation;

    function renderExamQuestion() {
                if (!examQuestions || examQuestions.length === 0) {
                    console.warn("Attempted to render exam question, but examQuestions array is empty.");
                    return;
                }
                if (examCurrentIdx < 0 || examCurrentIdx >= examQuestions.length) {
                    examCurrentIdx = 0;
                }
                const q = examQuestions[examCurrentIdx];
                if (!q) return;
                document.getElementById('exam-question-card').innerHTML = q.promptHTML;
                document.getElementById('exam-question-number').innerText = `QUESTION ${examCurrentIdx + 1} OF 5`;
                document.getElementById('exam-question-category').innerText = getCategoryDisplayName(q.category);
    
                const dots = document.getElementById('exam-steps-indicator').children;
                for (let i=0; i<dots.length; i++) {
                    dots[i].className = 'step-dot';
                    if (i === examCurrentIdx) dots[i].classList.add('active');
                }
                restoreExamAnswers(examCurrentIdx);
                document.getElementById('exam-next-btn').innerText = examCurrentIdx === 4 ? "Submit Exam" : "Next";
            }

    window.UI.renderExamQuestion = renderExamQuestion;
    window.renderExamQuestion = renderExamQuestion;

    function navigateExamQuestion(dir) {
                saveExamAnswers(examCurrentIdx);
                if (dir === 1) {
                    if (examCurrentIdx < 4) { examCurrentIdx++; renderExamQuestion(); }
                    else { clearInterval(examTimer); submitExam(); }
                } else {
                    if (examCurrentIdx > 0) { examCurrentIdx--; renderExamQuestion(); }
                }
            }

    window.UI.navigateExamQuestion = navigateExamQuestion;
    window.navigateExamQuestion = navigateExamQuestion;

    function saveExamAnswers(idx) {
                if (!examQuestions || examQuestions.length === 0 || !examQuestions[idx]) return;
                const q = examQuestions[idx];
                const ans = {};
                const tid = q.templateId;
                ans.templateId = tid;
                
                if (q.category === 'concepts') {
                    if (tid === 0) {
                        ans.di = document.getElementById('c-ans-q1-di').value;
                        ans.vf = document.getElementById('c-ans-q1-vf').value;
                    } else if (tid === 1) {
                        ans.tot500 = parseFloat(document.getElementById('c-tot500').value) || 0;
                        ans.unit500 = parseFloat(document.getElementById('c-unit500').value) || 0;
                        ans.tot2000 = parseFloat(document.getElementById('c-tot2000').value) || 0;
                        ans.unit2000 = parseFloat(document.getElementById('c-unit2000').value) || 0;
                    } else if (tid === 2) {
                        ans.func = document.getElementById('c-func').value;
                    }
                } else if (q.category === 'abc') {
                    if (tid === 0) {
                        ans.tr = parseFloat(document.getElementById('ans-trad-rate').value) || 0;
                        ans.tcA = parseFloat(document.getElementById('ans-trad-costA').value) || 0;
                        ans.tcB = parseFloat(document.getElementById('ans-trad-costB').value) || 0;
                        ans.abcA = parseFloat(document.getElementById('ans-abc-costA').value) || 0;
                        ans.abcB = parseFloat(document.getElementById('ans-abc-costB').value) || 0;
                    } else {
                        ans.profit = parseFloat(document.getElementById('ans-restruct-profit').value) || 0;
                        ans.perTile = parseFloat(document.getElementById('ans-restruct-per-tile').value) || 0;
                    }
                } else if (q.category === 'variance') {
                    if (tid === 0) {
                        ans.dmPrice = parseFloat(document.getElementById('ans-dm-price').value) || 0;
                        ans.dmPeff = document.getElementById('effect-dm-price').value;
                        ans.dmEff = parseFloat(document.getElementById('ans-dm-eff').value) || 0;
                        ans.dmEeff = document.getElementById('effect-dm-eff').value;
                        ans.dlPrice = parseFloat(document.getElementById('ans-dl-price').value) || 0;
                        ans.dlPeff = document.getElementById('effect-dl-price').value;
                        ans.dlEff = parseFloat(document.getElementById('ans-dl-eff').value) || 0;
                        ans.dlEeff = document.getElementById('effect-dl-eff').value;
                    } else {
                        ans.seqProd = parseInt(document.getElementById('ans-seq-prod').value) || 0;
                        ans.seqSales = parseInt(document.getElementById('ans-seq-sales').value) || 0;
                        ans.seqDM = parseInt(document.getElementById('ans-seq-dm').value) || 0;
                        ans.seqOp = parseInt(document.getElementById('ans-seq-op').value) || 0;
                        ans.seqBS = parseInt(document.getElementById('ans-seq-bs').value) || 0;
                    }
                } else if (q.category === 'fifo') {
                    if (tid === 0) {
                        ans.dmEU = parseFloat(document.getElementById('ans-fifo-dm-eu').value) || 0;
                        ans.convEU = parseFloat(document.getElementById('ans-fifo-conv-eu').value) || 0;
                        ans.dmRate = parseFloat(document.getElementById('ans-fifo-dm-rate').value) || 0;
                        ans.convRate = parseFloat(document.getElementById('ans-fifo-conv-rate').value) || 0;
                    } else if (tid === 1) {
                        ans.rateBillable = parseFloat(document.getElementById('ans-rate-billable').value) || 0;
                        ans.rateTotal = parseFloat(document.getElementById('ans-rate-total').value) || 0;
                    } else {
                        ans.ohRate = parseFloat(document.getElementById('ans-oh-rate').value) || 0;
                        ans.ohAllocated = parseFloat(document.getElementById('ans-oh-allocated').value) || 0;
                        ans.ohDiff = parseFloat(document.getElementById('ans-oh-diff').value) || 0;
                    }
                } else if (q.category === 'cvp') {
                    if (tid === 0) {
                        ans.cmu = parseFloat(document.getElementById('ans-cvp-cmu').value) || 0;
                        ans.be = parseFloat(document.getElementById('ans-cvp-be').value) || 0;
                        ans.profit = parseFloat(document.getElementById('ans-cvp-profit').value) || 0;
                    } else {
                        ans.cmCase = parseFloat(document.getElementById('ans-bottle-cm-case').value) || 0;
                        ans.cmMeter = parseFloat(document.getElementById('ans-bottle-cm-meter').value) || 0;
                    }
                }
                examAnswers[idx] = ans;
            }

    window.UI.saveExamAnswers = saveExamAnswers;
    window.saveExamAnswers = saveExamAnswers;

    function restoreExamAnswers(idx) {
                if (!examQuestions || examQuestions.length === 0 || !examQuestions[idx]) return;
                const q = examQuestions[idx];
                const ans = examAnswers[idx];
                if (!ans) return;
                const tid = q.templateId;
                
                if (q.category === 'concepts') {
                    if (tid === 0) {
                        document.getElementById('c-ans-q1-di').value = ans.di || '';
                        document.getElementById('c-ans-q1-vf').value = ans.vf || '';
                    } else if (tid === 1) {
                        document.getElementById('c-tot500').value = ans.tot500 || '';
                        document.getElementById('c-unit500').value = ans.unit500 || '';
                        document.getElementById('c-tot2000').value = ans.tot2000 || '';
                        document.getElementById('c-unit2000').value = ans.unit2000 || '';
                    } else if (tid === 2) {
                        document.getElementById('c-func').value = ans.func || '';
                    }
                } else if (q.category === 'abc') {
                    if (tid === 0) {
                        document.getElementById('ans-trad-rate').value = ans.tr || '';
                        document.getElementById('ans-trad-costA').value = ans.tcA || '';
                        document.getElementById('ans-trad-costB').value = ans.tcB || '';
                        document.getElementById('ans-abc-costA').value = ans.abcA || '';
                        document.getElementById('ans-abc-costB').value = ans.abcB || '';
                    } else {
                        document.getElementById('ans-restruct-profit').value = ans.profit || '';
                        document.getElementById('ans-restruct-per-tile').value = ans.perTile || '';
                    }
                } else if (q.category === 'variance') {
                    if (tid === 0) {
                        document.getElementById('ans-dm-price').value = ans.dmPrice || '';
                        document.getElementById('effect-dm-price').value = ans.dmPeff || '';
                        document.getElementById('ans-dm-eff').value = ans.dmEff || '';
                        document.getElementById('effect-dm-eff').value = ans.dmEeff || '';
                        document.getElementById('ans-dl-price').value = ans.dlPrice || '';
                        document.getElementById('effect-dl-price').value = ans.dlPeff || '';
                        document.getElementById('ans-dl-eff').value = ans.dlEff || '';
                        document.getElementById('effect-dl-eff').value = ans.dlEeff || '';
                    } else {
                        document.getElementById('ans-seq-prod').value = ans.seqProd || '';
                        document.getElementById('ans-seq-sales').value = ans.seqSales || '';
                        document.getElementById('ans-seq-dm').value = ans.seqDM || '';
                        document.getElementById('ans-seq-op').value = ans.seqOp || '';
                        document.getElementById('ans-seq-bs').value = ans.seqBS || '';
                    }
                } else if (q.category === 'fifo') {
                    if (tid === 0) {
                        document.getElementById('ans-fifo-dm-eu').value = ans.dmEU || '';
                        document.getElementById('ans-fifo-conv-eu').value = ans.convEU || '';
                        document.getElementById('ans-fifo-dm-rate').value = ans.dmRate || '';
                        document.getElementById('ans-fifo-conv-rate').value = ans.convRate || '';
                    } else if (tid === 1) {
                        document.getElementById('ans-rate-billable').value = ans.rateBillable || '';
                        document.getElementById('ans-rate-total').value = ans.rateTotal || '';
                    } else {
                        document.getElementById('ans-oh-rate').value = ans.ohRate || '';
                        document.getElementById('ans-oh-allocated').value = ans.ohAllocated || '';
                        document.getElementById('ans-oh-diff').value = ans.ohDiff || '';
                    }
                } else if (q.category === 'cvp') {
                    if (tid === 0) {
                        document.getElementById('ans-cvp-cmu').value = ans.cmu || '';
                        document.getElementById('ans-cvp-be').value = ans.be || '';
                        document.getElementById('ans-cvp-profit').value = ans.profit || '';
                    } else {
                        document.getElementById('ans-bottle-cm-case').value = ans.cmCase || '';
                        document.getElementById('ans-bottle-cm-meter').value = ans.cmMeter || '';
                    }
                }
            }

    window.UI.restoreExamAnswers = restoreExamAnswers;
    window.restoreExamAnswers = restoreExamAnswers;

    function submitExam() {
                if (window.examSubmitted) return;
                window.examSubmitted = true;
                saveExamAnswers(examCurrentIdx);
                document.getElementById('exam-active-panel').style.display = 'none';
                document.getElementById('exam-scorecard-panel').style.display = 'block';
    
                let correct = 0;
                const review = document.getElementById('exam-review-questions-list');
                review.innerHTML = '';
                const tol = 0.25;
    
                examQuestions.forEach((q, idx) => {
                    const ans = examAnswers[idx] || {};
                    const c = q.correctAnswers;
                    const tid = q.templateId;
                    const validation = window.Controllers.answerVerifier.verify(q.category, q.templateId, c, ans);
                    const isCorrect = validation.correct;
    
                    // Update topic performance for decay-based mastery (Bug 4 fix)
                    updateTopicPerformance(q.category, isCorrect);
    
                    if (isCorrect) correct++;
                    else {
                        if (!stats.spacedRepQueue.some(i => i.category === q.category)) {
                            stats.spacedRepQueue.push({ category: q.category, name: getCategoryDisplayName(q.category), dueDate: Date.now() + 60*1000 });
                        }
                    }
    
                    let answerText = "";
                    if (q.category === 'concepts') {
                        if (tid === 0) answerText = `D/I: ${c.q1_di}, V/F: ${c.q1_vf}`;
                        else if (tid === 1) answerText = `Scenario 1 (total: €${c.tot500}, unit: €${c.unit500}), Scenario 2 (total: €${c.tot2000}, unit: €${c.unit2000})`;
                        else answerText = `Function: ${c.func === 'SK' ? 'Scorekeeping' : (c.func === 'AD' ? 'Attention Directing' : 'Problem Solving')}`;
                    } else if (q.category === 'abc') {
                        if (tid === 0) answerText = `Traditional Rate: €${c.tradRate}, Traditional Cost Premium: €${c.tradCostA}, Cost Basic: €${c.tradCostB}, ABC Cost Premium: €${c.abcCostA}, Cost Basic: €${c.abcCostB}`;
                        else answerText = `Operating profit: €${c.profit.toLocaleString()}, Profit/tile: €${c.perTile}`;
                    } else if (q.category === 'variance') {
                        if (tid === 0) answerText = `DM Price: €${Math.abs(c.dmPriceVar)} ${c.dmPriceVar>=0?'F':'U'}, DM Eff: €${Math.abs(c.dmEffVar)} ${c.dmEffVar>=0?'F':'U'}, DL Price: €${Math.abs(c.dlPriceVar)} ${c.dlPriceVar>=0?'F':'U'}, DL Eff: €${Math.abs(c.dlEffVar)} ${c.dlEffVar>=0?'F':'U'}`;
                        else answerText = `Sequence (Prod: ${c.prod}, Sales: ${c.sales}, DM: ${c.dm}, OpStatement: ${c.op}, BalanceSheet: ${c.bs})`;
                    } else if (q.category === 'fifo') {
                        if (tid === 0) answerText = `DM EU: ${c.currDmEU}, Conv EU: ${c.currConvEU}, DM Rate: €${c.rateDM.toFixed(2)}, Conv Rate: €${c.rateConv.toFixed(2)}`;
                        else if (tid === 1) answerText = `Scenario 1 Billable Rate: €${c.rateBillable.toFixed(2)}/hr, Scenario 2 Rate: €${c.rateTotal.toFixed(2)}/hr`;
                        else answerText = `OH Rate: €${c.ohRate.toFixed(2)}/MH, Allocated: €${c.ohAllocated.toLocaleString()}, Status: ${c.ohDiff >= 0 ? 'Over' : 'Under'}allocated by €${Math.abs(c.ohDiff).toLocaleString()}`;
                    } else if (q.category === 'cvp') {
                        if (tid === 0) answerText = `CM/unit: €${c.cmu.toFixed(2)}, Breakeven: ${c.be} units, Profit: €${c.profit.toLocaleString()}`;
                        else answerText = `CM/case: €${c.cmCase.toFixed(2)}, CM/meter/day: €${c.cmMeter.toFixed(2)}`;
                    }
    
                    let mistakeHtml = "";
                    if (!isCorrect) {
                        const mistake = diagnosePracticeMistake(q.category, q.templateId, q.mathDetails, c, ans);
                        if (mistake) {
                            mistakeHtml = `
                                <div style="margin-top: 10px; background-color: rgba(239, 68, 68, 0.05); border-left: 3px solid var(--danger); padding: 8px 12px; border-radius: 4px; border: 1px solid rgba(239,68,68,0.2);">
                                    <div style="font-weight: 700; color: var(--danger); font-size: 12px;">⚠️ Diagnosed Misconception: ${mistake.title}</div>
                                    <div style="font-size: 11px; color: white; margin-top: 2px;">${mistake.desc}</div>
                                    <div style="font-size: 11px; color: var(--accent-primary); margin-top: 4px; font-weight: 700;">💡 Remedy: ${mistake.remedy}</div>
                                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px; font-style: italic;"><strong>Concept:</strong> ${mistake.explanation}</div>
                                </div>
                            `;
                        }
                    }
    
                    review.innerHTML += `
                        <div class="collapsible-trigger" onclick="toggleCollapsible('ex-rev-${idx}')">Question ${idx+1}: ${getCategoryDisplayName(q.category)} <span>${isCorrect ? '✅':'❌'} ▼</span></div>
                        <div class="collapsible-content" id="ex-rev-${idx}">
                            <div class="collapsible-body" style="display: flex; flex-direction: column; gap: 12px;">
                                <div style="background-color: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px;">
                                    <div style="font-weight: 700; font-size: 13px; color: var(--accent-primary); margin-bottom: 4px;">Your Answers:</div>
                                    <div style="font-size: 13px;">${formatUserAnswers(q.category, q.templateId, ans, c)}</div>
                                    ${mistakeHtml}
                                </div>
                                <div style="background-color: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px;">
                                    <div style="font-weight: 700; font-size: 13px; color: var(--success); margin-bottom: 4px;">Correct Solutions:</div>
                                    <div style="font-size: 13px;">${answerText}</div>
                                </div>
                                <div style="background-color: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px;">
                                    <div style="font-weight: 700; font-size: 13px; color: #60a5fa; margin-bottom: 4px;">Step-by-Step Explanation:</div>
                                    <div style="font-size: 13px; line-height: 1.5;">${getWalkthroughHTML(q.category, q.templateId, q.mathDetails, c)}</div>
                                </div>
                                <div id="exam-diagram-panel-${idx}" style="background-color: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px; margin-top: 10px;"></div>
                            </div>
                        </div>
                    `;
                });
    
                // Call renderDynamicDiagram for each card after elements are in DOM
                examQuestions.forEach((q, idx) => {
                    const c = q.correctAnswers;
                    renderDynamicDiagram(q.category, q.templateId, q.mathDetails, 'exam-diagram-panel-' + idx, c);
                });
    
                document.getElementById('exam-score-large').innerText = `${correct} / 5`;
                document.getElementById('exam-score-pct').innerText = `${correct * 20}% Accuracy`;
    
                let bonus = correct === 5 ? 150 : (correct >= 3 ? 50 : 0);
                stats.xp += bonus;
                document.getElementById('exam-scorecard-summary-text').innerHTML = `Awarded <strong>+${bonus} XP</strong>. Spaced repetition review queue updated for failures.`;
                saveStats();
                updateAllUI();
            }

    window.UI.submitExam = submitExam;
    window.submitExam = submitExam;

    function exitExamReview() {
                document.getElementById('exam-intro-card').style.display = 'block';
                document.getElementById('exam-active-panel').style.display = 'none';
                document.getElementById('exam-scorecard-panel').style.display = 'none';
            }

    window.UI.exitExamReview = exitExamReview;
    window.exitExamReview = exitExamReview;

    function toggleCollapsible(id) {
                const el = document.getElementById(id);
                if (el.style.maxHeight && el.style.maxHeight !== '0px') el.style.maxHeight = '0px';
                else el.style.maxHeight = el.scrollHeight + 'px';
            }

    window.UI.toggleCollapsible = toggleCollapsible;
    window.toggleCollapsible = toggleCollapsible;

    function updateAllUI() {
        if (window.Cognitive && window.Cognitive.masteryEngine && window.Cognitive.masteryEngine.updateDecayedMastery) {
            window.Cognitive.masteryEngine.updateDecayedMastery();
        } else if (window.updateDecayedMastery) {
            window.updateDecayedMastery();
        }

        if (window.updateStatsHUD) window.updateStatsHUD();
        else if (window.UI && window.UI.updateStatsHUD) window.UI.updateStatsHUD();

        if (window.updateMasteryUI) window.updateMasteryUI();
        else if (window.UI && window.UI.updateMasteryUI) window.UI.updateMasteryUI();

        if (window.updateTelemetryUI) window.updateTelemetryUI();
        else if (window.UI && window.UI.updateTelemetryUI) window.UI.updateTelemetryUI();

        if (window.updateDecayTracker) window.updateDecayTracker();
        else if (window.UI && window.UI.updateDecayTracker) window.UI.updateDecayTracker();

        if (window.computeStudyPlan) window.computeStudyPlan();
        else if (window.UI && window.UI.computeStudyPlan) window.UI.computeStudyPlan();

        if (window.updateCalibrationHUD) window.updateCalibrationHUD();
        else if (window.UI && window.UI.updateCalibrationHUD) window.UI.updateCalibrationHUD();

        if (window.updateDashboardMistakes) window.updateDashboardMistakes();
        else if (window.UI && window.UI.updateDashboardMistakes) window.UI.updateDashboardMistakes();

        if (window.updateDashboardSpacedRep) window.updateDashboardSpacedRep();
        else if (window.UI && window.UI.updateDashboardSpacedRep) window.UI.updateDashboardSpacedRep();

        if (window.updateRSIUI) window.updateRSIUI();
        else if (window.UI && window.UI.updateRSIUI) window.UI.updateRSIUI();
    }

    window.UI.appUI = window.UI.appUI || {};
    window.UI.appUI.updateAllUI = updateAllUI;
    window.UI.updateAllUI = updateAllUI;
    window.updateAllUI = updateAllUI;

    // Metacognitive Study Portal Initialization
    window.addEventListener('DOMContentLoaded', () => {
        if (typeof loadStats === 'function') {
            loadStats();
        } else if (window.Storage && typeof window.Storage.loadStats === 'function') {
            window.Storage.loadStats();
        }
        
        if (typeof switchTab === 'function') {
            switchTab('dashboard');
        } else if (window.UI && typeof window.UI.switchTab === 'function') {
            window.UI.switchTab('dashboard');
        }
    });

})();