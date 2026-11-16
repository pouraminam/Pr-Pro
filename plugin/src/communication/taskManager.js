/**
 * Background Task Polling and Lifecycle Manager.
 */

import { client } from "./client.js";

export class TaskManager {
  constructor(engineClient = client) {
    this.client = engineClient;
    this.activePollers = new Map();
  }

  /**
   * Polls a background task until completion or failure.
   *
   * @param {string} taskId
   * @param {Function} onProgress - (progressPct, stageMsg) => void
   * @param {number} pollIntervalMs - Interval in ms (default: 400)
   * @returns {Promise<Object>} Task result
   */
  pollTask(taskId, onProgress = null, pollIntervalMs = 400) {
    return new Promise((resolve, reject) => {
      let isCancelled = false;

      const poller = setInterval(async () => {
        if (isCancelled) {
          clearInterval(poller);
          return;
        }

        try {
          const task = await this.client.getTask(taskId);

          if (onProgress) {
            onProgress(task.progress || 0, task.stage || "Processing...");
          }

          if (task.status === "completed") {
            clearInterval(poller);
            this.activePollers.delete(taskId);
            resolve(task.result || task);
          } else if (task.status === "failed") {
            clearInterval(poller);
            this.activePollers.delete(taskId);
            reject(new Error(task.error || "Background task failed."));
          } else if (task.status === "cancelled") {
            clearInterval(poller);
            this.activePollers.delete(taskId);
            reject(new Error("Task was cancelled."));
          }
        } catch (e) {
          clearInterval(poller);
          this.activePollers.delete(taskId);
          reject(e);
        }
      }, pollIntervalMs);

      this.activePollers.set(taskId, {
        cancel: () => {
          isCancelled = true;
          clearInterval(poller);
          this.client.cancelTask(taskId).catch(() => {});
        },
      });
    });
  }

  cancelTask(taskId) {
    const entry = this.activePollers.get(taskId);
    if (entry) {
      entry.cancel();
      this.activePollers.delete(taskId);
    }
  }
}

export const taskManager = new TaskManager();
