/**
 * Silence Detection and Review View.
 *
 * Provides:
 * - Dynamic metrics summary (original duration, cuts, silence removed, edited duration, % saved)
 * - Bulk selection and protection controls
 * - Individual region list with enable/protect toggles and start/end adjustments
 * - Safe timeline cut execution buttons
 */

import { store } from "../state/store.js";
import { bridge } from "../premiere/bridge.js";
import { secondsToTimecode, formatDuration } from "../utilities/formatters.js";

export class SilenceView {
  constructor(containerElement, options = {}) {
    this.container = containerElement;
    this.onCutExecute = options.onCutExecute || null;
    this.onIntervalClick = options.onIntervalClick || null;
  }

  render(state) {
    const intervals = state.silenceIntervals || [];
    const origDuration = state.waveform ? state.waveform.duration : (state.sequence ? state.sequence.duration : 0);

    // Calculate dynamic summary metrics
    const totalSilencesCount = intervals.length;
    const approvedCuts = intervals.filter((s) => s.enabled && !s.protected);
    const approvedCutsCount = approvedCuts.length;

    const totalDetectedSilenceSec = intervals.reduce((acc, s) => acc + (s.end - s.start), 0);
    const proposedRemovalSec = approvedCuts.reduce((acc, s) => acc + (s.end - s.start), 0);
    const estimatedEditedDuration = Math.max(0, origDuration - proposedRemovalSec);
    const timeSavedPct = origDuration > 0 ? (proposedRemovalSec / origDuration) * 100 : 0;

    this.container.innerHTML = `
      <!-- Dynamic Analysis Summary -->
      <div class="card">
        <div class="card-title">
          <span>Silence Analysis Summary</span>
          <span class="badge ${approvedCutsCount > 0 ? 'badge-success' : 'badge-warning'}">
            ${approvedCutsCount} cuts selected
          </span>
        </div>
        <div class="summary-grid">
          <div class="summary-metric">
            <div class="metric-label">Original Duration</div>
            <div class="metric-value">${formatDuration(origDuration)}</div>
          </div>
          <div class="summary-metric">
            <div class="metric-label">Estimated Edited</div>
            <div class="metric-value">${formatDuration(estimatedEditedDuration)}</div>
          </div>
          <div class="summary-metric">
            <div class="metric-label">Silence Removed</div>
            <div class="metric-value">${formatDuration(proposedRemovalSec)}</div>
          </div>
          <div class="summary-metric">
            <div class="metric-label">Time Saved</div>
            <div class="metric-value" style="color: var(--accent-hover);">${timeSavedPct.toFixed(1)}%</div>
          </div>
        </div>
      </div>

      <!-- Bulk Controls -->
      <div class="card">
        <div class="card-title">Bulk Selection Controls</div>
        <div style="display: flex; gap: 4px; flex-wrap: wrap;">
          <button class="btn btn-secondary btn-sm" id="btn-select-all">Select All</button>
          <button class="btn btn-secondary btn-sm" id="btn-deselect-all">Deselect All</button>
          <button class="btn btn-secondary btn-sm" id="btn-select-confirmed">Confirmed Only</button>
          <button class="btn btn-secondary btn-sm" id="btn-select-long">> 1.0s</button>
          <button class="btn btn-secondary btn-sm" id="btn-protect-short">Protect < 500ms</button>
          <button class="btn btn-secondary btn-sm" id="btn-invert-selection">Invert</button>
        </div>
      </div>

      <!-- Individual Silence Regions List -->
      <div class="card" style="flex: 1; display: flex; flex-direction: column;">
        <div class="card-title">
          <span>Detected Silence Regions (${intervals.length})</span>
        </div>
        <div class="silence-list" id="silence-items-container">
          ${intervals.length === 0 ? '<div style="padding: 12px; text-align: center; color: var(--text-muted);">No silence regions detected. Run Analyze first.</div>' : ''}
          ${intervals.map((sil) => this._renderSilenceRow(sil)).join("")}
        </div>
      </div>

      <!-- Timeline Cutting Action Options -->
      <div class="card">
        <div class="card-title">Timeline Cutting Options</div>
        <div class="toggle-row">
          <span class="toggle-label">Safe duplicate sequence (Original preserved)</span>
          <input type="checkbox" id="chk-safe-duplicate" ${state.safeDuplicate ? "checked" : ""}>
        </div>
        <div class="toggle-row">
          <span class="toggle-label">Ripple delete (Close gaps)</span>
          <input type="checkbox" id="chk-ripple-delete" ${state.rippleDelete ? "checked" : ""}>
        </div>
        <div class="action-row" style="margin-top: 10px;">
          <button class="btn btn-secondary" id="btn-cut-only" ${approvedCutsCount === 0 ? "disabled" : ""}>
            Cut Only (Split)
          </button>
          <button class="btn btn-primary" id="btn-cut-remove" ${approvedCutsCount === 0 ? "disabled" : ""}>
            Cut & Remove Silence
          </button>
        </div>
      </div>
    `;

    this._bindEvents();
  }

