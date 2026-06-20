// utilities/dateUtils.js
(function() {
    window.Utils = window.Utils || {};

    function formatTimeAgo(timestamp) {
                const diff = Date.now() - timestamp;
                if (diff < 60 * 1000) return "Just now";
                const mins = Math.floor(diff / (60 * 1000));
                if (mins < 60) return `${mins}m ago`;
                const hrs = Math.floor(diff / (3600 * 1000));
                if (hrs < 24) return `${hrs}h ago`;
                const days = Math.floor(diff / (24 * 3600 * 1000));
                return `${days}d ago`;
            }

    window.Utils.formatTimeAgo = formatTimeAgo;
    window.formatTimeAgo = formatTimeAgo;

})();