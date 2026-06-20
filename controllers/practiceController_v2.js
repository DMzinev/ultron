// controllers/practiceController.js

(function() {
    window.Controllers = window.Controllers || {};
    window.Controllers.practiceController = {};

    // Temporary practice runtime session variables (re-initialized on reload)
    var currentPracProblem = null;
    var currentAttemptNum = 1;
    var currentPracticeReflection = { selectedCategory: '', reflectionText: '' };
    var currentRetrievalConfidence = null;
    var currentRetrievalQuestion = null;

    Object.defineProperty(window, 'currentPracProblem', {
        get: function() { return currentPracProblem; },
        set: function(val) { currentPracProblem = val; },
        configurable: true
    });
    Object.defineProperty(window, 'currentAttemptNum', {
        get: function() { return currentAttemptNum; },
        set: function(val) { currentAttemptNum = val; },
        configurable: true
    });
    Object.defineProperty(window, 'currentPracticeReflection', {
        get: function() { return currentPracticeReflection; },
        set: function(val) { currentPracticeReflection = val; },
        configurable: true
    });
    Object.defineProperty(window, 'currentRetrievalConfidence', {
        get: function() { return currentRetrievalConfidence; },
        set: function(val) { currentRetrievalConfidence = val; },
        configurable: true
    });
    Object.defineProperty(window, 'currentRetrievalQuestion', {
        get: function() { return currentRetrievalQuestion; },
        set: function(val) { currentRetrievalQuestion = val; },
        configurable: true
    });

    const retrievalQuestions = {
        concepts: [
            { q: "What is the difference between direct and indirect costs?", r: /trace|allocat|direct|indirect/i, sol: "Direct costs can be traced to a cost object in an economically feasible way, whereas indirect costs cannot be traced and must be allocated." },
            { q: "How does a variable cost behave in total and per unit as volume increases?", r: /total.*increase|unit.*constant/i, sol: "Total variable costs increase in direct proportion to volume, while unit variable cost remains constant." }
        ],
        costing: [
            { q: "How do you calculate equivalent units under the Weighted-Average method?", r: /completed.*ending|completed.*ewip/i, sol: "Weighted-Average Equivalent Units = Units Completed and Transferred Out + (Ending Work in Process * % Completion)." },
            { q: "What is the formula for the budgeted indirect cost allocation rate?", r: /budgeted.*indirect.*cost|budgeted.*allocation.*base/i, sol: "Budgeted Indirect Cost Rate = Budgeted Total Indirect Costs / Budgeted Total Quantity of Cost-Allocation Base." }
        ],
        cvp: [
            { q: "What is the formula for Breakeven Point in Units?", r: /fixed.*cost.*contribution.*margin|fc.*cmu|fc.*\(p.*vc\)/i, sol: "Breakeven Quantity = Total Fixed Costs / Contribution Margin per Unit (USP - UVC)." },
            { q: "When managing a bottleneck constraint, how should product priority be ranked?", r: /contribution.*margin.*per.*constraint|cm.*per.*hour|cm.*per.*meter/i, sol: "Products should be prioritized based on their Contribution Margin per unit of the limiting resource (bottleneck), not Contribution Margin per unit of product." }
        ],
        abc: [
            { q: "How does Activity-Based Costing (ABC) differ from traditional costing systems in overhead allocation?", r: /multiple.*activity.*pool|cost.*driver|cause.*effect/i, sol: "ABC uses multiple activity-level cost pools and cause-and-effect cost drivers, whereas traditional costing uses a single department or plant-wide rate based on volume metrics like direct labor hours." }
        ],
        variance: [
            { q: "What is the formula for Direct Materials Price Variance, and what is its sign convention?", r: /\(sp.*ap\).*aq|standard.*price.*actual.*price|sp.*ap/i, sol: "DM Price Variance = (Standard Price - Actual Price) * Actual Quantity Purchased/Used. Positive represents Favorable (actual price paid was lower than standard), negative represents Unfavorable." },
            { q: "What is the formula for Direct Materials Efficiency Variance?", r: /\(sq.*aq\).*sp|standard.*qty.*actual.*qty|sq.*aq/i, sol: "DM Efficiency Variance = (Standard Quantity Allowed - Actual Quantity Used) * Standard Price." }
        ],
        fifo: [
            { q: "How do you calculate equivalent units under the FIFO method?", r: /opening.*started.*ending|started.*completed/i, sol: "FIFO Equivalent Units = (Opening WIP * % remaining) + Units Started and Completed + (Ending WIP * % complete)." }
        ]
    };

    function startPracticeChallenge() {
        try {
            const category = document.getElementById('prac-category-select').value;
            const diff = document.getElementById('prac-difficulty-select').value;

            document.getElementById('practice-selector-panel').style.display = 'none';
            document.getElementById('practice-active-panel').style.display = 'block';
            document.getElementById('prac-solution-panel').style.display = 'none';
            document.getElementById('prac-hint-textbox').style.display = 'none';
            
            currentAttemptNum = 1;
            var verifyBtn = document.getElementById('prac-verify-btn');
            if (verifyBtn) {
                verifyBtn.innerText = "Verify Answer";
                verifyBtn.disabled = false;
            }
            
            // Metacognitive Reflection container check
            const refContainer = document.getElementById('prac-reflection-container');
            if (refContainer) refContainer.style.display = 'none';

            const mistPanel = document.getElementById('prac-mistake-analysis');
            if (mistPanel) {
                mistPanel.style.display = 'none';
                mistPanel.innerHTML = '';
            }

            // Restore active buttons innerHTML in case they were modified by slide review or worked example
            const activeButtons = document.getElementById('prac-active-buttons');
            if (activeButtons) {
                activeButtons.style.display = 'flex';
                activeButtons.innerHTML = `
                    <button class="btn btn-primary" id="prac-verify-btn" onclick="verifyPracticeAnswer()">Verify Answer</button>
                    <button class="btn btn-secondary" onclick="exitActivePractice()">Reset</button>
                `;
            }

            let adaptiveDiff = diff;
            let sel = category;
            if (category === 'mixed') {
                const rsi = window.Storage && window.Storage.rsiState;
                if (rsi && rsi.weakestCategory && rsi.weakestCategory !== 'None') {
                    sel = rsi.weakestCategory;
                    adaptiveDiff = 'hard';
                } else {
                    const c = ['concepts', 'abc', 'variance', 'fifo', 'cvp'];
                    sel = c[Math.floor(Math.random() * c.length)];
                }
            }

            // Update CPC HUD
            let cpcDecision = { type: 'STANDARD' };
            if (window.Cognitive && window.Cognitive.PolicyController && window.ConceptStateMachine) {
                const csmTopic = sel === 'fifo' ? 'costing' : sel;
                cpcDecision = window.Cognitive.PolicyController.decide(window.ConceptStateMachine, csmTopic);
            }

            const cpcHud = document.getElementById('cpc-hud-panel');
            const cpcMsg = document.getElementById('cpc-hud-message');
            const getDispName = window.getCategoryDisplayName || (c => c === 'costing' ? 'FIFO Process Costing' : c);
            if (cpcHud && cpcMsg) {
                cpcHud.style.display = 'block';
                if (cpcDecision.type === 'SHOW_SLIDES') {
                    cpcHud.style.background = 'linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.05))';
                    cpcHud.style.borderColor = 'rgba(239, 68, 68, 0.3)';
                    cpcMsg.innerHTML = `⚠️ [CRITICAL REVIEW] Local collapse detected in <strong>${getDispName(cpcDecision.target === 'costing' ? 'fifo' : cpcDecision.target)}</strong> (pressure > 0.8). Normal challenge generation is locked.`;
                } else if (cpcDecision.type === 'WORKED_EXAMPLE') {
                    cpcHud.style.background = 'linear-gradient(135deg, rgba(167, 139, 250, 0.15), rgba(167, 139, 250, 0.05))';
                    cpcHud.style.borderColor = 'rgba(167, 139, 250, 0.3)';
                    cpcMsg.innerHTML = `💡 [COGNITIVE ASSIST] Learning velocity is low (average velocity < -0.3). Reviewing worked example for <strong>${getDispName(cpcDecision.target === 'costing' ? 'fifo' : cpcDecision.target)}</strong> to rebuild momentum.`;
                } else if (cpcDecision.type === 'HARD_PROBLEM') {
                    cpcHud.style.background = 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05))';
                    cpcHud.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                    cpcMsg.innerHTML = `🚀 [ELITE CHALLENGE] Mastery is stable (>80%) across all modules! Difficulty locked to <strong>Hard</strong>.`;
                } else {
                    cpcHud.style.background = 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.05))';
                    cpcHud.style.borderColor = 'rgba(59, 130, 246, 0.2)';
                    cpcMsg.innerHTML = `✅ [STABLE REGIME] Cognitive field is stable. Proceeding with standard practice.`;
                }
            }

            // Action routing
            if (cpcDecision.type === 'SHOW_SLIDES') {
                const targetCat = cpcDecision.target === 'costing' ? 'fifo' : cpcDecision.target;
                currentPracProblem = { category: targetCat, difficulty: adaptiveDiff, status: 'LOCKED', forfeited: false };
                document.getElementById('prac-active-badge').innerText = targetCat.toUpperCase() + ' REVIEW';
                document.getElementById('prac-diff-badge').innerText = 'Slides';
                if (window.renderCpcSlides) {
                    window.renderCpcSlides(cpcDecision.target);
                }
                return;
            } else if (cpcDecision.type === 'WORKED_EXAMPLE') {
                const targetCat = cpcDecision.target === 'costing' ? 'fifo' : cpcDecision.target;
                currentPracProblem = { category: targetCat, difficulty: adaptiveDiff, status: 'LOCKED', forfeited: false };
                document.getElementById('prac-active-badge').innerText = targetCat.toUpperCase() + ' EXAMPLE';
                document.getElementById('prac-diff-badge').innerText = 'Worked Solution';
                if (window.loadWorkedExample) {
                    window.loadWorkedExample(cpcDecision.target);
                }
                return;
            } else if (cpcDecision.type === 'HARD_PROBLEM') {
                adaptiveDiff = 'hard';
            }

            currentPracProblem = { category: sel, difficulty: adaptiveDiff, forfeited: false, status: 'ACTIVE' };
            document.getElementById('prac-active-badge').innerText = sel.toUpperCase() + ' CHALLENGE';
            if (window.capitalizeFirst) {
                document.getElementById('prac-diff-badge').innerText = window.capitalizeFirst(adaptiveDiff);
            } else {
                document.getElementById('prac-diff-badge').innerText = adaptiveDiff;
            }

            const prompt = document.getElementById('prac-question-prompt');
            
            const domainCat = sel === 'fifo' ? 'Costing' : (sel === 'concepts' ? 'Concepts' : (sel === 'cvp' ? 'CVP' : (sel === 'abc' ? 'ABC' : 'Variance')));
            if (window.Domain && window.Domain[domainCat] && window.Domain[domainCat].generate) {
                window.Domain[domainCat].generate(prompt);
            }

            // Draw Visual Coding Diagram
            const diagPanel = document.getElementById('prac-diagram-panel');
            if (diagPanel && window.renderDynamicDiagram) {
                window.renderDynamicDiagram(currentPracProblem.category, currentPracProblem.templateId, currentPracProblem.mathDetails, 'prac-diagram-panel');
            }
            
            // ================= RETRIEVAL PRE-TEST INJECTION =================
            const qList = retrievalQuestions[sel];
            if (qList && qList.length > 0) {
                const qIdx = Math.floor(Math.random() * qList.length);
                currentRetrievalQuestion = qList[qIdx];
                currentRetrievalConfidence = null;
                
                // Show pre-test overlay and hide prompt details
                document.getElementById('retrieval-pretest-panel').style.display = 'block';
                document.getElementById('retrieval-question-text').innerText = currentRetrievalQuestion.q;
                document.getElementById('retrieval-answer-input').value = '';
                document.getElementById('retrieval-answer-input').disabled = false;
                document.getElementById('retrieval-submit-btn').disabled = false;
                document.getElementById('retrieval-feedback-panel').style.display = 'none';
                
                // Reset confidence button styles
                document.querySelectorAll('.btn-confidence').forEach(btn => {
                    btn.style.borderColor = 'var(--border-color)';
                    btn.style.backgroundColor = 'var(--bg-primary)';
                    btn.style.color = 'var(--text-secondary)';
                    btn.style.pointerEvents = 'auto';
                });
                
                document.getElementById('prac-question-prompt').style.display = 'none';
                if (diagPanel) diagPanel.style.display = 'none';
                const scaffoldPanel = document.getElementById('prac-scaffold-panel');
                if (scaffoldPanel) scaffoldPanel.style.display = 'none';
                const activeBtns = document.getElementById('prac-active-buttons');
                if (activeBtns) activeBtns.style.display = 'none';
            } else {
                const pretestPanel = document.getElementById('retrieval-pretest-panel');
                if (pretestPanel) pretestPanel.style.display = 'none';
                document.getElementById('prac-question-prompt').style.display = 'block';
                if (diagPanel) diagPanel.style.display = 'block';
                const scaffoldPanel = document.getElementById('prac-scaffold-panel');
                if (scaffoldPanel) scaffoldPanel.style.display = 'block';
                const activeBtns = document.getElementById('prac-active-buttons');
                if (activeBtns) activeBtns.style.display = 'flex';
            }
            
            if (window.updatePracticePdfRecommendations) {
                window.updatePracticePdfRecommendations(sel);
            }
        } catch (e) {
            const errDiv = document.createElement('div');
            errDiv.style.color = 'white';
            errDiv.style.backgroundColor = 'red';
            errDiv.style.padding = '20px';
            errDiv.style.margin = '20px';
            errDiv.style.zIndex = '9999';
            errDiv.style.position = 'relative';
            errDiv.innerHTML = '<h3>CRITICAL ERROR IN PRACTICE ARENA</h3><p>' + e.message + '</p><pre>' + e.stack + '</pre>';
            document.getElementById('practice-selector-panel').insertAdjacentElement('afterend', errDiv);
            
            console.error('START PRACTICE FAILED', e);
            try { alert('START PRACTICE FAILED:\n' + e.message); } catch (err) {}
        }
    }

    function exitActivePractice() {
        document.getElementById('practice-selector-panel').style.display = 'block';
        document.getElementById('practice-active-panel').style.display = 'none';
        document.getElementById('prac-solution-panel').style.display = 'none';
        // Hide the CPC HUD when returning to lobby
        const cpcHud = document.getElementById('cpc-hud-panel');
        if (cpcHud) cpcHud.style.display = 'none';
    }

    function rateSRS(easiness) {
        if (!currentPracProblem) return;
        const cat = currentPracProblem.category;
        const name = getCategoryDisplayName(cat);
        let interval = 60 * 1000; // Hard = 1 min
        let label = "Hard";
        
        const conf = currentPracProblem.retrievalConfidence || 2;
        
        if (easiness === 'good') {
            if (conf === 1) {
                interval = 2 * 3600 * 1000; // Guessing override -> 2 hours
                label = "Good (Guessing override: 2h)";
            } else if (conf === 3) {
                interval = 4 * 24 * 3600 * 1000; // Very Confident override -> 4 days
                label = "Good (Confident override: 4d)";
            } else {
                interval = 24 * 3600 * 1000; // Good = 1 day
                label = "Good (1d)";
            }
        } else if (easiness === 'easy') {
            if (conf === 3) {
                interval = 7 * 24 * 3600 * 1000; // Super Easy for confident -> 7 days
                label = "Easy (Confident override: 7d)";
            } else {
                interval = 4 * 24 * 3600 * 1000; // Easy = 4 days
                label = "Easy (4d)";
            }
        }
        
        // Remove existing entry
        stats.spacedRepQueue = stats.spacedRepQueue.filter(i => i.category !== cat);
        // Push new scheduled entry
        stats.spacedRepQueue.push({
            category: cat,
            name: name,
            dueDate: Date.now() + interval,
            intervalLabel: label
        });
        
        // Passive persistence save and UI updates
        window.UI.appUI.updateAllUI();
        window.Storage.saveStats();
        
        // Hide rating panel and show feedback
        document.getElementById('srs-rating-panel').innerHTML = `<p style="color: var(--success); font-weight: 600; margin-bottom: 0; font-size:12px;">Topic scheduled for review in ${label}.</p>`;
    }

    function submitFeynmanExplanation() {
        const input = document.getElementById('feynman-input');
        const feedback = document.getElementById('feynman-feedback');
        if (!input || !feedback || !currentPracProblem) return;
        const val = input.value.trim().toLowerCase();
        if (val.length < 10) {
            feedback.innerText = "Please write a slightly longer explanation (at least 10 characters) to solidify your memory.";
            feedback.style.color = 'var(--danger)';
            return;
        }
        
        const keywordsMap = {
            'concepts': {
                0: ['direct', 'indirect', 'trace', 'allocate', 'fixed', 'variable', 'volume'],
                1: ['fixed', 'spread', 'denominator', 'divide', 'people', 'constant', 'unit', 'decrease'],
                2: ['scorekeeping', 'attention', 'problem', 'decision', 'report', 'analyze', 'record']
            },
            'fifo': {
                0: ['current', 'work', 'opening', 'subtract', 'exclude', 'period', 'equivalent'],
                1: ['billable', 'denominator', 'total', 'overhead', 'recover', 'salary', 'hours'],
                2: ['under', 'over', 'allocated', 'actual', 'rate', 'budgeted', 'machine']
            },
            'cvp': {
                0: ['breakeven', 'margin', 'contribution', 'fixed', 'price', 'cover', 'profit'],
                1: ['bottleneck', 'constraint', 'meter', 'shelf', 'maximize', 'priority', 'limit']
            },
            'abc': {
                0: ['distort', 'volume', 'setup', 'shipment', 'activity', 'overhead', 'driver', 'rate'],
                1: ['opex', 'profit', 'restructuring', 'costs', 'budget', 'activity', 'reduce']
            },
            'variance': {
                0: ['price', 'efficiency', 'quantity', 'favorable', 'unfavorable', 'standard', 'actual'],
                1: ['sequence', 'sales', 'production', 'materials', 'income', 'balance', 'budget']
            }
        };
        
        const cat = currentPracProblem.category;
        const tid = currentPracProblem.templateId;
        const keywords = (keywordsMap[cat] && keywordsMap[cat][tid]) ? keywordsMap[cat][tid] : ['cost', 'accounting', 'math'];
        
        const matched = keywords.filter(k => val.includes(k));
        if (matched.length >= 1) {
            feedback.innerHTML = `✨ Success! +15 XP awarded. Your explanation uses key terms (<i>${matched.join(', ')}</i>).`;
            feedback.style.color = 'var(--success)';
            stats.xp += 15;
            
            window.UI.appUI.updateAllUI();
            window.Storage.saveStats();
            
            input.disabled = true;
            const btn = document.querySelector('#feynman-challenge-panel button');
            if (btn) btn.disabled = true;
        } else {
            feedback.innerHTML = `Explanation received, but try to use more specific keywords (e.g. <i>${keywords.slice(0, 4).join(', ')}</i>).`;
            feedback.style.color = 'var(--warning)';
        }
    }

    function verifyPracticeAnswer() {
        if (currentPracProblem && (currentPracProblem.status === 'COMPLETED' || currentPracProblem.status === 'FORFEITED' || currentPracProblem.status === 'LOCKED')) {
            return;
        }
        function getUserAnswers(category, tid) {
            const ans = {};
            if (category === 'concepts') {
                if (tid === 0) {
                    ans.di = document.getElementById('c-ans-q1-di').value;
                    ans.vf = document.getElementById('c-ans-q1-vf').value;
                } else if (tid === 1) {
                    ans.tot500 = document.getElementById('c-tot500').value;
                    ans.unit500 = document.getElementById('c-unit500').value;
                    ans.tot2000 = document.getElementById('c-tot2000').value;
                    ans.unit2000 = document.getElementById('c-unit2000').value;
                } else if (tid === 2) {
                    ans.func = document.getElementById('c-func').value;
                }
            } else if (category === 'abc') {
                if (tid === 0) {
                    ans.tr = document.getElementById('ans-trad-rate').value;
                    ans.tcA = document.getElementById('ans-trad-costA').value;
                    ans.tcB = document.getElementById('ans-trad-costB').value;
                    ans.abcA = document.getElementById('ans-abc-costA').value;
                    ans.abcB = document.getElementById('ans-abc-costB').value;
                } else {
                    ans.profit = document.getElementById('ans-restruct-profit').value;
                    ans.perTile = document.getElementById('ans-restruct-per-tile').value;
                }
            } else if (category === 'variance') {
                if (tid === 0) {
                    ans.dmPrice = document.getElementById('ans-dm-price').value;
                    ans.dmPeff = document.getElementById('effect-dm-price').value;
                    ans.dmEff = document.getElementById('ans-dm-eff').value;
                    ans.dmEeff = document.getElementById('effect-dm-eff').value;
                    ans.dlPrice = document.getElementById('ans-dl-price').value;
                    ans.dlEff = document.getElementById('ans-dl-eff').value;
                    ans.dlPeff = document.getElementById('effect-dl-price').value;
                    ans.dlEeff = document.getElementById('effect-dl-eff').value;
                } else {
                    ans.seqProd = document.getElementById('ans-seq-prod').value;
                    ans.seqSales = document.getElementById('ans-seq-sales').value;
                    ans.seqDM = document.getElementById('ans-seq-dm').value;
                    ans.seqOp = document.getElementById('ans-seq-op').value;
                    ans.seqBS = document.getElementById('ans-seq-bs').value;
                }
            } else if (category === 'fifo') {
                if (tid === 0) {
                    ans.dmEU = document.getElementById('ans-fifo-dm-eu').value;
                    ans.convEU = document.getElementById('ans-fifo-conv-eu').value;
                    ans.dmRate = document.getElementById('ans-fifo-dm-rate').value;
                    ans.convRate = document.getElementById('ans-fifo-conv-rate').value;
                } else if (tid === 1) {
                    ans.rateBillable = document.getElementById('ans-rate-billable').value;
                    ans.rateTotal = document.getElementById('ans-rate-total').value;
                } else {
                    ans.ohRate = document.getElementById('ans-oh-rate').value;
                    ans.ohAllocated = document.getElementById('ans-oh-allocated').value;
                    ans.ohDiff = document.getElementById('ans-oh-diff').value;
                }
            } else if (category === 'cvp') {
                if (tid === 0) {
                    ans.cmu = document.getElementById('ans-cvp-cmu').value;
                    ans.be = document.getElementById('ans-cvp-be').value;
                    ans.profit = document.getElementById('ans-cvp-profit').value;
                } else {
                    ans.cmCase = document.getElementById('ans-bottle-cm-case').value;
                    ans.cmMeter = document.getElementById('ans-bottle-cm-meter').value;
                }
            }
            return ans;
        }

        function checkInputs() {
            const userAnswers = getUserAnswers(currentPracProblem.category, currentPracProblem.templateId);
            return window.Controllers.answerVerifier.verify(
                currentPracProblem.category,
                currentPracProblem.templateId,
                currentPracProblem.correctAnswers,
                userAnswers
            );
        }

        const validation = checkInputs();
        const correct = validation.correct;
        const results = validation.results;
        
        // Highlight all fields based on results
        for (const id in results) {
            const el = document.getElementById(id);
            if (el) {
                if (results[id]) {
                    el.style.border = '2px solid var(--success)';
                    el.style.boxShadow = '0 0 5px var(--success)';
                } else {
                    el.style.border = '2px solid var(--danger)';
                    el.style.boxShadow = '0 0 5px var(--danger)';
                }
            }
        }

        const activeTopic = currentPracProblem.category === 'fifo' ? 'costing' : currentPracProblem.category;
        const det = document.getElementById('prac-detailed-steps');
        const panel = document.getElementById('prac-solution-panel');
        const c = currentPracProblem.correctAnswers;
        const tid = currentPracProblem.templateId;

        // Compute XP based on topic
        let baseXp = 40; 
        if (currentPracProblem.category === 'concepts') baseXp = 30;
        else if (currentPracProblem.category === 'abc') baseXp = (tid === 0 ? 60 : 50);
        else if (currentPracProblem.category === 'variance') baseXp = (tid === 0 ? 50 : 30);
        else if (currentPracProblem.category === 'fifo') baseXp = (tid === 0 ? 50 : 40);
        else if (currentPracProblem.category === 'cvp') baseXp = 40;

        if (correct && !currentPracProblem.forfeited) {
            // Success path!
            currentPracProblem.status = 'COMPLETED';
            const inputs = document.getElementById('prac-question-prompt').querySelectorAll('input, select, textarea');
            inputs.forEach(el => el.disabled = true);
            var verifyBtn = document.getElementById('prac-verify-btn');
            if (verifyBtn) verifyBtn.disabled = true;

            stats.totalAttempts++;
            
            // Update cognitive state with correct attempt details
            window.Controllers.sessionController.updateCognitiveState(activeTopic, true, currentAttemptNum, null);
            
            det.innerHTML = getWalkthroughHTML(currentPracProblem.category, tid, currentPracProblem.mathDetails, c);
            
            panel.style.display = 'block';
            const titleEl = document.getElementById('prac-solution-title');
            const textEl = document.getElementById('prac-solution-xp-text');
            
            titleEl.innerText = "Conquered! 🎉"; 
            titleEl.style.color = 'var(--success)';
            
            let earnedXp = baseXp;
            textEl.innerText = `+${earnedXp} XP awarded. Active recall challenge and spaced scheduling unlocked below!`; 
            textEl.style.color = 'var(--success)';
            
            stats.xp += earnedXp; 
            stats.streak++; 
            stats.correctAttempts++;
            stats.spacedRepQueue = stats.spacedRepQueue.filter(i => i.category !== currentPracProblem.category);

            // Adaptive Difficulty: track consecutive correct streak
            if (stats.consecutiveStats && stats.consecutiveStats[activeTopic]) {
                const cs = stats.consecutiveStats[activeTopic];
                cs.correct++;
                cs.incorrect = 0;
                if (cs.correct >= 3) {
                    if (cs.activeDifficulty === 'easy') cs.activeDifficulty = 'intermediate';
                    else if (cs.activeDifficulty === 'intermediate') cs.activeDifficulty = 'hard';
                    cs.hintsEnabled = false;
                    cs.correct = 0;
                }
            }
            
            // Hide mistake analysis panel if any
            const mistPanel = document.getElementById('prac-mistake-analysis');
            if (mistPanel) {
                mistPanel.style.display = 'none';
                mistPanel.innerHTML = '';
            }
            
            // Show Feynman Active Recall & SRS ratings
            document.getElementById('feynman-challenge-panel').style.display = 'block';
            document.getElementById('feynman-input').value = '';
            document.getElementById('feynman-input').disabled = false;
            const fBtn = document.querySelector('#feynman-challenge-panel button');
            if (fBtn) fBtn.disabled = false;
            document.getElementById('feynman-feedback').innerText = '';
            
            document.getElementById('srs-rating-panel').style.display = 'block';
            document.getElementById('srs-rating-panel').innerHTML = `
                <h4 style="color: white; font-size: 13px; margin-bottom: 4px;">Rate this topic's ease of recall:</h4>
                <p style="font-size: 11px; color: var(--text-secondary); margin-bottom: 8px;">Your rating determines when you will review this topic next.</p>
                <div class="srs-rating-container">
                    <button class="srs-btn srs-btn-hard" onclick="rateSRS('hard')">Hard (Soon)</button>
                    <button class="srs-btn srs-btn-good" onclick="rateSRS('good')">Good (1 Day)</button>
                    <button class="srs-btn srs-btn-easy" onclick="rateSRS('easy')">Easy (4 Days)</button>
                </div>
            `;
            
            // Reset attempt number for next challenge
            currentAttemptNum = 1;
            var verifyBtn = document.getElementById('prac-verify-btn');
            if (verifyBtn) verifyBtn.innerText = "Verify Answer";
            
            window.UI.appUI.updateAllUI();
            window.Storage.saveStats();
            panel.scrollIntoView({ behavior: 'smooth' });
            
        } else if (currentPracProblem.forfeited) {
            currentPracProblem.status = 'FORFEITED';
            const inputs = document.getElementById('prac-question-prompt').querySelectorAll('input, select, textarea');
            inputs.forEach(el => el.disabled = true);
            var verifyBtn = document.getElementById('prac-verify-btn');
            if (verifyBtn) verifyBtn.disabled = true;

            stats.totalAttempts++;
            window.Controllers.sessionController.updateCognitiveState(activeTopic, false, currentAttemptNum, null);
            
            det.innerHTML = getWalkthroughHTML(currentPracProblem.category, tid, currentPracProblem.mathDetails, c);
            
            panel.style.display = 'block';
            const titleEl = document.getElementById('prac-solution-title');
            const textEl = document.getElementById('prac-solution-xp-text');
            
            titleEl.innerText = "Solution Path Revealed"; 
            titleEl.style.color = 'var(--warning)';
            textEl.innerText = "No XP awarded."; 
            textEl.style.color = 'var(--warning)';
            
            stats.streak = 0;
            
            // Add topic to review queue
            if (!stats.spacedRepQueue.some(i => i.category === currentPracProblem.category)) {
                stats.spacedRepQueue.push({
                    category: currentPracProblem.category, name: getCategoryDisplayName(currentPracProblem.category), dueDate: Date.now() + 60*1000
                });
            }
            
            // Hide Feynman and SRS
            document.getElementById('feynman-challenge-panel').style.display = 'none';
            document.getElementById('srs-rating-panel').style.display = 'none';
            
            // Show worked steps immediately
            det.style.display = 'block';
            
            // Reset attempt number for next challenge
            currentAttemptNum = 1;
            var verifyBtn = document.getElementById('prac-verify-btn');
            if (verifyBtn) verifyBtn.innerText = "Verify Answer";
            
            window.UI.appUI.updateAllUI();
            window.Storage.saveStats();
            panel.scrollIntoView({ behavior: 'smooth' });
            
        } else {
            // Incorrect path!
            if (currentAttemptNum === 1) {
                // Strike 1! Get mistake details and IMMEDIATELY update belief profile
                const diag = diagnosePracticeMistake(currentPracProblem.category, currentPracProblem.templateId, currentPracProblem.mathDetails, currentPracProblem.correctAnswers);
                const errorVector = diag ? diag.vector : null;
                
                // Immediately feed observation into the Bayesian Belief Engine on Strike 1
                window.Cognitive.beliefEngine.updateBelief(activeTopic, errorVector);

                // Lock inputs
                currentPracProblem.status = 'LOCKED';
                const inputs = document.getElementById('prac-question-prompt').querySelectorAll('input, select, textarea');
                inputs.forEach(el => el.disabled = true);
                
                // Show reflection checkpoint
                showReflectionCheckpoint();
                
            } else {
                // Strike 2 (Final Failure)!
                currentPracProblem.status = 'FORFEITED';
                const inputs = document.getElementById('prac-question-prompt').querySelectorAll('input, select, textarea');
                inputs.forEach(el => el.disabled = true);
                var verifyBtn = document.getElementById('prac-verify-btn');
                if (verifyBtn) verifyBtn.disabled = true;

                stats.totalAttempts++;
                
                // Get mistake diagnostic and error vector
                const diag = diagnosePracticeMistake(currentPracProblem.category, currentPracProblem.templateId, currentPracProblem.mathDetails, currentPracProblem.correctAnswers);
                const errorVector = diag ? diag.vector : null;
                
                // Update cognitive state with failure details (this will update belief again and run the tau Spacing Spacing Controller)
                window.Controllers.sessionController.updateCognitiveState(activeTopic, false, 2, errorVector);
                
                det.innerHTML = getWalkthroughHTML(currentPracProblem.category, tid, currentPracProblem.mathDetails, c);
                
                const mistPanel = document.getElementById('prac-mistake-analysis');
                if (diag && mistPanel) {
                    mistPanel.style.display = 'flex';
                    mistPanel.innerHTML = `
                        <div class="mistake-title">⚠️ Cognitive Trap Detected: ${diag.title}</div>
                        <div class="mistake-desc">${diag.desc}</div>
                        <div class="mistake-remedy">💡 Remedy: ${diag.remedy}</div>
                    `;
                    
                    // Add to mistakes log
                    if (!stats.mistakesLog) stats.mistakesLog = [];
                    diag.category = activeTopic;
                    if (!stats.mistakesLog.some(m => m.title === diag.title)) {
                        stats.mistakesLog.unshift(diag);
                        if (stats.mistakesLog.length > 5) stats.mistakesLog.pop();
                    }
                }
                
                stats.streak = 0;
                
                // Add topic to review queue
                if (!stats.spacedRepQueue.some(i => i.category === currentPracProblem.category)) {
                    stats.spacedRepQueue.push({
                        category: currentPracProblem.category, name: getCategoryDisplayName(currentPracProblem.category), dueDate: Date.now() + 60*1000
                    });
                }

                // Adaptive Difficulty: track consecutive incorrect streak
                if (stats.consecutiveStats && stats.consecutiveStats[activeTopic]) {
                    const cs = stats.consecutiveStats[activeTopic];
                    cs.incorrect++;
                    cs.correct = 0;
                    if (cs.incorrect >= 2) {
                        if (cs.activeDifficulty === 'hard') cs.activeDifficulty = 'intermediate';
                        else if (cs.activeDifficulty === 'intermediate') cs.activeDifficulty = 'easy';
                        cs.hintsEnabled = true;
                        cs.incorrect = 0;
                    }
                }
                
                panel.style.display = 'block';
                const titleEl = document.getElementById('prac-solution-title');
                const textEl = document.getElementById('prac-solution-xp-text');
                
                titleEl.innerText = "Incorrect answers ❌"; 
                titleEl.style.color = 'var(--danger)';
                textEl.innerText = "Topic added to Spaced Repetition Queue. Review the trap analysis and solution path below."; 
                textEl.style.color = 'var(--danger)';
                
                // Hide Feynman and SRS
                document.getElementById('feynman-challenge-panel').style.display = 'none';
                document.getElementById('srs-rating-panel').style.display = 'none';
                
                // Show worked steps immediately
                det.style.display = 'block';
                
                // Reset attempt number for next challenge
                currentAttemptNum = 1;
                var verifyBtn = document.getElementById('prac-verify-btn');
                if (verifyBtn) verifyBtn.innerText = "Verify Answer";
                
                window.UI.appUI.updateAllUI();
                window.Storage.saveStats();
                panel.scrollIntoView({ behavior: 'smooth' });
            }
        }
    }

    function showReflectionCheckpoint() {
        const sPanel = document.getElementById('prac-solution-panel');
        const stepsEl = document.getElementById('prac-detailed-steps');
        const srsPanel = document.getElementById('srs-rating-panel');
        const feynmanPanel = document.getElementById('feynman-challenge-panel');
        const mistPanel = document.getElementById('prac-mistake-analysis');
        
        stepsEl.style.display = 'none';
        srsPanel.style.display = 'none';
        feynmanPanel.style.display = 'none';
        document.getElementById('prac-active-buttons').style.display = 'none';
        
        const mistake = diagnosePracticeMistake(currentPracProblem.category, currentPracProblem.templateId, currentPracProblem.mathDetails, currentPracProblem.correctAnswers);
        if (mistake && mistPanel) {
            mistPanel.style.display = 'flex';
            mistPanel.innerHTML = `
                <div style="font-weight:700; color:var(--warning); margin-bottom: 4px;">⚠️ Diagnosed Misconception: ${mistake.title}</div>
                <div style="font-size:12px; line-height:1.4; color:white;">${mistake.desc}</div>
                <div style="font-size:11px; color:var(--text-secondary); margin-top:4px; font-style:italic;">
                    <strong>Explanation:</strong> ${mistake.explanation || "Review standard formulas and check calculations."}
                </div>
            `;
        } else {
            if (mistPanel) mistPanel.style.display = 'none';
        }
        
        sPanel.style.display = 'block';
        const titleEl = document.getElementById('prac-solution-title');
        const textEl = document.getElementById('prac-solution-xp-text');
        
        titleEl.innerText = "First Attempt Incorrect ❌";
        titleEl.style.color = 'var(--warning)';
        textEl.innerHTML = `<span style="color:var(--text-secondary);">Your calculation does not match. Let's reflect on the mistake to unlock your second (final) attempt.</span>`;
        
        currentPracticeReflection = { selectedCategory: '', reflectionText: '' };
        
        let refContainer = document.getElementById('prac-reflection-container');
        if (!refContainer) {
            refContainer = document.createElement('div');
            refContainer.id = 'prac-reflection-container';
            sPanel.appendChild(refContainer);
        }
        refContainer.style.display = 'block';
        refContainer.innerHTML = `
            <div style="background-color: rgba(244, 63, 94, 0.05); border: 1px solid rgba(244, 63, 94, 0.2); padding: 14px; border-radius: 8px; margin-top: 15px; margin-bottom: 15px;">
                <h4 style="color: white; font-size: 13px; margin-top:0; margin-bottom: 6px; font-family:'Outfit', sans-serif; display:flex; align-items:center; gap:6px;">
                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 18px; height: 18px; stroke: #f43f5e;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
                    Metacognitive Error Reflection Checkpoint
                </h4>
                <p style="font-size: 11px; color: var(--text-secondary); margin-bottom: 12px; line-height:1.4;">
                    Select what caused this calculation mismatch. Understanding your own errors prevents repetitions.
                </p>
                
                <div style="margin-bottom: 12px;">
                    <span style="font-size:11px; font-weight:700; color:white; margin-bottom: 6px; display:block;">Primary mistake category:</span>
                    <div style="display:flex; flex-direction:column; gap:6px;">
                        <label style="font-size:12px; color:var(--text-secondary); display:flex; align-items:center; gap:6px; cursor:pointer;">
                            <input type="radio" name="error-source" value="arithmetic" onclick="selectReflectionCategory('Arithmetic/Calculation error')"> Arithmetic error / Calculator typo
                        </label>
                        <label style="font-size:12px; color:var(--text-secondary); display:flex; align-items:center; gap:6px; cursor:pointer;">
                            <input type="radio" name="error-source" value="formula" onclick="selectReflectionCategory('Formula / Method mix-up')"> Formula or method mix-up (e.g. WA vs FIFO)
                        </label>
                        <label style="font-size:12px; color:var(--text-secondary); display:flex; align-items:center; gap:6px; cursor:pointer;">
                            <input type="radio" name="error-source" value="rounding" onclick="selectReflectionCategory('Rounding / Decimal precision')"> Rounding or decimal precision error
                        </label>
                        <label style="font-size:12px; color:var(--text-secondary); display:flex; align-items:center; gap:6px; cursor:pointer;">
                            <input type="radio" name="error-source" value="parameter" onclick="selectReflectionCategory('Parameter misinterpretation')"> Misread parameters or text guidelines
                        </label>
                    </div>
                </div>
                
                <div class="form-group" style="margin-bottom: 12px;">
                    <label class="form-label" style="font-size:11px;">What will you do differently next time?</label>
                    <input class="form-input" id="prac-reflection-input" placeholder="e.g. I will multiply by actual quantity purchased instead of standard..." style="font-size:12px; padding: 6px 10px;">
                </div>
                
                <button class="btn btn-primary" onclick="submitReflectionCheckpoint()" style="font-size:12px; padding: 6px 12px; background-color:#f43f5e; border-color:#f43f5e; color:white;">Submit Reflection & Unlock 2nd Attempt (+2 XP)</button>
            </div>
        `;
        
        sPanel.scrollIntoView({ behavior: 'smooth' });
    }

    function selectReflectionCategory(cat) {
        currentPracticeReflection.selectedCategory = cat;
        
        const activeTopic = currentPracProblem.category === 'fifo' ? 'costing' : currentPracProblem.category;
        const belief = stats.beliefProfile[activeTopic] || { slip: 0.333, procedural: 0.333, conceptual: 0.334 };
        
        let sTip = document.getElementById('socratic-audit-tip');
        if (!sTip) {
            sTip = document.createElement('div');
            sTip.id = 'socratic-audit-tip';
            const inputEl = document.getElementById('prac-reflection-input');
            if (inputEl) {
                const refInputGroup = inputEl.closest('.form-group');
                if (refInputGroup) {
                    refInputGroup.parentNode.insertBefore(sTip, refInputGroup);
                }
            }
        }
        
        // Decoupled Socratic Audit call
        const audit = window.Cognitive.reflectionEngine.compareReflectionToBelief(cat, belief);
        
        if (audit.mismatchDetected) {
            if (sTip) {
                sTip.style.display = 'block';
                sTip.innerHTML = `
                    <div style="background-color: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); padding: 10px; border-radius: 6px; margin-bottom: 12px; font-size: 11px; color: #f59e0b; line-height: 1.4;">
                        <strong>Diagnostic Tip:</strong> ${audit.diagnosticTip}
                    </div>
                `;
            }
        } else {
            if (sTip) sTip.style.display = 'none';
        }
    }

    function submitReflectionCheckpoint() {
        if (!currentPracticeReflection.selectedCategory) {
            alert("Please select your error category first!");
            return;
        }
        const val = document.getElementById('prac-reflection-input').value.trim();
        if (!val) {
            alert("Please write a quick reflection note to help commit the lesson to memory.");
            return;
        }
        currentPracticeReflection.reflectionText = val;
        
        // Award reflection XP
        stats.xp += 2;
        stats.reflectionStats = stats.reflectionStats || { reflectionAttempts: 0, reflectionCorrect: 0 };
        stats.reflectionStats.reflectionAttempts++;
        
        // Append mistake log
        const mistake = diagnosePracticeMistake(currentPracProblem.category, currentPracProblem.templateId, currentPracProblem.mathDetails, currentPracProblem.correctAnswers);
        if (mistake && stats.mistakesLog) {
            if (!stats.mistakesLog.some(m => m.title === mistake.title)) {
                stats.mistakesLog.unshift({
                    category: currentPracProblem.category === 'fifo' ? 'costing' : currentPracProblem.category,
                    title: mistake.title,
                    desc: mistake.desc + ` | Note: ${currentPracticeReflection.reflectionText}`,
                    remedy: mistake.remedy
                });
            }
        }
        
        // Unlock inputs
        const inputs = document.getElementById('prac-question-prompt').querySelectorAll('input, select, textarea');
        inputs.forEach(el => {
            el.disabled = false;
            el.style.border = '';
            el.style.boxShadow = '';
        });
        
        // Clear Socratic audit tip
        currentPracProblem.status = 'ACTIVE';
        const sTip = document.getElementById('socratic-audit-tip');
        if (sTip) sTip.style.display = 'none';
        
        // Increment attempt number and change button text
        currentAttemptNum = 2;
        var verifyBtn = document.getElementById('prac-verify-btn');
        if (verifyBtn) verifyBtn.innerText = "Check Answer (Final Attempt)";
        
        window.UI.appUI.updateAllUI();
        window.Storage.saveStats();
        
        // Hide reflection panel
        document.getElementById('prac-reflection-container').style.display = 'none';
        document.getElementById('prac-solution-panel').style.display = 'none';
        
        // Show active buttons
        document.getElementById('prac-active-buttons').style.display = 'flex';
        
        alert("Metacognitive reflection recorded! Your inputs have been unlocked. Please correct your answers and submit your final attempt.");
    }

    function updatePracticePdfRecommendations(category) {
        const container = document.getElementById('prac-pdf-study-recommendations');
        if (!container) return;

        const sessionMap = {
            'concepts': { key: 's1-concepts', num: 1, name: 'Session 1: Cost Concepts' },
            'costing': { key: 's2-fifo', num: 2, name: 'Session 2: Process Costing' },
            'fifo': { key: 's2-fifo', num: 2, name: 'Session 2: Process Costing' },
            'cvp': { key: 's3-cvp', num: 3, name: 'Session 3: CVP & Bottlenecks' },
            'abc': { key: 's4-abc', num: 4, name: 'Session 4: Activity-Based Costing' },
            'variance': { key: 's5-variance', num: 5, name: 'Session 5: Variance Analysis' }
        };

        const sessionInfo = sessionMap[category];
        if (!sessionInfo) {
            container.style.display = 'none';
            return;
        }

        if (!window.Storage || !window.Storage.knowledgeBase || !window.Storage.knowledgeBase.rawPages) {
            container.style.display = 'none';
            return;
        }

        const pages = window.Storage.knowledgeBase.rawPages.filter(p => p.session === sessionInfo.num);
        if (pages.length === 0) {
            container.style.display = 'none';
            return;
        }

        const recommendations = [];
        pages.forEach(p => {
            if (p.text.toLowerCase().includes('solution') || p.text.toLowerCase().includes('exercise')) {
                if (recommendations.length < 3) {
                    recommendations.push(p);
                }
            }
        });

        pages.forEach(p => {
            if (recommendations.length < 3 && !recommendations.includes(p)) {
                recommendations.push(p);
            }
        });

        recommendations.sort((a, b) => a.page - b.page);

        container.style.display = 'block';
        container.innerHTML = `
            <div style="font-size: 11px; text-transform: uppercase; color: var(--accent-primary); font-weight: 700; margin-bottom: 8px; display: flex; align-items: center; gap: 4px;">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 14px; height: 14px; stroke: var(--accent-primary);"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
                Recommended PDF Slides for Study
            </div>
            <p style="font-size: 11px; color: var(--text-secondary); margin-bottom: 10px;">The cognitive assistant has retrieved relevant slides from your course material to help you solve this challenge.</p>
            <div style="display: flex; flex-direction: column; gap: 8px;">
                ${recommendations.map(r => {
                    const snippet = r.text.length > 90 ? r.text.slice(0, 90) + '...' : r.text;
                    return `
                        <div style="background-color: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-color); padding: 8px 10px; border-radius: 6px; display: flex; flex-direction: column; gap: 4px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 11px; font-weight: 700; color: white;">Page ${r.page}: ${r.sessionTitle}</span>
                                <button class="btn btn-secondary" onclick="window.goToLearnSlide('${sessionInfo.key}', ${r.page})" style="font-size: 10px; padding: 2px 6px; line-height: 1; border-color: var(--accent-primary); color: var(--accent-primary);">View Slide 📖</button>
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.3;">${snippet}</div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }

    // Expose functions under window.Controllers.practiceController namespace
    window.Controllers.practiceController.startChallenge = startPracticeChallenge;
    window.Controllers.practiceController.submitAttempt = verifyPracticeAnswer;
    window.Controllers.practiceController.submitReflection = submitReflectionCheckpoint;
    window.Controllers.practiceController.rateSRS = rateSRS;
    window.Controllers.practiceController.updatePracticePdfRecommendations = updatePracticePdfRecommendations;
    
    // Bind global aliases
    window.startPracticeChallenge = startPracticeChallenge;
    window.exitActivePractice = exitActivePractice;
    window.rateSRS = rateSRS;
    window.submitFeynmanExplanation = submitFeynmanExplanation;
    window.verifyPracticeAnswer = verifyPracticeAnswer;
    window.showReflectionCheckpoint = showReflectionCheckpoint;
    window.selectReflectionCategory = selectReflectionCategory;
    window.submitReflectionCheckpoint = submitReflectionCheckpoint;
    window.updatePracticePdfRecommendations = updatePracticePdfRecommendations;

})();