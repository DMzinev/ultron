// cognitive/reflectionEngine.js
(function() {
    window.Cognitive = window.Cognitive || {};

    window.Cognitive.reflectionEngine = {
        compareReflectionToBelief: function(selectedCategory, beliefProfile) {
            const isArithmetic = selectedCategory && (selectedCategory.includes('Arithmetic') || selectedCategory.includes('arithmetic') || selectedCategory.includes('Calculation'));
            const isConceptualConfusion = beliefProfile && (beliefProfile.conceptual > 0.65);
            
            if (isArithmetic && isConceptualConfusion) {
                return {
                    mismatchDetected: true,
                    diagnosticTip: "The error pattern resembles a procedural or conceptual formula mix-up. Take a moment to verify your formula rules before your second attempt."
                };
            }
            return {
                mismatchDetected: false,
                diagnosticTip: ""
            };
        }
    };

})();