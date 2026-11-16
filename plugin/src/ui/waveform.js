/**
 * Interactive Audio Waveform Renderer.
 *
 * Renders:
 * - Downsampled audio waveform
 * - Time ruler
 * - Silence regions (muted red)
 * - Protected regions (green outline)
 * - Selected region (blue highlight)
 * - Interactive playhead scrubber and click-to-seek
 */

import { bridge } from "../premiere/bridge.js";
import { secondsToTimecode } from "../utilities/formatters.js";

export class WaveformRenderer {
  constructor(canvasElement, options = {}) {
    this.canvas = canvasElement;
    this.ctx = canvasElement.getContext("2d");
    this.waveform = null;
    this.silenceIntervals = [];
    this.selectedIntervalId = null;
    this.currentTime = 0;
    this.duration = 0;
    this.zoom = 1.0;
    this.onIntervalSelect = options.onIntervalSelect || null;

    this._bindEvents();
  }

  setData(waveformData, silenceIntervals = [], duration = 0) {
    this.waveform = waveformData;
    this.silenceIntervals = silenceIntervals || [];
    this.duration = duration || (waveformData ? waveformData.duration : 0);
    this.render();
  }

  setSelection(intervalId) {
    this.selectedIntervalId = intervalId;
    this.render();
  }

  setCurrentTime(seconds) {
    this.currentTime = Math.max(0, Number(seconds) || 0);
    this.render();
  }

  setZoom(zoomFactor) {
    this.zoom = Math.max(1.0, Math.min(10.0, zoomFactor));
    this.render();
  }

  render() {
    if (!this.canvas || !this.ctx) return;

    const width = this.canvas.width = this.canvas.parentElement.clientWidth || 360;
    const height = this.canvas.height = 110;
    const ctx = this.ctx;

    // Background
    ctx.fillStyle = "#141414";
    ctx.fillRect(0, 0, width, height);

    if (!this.waveform || !this.waveform.peaks_max || this.waveform.peaks_max.length === 0) {
      // Draw placeholder guide
      ctx.fillStyle = "#333333";
      ctx.font = "11px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("No audio loaded or analyzed yet", width / 2, height / 2 + 4);
      return;
    }

    const dur = Math.max(0.1, this.duration);
    const midY = height / 2;

    // 1. Draw Silence and Cut Regions
    for (const sil of this.silenceIntervals) {
      const startX = (sil.start / dur) * width;
      const endX = (sil.end / dur) * width;
      const regionW = Math.max(2, endX - startX);

      if (sil.id === this.selectedIntervalId) {
        // Selected highlight
        ctx.fillStyle = "rgba(20, 115, 230, 0.5)";
        ctx.fillRect(startX, 0, regionW, height);
      } else if (sil.protected) {
        // Protected region
        ctx.fillStyle = "rgba(38, 142, 108, 0.25)";
        ctx.fillRect(startX, 0, regionW, height);
        ctx.strokeStyle = "#268e6c";
        ctx.lineWidth = 1.5;
        ctx.strokeRect(startX, 0, regionW, height);
      } else if (sil.enabled) {
        // Proposed cut
        ctx.fillStyle = "rgba(215, 55, 63, 0.65)";
        ctx.fillRect(startX, 0, regionW, height);
      } else {
        // Disabled cut
        ctx.fillStyle = "rgba(80, 80, 80, 0.25)";
        ctx.fillRect(startX, 0, regionW, height);
      }
    }

    // 2. Draw Waveform Peaks
    const peaksMax = this.waveform.peaks_max;
    const peaksMin = this.waveform.peaks_min;
    const numPoints = peaksMax.length;

    ctx.fillStyle = "#68809a";

    for (let i = 0; i < numPoints; i++) {
      const x = (i / numPoints) * width;
      const barW = Math.max(1, width / numPoints);

      const topY = midY - peaksMax[i] * (midY - 4);
      const bottomY = midY - peaksMin[i] * (midY - 4);
      const barH = Math.max(1, bottomY - topY);

      ctx.fillRect(x, topY, barW, barH);
    }

    // 3. Draw Center Baseline
    ctx.strokeStyle = "#2a2a2a";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, midY);
    ctx.lineTo(width, midY);
    ctx.stroke();

    // 4. Draw Playhead Line
    if (this.currentTime >= 0 && this.currentTime <= dur) {
      const playheadX = (this.currentTime / dur) * width;
      ctx.strokeStyle = "#2680eb";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(playheadX, 0);
      ctx.lineTo(playheadX, height);
      ctx.stroke();

      // Playhead handle
      ctx.fillStyle = "#2680eb";
      ctx.beginPath();
      ctx.moveTo(playheadX - 4, 0);
      ctx.lineTo(playheadX + 4, 0);
      ctx.lineTo(playheadX, 7);
      ctx.fill();
    }
  }

  _bindEvents() {
    this.canvas.addEventListener("click", (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const width = this.canvas.width;

      if (!this.duration || width <= 0) return;

      const clickTime = (clickX / width) * this.duration;
      this.currentTime = clickTime;
      this.render();

      // Move Premiere playhead
      bridge.setPlayheadPosition(Math.round(clickTime * 254016000000));

      // Check if clicked inside a silence interval
      const clickedInterval = this.silenceIntervals.find(
        (s) => clickTime >= s.start && clickTime <= s.end
      );

      if (clickedInterval) {
        this.selectedIntervalId = clickedInterval.id;
        if (this.onIntervalSelect) {
          this.onIntervalSelect(clickedInterval);
        }
        this.render();
      }
    });
  }
}
