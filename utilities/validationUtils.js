// utilities/validationUtils.js
(function() {
    window.Utils = window.Utils || {};

    function formatUserAnswers(category, templateId, ans, c) {
                if (!ans || Object.keys(ans).length === 0) return "<span style='color: var(--danger); font-weight: 600;'>No answer submitted</span>";
                let html = "";
                if (category === 'concepts') {
                    if (templateId === 0) {
                        html = `Direct/Indirect: <strong>${ans.di || 'None'}</strong>, Variable/Fixed: <strong>${ans.vf || 'None'}</strong>`;
                    } else if (templateId === 1) {
                        html = `Scenario 1: Total: <strong>€${ans.tot500 || 0}</strong>, Unit: <strong>€${ans.unit500 || 0}</strong> | Scenario 2: Total: <strong>€${ans.tot2000 || 0}</strong>, Unit: <strong>€${ans.unit2000 || 0}</strong>`;
                    } else if (templateId === 2) {
                        html = `Function: <strong>${ans.func === 'SK' ? 'Scorekeeping' : (ans.func === 'AD' ? 'Attention Directing' : (ans.func === 'PS' ? 'Problem Solving' : 'None'))}</strong>`;
                    }
                } else if (category === 'abc') {
                    if (templateId === 0) {
                        html = `Trad Rate: <strong>€${ans.tr || 0}</strong>, Trad Unit Premium: <strong>€${ans.tcA || 0}</strong>, Basic: <strong>€${ans.tcB || 0}</strong> | ABC Unit Premium: <strong>€${ans.abcA || 0}</strong>, Basic: <strong>€${ans.abcB || 0}</strong>`;
                    } else {
                        html = `Operating Profit: <strong>€${(ans.profit || 0).toLocaleString()}</strong>, Profit per tile: <strong>€${ans.perTile || 0}</strong>`;
                    }
                } else if (category === 'variance') {
                    if (templateId === 0) {
                        html = `DM Price: <strong>€${ans.dmPrice || 0} ${ans.dmPeff || ''}</strong>, DM Eff: <strong>€${ans.dmEff || 0} ${ans.dmEeff || ''}</strong> | DL Price: <strong>€${ans.dlPrice || 0} ${ans.dlPeff || ''}</strong>, DL Eff: <strong>€${ans.dlEff || 0} ${ans.dlEeff || ''}</strong>`;
                    } else {
                        html = `Prod: <strong>${ans.seqProd || 0}</strong>, Sales: <strong>${ans.seqSales || 0}</strong>, DM: <strong>${ans.seqDM || 0}</strong>, OpStatement: <strong>${ans.seqOp || 0}</strong>, BalSheet: <strong>${ans.seqBS || 0}</strong>`;
                    }
                } else if (category === 'fifo') {
                    if (templateId === 0) {
                        html = `DM EU: <strong>${ans.dmEU || 0}</strong>, Conv EU: <strong>${ans.convEU || 0}</strong> | DM Rate: <strong>€${ans.dmRate || 0}</strong>, Conv Rate: <strong>€${ans.convRate || 0}</strong>`;
                    } else if (templateId === 1) {
                        html = `Scenario 1 Billable: <strong>€${ans.rateBillable || 0}/hr</strong> | Scenario 2 Total: <strong>€${ans.rateTotal || 0}/hr</strong>`;
                    } else {
                        html = `OH Rate: <strong>€${ans.ohRate || 0}/MH</strong>, Allocated: <strong>€${(ans.ohAllocated || 0).toLocaleString()}</strong>, Diff: <strong>€${(ans.ohDiff || 0).toLocaleString()}</strong>`;
                    }
                } else if (category === 'cvp') {
                    if (templateId === 0) {
                        html = `CM/Unit: <strong>€${ans.cmu || 0}</strong>, BEP: <strong>${ans.be || 0} units</strong>, Profit: <strong>€${(ans.profit || 0).toLocaleString()}</strong>`;
                    } else {
                        html = `CM/Case: <strong>€${ans.cmCase || 0}</strong>, CM/Meter: <strong>€${ans.cmMeter || 0}</strong>`;
                    }
                }
                return html;
            }

    window.Utils.formatUserAnswers = formatUserAnswers;
    window.formatUserAnswers = formatUserAnswers;

})();