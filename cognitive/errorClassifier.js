// cognitive/errorClassifier.js
(function() {
    window.Cognitive = window.Cognitive || {};

    function diagnosePracticeMistake(category, templateId, mathDetails, correctAnswers, examAnsObj) {
                if (!mathDetails) return null;
                const tol = 0.25;
                
                function getVal(id, examObj, examKey) {
                    if (examObj && examObj[examKey] !== undefined) {
                        return examObj[examKey];
                    }
                    const el = document.getElementById(id);
                    return el ? el.value : '';
                }
                
                if (category === 'concepts' && templateId === 1) {
                    const tot2000 = parseFloat(getVal('c-tot2000', examAnsObj, 'tot2000')) || 0;
                    if (Math.abs(tot2000 - mathDetails.fixedFee * (mathDetails.p2 / mathDetails.p1)) < 5.0) {
                        return {
                            type: 'CONCEPTUAL',
                            vector: { slip: 0.1, procedural: 0.1, conceptual: 0.8 },
                            title: "Fixed Cost Behaved as Variable",
                            desc: `You calculated Scenario 2 total cost as €${tot2000.toLocaleString()} by multiplying/scaling total cost with attendance.`,
                            remedy: `The music group is a FIXED fee of €${mathDetails.fixedFee.toLocaleString()}. Its total cost remains €${mathDetails.fixedFee.toLocaleString()} regardless of whether ${mathDetails.p1} or ${mathDetails.p2} people attend.`,
                            explanation: "This mistake occurs because total fixed costs do not vary with volume changes; they remain constant in aggregate."
                        };
                    }
                } else if (category === 'fifo' && templateId === 0) {
                    const dmEU = parseFloat(getVal('ans-fifo-dm-eu', examAnsObj, 'dmEU')) || 0;
                    const expectedWA = mathDetails.completed + (mathDetails.clUnits * mathDetails.clDmPct);
                    if (Math.abs(dmEU - expectedWA) < 1.0) {
                        return {
                            type: 'CONCEPTUAL',
                            vector: { slip: 0.0, procedural: 0.2, conceptual: 0.8 },
                            title: "Weighted Average vs. FIFO Mix-up",
                            desc: "You computed DM Equivalent Units as Completed + Ending WIP, which is the Weighted Average method.",
                            remedy: "Under FIFO, we only measure work performed in the current period. You must subtract opening WIP equivalent units from your total.",
                            explanation: "This mistake occurs because Weighted-Average combines prior-period and current-period work, while FIFO isolates current-period effort."
                        };
                    }
                } else if (category === 'fifo' && templateId === 1) {
                    const rateBillable = parseFloat(getVal('ans-rate-billable', examAnsObj, 'rateBillable')) || 0;
                    const correctTotal = correctAnswers ? correctAnswers.rateTotal : 0;
                    if (Math.abs(rateBillable - correctTotal) < tol) {
                        return {
                            type: 'PROCEDURAL',
                            vector: { slip: 0.1, procedural: 0.7, conceptual: 0.2 },
                            title: "Billing Rate Denominators Swapped",
                            desc: "You entered the lower rate (from total hours) for Scenario 1 (billable hours).",
                            remedy: "Scenario 1 uses a smaller denominator (only client-billable hours), which must yield a HIGHER rate.",
                            explanation: "This mistake occurs because spreading cost over fewer hours (billable hours) increases the cost rate per hour."
                        };
                    }
                } else if (category === 'fifo' && templateId === 2) {
                    const ohDiff = parseFloat(getVal('ans-oh-diff', examAnsObj, 'ohDiff')) || 0;
                    const actualOHDiff = correctAnswers ? correctAnswers.ohDiff : 0;
                    if (Math.abs(ohDiff + actualOHDiff) < 5.0 && ohDiff !== actualOHDiff) {
                        return {
                            type: 'PROCEDURAL',
                            vector: { slip: 0.2, procedural: 0.7, conceptual: 0.1 },
                            title: "Under/Overallocated Sign Swap",
                            desc: "You calculated the correct absolute amount but entered the wrong sign (swapping over-allocated and under-allocated status).",
                            remedy: "If Allocated Overhead is less than Actual Overhead, overhead is UNDER-allocated (represented as a negative amount).",
                            explanation: "This mistake occurs because if the actual overhead spent is higher than what was allocated to products, standard cost is under-allocated."
                        };
                    }
                } else if (category === 'cvp' && templateId === 0) {
                    const be = parseFloat(getVal('ans-cvp-be', examAnsObj, 'be')) || 0;
                    const exactBe = mathDetails.fc / mathDetails.cmu;
                    const correctBe = correctAnswers ? correctAnswers.be : 0;
                    
                    if (be !== correctBe && (Math.abs(be - exactBe) < 0.1 || be === Math.floor(exactBe))) {
                        return {
                            type: 'PROCEDURAL',
                            vector: { slip: 0.3, procedural: 0.6, conceptual: 0.1 },
                            title: "Unrounded/Rounded-down Breakeven Point",
                            desc: "You entered a fractional or rounded-down value for the breakeven quantity.",
                            remedy: "Round the breakeven quantity up to the next integer: " + Math.ceil(exactBe) + " units.",
                            explanation: "This mistake occurs because you cannot produce or sell a fraction of a unit. To truly break even (cover all fixed costs), any fractional unit must be rounded UP to the next whole unit."
                        };
                    }
                    
                    const vcDivision = Math.ceil(mathDetails.fc / mathDetails.vc);
                    if (Math.abs(be - vcDivision) < 5) {
                        return {
                            type: 'CONCEPTUAL',
                            vector: { slip: 0.1, procedural: 0.1, conceptual: 0.8 },
                            title: "Divided Fixed Cost by Variable Cost",
                            desc: "Your Breakeven Units match dividing Fixed Cost by Variable Cost directly.",
                            remedy: "Breakeven Quantity = Fixed Cost / Contribution Margin per unit (Price - Variable Cost). You must divide by CM (€" + mathDetails.cmu.toFixed(2) + ") instead of VC (€" + mathDetails.vc.toFixed(2) + ").",
                            explanation: "This mistake occurs because fixed costs must be recovered by the margin contribution (Price - Variable Cost), not the variable cost itself."
                        };
                    }
                } else if (category === 'cvp' && templateId === 1) {
                    const cmMeter = parseFloat(getVal('ans-bottle-cm-meter', examAnsObj, 'cmMeter')) || 0;
                    const dividedVal = mathDetails.cmCase / mathDetails.casesPerMeter;
                    if (Math.abs(cmMeter - dividedVal) < 0.1) {
                        return {
                            type: 'CONCEPTUAL',
                            vector: { slip: 0.0, procedural: 0.2, conceptual: 0.8 },
                            title: "Divided by Bottleneck instead of Multiplying",
                            desc: "You divided contribution margin per case by capacity cases per meter.",
                            remedy: "Since a meter fits " + mathDetails.casesPerMeter + " cases and each case yields €" + mathDetails.cmCase.toFixed(2) + " CM, a shelf-meter yields: CM per case × cases per meter = €" + (correctAnswers ? correctAnswers.cmMeter.toFixed(2) : '0.00') + ".",
                            explanation: "This mistake occurs because linear capacity indicates cases sold PER meter, which must scale up direct contribution."
                        };
                    }
                } else if (category === 'abc' && templateId === 0) {
                    const tradRate = parseFloat(getVal('ans-trad-rate', examAnsObj, 'tr')) || 0;
                    const incorrectDenomA = mathDetails.totalOH / mathDetails.volA;
                    const incorrectDenomB = mathDetails.totalOH / mathDetails.volB;
                    if (Math.abs(tradRate - incorrectDenomA) < 1.0 || Math.abs(tradRate - incorrectDenomB) < 1.0) {
                        return {
                            type: 'CONCEPTUAL',
                            vector: { slip: 0.1, procedural: 0.2, conceptual: 0.7 },
                            title: "Single Model Volume Denominator",
                            desc: "You calculated the traditional overhead rate using only one model's volume as the denominator.",
                            remedy: "Under traditional allocation, compute a single rate by dividing total overhead by the COMBINED volume of Premium + Basic.",
                            explanation: "This mistake occurs because plant-wide overhead rates require scaling costs by the total allocation base of all products combined."
                        };
                    }
                } else if (category === 'variance' && templateId === 0) {
                    const dmPrice = parseFloat(getVal('ans-dm-price', examAnsObj, 'dmPrice')) || 0;
                    const dmPeff = getVal('effect-dm-price', examAnsObj, 'dmPeff');
                    const dmEff = parseFloat(getVal('ans-dm-eff', examAnsObj, 'dmEff')) || 0;
                    const dmEeff = getVal('effect-dm-eff', examAnsObj, 'dmEeff');
                    
                    const dmPriceCorrectVal = correctAnswers ? Math.abs(correctAnswers.dmPriceVar) : 0;
                    const dmPriceCorrectEff = correctAnswers ? (correctAnswers.dmPriceVar >= 0 ? 'F' : 'U') : 'F';
                    const dmEffCorrectVal = correctAnswers ? Math.abs(correctAnswers.dmEffVar) : 0;
                    const dmEffCorrectEff = correctAnswers ? (correctAnswers.dmEffVar >= 0 ? 'F' : 'U') : 'F';
                    
                    // Price quantity base error checking
                    const stdQtyAllowed = mathDetails.actualVol * mathDetails.stdDM_qty;
                    const wrongPriceVarSq = Math.abs((mathDetails.stdDM_price - mathDetails.actDM_price) * stdQtyAllowed);
                    if (Math.abs(dmPrice - wrongPriceVarSq) < 5.0) {
                        return {
                            type: 'CONCEPTUAL',
                            vector: { slip: 0.0, procedural: 0.2, conceptual: 0.8 },
                            title: "Direct Materials Price Variance Quantity Base Error",
                            desc: "You calculated the price variance on the standard quantity allowed rather than actual quantity used/purchased.",
                            remedy: "Multiply the price difference by the actual quantity used instead of the standard quantity allowed.",
                            explanation: "This mistake occurs because price variances measure the price difference on the actual materials purchased, not standard materials allowed."
                        };
                    }
                    
                    // Static budget volume error checking
                    const wrongEffVarSb = Math.abs((mathDetails.budgetedVol * mathDetails.stdDM_qty - mathDetails.actDM_qty) * mathDetails.stdDM_price);
                    if (Math.abs(dmEff - wrongEffVarSb) < 5.0) {
                        return {
                            type: 'CONCEPTUAL',
                            vector: { slip: 0.0, procedural: 0.2, conceptual: 0.8 },
                            title: "Static Budget Volume Error",
                            desc: "You calculated the DM efficiency variance using the budgeted volume rather than the actual volume achieved.",
                            remedy: "Use actual production achieved to calculate standard materials allowed, rather than budgeted production.",
                            explanation: "This mistake occurs because flexible budget variances must compare actual quantities to the flexible budget standard for the actual volume achieved, not the static budget volume."
                        };
                    }
                    
                    if (Math.abs(dmPrice - dmPriceCorrectVal) < 5.0 && dmPeff !== dmPriceCorrectEff && dmPeff !== '') {
                        return {
                            type: 'PROCEDURAL',
                            vector: { slip: 0.2, procedural: 0.7, conceptual: 0.1 },
                            title: "Variance Effect Direction Confusion",
                            desc: "Your variance amount is correct, but you labeled it incorrectly.",
                            remedy: "If Actual Price/Rate is lower than Standard, you spent less than standard, making the variance Favorable (F).",
                            explanation: "This mistake occurs because if the actual cost paid is lower than standard cost budgeted, it is Favorable. If actual is higher, it is Unfavorable."
                        };
                    }
                    if (Math.abs(dmEff - dmEffCorrectVal) < 5.0 && dmEeff !== dmEffCorrectEff && dmEeff !== '') {
                        return {
                            type: 'PROCEDURAL',
                            vector: { slip: 0.2, procedural: 0.7, conceptual: 0.1 },
                            title: "Efficiency Variance Direction Confusion",
                            desc: "Your DM efficiency variance amount is correct, but you labeled it incorrectly.",
                            remedy: "If Actual Quantity used is less than Standard Quantity allowed, it is Favorable (F).",
                            explanation: "This mistake occurs because if the actual quantity of input consumed is lower than what was budgeted/standard for that volume, it is Favorable (F)."
                        };
                    }
                }
                
                // Fallback for general errors
                if (correctAnswers) {
                    const inputs = document.querySelectorAll('#prac-question-prompt input, #prac-question-prompt select');
                    let isAnyInputFilled = false;
                    let totalNumericError = 0;
                    let numericCount = 0;
                    
                    inputs.forEach(el => {
                        const id = el.id;
                        let userVal = el.value.trim();
                        if (userVal !== '') {
                            isAnyInputFilled = true;
                            const fVal = parseFloat(userVal);
                            if (!isNaN(fVal)) {
                                let correctVal = null;
                                if (id === 'ans-fifo-dm-eu') correctVal = correctAnswers.currDmEU;
                                else if (id === 'ans-fifo-conv-eu') correctVal = correctAnswers.currConvEU;
                                else if (id === 'ans-fifo-dm-rate') correctVal = correctAnswers.rateDM;
                                else if (id === 'ans-fifo-conv-rate') correctVal = correctAnswers.rateConv;
                                else if (id === 'ans-rate-billable') correctVal = correctAnswers.rateBillable;
                                else if (id === 'ans-rate-total') correctVal = correctAnswers.rateTotal;
                                else if (id === 'ans-oh-rate') correctVal = correctAnswers.ohRate;
                                else if (id === 'ans-oh-allocated') correctVal = correctAnswers.ohAllocated;
                                else if (id === 'ans-oh-diff') correctVal = correctAnswers.ohDiff;
                                else if (id === 'ans-cvp-cmu') correctVal = correctAnswers.cmu;
                                else if (id === 'ans-cvp-be') correctVal = correctAnswers.be;
                                else if (id === 'ans-cvp-profit') correctVal = correctAnswers.profit;
                                else if (id === 'ans-bottle-cm-case') correctVal = correctAnswers.cmCase;
                                else if (id === 'ans-bottle-cm-meter') correctVal = correctAnswers.cmMeter;
                                else if (id === 'ans-trad-rate') correctVal = correctAnswers.tradRate;
                                else if (id === 'ans-trad-costA') correctVal = correctAnswers.tradCostA;
                                else if (id === 'ans-trad-costB') correctVal = correctAnswers.tradCostB;
                                else if (id === 'ans-abc-costA') correctVal = correctAnswers.abcCostA;
                                else if (id === 'ans-abc-costB') correctVal = correctAnswers.abcCostB;
                                else if (id === 'ans-restruct-profit') correctVal = correctAnswers.profit;
                                else if (id === 'ans-restruct-per-tile') correctVal = correctAnswers.perTile;
                                else if (id === 'ans-dm-price') correctVal = Math.abs(correctAnswers.dmPriceVar);
                                else if (id === 'ans-dm-eff') correctVal = Math.abs(correctAnswers.dmEffVar);
                                else if (id === 'ans-dl-price') correctVal = Math.abs(correctAnswers.dlPriceVar);
                                else if (id === 'ans-dl-eff') correctVal = Math.abs(correctAnswers.dlEffVar);
                                else if (id === 'c-tot500') correctVal = correctAnswers.tot500;
                                else if (id === 'c-unit500') correctVal = correctAnswers.unit500;
                                else if (id === 'c-tot2000') correctVal = correctAnswers.tot2000;
                                else if (id === 'c-unit2000') correctVal = correctAnswers.unit2000;
                                
                                if (correctVal !== null) {
                                    numericCount++;
                                    if (correctVal !== 0) {
                                        totalNumericError += Math.abs(fVal - correctVal) / Math.abs(correctVal);
                                    } else {
                                        totalNumericError += Math.abs(fVal);
                                    }
                                }
                            }
                        }
                    });
                    
                    if (isAnyInputFilled) {
                        const avgError = numericCount > 0 ? (totalNumericError / numericCount) : 1.0;
                        if (avgError < 0.05) {
                            return {
                                type: 'SLIP',
                                vector: { slip: 0.8, procedural: 0.1, conceptual: 0.1 },
                                title: "Calculation Slip",
                                desc: "The inputs are very close to the correct answers, suggesting a small mathematical or rounding typo.",
                                remedy: "Review intermediate calculation stages and ensure proper input precision.",
                                explanation: "This slip occurs due to simple calculation slip or numeric input typos."
                            };
                        } else {
                            return {
                                type: 'CONCEPTUAL',
                                vector: { slip: 0.1, procedural: 0.4, conceptual: 0.5 },
                                title: "Procedural Discrepancy",
                                desc: "Your calculated answers deviate significantly from the expected solution path.",
                                remedy: "Review the formula guidelines, standard rates, and step-by-step illustrations.",
                                explanation: "This discrepancy occurs when standard formula structures or parameters are misapplied."
                            };
                        }
                    }
                }
                
                return null;
            }

    window.Cognitive.diagnosePracticeMistake = diagnosePracticeMistake;
    window.Cognitive.errorClassifier = { classify: diagnosePracticeMistake };
    window.diagnosePracticeMistake = diagnosePracticeMistake;

})();