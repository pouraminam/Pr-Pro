/**
 * Local Engine HTTP Communication Client.
 *
 * Connects securely to the local helper service at http://127.0.0.1:8990
 * with session token authentication.
 */

import { Logger } from "../utilities/logger.js";

export class EngineClient {
  constructor(baseUrl = "http://127.0.0.1:8990", token = "") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.token = token;
    this.isOnline = false;
  }

  setToken(token) {
    this.token = token;
  }

  setBaseUrl(url) {
    this.baseUrl = url.replace(/\/$/, "");
  }

  async checkHealth() {
    try {
      const resp = await fetch(`${this.baseUrl}/health`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      if (resp.ok) {
        const data = await resp.json();
        this.isOnline = true;
        return { online: true, data };
      }
    } catch (e) {
      this.isOnline = false;
    }
    return { online: false, data: null };
  }

  async request(method, path, body = null) {
    const url = `${this.baseUrl}${path.startsWith("/") ? path : "/" + path}`;
    const headers = {
      "Content-Type": "application/json",
    };

    if (this.token) {
      headers["X-Session-Token"] = this.token;
    }

    const opts = {
      method,
      headers,
    };

    if (body && (method === "POST" || method === "PUT" || method === "DELETE")) {
      opts.body = JSON.stringify(body);
    }

    try {
      const resp = await fetch(url, opts);
      const text = await resp.text();
      let data = {};
      try {
        data = JSON.parse(text);
      } catch (e) {
        data = { raw: text };
      }

      if (!resp.ok) {
        throw new Error(data.error || `HTTP ${resp.status}: ${resp.statusText}`);
      }

      return data;
    } catch (err) {
      Logger.error(`API request failed: ${method} ${path}`, err.message);
      throw err;
    }
  }

  // Model Management Endpoints
  async getModels() {
    return await this.request("GET", "/models");
  }

  async downloadModel(modelName) {
    return await this.request("POST", "/models/download", { model: modelName });
  }

  async deleteModel(modelName) {
    return await this.request("DELETE", `/models/${modelName}`);
  }

  // Audio & Waveform Endpoints
  async extractAudio(mediaFile, outputFile) {
    return await this.request("POST", "/audio/extract", { media_file: mediaFile, output_file: outputFile });
  }

  async getWaveform(wavFile, targetPoints = 1200) {
    return await this.request("POST", "/audio/waveform", { wav_file: wavFile, target_points: targetPoints });
  }

  // Analysis Endpoints
  async transcribe(params) {
    return await this.request("POST", "/analysis/transcribe", params);
  }

  async detectSilence(params) {
    return await this.request("POST", "/analysis/silence", params);
  }

  async quickEdit(params) {
    return await this.request("POST", "/analysis/quick-edit", params);
  }

  // Subtitle Endpoints
  async generateSubtitles(params) {
    return await this.request("POST", "/subtitles/generate", params);
  }

  async translateSubtitles(params) {
    return await this.request("POST", "/subtitles/translate", params);
  }

  async remapSubtitles(params) {
    return await this.request("POST", "/subtitles/remap", params);
  }

  async exportSubtitles(params) {
    return await this.request("POST", "/subtitles/export", params);
  }

  // Task Endpoints
  async getTask(taskId) {
    return await this.request("GET", `/tasks/${taskId}`);
  }

  async cancelTask(taskId) {
    return await this.request("POST", `/tasks/${taskId}/cancel`);
  }
}

export const client = new EngineClient();
