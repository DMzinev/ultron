// domain/abcProblems.js
(function() {
    window.Domain = window.Domain || {};
    window.Domain.ABC = window.Domain.ABC || {};

    function generateABCProblemPrac(container) {
                const tid = Math.floor(Math.random() * 2);
                currentPracProblem.templateId = tid;
    
                if (tid === 0) {
                    const volA = adjustVal(4000 + Math.floor(Math.random() * 5) * 500); // 4000 to 6000
                    const volB = adjustVal(9000 + Math.floor(Math.random() * 5) * 500); // 9000 to 11000
                    const dmA = adjustVal(120 + Math.floor(Math.random() * 7) * 5); // 120 to 150
                    const dlA = adjustVal(80 + Math.floor(Math.random() * 7) * 5); // 80 to 110
                    const dmB = adjustVal(70 + Math.floor(Math.random() * 5) * 5); // 70 to 90
                    const dlB = adjustVal(50 + Math.floor(Math.random() * 5) * 5); // 50 to 70
                    
                    const setupPool = adjustVal(400000 + Math.floor(Math.random() * 3) * 50000); // 400k to 500k
                    const delPool = adjustVal(180000 + Math.floor(Math.random() * 3) * 20000); // 180k to 220k
                    
                    const setupsA = 20 + Math.floor(Math.random() * 3) * 5; // 20, 25, 30
                    const setupsB = 70 + Math.floor(Math.random() * 3) * 5; // 70, 75, 80
                    const delA = 30 + Math.floor(Math.random() * 3) * 10; // 30, 40, 50
                    const delB = 180 + Math.floor(Math.random() * 5) * 20; // 180 to 260
                    
                    const totalVol = volA + volB;
                    const totalOH = setupPool + delPool;
                    const tradRate = totalOH / totalVol;
                    
                    const tradCostA = dmA + dlA + tradRate;
                    const tradCostB = dmB + dlB + tradRate;
                    
                    const setupRate = setupPool / (setupsA + setupsB);
                    const delRate = delPool / (delA + delB);
                    
                    const abcCostA = dmA + dlA + ((setupsA * setupRate) + (delA * delRate)) / volA;
                    const abcCostB = dmB + dlB + ((setupsB * setupRate) + (delB * delRate)) / volB;
                    
                    currentPracProblem.correctAnswers = {
                        tradRate: Math.round(tradRate * 100) / 100,
                        tradCostA: Math.round(tradCostA * 100) / 100,
                        tradCostB: Math.round(tradCostB * 100) / 100,
                        abcCostA: Math.round(abcCostA * 100) / 100,
                        abcCostB: Math.round(abcCostB * 100) / 100
                    };
                    
                    currentPracProblem.mathDetails = {
                        volA, volB, dmA, dlA, dmB, dlB, setupPool, delPool,
                        setupsA, setupsB, delA, delB, totalVol, totalOH,
                        tradRate, tradCostA, tradCostB, setupRate, delRate, abcCostA, abcCostB
                    };
    
                    container.innerHTML = `
                        <h3 style="font-size:14px; color:white; margin-bottom:8px;">Traditional vs. ABC allocation (Ex 4.2)</h3>
                        <p>Titan Thrones company produces two models: Premium and Basic. Calculate traditional and ABC unit costs based on these figures:</p>
                        <ul>
                            <li><strong>Output Volume:</strong> Premium: ${volA.toLocaleString()} units; Basic: ${volB.toLocaleString()} units.</li>
                            <li><strong>Direct Costs per unit:</strong> Premium: DM €${dmA.toFixed(2)}, DL €${dlA.toFixed(2)}; Basic: DM €${dmB.toFixed(2)}, DL €${dlB.toFixed(2)}.</li>
                            <li><strong>Indirect Overhead pools:</strong> Setup-related: €${setupPool.toLocaleString()} (driver: setup hours); Delivery-related: €${delPool.toLocaleString()} (driver: shipments).</li>
                            <li><strong>Driver usage:</strong> Setup hours: Premium ${setupsA} hrs, Basic ${setupsB} hrs; Shipments: Premium ${delA}, Basic ${delB}.</li>
                        </ul>
                        <div class="inline-inputs-table" style="margin-top:12px;">
                            <table>
                                <thead><tr><th>Metric</th><th>Input Answer (€)</th></tr></thead>
                                <tbody>
                                    <tr><td>Traditional Overhead Allocation Rate per unit</td><td><input type="number" class="form-input" id="ans-trad-rate" step="0.01"></td></tr>
                                    <tr><td>Traditional unit cost Premium (Titan Throne)</td><td><input type="number" class="form-input" id="ans-trad-costA" step="0.01"></td></tr>
                                    <tr><td>Traditional unit cost Basic (Arena X)</td><td><input type="number" class="form-input" id="ans-trad-costB" step="0.01"></td></tr>
                                    <tr><td>ABC unit cost Premium</td><td><input type="number" class="form-input" id="ans-abc-costA" step="0.01"></td></tr>
                                    <tr><td>ABC unit cost Basic</td><td><input type="number" class="form-input" id="ans-abc-costB" step="0.01"></td></tr>
                                </tbody>
                            </table>
                        </div>
                    `;
                } else {
                    const tiles = 200000 + Math.floor(Math.random() * 11) * 10000; // 200k to 300k
                    const rev = 800000 + Math.floor(Math.random() * 7) * 50000; // 800k to 1.1M
                    const cogs = Math.round(rev * 0.75 / 10000) * 10000;
                    const orders = 150 + Math.floor(Math.random() * 11) * 10;
                    const orderCost = 20 + Math.floor(Math.random() * 3) * 5;
                    const loads = 2000 + Math.floor(Math.random() * 21) * 100;
                    const loadCost = 25 + Math.floor(Math.random() * 3) * 5;
                    const setups = 1000 + Math.floor(Math.random() * 11) * 100;
                    const setupCost = 35 + Math.floor(Math.random() * 3) * 5;
                    const adminFixed = 30000 + Math.floor(Math.random() * 5) * 5000;
                    
                    const opex = (orders * orderCost) + (loads * loadCost) + (setups * setupCost) + adminFixed;
                    const profit = rev - cogs - opex;
                    const perTile = profit / tiles;
                    
                    currentPracProblem.correctAnswers = {
                        profit: profit,
                        perTile: Math.round(perTile * 1000) / 1000
                    };
                    currentPracProblem.mathDetails = {
                        tiles, rev, cogs, orders, orderCost, loads, loadCost, setups, setupCost, adminFixed, opex, profit, perTile
                    };
    
                    container.innerHTML = `
                        <h3 style="font-size:14px; color:white; margin-bottom:8px;">Logistics Restructuring (Ex 12.12)</h3>
                        <p>Pagnol-Carrelages sells <strong>${tiles.toLocaleString()}</strong> tiles. Its budgeted parameters for the coming year are:</p>
                        <ul>
                            <li>Revenue: €${rev.toLocaleString()} | Cost of Goods Sold: €${cogs.toLocaleString()}</li>
                            <li>Budgeted distribution activities include:
                                <ul>
                                    <li>${orders} orders at €${orderCost}/order</li>
                                    <li>${loads.toLocaleString()} loads moved at €${loadCost}/load</li>
                                    <li>${setups.toLocaleString()} setup hours at €${setupCost}/setup hour</li>
                                    <li>Fixed administration costs of €${adminFixed.toLocaleString()}</li>
                                </ul>
                            </li>
                        </ul>
                        <p>Calculate the budgeted operating profit and operating profit per tile:</p>
                        <div class="grid-2" style="margin-top:12px;">
                            <div class="form-group"><label class="form-label">Operating Profit (€)</label><input class="form-input" type="number" id="ans-restruct-profit" step="1"></div>
                            <div class="form-group"><label class="form-label">Operating Profit per Tile (€/tile)</label><input class="form-input" type="number" id="ans-restruct-per-tile" step="0.001"></div>
                        </div>
                    `;
                }
            }

    function getWalkthrough(templateId, md, c) {
            let html = "";
            {
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
                }
            return html;
        }

    function getHint(templateId, tier, md) {
            const tid = templateId;
            if (tier === 1) {
                        if (tid === 0) return "Traditional allocation uses a single volume-based rate, over-costing simple products and under-costing complex ones. ABC allocates based on setups and shipments to reduce distortion.";
                        else return "Calculate total operating expenses by multiplying each driver activity level (orders, loads, setup hours) by its respective cost rate, then add fixed admin costs.";
                    }
            if (tier === 2) {
                        if (tid === 0) return "Traditional Rate = Total OH / Total Units. ABC Activity Rate = Pool Cost / Total Activity Units. Unit cost = DM + DL + Unit OH.";
                        else return "OPEX = (Orders × Rate) + (Loads × Rate) + (Setups × Rate) + Admin. Profit = Rev - COGS - OPEX. Per Tile = Profit / Tiles.";
                    }
            if (tier === 3) {
                        if (tid === 0) return `Total OH = €${md.setupPool.toLocaleString()} + €${md.delPool.toLocaleString()} = €${md.totalOH.toLocaleString()}. Traditional Overhead Rate = €${md.totalOH.toLocaleString()} / (${md.volA.toLocaleString()} + ${md.volB.toLocaleString()}). ABC Setup Hour Rate = €${md.setupPool.toLocaleString()} / (${md.setupsA} + ${md.setupsB}). ABC Shipment Rate = €${md.delPool.toLocaleString()} / (${md.delA} + ${md.delB}).`;
                        else return `OPEX = (${md.orders} orders × €${md.orderCost}) + (${md.loads.toLocaleString()} loads × €${md.loadCost}) + (${md.setups.toLocaleString()} setups × €${md.setupCost}) + €${md.adminFixed.toLocaleString()}. Net Profit = €${md.rev.toLocaleString()} (Revenue) - €${md.cogs.toLocaleString()} (COGS) - OPEX.`;
                    }
            return "";
        }

    window.Domain.ABC.generate = generateABCProblemPrac;
    window.Domain.ABC.getWalkthrough = getWalkthrough;
    window.Domain.ABC.getHint = getHint;

    window.generateABCProblemPrac = window.Domain.ABC.generate;
})();