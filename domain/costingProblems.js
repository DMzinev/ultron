// domain/costingProblems.js
(function() {
    window.Domain = window.Domain || {};
    window.Domain.Costing = window.Domain.Costing || {};

    function generateFIFOProblemPrac(container) {
                const tid = Math.floor(Math.random() * 3);
                currentPracProblem.templateId = tid;
    
                if (tid === 0) {
                    const opUnits = adjustVal(5 + Math.floor(Math.random() * 11));
                    const started = adjustVal(40 + Math.floor(Math.random() * 21));
                    const completed = started - 5 + Math.floor(Math.random() * 11);
                    const clUnits = opUnits + started - completed;
                    
                    const opDmPct = (80 + Math.floor(Math.random() * 3) * 10) / 100;
                    const opConvPct = (30 + Math.floor(Math.random() * 3) * 10) / 100;
                    const clDmPct = (50 + Math.floor(Math.random() * 3) * 10) / 100;
                    const clConvPct = (20 + Math.floor(Math.random() * 3) * 10) / 100;
                    
                    const addDmCost = adjustVal(10000000 + Math.floor(Math.random() * 26) * 1000000);
                    const addConvCost = adjustVal(5000000 + Math.floor(Math.random() * 11) * 1000000);
                    
                    const currDmEU = completed + (clUnits * clDmPct) - (opUnits * opDmPct);
                    const currConvEU = completed + (clUnits * clConvPct) - (opUnits * opConvPct);
                    
                    const rateDM = addDmCost / currDmEU;
                    const rateConv = addConvCost / currConvEU;
                    
                    currentPracProblem.correctAnswers = {
                        currDmEU: Math.round(currDmEU * 10) / 10,
                        currConvEU: Math.round(currConvEU * 10) / 10,
                        rateDM: Math.round(rateDM * 100) / 100,
                        rateConv: Math.round(rateConv * 100) / 100
                    };
                    
                    currentPracProblem.mathDetails = {
                        opUnits, started, completed, clUnits,
                        opDmPct, opConvPct, clDmPct, clConvPct,
                        addDmCost, addConvCost, currDmEU, currConvEU, rateDM, rateConv
                    };
    
                    container.innerHTML = `
                        <h3 style="font-size:14px; color:white; margin-bottom:8px;">FIFO Equivalent Units (Ex 4.13)</h3>
                        <p>Determine equivalent units of work done in the current period and cost per equivalent unit using the FIFO method:</p>
                        <ul>
                            <li><strong>Opening Work in Process:</strong> ${opUnits} units (degree of completion: Direct Materials ${opDmPct*100}%, Conversion ${opConvPct*100}%).</li>
                            <li><strong>Activity:</strong> Units started during period: ${started} | Units completed and transferred out: ${completed}.</li>
                            <li><strong>Closing Work in Process:</strong> ${clUnits} units (degree of completion: Direct Materials ${clDmPct*100}%, Conversion ${clConvPct*100}%).</li>
                            <li><strong>Current Period Costs Added:</strong> Direct Materials €${addDmCost.toLocaleString()} | Conversion €${addConvCost.toLocaleString()}.</li>
                        </ul>
                        <div class="inline-inputs-table" style="margin-top:12px;">
                            <table>
                                <thead><tr><th>Metric</th><th>Input Answer</th></tr></thead>
                                <tbody>
                                    <tr><td>DM Equivalent Units of work done</td><td><input type="number" class="form-input" id="ans-fifo-dm-eu" step="0.1"></td></tr>
                                    <tr><td>Conversion Equivalent Units of work done</td><td><input type="number" class="form-input" id="ans-fifo-conv-eu" step="0.1"></td></tr>
                                    <tr><td>Cost per DM Equivalent Unit (€)</td><td><input type="number" class="form-input" id="ans-fifo-dm-rate" step="0.01"></td></tr>
                                    <tr><td>Cost per Conversion Equivalent Unit (€)</td><td><input type="number" class="form-input" id="ans-fifo-conv-rate" step="0.01"></td></tr>
                                </tbody>
                            </table>
                        </div>
                    `;
                } else if (tid === 1) {
                    const salary = 120000 + Math.floor(Math.random() * 14) * 10000;
                    const billableHours = 1200 + Math.floor(Math.random() * 5) * 100;
                    const leaveHours = 120 + Math.floor(Math.random() * 5) * 20;
                    const devHours = 160 + Math.floor(Math.random() * 5) * 20;
                    const totalHours = billableHours + leaveHours + devHours;
                    
                    const rateBillable = salary / billableHours;
                    const rateTotal = salary / totalHours;
                    
                    currentPracProblem.correctAnswers = {
                        rateBillable: Math.round(rateBillable * 100) / 100,
                        rateTotal: Math.round(rateTotal * 100) / 100
                    };
                    currentPracProblem.mathDetails = { salary, billableHours, leaveHours, devHours, totalHours, rateBillable, rateTotal };
    
                    container.innerHTML = `
                        <h3 style="font-size:14px; color:white; margin-bottom:8px;">Billing Rates calculation (Ex 3.12)</h3>
                        <p>Zimmermann GmbH has a budgeted annual salary + fringe benefits cost of <strong>€${salary.toLocaleString()}</strong> for a controller. The budgeted hours breakdown for the controller is:</p>
                        <ul>
                            <li>Client billable work: ${billableHours.toLocaleString()} hours</li>
                            <li>Vacation, sick, and holidays: ${leaveHours.toLocaleString()} hours</li>
                            <li>Professional development and training: ${devHours.toLocaleString()} hours</li>
                        </ul>
                        <p>Calculate the hourly labor rate under two different allocation scenarios:</p>
                        <div class="grid-2" style="margin-top:12px;">
                            <div class="form-group"><label class="form-label">Scenario (1): denominator is only client billable hours (€/hr)</label><input class="form-input" type="number" id="ans-rate-billable" step="0.01"></div>
                            <div class="form-group"><label class="form-label">Scenario (2): denominator is total budgeted hours (€/hr)</label><input class="form-input" type="number" id="ans-rate-total" step="0.01"></div>
                        </div>
                    `;
                } else {
                    const budgetedOH = 5000000 + Math.floor(Math.random() * 9) * 500000;
                    const budgetedMH = 150000 + Math.floor(Math.random() * 11) * 10000;
                    const actualMH = budgetedMH - 10000 + Math.floor(Math.random() * 5) * 5000;
                    const actualOH = budgetedOH - 300000 + Math.floor(Math.random() * 13) * 50000;
                    
                    const ohRate = budgetedOH / budgetedMH;
                    const ohAllocated = ohRate * actualMH;
                    const ohDiff = ohAllocated - actualOH;
                    
                    currentPracProblem.correctAnswers = {
                        ohRate: Math.round(ohRate * 100) / 100,
                        ohAllocated: Math.round(ohAllocated),
                        ohDiff: Math.round(ohDiff)
                    };
                    currentPracProblem.mathDetails = { budgetedOH, budgetedMH, actualMH, actualOH, ohRate, ohAllocated, ohDiff };
    
                    container.innerHTML = `
                        <h3 style="font-size:14px; color:white; margin-bottom:8px;">Overhead Allocation (Ex 3.13)</h3>
                        <p>Schwarzmetal GmbH allocates manufacturing overhead based on machine-hours. Budgeted and actual numbers are:</p>
                        <ul>
                            <li>Budgeted manufacturing overhead: €${budgetedOH.toLocaleString()} | Budgeted machine-hours: ${budgetedMH.toLocaleString()} MH</li>
                            <li>Actual manufacturing overhead incurred: €${actualOH.toLocaleString()} | Actual machine-hours used: ${actualMH.toLocaleString()} MH</li>
                        </ul>
                        <p>Calculate the predetermined overhead rate, total allocated overhead, and the under- or over-allocated amount:</p>
                        <div class="inline-inputs-table" style="margin-top:12px;">
                            <table>
                                <thead><tr><th>Metric</th><th>Input Answer (€)</th></tr></thead>
                                <tbody>
                                    <tr><td>Predetermined overhead rate per machine-hour</td><td><input type="number" class="form-input" id="ans-oh-rate" step="0.01"></td></tr>
                                    <tr><td>Overhead allocated to production in total</td><td><input type="number" class="form-input" id="ans-oh-allocated" step="1"></td></tr>
                                    <tr><td>Under/Over-allocation amount (positive for overallocated, negative for underallocated)</td><td><input type="number" class="form-input" id="ans-oh-diff" step="1"></td></tr>
                                </tbody>
                            </table>
                        </div>
                    `;
                }
            }

    function getWalkthrough(templateId, md, c) {
            let html = "";
            {
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
                }
            return html;
        }

    function getHint(templateId, tier, md) {
            const tid = templateId;
            if (tier === 1) {
                        if (tid === 0) return "FIFO process costing measures work done ONLY in the current period. Work done on opening WIP in the prior period is excluded.";
                        else if (tid === 1) return "Recall that billing rates can include non-billable hours (like training and sick leave) in the denominator to ensure all expenses are recovered.";
                        else return "Predetermined overhead rate is set before the year starts. Allocated overhead uses this rate multiplied by actual hours used.";
                    }
            if (tier === 2) {
                        if (tid === 0) return "FIFO EU = Completed + (Closing WIP × Cl%) - (Opening WIP × Op%). Rate = Current Cost Added / FIFO EU.";
                        else if (tid === 1) return "Scenario 1 Rate = Salary / Billable Hours. Scenario 2 Rate = Salary / Total Hours.";
                        else return "Rate = Budgeted OH / Budgeted MH. Allocated = Rate × Actual MH. Under/Over = Allocated - Actual OH.";
                    }
            if (tier === 3) {
                        if (tid === 0) return `DM EU = Completed ${md.completed} + (Closing WIP ${md.clUnits} × ${md.clDmPct*100}%) - (Opening WIP ${md.opUnits} × ${md.opDmPct*100}%). Cost/EU = Current Added Cost €${md.addDmCost.toLocaleString()} / DM EU. Same structure applies to Conversion.`;
                        else if (tid === 1) return `Scenario 1 Hourly Rate = Salary €${md.salary.toLocaleString()} / Billable hours ${md.billableHours.toLocaleString()} hrs. Scenario 2 Hourly Rate = Salary €${md.salary.toLocaleString()} / Total hours ${md.totalHours.toLocaleString()} hrs.`;
                        else return `Predetermined OH Rate = Budgeted OH €${md.budgetedOH.toLocaleString()} / Budgeted MH ${md.budgetedMH.toLocaleString()} MH. Allocated OH = Rate × Actual MH ${md.actualMH.toLocaleString()} MH. Under/Overallocated = Allocated OH - Actual OH incurred €${md.actualOH.toLocaleString()}.`;
                    }
            return "";
        }

    window.Domain.Costing.generate = generateFIFOProblemPrac;
    window.Domain.Costing.getWalkthrough = getWalkthrough;
    window.Domain.Costing.getHint = getHint;

    window.generateFIFOProblemPrac = window.Domain.Costing.generate;
})();