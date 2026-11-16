/**
 * Local Helper Service Launcher and Health Poller.
 * Checks for running helper service or attempts connection across standard ports.
 */

import { client } from "./client.js";
import { Logger } from "../utilities/logger.js";

export class ServiceLauncher {
  constructor(engineClient = client) {
    this.client = engineClient;
  }

  async checkOrConnect(ports = [8990, 8991, 8992]) {
    for (const port of ports) {
      this.client.setBaseUrl(`http://127.0.0.1:${port}`);
      const health = await this.client.checkHealth();
      if (health.online) {
        Logger.info(`Connected to Premiere AI Editor Engine on port ${port}`);
        return { connected: true, port, data: health.data };
      }
    }
    return { connected: false, port: null, data: null };
  }
}

export const launcher = new ServiceLauncher();
