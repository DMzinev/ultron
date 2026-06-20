// cognitive/scaffoldingEngine.js
(function() {
    window.Cognitive = window.Cognitive || {};

    window.Cognitive.scaffoldingEngine = {
        determineHintTier: function(topic) {
            if (topic === 'fifo') topic = 'costing';
            return (!stats.consecutiveStats || !stats.consecutiveStats[topic] || stats.consecutiveStats[topic].hintsEnabled !== false);
        },

        getPracHint: function(tier) {
            const box = document.getElementById('prac-hint-textbox');
            if (!box) return;
            box.style.display = 'block';
            if (!currentPracProblem) return;

            const tid = currentPracProblem.templateId;
            const cat = currentPracProblem.category;
            const md = currentPracProblem.mathDetails;

            // Map category name for Domain lookups
            const domainCat = cat === 'fifo' ? 'Costing' : (cat === 'concepts' ? 'Concepts' : (cat === 'cvp' ? 'CVP' : (cat === 'abc' ? 'ABC' : 'Variance')));

            if (tier === 1) {
                let hintContent = "";
                if (window.Domain && window.Domain[domainCat] && window.Domain[domainCat].getHint) {
                    hintContent = window.Domain[domainCat].getHint(tid, 1, md);
                }
                box.innerHTML = "<strong>Conceptual Hint:</strong> " + hintContent;
            } else if (tier === 2) {
                stats.xp = Math.max(0, stats.xp - 5);
                if (window.UI && window.UI.appUI && window.UI.appUI.updateStatsHUD) {
                    window.UI.appUI.updateStatsHUD(); // update HUD XP display
                } else if (window.updateStatsHUD) {
                    window.updateStatsHUD();
                }
                window.Storage.saveStats();

                let hintContent = "";
                if (window.Domain && window.Domain[domainCat] && window.Domain[domainCat].getHint) {
                    hintContent = window.Domain[domainCat].getHint(tid, 2, md);
                }
                box.innerHTML = "<strong>Formula Blueprint (-5 XP):</strong> " + hintContent;
            } else if (tier === 3) {
                stats.xp = Math.max(0, stats.xp - 10);
                if (window.UI && window.UI.appUI && window.UI.appUI.updateStatsHUD) {
                    window.UI.appUI.updateStatsHUD();
                } else if (window.updateStatsHUD) {
                    window.updateStatsHUD();
                }
                window.Storage.saveStats();

                let hintContent = "";
                if (window.Domain && window.Domain[domainCat] && window.Domain[domainCat].getHint) {
                    hintContent = window.Domain[domainCat].getHint(tid, 3, md);
                }
                box.innerHTML = "<strong>Numerical Setup (-10 XP):</strong> " + hintContent;
            } else if (tier === 4) {
                box.innerHTML = `<strong>Solution Loaded.</strong> Correct outputs have been pre-filled. You forfeit XP for this exercise.`;
                currentPracProblem.forfeited = true;
                
                const c = currentPracProblem.correctAnswers;
                if (cat === 'concepts') {
                    if (tid === 0) {
                        document.getElementById('c-ans-q1-di').value = c.q1_di;
                        document.getElementById('c-ans-q1-vf').value = c.q1_vf;
                    } else if (tid === 1) {
                        document.getElementById('c-tot500').value = c.tot500;
                        document.getElementById('c-unit500').value = c.unit500;
                        document.getElementById('c-tot2000').value = c.tot2000;
                        document.getElementById('c-unit2000').value = c.unit2000;
                    } else if (tid === 2) {
                        document.getElementById('c-func').value = c.func;
                    }
                } else if (cat === 'abc') {
                    if (tid === 0) {
                        document.getElementById('ans-trad-rate').value = c.tradRate;
                        document.getElementById('ans-trad-costA').value = c.tradCostA;
                        document.getElementById('ans-trad-costB').value = c.tradCostB;
                        document.getElementById('ans-abc-costA').value = c.abcCostA;
                        document.getElementById('ans-abc-costB').value = c.abcCostB;
                    } else {
                        document.getElementById('ans-restruct-profit').value = c.profit;
                        document.getElementById('ans-restruct-per-tile').value = c.perTile;
                    }
                } else if (cat === 'variance') {
                    if (tid === 0) {
                        document.getElementById('ans-dm-price').value = Math.abs(c.dmPriceVar);
                        document.getElementById('effect-dm-price').value = c.dmPriceVar >= 0 ? 'F' : 'U';
                        document.getElementById('ans-dm-eff').value = Math.abs(c.dmEffVar);
                        document.getElementById('effect-dm-eff').value = c.dmEffVar >= 0 ? 'F' : 'U';
                        document.getElementById('ans-dl-price').value = Math.abs(c.dlPriceVar);
                        document.getElementById('effect-dl-price').value = c.dlPriceVar >= 0 ? 'F' : 'U';
                        document.getElementById('ans-dl-eff').value = Math.abs(c.dlEffVar);
                        document.getElementById('effect-dl-eff').value = c.dlEffVar >= 0 ? 'F' : 'U';
                    } else {
                        document.getElementById('ans-seq-prod').value = c.prod;
                        document.getElementById('ans-seq-sales').value = c.sales;
                        document.getElementById('ans-seq-dm').value = c.dm;
                        document.getElementById('ans-seq-op').value = c.op;
                        document.getElementById('ans-seq-bs').value = c.bs;
                    }
                } else if (cat === 'fifo') {
                    if (tid === 0) {
                        document.getElementById('ans-fifo-dm-eu').value = c.currDmEU;
                        document.getElementById('ans-fifo-conv-eu').value = c.currConvEU;
                        document.getElementById('ans-fifo-dm-rate').value = c.rateDM;
                        document.getElementById('ans-fifo-conv-rate').value = c.rateConv;
                    } else if (tid === 1) {
                        document.getElementById('ans-rate-billable').value = c.rateBillable;
                        document.getElementById('ans-rate-total').value = c.rateTotal;
                    } else {
                        document.getElementById('ans-oh-rate').value = c.ohRate;
                        document.getElementById('ans-oh-allocated').value = c.ohAllocated;
                        document.getElementById('ans-oh-diff').value = c.ohDiff;
                    }
                } else if (cat === 'cvp') {
                    if (tid === 0) {
                        document.getElementById('ans-cvp-cmu').value = c.cmu;
                        document.getElementById('ans-cvp-be').value = c.be;
                        document.getElementById('ans-cvp-profit').value = c.profit;
                    } else {
                        document.getElementById('ans-bottle-cm-case').value = c.cmCase;
                        document.getElementById('ans-bottle-cm-meter').value = c.cmMeter;
                    }
                }
                
                // Automatically verify and submit as forfeited to show solutions and next buttons
                if (window.verifyPracticeAnswer) {
                    window.verifyPracticeAnswer();
                } else if (typeof verifyPracticeAnswer === 'function') {
                    verifyPracticeAnswer();
                }
            }
        }
    };

    // Keep global alias for compatibility
    window.getPracHint = window.Cognitive.scaffoldingEngine.getPracHint;

})();