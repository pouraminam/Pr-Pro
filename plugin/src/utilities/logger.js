/**
 * Logger Utility for Premiere AI Editor.
 * Maintains an in-memory buffer of log events for the Settings Diagnostics view.
 */

const MAX_LOGS = 200;
const logBuffer = [];

export const Logger = {
  info(msg, meta = null) {
    this._log("INFO", msg, meta);
  },
  warn(msg, meta = null) {
    this._log("WARN", msg, meta);
  },
  error(msg, meta = null) {
    this._log("ERROR", msg, meta);
  },
  debug(msg, meta = null) {
    this._log("DEBUG", msg, meta);
  },

  _log(level, msg, meta) {
    const entry = {
      timestamp: new Date().toISOString().split("T")[1].slice(0, 12),
      level,
      message: typeof msg === "string" ? msg : JSON.stringify(msg),
      meta: meta ? JSON.stringify(meta) : null,
    };
    logBuffer.push(entry);
    if (logBuffer.length > MAX_LOGS) {
      logBuffer.shift();
    }
    const logStr = `[${entry.timestamp}] [${level}] ${entry.message}`;
    if (level === "ERROR") {
      console.error(logStr, meta || "");
    } else if (level === "WARN") {
      console.warn(logStr, meta || "");
    } else {
      console.log(logStr, meta || "");
    }
  },

  getLogs() {
    return [...logBuffer];
  },

  clearLogs() {
    logBuffer.length = 0;
  },
};
