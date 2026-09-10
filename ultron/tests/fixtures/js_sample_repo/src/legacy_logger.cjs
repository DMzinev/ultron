// CommonJS logging module using require and module.exports
const path = require("path");

function logMessage(level, message) {
  const timestamp = new Date().toISOString();
  return `[${timestamp}] [${level.toUpperCase()}] ${message}`;
}

module.exports = {
  logMessage
};
