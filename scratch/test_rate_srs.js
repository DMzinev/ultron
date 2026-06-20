// scratch/test_rate_srs.js
const fs = require('fs');
const path = require('path');

// Mock browser globals
global.window = global;
global.document = {
    getElementById: function(id) {
        return {
            style: {},
            innerHTML: "",
            value: ""
        };
    }
};

global.stats = {
    spacedRepQueue: [],
    xp: 0
};

// Mock window.UI.appUI.updateAllUI
global.window.UI = {
    appUI: {
        updateAllUI: function() {
            console.log("updateAllUI called");
        }
    }
};

global.window.Storage = {
    saveStats: function() {
        console.log("saveStats called");
    }
};

// Helper for category display
global.getCategoryDisplayName = function(cat) { return cat; };

// Load mathUtils.js
const mathUtilsContent = fs.readFileSync(path.join(__dirname, '../utilities/mathUtils.js'), 'utf8');
eval(mathUtilsContent);

// Load practiceController.js
const practiceControllerContent = fs.readFileSync(path.join(__dirname, '../controllers/practiceController.js'), 'utf8');
eval(practiceControllerContent);

console.log("Initial currentPracProblem:", window.currentPracProblem);
console.log("Setting window.currentPracProblem...");
window.currentPracProblem = { category: 'concepts', difficulty: 'easy', status: 'ACTIVE', forfeited: false };
console.log("currentPracProblem after set:", window.currentPracProblem);

let saveCount = 0;
window.Storage.saveStats = function() {
    saveCount++;
};

console.log("Calling rateSRS...");
window.rateSRS('good');
console.log("saveCount:", saveCount);
