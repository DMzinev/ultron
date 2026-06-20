// domain/conceptsProblems.js
(function() {
    window.Domain = window.Domain || {};
    window.Domain.Concepts = window.Domain.Concepts || {};

    const conceptItems = [
        { id: 'c-q1', name: "Annual retainer paid to film distributor", di: 'D', vf: 'F', desc: "Direct because it is paid specifically to secure films for the film section; Fixed because the annual fee does not vary with the quantity of films sold." },
        { id: 'c-q2', name: "Electricity costs of store (single bill)", di: 'I', vf: 'V', desc: "Indirect because a single bill covers the entire store and must be allocated to departments; Variable because electricity usage varies in total with store activity and operational hours." },
        { id: 'c-q3', name: "Costs of films purchased for sale", di: 'D', vf: 'V', desc: "Direct because the cost is traced directly to the films sold in this department; Variable because the total cost changes in direct proportion to the volume of films purchased." },
        { id: 'c-q4', name: "Subscription to Video-Novo magazine", di: 'D', vf: 'F', desc: "Direct because the magazine is specialized for the film section; Fixed because the subscription fee remains constant regardless of sales volume." },
        { id: 'c-q5', name: "Leasing of budgeting computer software", di: 'I', vf: 'F', desc: "Indirect because the software is used for store-wide budgeting and allocated to the department; Fixed because lease payments are constant monthly fees." },
        { id: 'c-q6', name: "Cost of popcorn provided free to customers", di: 'I', vf: 'V', desc: "Indirect because popcorn is provided to all store customers, not just film buyers, so it's a store-wide customer relation cost; Variable because total consumption increases with the number of store visitors." },
        { id: 'c-q7', name: "Earthquake insurance policy for store", di: 'I', vf: 'F', desc: "Indirect because a single policy covers the entire facility and must be allocated; Fixed because the premium is a flat cost independent of store traffic." },
        { id: 'c-q8', name: "Freight-in costs of films purchased", di: 'D', vf: 'V', desc: "Direct because shipping charges are traced directly to the films acquired; Variable because shipping cost changes based on the volume of films ordered." }
    ];

    function generateConceptsProblemPrac(container) {
                const tid = Math.floor(Math.random() * 3);
                currentPracProblem.templateId = tid;
                
                if (tid === 0) {
                    const item = conceptItems[Math.floor(Math.random() * conceptItems.length)];
                    currentPracProblem.correctAnswers = { q1_di: item.di, q1_vf: item.vf };
                    currentPracProblem.mathDetails = { itemName: item.name, desc: item.desc };
                    container.innerHTML = `
                        <h3 style="font-size:14px; color:white; margin-bottom:8px;">Cost Classification (Ex 2.15)</h3>
                        <p>Classify the following cost item with respect to the <strong>Film Section</strong> of Crescendo Store:</p>
                        <p style="padding:10px; background-color:var(--bg-primary); border-radius:6px; margin-bottom:12px; font-weight:600; text-align:center; color:var(--accent-primary);">"${item.name}"</p>
                        <div class="grid-2">
                            <div class="form-group"><label class="form-label">Direct or Indirect?</label>
                                <select class="form-input" id="c-ans-q1-di"><option value="">--</option><option value="D">Direct (D)</option><option value="I">Indirect (I)</option></select>
                            </div>
                            <div class="form-group"><label class="form-label">Variable or Fixed?</label>
                                <select class="form-input" id="c-ans-q1-vf"><option value="">--</option><option value="V">Variable (V)</option><option value="F">Fixed (F)</option></select>
                            </div>
                        </div>
                    `;
                } else if (tid === 1) {
                    const fixedFee = adjustVal(20000 + Math.floor(Math.random() * 9) * 5000); // 20k to 60k
                    const p1 = adjustVal(400 + Math.floor(Math.random() * 5) * 100); // 400 to 800
                    const p2 = adjustVal(1500 + Math.floor(Math.random() * 3) * 500); // 1500 to 2500
                    
                    currentPracProblem.correctAnswers = {
                        tot500: fixedFee,
                        unit500: Math.round((fixedFee / p1) * 100) / 100,
                        tot2000: fixedFee,
                        unit2000: Math.round((fixedFee / p2) * 100) / 100
                    };
                    currentPracProblem.mathDetails = { fixedFee, p1, p2 };
                    
                    container.innerHTML = `
                        <h3 style="font-size:14px; color:white; margin-bottom:8px;">Fixed cost behavior (Ex 2.11)</h3>
                        <p>A student association hired a music group for a graduation party for a fixed amount of <strong>€${fixedFee.toLocaleString()}</strong>. Calculate cost details under two different attendance scenarios:</p>
                        <div class="grid-2">
                            <div>
                                <h4 style="color:white; margin-bottom:6px; font-size:12px;">Scenario 1: ${p1.toLocaleString()} People Attend</h4>
                                <div class="form-group"><label class="form-label">Total Cost (€)</label><input class="form-input" type="number" id="c-tot500"></div>
                                <div class="form-group"><label class="form-label">Unit Cost per Person (€)</label><input class="form-input" type="number" id="c-unit500" step="0.01"></div>
                            </div>
                            <div>
                                <h4 style="color:white; margin-bottom:6px; font-size:12px;">Scenario 2: ${p2.toLocaleString()} People Attend</h4>
                                <div class="form-group"><label class="form-label">Total Cost (€)</label><input class="form-input" type="number" id="c-tot2000"></div>
                                <div class="form-group"><label class="form-label">Unit Cost per Person (€)</label><input class="form-input" type="number" id="c-unit2000" step="0.01"></div>
                            </div>
                        </div>
                    `;
                } else if (tid === 2) {
                    const accountantActivities = [
                        { text: "Preparing a monthly statement of sales for the BMW marketing vice-president.", ans: 'SK', name: "Scorekeeping", desc: "Scorekeeping because it involves accumulating and reporting data to help managers track progress." },
                        { text: "Interpreving differences between actual results and budgeted amounts on Tefal warranty performance reports.", ans: 'AD', name: "Attention Directing", desc: "Attention Directing because it interprets warranty reports to find deviations and focus managers on problem areas." },
                        { text: "Analysing, for a Toshiba manager, the desirability of buying some semiconductors made in Ireland.", ans: 'PS', name: "Problem Solving", desc: "Problem Solving because it evaluates alternative business actions (buy vs. make) to support management decisions." },
                        { text: "Preparing a scrap report for the Volvo parts plant finishing department.", ans: 'SK', name: "Scorekeeping", desc: "Scorekeeping because it is standard reporting of material waste data." }
                    ];
                    const act = accountantActivities[Math.floor(Math.random() * accountantActivities.length)];
                    currentPracProblem.correctAnswers = { func: act.ans };
                    currentPracProblem.mathDetails = { text: act.text, ansName: act.name, desc: act.desc };
                    
                    container.innerHTML = `
                        <h3 style="font-size:14px; color:white; margin-bottom:8px;">Accountant Functions (Ex 1.16)</h3>
                        <p>Classify the accountant's major function (Scorekeeping, Attention Directing, or Problem Solving) for the following activity:</p>
                        <p style="padding:10px; background-color:var(--bg-primary); border-radius:6px; margin-bottom:12px; font-weight:600; text-align:center; color:var(--accent-primary);">"${act.text}"</p>
                        <div class="form-group">
                            <label class="form-label">Accountant Function</label>
                            <select class="form-input" id="c-func">
                                <option value="">-- Select --</option>
                                <option value="SK">Scorekeeping</option>
                                <option value="AD">Attention Directing</option>
                                <option value="PS">Problem Solving</option>
                            </select>
                        </div>
                    `;
                }
            }

    function getWalkthrough(templateId, md, c) {
            let html = "";
            {
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
                }
            return html;
        }

    function getHint(templateId, tier, md) {
            const tid = templateId;
            if (tier === 1) {
                        if (tid === 0) return "Direct costs can be physically traced to the Film Section specifically. Variable costs change in total when sales volume goes up.";
                        else if (tid === 1) return "A fixed cost remains constant in total regardless of attendance. However, when attendance increases, that total cost is spread over more people, lowering the cost per person.";
                        else return "Scorekeeping is recording past data. Attention Directing is interpreting reports to find problems. Problem Solving is evaluating alternative actions for decisions.";
                    }
            if (tier === 2) {
                        if (tid === 1) return "Unit cost = Total Fixed Cost / People. Total cost = Fixed fee.";
                        else return "Read definitions in Session 1 slide summaries.";
                    }
            if (tier === 3) {
                        if (tid === 1) return `Scenario 1 Unit Cost = €${md.fixedFee.toLocaleString()} / ${md.p1} people. Scenario 2 Unit Cost = €${md.fixedFee.toLocaleString()} / ${md.p2} people. (Total Cost = €${md.fixedFee.toLocaleString()} in both cases).`;
                        else return "Refer to definitions on the dashboard topic summaries.";
                    }
            return "";
        }

    window.Domain.Concepts.generate = generateConceptsProblemPrac;
    window.Domain.Concepts.getWalkthrough = getWalkthrough;
    window.Domain.Concepts.getHint = getHint;

    window.generateConceptsProblemPrac = window.Domain.Concepts.generate;
})();