/**
 * First-Launch Onboarding Wizard.
 *
 * Verifies Premiere integration, local engine connection, and initial model setup.
 */

import { store } from "../state/store.js";
import { client } from "../communication/client.js";

export class WizardView {
  constructor(containerElement, onFinish = null) {
    this.container = containerElement;
    this.onFinish = onFinish;
  }

  render(state) {
    const isOnline = state.isServiceOnline;
    const hasSeq = !!state.sequence;
    const hw = state.hardwareInfo || {};

    this.container.innerHTML = `
      <div style="padding: 20px; max-width: 480px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px;">
        <div style="text-align: center;">
          <h2 style="font-size: 16px; color: var(--text-primary); margin-bottom: 4px;">Welcome to Premiere AI Editor</h2>
          <p style="font-size: 11px; color: var(--text-secondary);">Local-first AI video editing, silence cutting, and subtitles for Premiere Pro.</p>
        </div>

        <!-- Verification Checklist -->
        <div class="card" style="display: flex; flex-direction: column; gap: 10px;">
          <div style="display: flex; align-items: center; justify-content: space-between; font-size: 12px;">
            <span>1. Adobe Premiere Pro Integration</span>
            <span class="badge ${hasSeq ? 'badge-success' : 'badge-warning'}">
              ${hasSeq ? 'Sequence Ready' : 'Open Sequence'}
            </span>
          </div>

          <div style="display: flex; align-items: center; justify-content: space-between; font-size: 12px;">
            <span>2. Local Processing Helper Engine</span>
            <span class="badge ${isOnline ? 'badge-success' : 'badge-danger'}">
              ${isOnline ? 'Connected' : 'Offline'}
            </span>
          </div>

          <div style="display: flex; align-items: center; justify-content: space-between; font-size: 12px;">
            <span>3. Hardware Acceleration</span>
            <span class="badge ${hw.has_cuda ? 'badge-success' : 'badge-info'}">
              ${hw.has_cuda ? 'NVIDIA CUDA GPU' : 'CPU Mode'}
            </span>
          </div>
        </div>

        <button class="btn btn-primary" id="btn-wizard-finish" style="padding: 8px; font-weight: 600;">
          Launch Panel
        </button>
      </div>
    `;

    this.container.querySelector("#btn-wizard-finish")?.addEventListener("click", () => {
      if (this.onFinish) this.onFinish();
    });
  }
}
