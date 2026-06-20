// domain/cvpProblems.js
(function() {
    window.Domain = window.Domain || {};
    window.Domain.CVP = window.Domain.CVP || {};

    function generateCVPProblemPrac(container) {
                const tid = Math.floor(Math.random() * 2);
                currentPracProblem.templateId = tid;
    
                if (tid === 0) {
                    const price = adjustVal(15 + Math.floor(Math.random() * 4) * 5);
                    const vc = price - 5 - Math.floor(Math.random() * 3) * 2;
                    const fc = adjustVal(10000 + Math.floor(Math.random() * 16) * 1000);
                    const extraVol = adjustVal(300 + Math.floor(Math.random() * 4) * 100);
                    
                    const cmu = price - vc;
                    const be = Math.ceil(fc / cmu);
                    const profit = extraVol * cmu;
                    
                    currentPracProblem.correctAnswers = {
                        cmu: Math.round(cmu * 100) / 100,
                        be: be,
                        profit: Math.round(profit * 100) / 100
                    };
                    currentPracProblem.mathDetails = { price, vc, fc, extraVol, cmu, be, profit };
    
                    container.innerHTML = `
                        <h3 style="font-size:14px; color:white; margin-bottom:8px;">CVP Practice Challenge (Ex 3.2)</h3>
                        <p>An enterprise sells a single product. Its monthly cost structure and selling conditions are:</p>
                        <ul>
                            <li>Selling Price: €${price.toFixed(2)} per unit | Variable Cost: €${vc.toFixed(2)} per unit</li>
                            <li>Total monthly fixed costs: €${fc.toLocaleString()}</li>
                        </ul>
                        <p>Calculate unit contribution margin, monthly breakeven quantity, and budgeted operating profit if sales volume exceeds breakeven by <strong>${extraVol.toLocaleString()}</strong> units:</p>
                        <div class="inline-inputs-table" style="margin-top:12px;">
                            <table>
                                <thead><tr><th>Metric</th><th>Input Answer</th></tr></thead>
                                <tbody>
                                    <tr><td>Contribution Margin per unit (€)</td><td><input type="number" class="form-input" id="ans-cvp-cmu" step="0.01"></td></tr>
                                    <tr><td>Breakeven Quantity (units)</td><td><input type="number" class="form-input" id="ans-cvp-be" step="1"></td></tr>
                                    <tr><td>Monthly Operating Profit if sales are ${extraVol.toLocaleString()} units above BEP (€)</td><td><input type="number" class="form-input" id="ans-cvp-profit" step="0.01"></td></tr>
                                </tbody>
                            </table>
                        </div>
                    `;
                } else {
                    const price = 90 + Math.floor(Math.random() * 7) * 10;
                    const vc = Math.round(price * 0.75 / 5) * 5;
                    const casesPerMeter = 15 + Math.floor(Math.random() * 4) * 5;
                    
                    const cmCase = price - vc;
                    const cmMeter = cmCase * casesPerMeter;
                    
                    currentPracProblem.correctAnswers = {
                        cmCase: Math.round(cmCase * 100) / 100,
                        cmMeter: Math.round(cmMeter * 100) / 100
                    };
                    currentPracProblem.mathDetails = { price, vc, casesPerMeter, cmCase, cmMeter };
    
                    container.innerHTML = `
                        <h3 style="font-size:14px; color:white; margin-bottom:8px;">Constrained Resource Optimizer (Ex 10.11)</h3>
                        <p>A retail store sells Cola. In terms of shelf space, store management has compiled the following daily performance data:</p>
                        <ul>
                            <li>Selling Price: €${price.toFixed(2)} per case | Variable Cost: €${vc.toFixed(2)} per case</li>
                            <li>Average sales capacity per linear shelf-meter: <strong>${casesPerMeter}</strong> cases per day</li>
                        </ul>
                        <p>Calculate the contribution margin per case and the daily contribution margin generated per shelf-meter for Cola:</p>
                        <div class="grid-2" style="margin-top:12px;">
                            <div class="form-group"><label class="form-label">Contribution Margin per Case (€/case)</label><input class="form-input" type="number" id="ans-bottle-cm-case" step="0.01"></div>
                            <div class="form-group"><label class="form-label">Daily Contribution Margin per linear shelf-meter (€/meter/day)</label><input class="form-input" type="number" id="ans-bottle-cm-meter" step="0.01"></div>
                        </div>
                    `;
                }
            }

    function getWalkthrough(templateId, md, c) {
            let html = "";
            {
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

    function getHint(templateId, tier, md) {
            const tid = templateId;
            if (tier === 1) {
                        if (tid === 0) return "Contribution margin represents how much sales revenue is left after variable costs to cover fixed expenses and generate operating profit.";
                        else return "When a constraint is present, the key metric is contribution margin per unit of that constraint (e.g. per shelf-meter), not per case.";
                    }
            if (tier === 2) {
                        if (tid === 0) return "CM/unit = Price - VC. Breakeven = Fixed Costs / CM/unit. Profit above BEP = (Sales Volume - BEP) × CM/unit.";
                        else return "CM per Case = Price - VC. CM per shelf-meter = CM per Case × Cases per Meter.";
                    }
            if (tier === 3) {
                        if (tid === 0) return `Unit CM = Price €${md.price.toFixed(2)} - Variable Cost €${md.vc.toFixed(2)} = €${md.cmu.toFixed(2)}. Breakeven Qty = Fixed Cost €${md.fc.toLocaleString()} / Unit CM €${md.cmu.toFixed(2)}. Profit above BEP = Sales units above BEP ${md.extraVol.toLocaleString()} × Unit CM €${md.cmu.toFixed(2)}.`;
                        else return `CM per case = Price €${md.price.toFixed(2)} - Variable Cost €${md.vc.toFixed(2)} = €${md.cmCase.toFixed(2)}. Daily CM per shelf-meter = CM per case €${md.cmCase.toFixed(2)} × capacity ${md.casesPerMeter} cases/meter/day.`;
                    }
            return "";
        }

    window.Domain.CVP.generate = generateCVPProblemPrac;
    window.Domain.CVP.getWalkthrough = getWalkthrough;
    window.Domain.CVP.getHint = getHint;

    window.generateCVPProblemPrac = window.Domain.CVP.generate;
})();