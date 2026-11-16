/**
 * Adobe Premiere Pro Bridge.
 *
 * Provides a unified abstraction over Adobe Premiere Pro UXP DOM APIs,
 * with fallbacks for testing and mock environments.
 */

import { Logger } from "../utilities/logger.js";

let pproHost = null;

// Attempt to load native Premiere Pro UXP module if available
try {
  if (typeof window !== "undefined" && typeof window.require === "function") {
    pproHost = window.require("premierepro");
  } else if (typeof require === "function") {
    pproHost = require("premierepro");
  }
} catch (e) {
  Logger.warn("Premiere Pro native module not detected. Using simulated bridge for standalone/test execution.");
}

export class PremiereBridge {
  constructor(customHost = null) {
    this.host = customHost || pproHost;
    this.isNative = !!this.host;
  }

  isAvailable() {
    return this.isNative && !!this.host.app;
  }

  getApp() {
    return this.isAvailable() ? this.host.app : null;
  }

  getActiveProject() {
    if (!this.isAvailable()) return null;
    return this.host.app.project || null;
  }

  getActiveSequence() {
    const proj = this.getActiveProject();
    return proj ? proj.activeSequence : null;
  }

  /**
   * Sets playhead time in the active sequence.
   * @param {number|BigInt} ticks - Premiere ticks or seconds
   */
  async setPlayheadPosition(ticks) {
    const seq = this.getActiveSequence();
    if (!seq) return false;

    try {
      if (typeof seq.setPlayerPosition === "function") {
        await seq.setPlayerPosition(String(ticks));
        return true;
      }
    } catch (e) {
      Logger.error("Failed to set playhead position", e);
    }
    return false;
  }

  /**
   * Imports a media or subtitle file into the Premiere project root bin.
   * @param {string} filePath - Absolute path to file
   */
  async importFile(filePath) {
    const proj = this.getActiveProject();
    if (!proj) return null;

    try {
      if (typeof proj.importFiles === "function") {
        const success = await proj.importFiles([filePath], true, proj.rootItem, false);
        return success;
      }
    } catch (e) {
      Logger.error(`Failed to import file: ${filePath}`, e);
    }
    return false;
  }

  /**
   * Executes an atomic undoable transaction in Premiere Pro.
   * @param {Function} transactionFn - Callback receiving transaction context
   * @param {string} transactionName - Undo label displayed in Premiere history
   */
  async executeTransaction(transactionFn, transactionName = "Premiere AI Editor Edits") {
    const proj = this.getActiveProject();
    if (!proj) {
      throw new Error("No active Premiere project found.");
    }

    if (typeof proj.executeTransaction === "function") {
      return await proj.executeTransaction(transactionFn, transactionName);
    } else {
      // Fallback direct execution if executeTransaction is unsupported in this version
      return await transactionFn();
    }
  }
}

export const bridge = new PremiereBridge();
