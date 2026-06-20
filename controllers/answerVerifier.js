// controllers/answerVerifier.js
(function() {
    window.Controllers = window.Controllers || {};
    window.Controllers.answerVerifier = window.Controllers.answerVerifier || {};

    function verify(category, templateId, correctAnswers, userAnswers, tolerance = 0.25) {
        const c = correctAnswers;
        const u = userAnswers;
        const results = {};
        const normalizedAnswers = {};
        let correct = true;

        const parseF = window.Utils.parseRobustFloat || parseFloat;
        const norm = window.Utils.normalizeText || (s => String(s).trim().toUpperCase());

        function getVal(key1, key2) {
            if (u[key1] !== undefined) return u[key1];
            return u[key2];
        }

        if (category === 'concepts') {
            if (templateId === 0) {
                const di = norm(getVal('c-ans-q1-di', 'di'));
                const vf = norm(getVal('c-ans-q1-vf', 'vf'));
                normalizedAnswers['c-ans-q1-di'] = di;
                normalizedAnswers['c-ans-q1-vf'] = vf;
                results['c-ans-q1-di'] = (di === norm(c.q1_di));
                results['c-ans-q1-vf'] = (vf === norm(c.q1_vf));
            } else if (templateId === 1) {
                const tot500 = parseF(getVal('c-tot500', 'tot500'));
                const unit500 = parseF(getVal('c-unit500', 'unit500'));
                const tot2000 = parseF(getVal('c-tot2000', 'tot2000'));
                const unit2000 = parseF(getVal('c-unit2000', 'unit2000'));
                normalizedAnswers['c-tot500'] = tot500;
                normalizedAnswers['c-unit500'] = unit500;
                normalizedAnswers['c-tot2000'] = tot2000;
                normalizedAnswers['c-unit2000'] = unit2000;

                results['c-tot500'] = Math.abs(tot500 - c.tot500) < tolerance;
                results['c-unit500'] = Math.abs(unit500 - c.unit500) < tolerance;
                results['c-tot2000'] = Math.abs(tot2000 - c.tot2000) < tolerance;
                results['c-unit2000'] = Math.abs(unit2000 - c.unit2000) < tolerance;
            } else if (templateId === 2) {
                const func = norm(getVal('c-func', 'func'));
                normalizedAnswers['c-func'] = func;
                results['c-func'] = (func === norm(c.func));
            }
        } else if (category === 'abc') {
            if (templateId === 0) {
                const tr = parseF(getVal('ans-trad-rate', 'tr'));
                const tcA = parseF(getVal('ans-trad-costA', 'tcA'));
                const tcB = parseF(getVal('ans-trad-costB', 'tcB'));
                const abcA = parseF(getVal('ans-abc-costA', 'abcA'));
                const abcB = parseF(getVal('ans-abc-costB', 'abcB'));
                normalizedAnswers['ans-trad-rate'] = tr;
                normalizedAnswers['ans-trad-costA'] = tcA;
                normalizedAnswers['ans-trad-costB'] = tcB;
                normalizedAnswers['ans-abc-costA'] = abcA;
                normalizedAnswers['ans-abc-costB'] = abcB;

                results['ans-trad-rate'] = Math.abs(tr - c.tradRate) < tolerance;
                results['ans-trad-costA'] = Math.abs(tcA - c.tradCostA) < tolerance;
                results['ans-trad-costB'] = Math.abs(tcB - c.tradCostB) < tolerance;
                results['ans-abc-costA'] = Math.abs(abcA - c.abcCostA) < tolerance;
                results['ans-abc-costB'] = Math.abs(abcB - c.abcCostB) < tolerance;
            } else {
                const profit = parseF(getVal('ans-restruct-profit', 'profit'));
                const perTile = parseF(getVal('ans-restruct-per-tile', 'perTile'));
                normalizedAnswers['ans-restruct-profit'] = profit;
                normalizedAnswers['ans-restruct-per-tile'] = perTile;

                results['ans-restruct-profit'] = Math.abs(profit - c.profit) < 2.0;
                results['ans-restruct-per-tile'] = Math.abs(perTile - c.perTile) < 0.01;
            }
        } else if (category === 'variance') {
            if (templateId === 0) {
                const dmPrice = parseF(getVal('ans-dm-price', 'dmPrice'));
                const dmEff = parseF(getVal('ans-dm-eff', 'dmEff'));
                const dmPeff = norm(getVal('effect-dm-price', 'dmPeff'));
                const dmEeff = norm(getVal('effect-dm-eff', 'dmEeff'));

                const dlPrice = parseF(getVal('ans-dl-price', 'dlPrice'));
                const dlEff = parseF(getVal('ans-dl-eff', 'dlEff'));
                const dlPeff = norm(getVal('effect-dl-price', 'dlPeff'));
                const dlEeff = norm(getVal('effect-dl-eff', 'dlEeff'));
                normalizedAnswers['ans-dm-price'] = dmPrice;
                normalizedAnswers['ans-dm-eff'] = dmEff;
                normalizedAnswers['effect-dm-price'] = dmPeff;
                normalizedAnswers['effect-dm-eff'] = dmEeff;
                normalizedAnswers['ans-dl-price'] = dlPrice;
                normalizedAnswers['ans-dl-eff'] = dlEff;
                normalizedAnswers['effect-dl-price'] = dlPeff;
                normalizedAnswers['effect-dl-eff'] = dlEeff;

                results['ans-dm-price'] = Math.abs(Math.abs(dmPrice) - Math.abs(c.dmPriceVar)) < 2.0;
                results['effect-dm-price'] = (dmPeff === norm(c.dmPriceVar >= 0 ? 'F' : 'U'));
                results['ans-dm-eff'] = Math.abs(Math.abs(dmEff) - Math.abs(c.dmEffVar)) < 2.0;
                results['effect-dm-eff'] = (dmEeff === norm(c.dmEffVar >= 0 ? 'F' : 'U'));
                results['ans-dl-price'] = Math.abs(Math.abs(dlPrice) - Math.abs(c.dlPriceVar)) < 2.0;
                results['effect-dl-price'] = (dlPeff === norm(c.dlPriceVar >= 0 ? 'F' : 'U'));
                results['ans-dl-eff'] = Math.abs(Math.abs(dlEff) - Math.abs(c.dlEffVar)) < 2.0;
                results['effect-dl-eff'] = (dlEeff === norm(c.dlEffVar >= 0 ? 'F' : 'U'));
            } else {
                const seqProd = parseInt(getVal('ans-seq-prod', 'seqProd')) || 0;
                const seqSales = parseInt(getVal('ans-seq-sales', 'seqSales')) || 0;
                const seqDM = parseInt(getVal('ans-seq-dm', 'seqDM')) || 0;
                const seqOp = parseInt(getVal('ans-seq-op', 'seqOp')) || 0;
                const seqBS = parseInt(getVal('ans-seq-bs', 'seqBS')) || 0;
                normalizedAnswers['ans-seq-prod'] = seqProd;
                normalizedAnswers['ans-seq-sales'] = seqSales;
                normalizedAnswers['ans-seq-dm'] = seqDM;
                normalizedAnswers['ans-seq-op'] = seqOp;
                normalizedAnswers['ans-seq-bs'] = seqBS;

                results['ans-seq-prod'] = seqProd === c.prod;
                results['ans-seq-sales'] = seqSales === c.sales;
                results['ans-seq-dm'] = seqDM === c.dm;
                results['ans-seq-op'] = seqOp === c.op;
                results['ans-seq-bs'] = seqBS === c.bs;
            }
        } else if (category === 'fifo') {
            if (templateId === 0) {
                const dmEU = parseF(getVal('ans-fifo-dm-eu', 'dmEU'));
                const convEU = parseF(getVal('ans-fifo-conv-eu', 'convEU'));
                const dmRate = parseF(getVal('ans-fifo-dm-rate', 'dmRate'));
                const convRate = parseF(getVal('ans-fifo-conv-rate', 'convRate'));
                normalizedAnswers['ans-fifo-dm-eu'] = dmEU;
                normalizedAnswers['ans-fifo-conv-eu'] = convEU;
                normalizedAnswers['ans-fifo-dm-rate'] = dmRate;
                normalizedAnswers['ans-fifo-conv-rate'] = convRate;

                results['ans-fifo-dm-eu'] = Math.abs(dmEU - c.currDmEU) < 1.5;
                results['ans-fifo-conv-eu'] = Math.abs(convEU - c.currConvEU) < 1.5;
                results['ans-fifo-dm-rate'] = Math.abs(dmRate - c.rateDM) < 2.5;
                results['ans-fifo-conv-rate'] = Math.abs(convRate - c.rateConv) < 2.5;
            } else if (templateId === 1) {
                const rateBillable = parseF(getVal('ans-rate-billable', 'rateBillable'));
                const rateTotal = parseF(getVal('ans-rate-total', 'rateTotal'));
                normalizedAnswers['ans-rate-billable'] = rateBillable;
                normalizedAnswers['ans-rate-total'] = rateTotal;

                results['ans-rate-billable'] = Math.abs(rateBillable - c.rateBillable) < tolerance;
                results['ans-rate-total'] = Math.abs(rateTotal - c.rateTotal) < tolerance;
            } else {
                const ohRate = parseF(getVal('ans-oh-rate', 'ohRate'));
                const ohAllocated = parseF(getVal('ans-oh-allocated', 'ohAllocated'));
                const ohDiff = parseF(getVal('ans-oh-diff', 'ohDiff'));
                normalizedAnswers['ans-oh-rate'] = ohRate;
                normalizedAnswers['ans-oh-allocated'] = ohAllocated;
                normalizedAnswers['ans-oh-diff'] = ohDiff;

                results['ans-oh-rate'] = Math.abs(ohRate - c.ohRate) < tolerance;
                results['ans-oh-allocated'] = Math.abs(ohAllocated - c.ohAllocated) < 2.0;
                results['ans-oh-diff'] = Math.abs(Math.abs(ohDiff) - Math.abs(c.ohDiff)) < 2.0;
            }
        } else if (category === 'cvp') {
            if (templateId === 0) {
                const cmu = parseF(getVal('ans-cvp-cmu', 'cmu'));
                const be = parseF(getVal('ans-cvp-be', 'be'));
                const profit = parseF(getVal('ans-cvp-profit', 'profit'));
                normalizedAnswers['ans-cvp-cmu'] = cmu;
                normalizedAnswers['ans-cvp-be'] = be;
                normalizedAnswers['ans-cvp-profit'] = profit;

                results['ans-cvp-cmu'] = Math.abs(cmu - c.cmu) < tolerance;
                results['ans-cvp-be'] = Math.abs(be - c.be) < tolerance;
                results['ans-cvp-profit'] = Math.abs(profit - c.profit) < 2.0;
            } else {
                const cmCase = parseF(getVal('ans-bottle-cm-case', 'cmCase'));
                const cmMeter = parseF(getVal('ans-bottle-cm-meter', 'cmMeter'));
                normalizedAnswers['ans-bottle-cm-case'] = cmCase;
                normalizedAnswers['ans-bottle-cm-meter'] = cmMeter;

                results['ans-bottle-cm-case'] = Math.abs(cmCase - c.cmCase) < tolerance;
                results['ans-bottle-cm-meter'] = Math.abs(cmMeter - c.cmMeter) < tolerance;
            }
        }

        let correctCount = 0;
        let totalCount = 0;
        const mistakes = [];
        for (const key in results) {
            totalCount++;
            if (results[key]) {
                correctCount++;
            } else {
                correct = false;
                mistakes.push(key);
            }
        }
        const score = totalCount > 0 ? (correctCount / totalCount) : 1.0;

        return {
            correct,
            score: Math.round(score * 100) / 100,
            results,
            mistakes,
            normalizedAnswers
        };
    }

    window.Controllers.answerVerifier.verify = verify;
    window.verifyAnswers = verify;
})();
