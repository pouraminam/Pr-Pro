/**
 * Settings and Diagnostics View.
 *
 * Provides:
 * - Whisper model manager (catalog, status, downloads, delete)
 * - Hardware and acceleration status (CPU, CUDA, VRAM)
 * - Cache management
 * - Live diagnostics log viewer
 */

import { store } from "../state/store.js";
import { client } from "../communication/client.js";
import { Logger } from "../utilities/logger.js";
import { ProjectCache } from "../state/projectCache.js";
import { formatBytes } from "../utilities/formatters.js";

export class SettingsView {
  constructor(containerElement) {
    this.container = containerElement;
    this.modelsList = [];
  }

  async loadModels() {
    try {
      const res = await client.getModels();
      if (res && res.models) {
        this.modelsList = res.models;
        this.render(store.getState());
      }
    } catch (e) {
      Logger.warn("Failed to load models list from engine", e);
    }
  }

  render(state) {
    const hw = state.hardwareInfo || { has_cuda: false, cpu_threads: 4, recommended_device: "cpu" };
    const logs = Logger.getLogs().slice(-40).reverse();
    const cacheSize = ProjectCache.getCacheSizeEstimate();

    this.container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 12px; height: 100%;">
        <!-- Hardware Info Card -->
        <div class="card">
          <div class="card-title">
            <span>Hardware & Processing Engine</span>
            <span class="badge ${hw.has_cuda ? 'badge-success' : 'badge-info'}">
              ${hw.has_cuda ? 'CUDA GPU Detected' : 'CPU Mode'}
            </span>
          </div>
          <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.6;">
            <div><strong>Device:</strong> ${hw.gpu_name || 'Standard CPU'} (${hw.cpu_threads} threads)</div>
            ${hw.vram_mb ? `<div><strong>VRAM:</strong> ${(hw.vram_mb / 1024).toFixed(1)} GB</div>` : ''}
            <div><strong>Recommended Backend:</strong> ${hw.recommended_device.toUpperCase()} (${hw.recommended_compute_type})</div>
          </div>
        </div>

        <!-- Whisper Model Manager -->
        <div class="card">
          <div class="card-title">
            <span>Whisper Speech Models</span>
            <button class="btn btn-secondary btn-sm" id="btn-refresh-models">Refresh</button>
          </div>
          <div style="display: flex; flex-direction: column; gap: 6px; max-height: 180px; overflow-y: auto;">
            ${this.modelsList.length === 0 ? '<div style="color: var(--text-muted); font-size: 11px;">Loading models catalog...</div>' : ''}
            ${this.modelsList.map((m) => this._renderModelRow(m)).join("")}
          </div>
        </div>

        <!-- Cache Management -->
        <div class="card">
          <div class="card-title">Project Data & Cache</div>
          <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px;">
            <span>Cached Projects Data: <strong>${formatBytes(cacheSize)}</strong></span>
            <button class="btn btn-secondary btn-sm" id="btn-clear-cache">Clear Cache</button>
          </div>
        </div>

        <!-- Diagnostics Log -->
        <div class="card" style="flex: 1; display: flex; flex-direction: column; min-height: 140px;">
          <div class="card-title">
            <span>Diagnostics Log</span>
            <button class="btn btn-secondary btn-sm" id="btn-clear-logs">Clear</button>
          </div>
          <div style="flex: 1; overflow-y: auto; background: #111; padding: 6px; border-radius: 3px; font-family: monospace; font-size: 10px; color: #a0a0a0;">
            ${logs.map((l) => `<div style="color: ${l.level === 'ERROR' ? '#fca5a5' : (l.level === 'WARN' ? '#fcd34d' : '#93c5fd')}">[${l.timestamp}] [${l.level}] ${l.message}</div>`).join("")}
          </div>
        </div>
      </div>
    `;

    this._bindEvents();
  }

  _renderModelRow(model) {
    const isInstalled = model.installed;
    return `
      <div style="display: flex; align-items: center; justify-content: space-between; padding: 4px 6px; background: var(--bg-primary); border-radius: 4px; border: 1px solid var(--border-subtle); font-size: 11px;">
        <div>
          <div style="font-weight: 600; color: var(--text-primary);">${model.label}</div>
          <div style="font-size: 10px; color: var(--text-muted);">${model.download_size_mb} MB • RAM: ~${model.ram_required_gb} GB</div>
        </div>
        <div style="display: flex; align-items: center; gap: 6px;">
          ${isInstalled ? '<span class="badge badge-success">Installed</span>' : '<span class="badge badge-info">Not Installed</span>'}
          ${isInstalled ? `
            <button class="btn btn-danger btn-sm btn-delete-model" data-name="${model.name}">Delete</button>
          ` : `
            <button class="btn btn-primary btn-sm btn-download-model" data-name="${model.name}">Download</button>
          `}
        </div>
      </div>
    `;
  }

  _bindEvents() {
    this.container.querySelector("#btn-refresh-models")?.addEventListener("click", () => this.loadModels());

    this.container.querySelectorAll(".btn-download-model").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const name = e.target.dataset.name;
        btn.innerText = "Downloading...";
        btn.disabled = true;
        try {
          await client.downloadModel(name);
          setTimeout(() => this.loadModels(), 2000);
        } catch (err) {
          btn.innerText = "Failed";
        }
      });
    });

    this.container.querySelectorAll(".btn-delete-model").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const name = e.target.dataset.name;
        if (confirm(`Are you sure you want to delete local model '${name}'?`)) {
          await client.deleteModel(name);
          this.loadModels();
        }
      });
    });

    this.container.querySelector("#btn-clear-cache")?.addEventListener("click", () => {
      ProjectCache.clearAll();
      this.render(store.getState());
    });

    this.container.querySelector("#btn-clear-logs")?.addEventListener("click", () => {
      Logger.clearLogs();
      this.render(store.getState());
    });
  }
}