  _renderSilenceRow(sil) {
    const durStr = `${(sil.end - sil.start).toFixed(2)}s`;
    const timeRange = `${secondsToTimecode(sil.start)} - ${secondsToTimecode(sil.end)}`;
    const classBadge = sil.classification === "confirmed_silence"
      ? '<span class="badge badge-success">Confirmed</span>'
      : (sil.classification === "protected_pause" ? '<span class="badge badge-info">Pause</span>' : '<span class="badge badge-warning">Likely</span>');

    return `
      <div class="silence-item ${sil.protected ? 'protected' : ''} ${!sil.enabled ? 'disabled' : ''}" data-id="${sil.id}">
        <div style="display: flex; align-items: center; gap: 8px;">
          <input type="checkbox" class="silence-toggle" data-id="${sil.id}" ${sil.enabled && !sil.protected ? "checked" : ""} ${sil.protected ? "disabled" : ""}>
          <span class="silence-time" style="cursor: pointer;" title="Click to jump timeline">${timeRange}</span>
          <span style="color: var(--text-secondary); font-size: 10px;">(${durStr})</span>
        </div>
        <div style="display: flex; align-items: center; gap: 6px;">
          ${classBadge}
          <button class="btn btn-secondary btn-sm btn-protect-toggle" data-id="${sil.id}" title="${sil.protected ? 'Unprotect' : 'Protect from cutting'}">
            ${sil.protected ? 'Protected' : 'Protect'}
          </button>
        </div>
      </div>
    `;
  }

  _bindEvents() {
    // Bulk buttons
    this.container.querySelector("#btn-select-all")?.addEventListener("click", () => store.setBulkSilenceSelection("select_all"));
    this.container.querySelector("#btn-deselect-all")?.addEventListener("click", () => store.setBulkSilenceSelection("deselect_all"));
    this.container.querySelector("#btn-select-confirmed")?.addEventListener("click", () => store.setBulkSilenceSelection("confirmed_only"));
    this.container.querySelector("#btn-select-long")?.addEventListener("click", () => store.setBulkSilenceSelection("longer_than_1s"));
    this.container.querySelector("#btn-protect-short")?.addEventListener("click", () => store.setBulkSilenceSelection("protect_under_500ms"));
    this.container.querySelector("#btn-invert-selection")?.addEventListener("click", () => store.setBulkSilenceSelection("invert"));

    // Checkboxes for Safe Duplicate and Ripple Delete
    this.container.querySelector("#chk-safe-duplicate")?.addEventListener("change", (e) => {
      store.setState({ safeDuplicate: e.target.checked });
    });
    this.container.querySelector("#chk-ripple-delete")?.addEventListener("change", (e) => {
      store.setState({ rippleDelete: e.target.checked });
    });

    // Individual toggles
    this.container.querySelectorAll(".silence-toggle").forEach((chk) => {
      chk.addEventListener("change", (e) => {
        const id = e.target.dataset.id;
        store.toggleSilenceCut(id);
      });
    });

    this.container.querySelectorAll(".btn-protect-toggle").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const id = e.target.dataset.id;
        store.toggleSilenceProtect(id);
      });
    });

    // Jump to timeline on click
    this.container.querySelectorAll(".silence-time").forEach((el) => {
      el.addEventListener("click", (e) => {
        const row = e.target.closest(".silence-item");
        const id = row.dataset.id;
        const interval = store.getState().silenceIntervals.find((s) => s.id === id);
        if (interval) {
          bridge.setPlayheadPosition(Math.round(interval.start * 254016000000));
          if (this.onIntervalClick) this.onIntervalClick(interval);
        }
      });
    });

    // Cut buttons
    this.container.querySelector("#btn-cut-only")?.addEventListener("click", () => {
      if (this.onCutExecute) this.onCutExecute({ mode: "cut_only" });
    });

    this.container.querySelector("#btn-cut-remove")?.addEventListener("click", () => {
      if (this.onCutExecute) this.onCutExecute({ mode: "cut_remove" });
    });
  }
}
