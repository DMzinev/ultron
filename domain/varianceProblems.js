// domain/varianceProblems.js
(function() {
    window.Domain = window.Domain || {};
    window.Domain.Variance = window.Domain.Variance || {};

    function generateVarianceProblemPrac(container) {
                const tid = Math.floor(Math.random() * 2);
                currentPracProblem.templateId = tid;
    
                if (tid === 0) {
                    const stdDM_qty = Math.random() < 0.5 ? 0.1 : 0.2;
                    const stdDM_price = adjustVal(40 + Math.floor(Math.random() * 5) * 5);
                    const stdDL_hours = Math.random() < 0.5 ? 0.25 : 0.2;
                    const stdDL_rate = 16 + Math.floor(Math.random() * 5) * 1;
                    
                    const budgetedVol = adjustVal(3000 + Math.floor(Math.random() * 5) * 500);
                    const actualVol = budgetedVol + 100 + Math.floor(Math.random() * 5) * 100;
                    
                    const expectedDM = actualVol * stdDM_qty;
                    const actDM_qty = Math.round(expectedDM * (0.9 + Math.random() * 0.2) * 10) / 10;
                    const actDM_price = Math.round((stdDM_price + (Math.random() * 2 - 1)) * 10) / 10;
                    
                    const expectedDL = actualVol * stdDL_hours;
                    const actDL_hours = Math.round(expectedDL * (0.9 + Math.random() * 0.2));
                    const actDL_rate = Math.round((stdDL_rate + (Math.random() * 1 - 0.5)) * 10) / 10;
                    
                    const dmPriceVar = (stdDM_price - actDM_price) * actDM_qty;
                    const dmEffVar = (actualVol * stdDM_qty - actDM_qty) * stdDM_price;
                    const dlPriceVar = (stdDL_rate - actDL_rate) * actDL_hours;
                    const dlEffVar = (actualVol * stdDL_hours - actDL_hours) * stdDL_rate;
                    
                    currentPracProblem.correctAnswers = {
                        dmPriceVar: Math.round(dmPriceVar * 100) / 100,
                        dmEffVar: Math.round(dmEffVar * 100) / 100,
                        dlPriceVar: Math.round(dlPriceVar * 100) / 100,
                        dlEffVar: Math.round(dlEffVar * 100) / 100
                    };
                    
                    currentPracProblem.mathDetails = {
                        stdDM_qty, stdDM_price, stdDL_hours, stdDL_rate, budgetedVol, actualVol,
                        actDM_qty, actDM_price, actDL_hours, actDL_rate,
                        dmPriceVar, dmEffVar, dlPriceVar, dlEffVar
                    };
    
                    container.innerHTML = `
                        <h3 style="font-size:14px; color:white; margin-bottom:8px;">Standard Cost Variances (Ex 15.23)</h3>
                        <p>Calculate direct material and direct labor variances based on the following standard and actual performance data:</p>
                        <ul>
                            <li><strong>Standard Standards:</strong> Direct Materials: ${stdDM_qty} roll(s) per unit at €${stdDM_price}/roll | Direct Labor: ${stdDL_hours} hour(s) per unit at €${stdDL_rate}/hour.</li>
                            <li><strong>Volume:</strong> Budgeted production: ${budgetedVol.toLocaleString()} units | Actual production achieved: ${actualVol.toLocaleString()} units.</li>
                            <li><strong>Actual results:</strong> Direct Materials purchased and used: ${actDM_qty.toLocaleString()} rolls costing €${actDM_price.toFixed(2)}/roll | Direct Labor worked: ${actDL_hours.toLocaleString()} hours at €${actDL_rate.toFixed(2)}/hour.</li>
                        </ul>
                        <div class="inline-inputs-table" style="margin-top:12px;">
                            <table>
                                <thead><tr><th>Variance</th><th>Amount (€)</th><th>F/U</th></tr></thead>
                                <tbody>
                                    <tr><td>DM Price Variance</td><td><input type="number" class="form-input" id="ans-dm-price" step="0.01"></td><td><select class="form-input" id="effect-dm-price" style="width:auto;"><option value="">--</option><option value="F">F</option><option value="U">U</option></select></td></tr>
                                    <tr><td>DM Efficiency Variance</td><td><input type="number" class="form-input" id="ans-dm-eff" step="0.01"></td><td><select class="form-input" id="effect-dm-eff" style="width:auto;"><option value="">--</option><option value="F">F</option><option value="U">U</option></select></td></tr>
                                    <tr><td>DL Price Variance</td><td><input type="number" class="form-input" id="ans-dl-price" step="0.01"></td><td><select class="form-input" id="effect-dl-price" style="width:auto;"><option value="">--</option><option value="F">F</option><option value="U">U</option></select></td></tr>
                                    <tr><td>DL Efficiency Variance</td><td><input type="number" class="form-input" id="ans-dl-eff" step="0.01"></td><td><select class="form-input" id="effect-dl-eff" style="width:auto;"><option value="">--</option><option value="F">F</option><option value="U">U</option></select></td></tr>
                                </tbody>
                            </table>
                        </div>
                    `;
                } else {
                    currentPracProblem.correctAnswers = { prod: 2, sales: 1, dm: 3, op: 4, bs: 5 };
                    container.innerHTML = `
                        <h3 style="font-size:14px; color:white; margin-bottom:8px;">Master Budget Sequencing (Ex 5.2)</h3>
                        <p>Order the steps in preparing a master budget from 1 (first step in the process) to 5 (final step in the process):</p>
                        <div style="display:flex; flex-direction:column; gap:12px; margin-top:12px; max-width:400px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;"><span>Production Budget:</span><input type="number" class="form-input" id="ans-seq-prod" style="max-width:80px;" min="1" max="5"></div>
                            <div style="display:flex; justify-content:space-between; align-items:center;"><span>Sales Budget:</span><input type="number" class="form-input" id="ans-seq-sales" style="max-width:80px;" min="1" max="5"></div>
                            <div style="display:flex; justify-content:space-between; align-items:center;"><span>Direct Materials Purchases Budget:</span><input type="number" class="form-input" id="ans-seq-dm" style="max-width:80px;" min="1" max="5"></div>
                            <div style="display:flex; justify-content:space-between; align-items:center;"><span>Budgeted Operating Income Statement:</span><input type="number" class="form-input" id="ans-seq-op" style="max-width:80px;" min="1" max="5"></div>
                            <div style="display:flex; justify-content:space-between; align-items:center;"><span>Budgeted Balance Sheet:</span><input type="number" class="form-input" id="ans-seq-bs" style="max-width:80px;" min="1" max="5"></div>
                        </div>
                    `;
                }
            }

    function getWalkthrough(templateId, md, c) {
            let html = "";
            {
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
                }
            return html;
        }

    function getHint(templateId, tier, md) {
            const tid = templateId;
            if (tier === 1) {
                        if (tid === 0) return "Price variances isolate the difference in unit purchase prices. Efficiency variances isolate the difference between actual inputs used and standard inputs allowed.";
                        else return "Budgets are prepared sequentially. You cannot determine production without knowing sales, and you cannot determine material purchases without knowing production.";
                    }
            if (tier === 2) {
                        if (tid === 0) return "DM Price Variance = (SP - AP) × AQ. DM Efficiency Variance = (SQ_allowed - AQ) × SP. SQ_allowed = Actual Production × Standard Qty per unit. Same logic applies for DL.";
                        else return "Flow: Sales Budget (1) -> Production Budget (2) -> Direct Materials purchases (3) -> Operating statement (4) -> Balance Sheet (5).";
                    }
            if (tier === 3) {
                        if (tid === 0) return `DM Price Var = (Standard €${md.stdDM_price.toFixed(2)} - Actual €${md.actDM_price.toFixed(2)}) × Actual ${md.actDM_qty.toLocaleString()} rolls. DM Eff Var = ((Actual Vol ${md.actualVol.toLocaleString()} × Standard ${md.stdDM_qty} rolls) - Actual ${md.actDM_qty.toLocaleString()} rolls used) × Standard €${md.stdDM_price.toFixed(2)}. Same structure applies to Direct Labor.`;
                        else return "Budget Prep Steps: Sales (1) -> Production (2) -> Materials purchases (3) -> Operating statement (4) -> Balance sheet (5).";
                    }
            return "";
        }

    window.Domain.Variance.generate = generateVarianceProblemPrac;
    window.Domain.Variance.getWalkthrough = getWalkthrough;
    window.Domain.Variance.getHint = getHint;

    window.generateVarianceProblemPrac = window.Domain.Variance.generate;
})();