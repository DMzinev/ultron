// cognitive/learningVelocity.js
(function() {
    window.Cognitive = window.Cognitive || {};

    window.Cognitive.learningVelocity = {
        calculate: function(isCorrect, attemptNum) {
            if (isCorrect) {
                // Correct on Strike 1 gets 1.0, Correct on Strike 2 gets 0.5
                return (attemptNum === 1) ? 1.0 : 0.5;
            } else {
                // Incorrect on final strike gets -1.0
                return -1.0;
            }
        }
    };

})();
