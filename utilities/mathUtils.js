// utilities/mathUtils.js
(function() {
    window.Utils = window.Utils || {};

    function adjustVal(val) {
        const multiplier = (typeof rsiState !== 'undefined' && rsiState && rsiState.rangeMultiplier) ? rsiState.rangeMultiplier : 1.0;
        return Math.round(val * multiplier);
    }

    window.Utils.adjustVal = adjustVal;
    window.adjustVal = adjustVal;

    function capitalizeFirst(str) { return str.charAt(0).toUpperCase() + str.slice(1); }

    window.Utils.capitalizeFirst = capitalizeFirst;
    window.capitalizeFirst = capitalizeFirst;

    function normalizeText(str) {
        if (str === null || str === undefined) return "";
        return String(str).trim().replace(/\s+/g, " ").toUpperCase();
    }

    window.Utils.normalizeText = normalizeText;
    window.normalizeText = normalizeText;

    /**
     * Deterministically parses a string to a float using accounting/numeric heuristics:
     * - Rule 1: If both comma and dot exist:
     *   - If comma is after dot (e.g. 1.234,56), it is German style: strip dots, replace comma with dot.
     *   - If dot is after comma (e.g. 1,234.56), it is English style: strip commas.
     * - Rule 2: If only comma exists:
     *   - If the comma is followed by exactly 3 digits at the end or in blocks (e.g. 1,234), treat as English thousands separator: strip comma.
     *   - Else (e.g. 12,5 or 1,23), treat as European decimal comma: replace comma with dot.
     * - Rule 3: If only dot exists:
     *   - Treat as thousands separator ONLY if there are multiple dots (e.g. 1.234.567).
     *   - A single dot (e.g. 1.234) is always treated as a decimal point, as decimal fractions are common in cost accounting.
     */
    function parseRobustFloat(val) {
        if (typeof val === 'number') return val;
        if (val === null || val === undefined) return 0;
        let clean = val.toString().trim();
        if (clean === '') return 0;

        // Remove currency symbols and other non-numeric text except digits, minus, dot, comma, and e/E
        clean = clean.replace(/[^\d.,eE-]/g, '');

        if (clean.includes(',') && clean.includes('.')) {
            const lastComma = clean.lastIndexOf(',');
            const lastDot = clean.lastIndexOf('.');
            if (lastComma > lastDot) {
                // German/European style: 1.234,56 -> remove dots, replace comma with dot
                clean = clean.replace(/\./g, '').replace(/,/g, '.');
            } else {
                // English style: 1,234.56 -> remove commas
                clean = clean.replace(/,/g, '');
            }
        } else if (clean.includes(',')) {
            // Check if it matches English thousands pattern (e.g. 40,000 or 1,234,567)
            if (/^\d{1,3}(,\d{3})+$/.test(clean)) {
                clean = clean.replace(/,/g, '');
            } else {
                // Otherwise decimal comma (e.g. 12,5 -> 12.5)
                clean = clean.replace(/,/g, '.');
            }
        } else if (clean.includes('.')) {
            // Check if it matches German thousands pattern (e.g. 12.500 or 40.000.000)
            if (/^\d{1,3}(\.\d{3})+$/.test(clean)) {
                clean = clean.replace(/\./g, '');
            }
        }

        return parseFloat(clean) || 0;
    }

    window.Utils.parseRobustFloat = parseRobustFloat;
    window.parseRobustFloat = parseRobustFloat;

})();