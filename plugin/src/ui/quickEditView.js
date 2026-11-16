/**
 * Quick Edit Workflow Component.
 *
 * One-click automated YouTube & creator workflow:
 * Transcribe -> Detect Silence -> Safe Duplicate -> Apply Cuts -> Prepare Captions.
 */

import { store } from "../state/store.js";
import { client } from "../communication/client.js";
import { taskManager } from "../communication/taskManager.js";
import { CutPlanner } from "../timeline/cutPlanner.js";
import { TimelineEditor } from "../timeline/timelineEditor.js";
import { Logger } from "../utilities/logger.js";

export class QuickEditView {
  constructor(containerElement, options = {}) {
    this.container = containerElement;
    this.onComplete = options.onComplete || null;
  }

  render(state) {
    this.container.innerHTML = `
      <div class="card" style="border: 1px solid var(--accent-primary); background: #111a24;">
        <div class="card-title" style="color: #7cc0ff;">
          <span>⚡ Quick Edit (YouTube & Creator Preset)</span>
        </div>
        <p style="font-size: 11px; color: var(--text-secondary); margin-bottom: 10px; line-height: 1.5;">
          Automatically transcribes dialogue, detects pauses with balanced timing (500ms / 150ms padding),
          creates a safe duplicate sequence, and removes silence with ripple delete.
        </p>
        <button class="btn btn-primary" id="btn-run-quick-edit" style="width: 100%; padding: 8px; font-weight: 600;" ${state.isBusy ? "disabled" : ""}>
          Run Quick Edit
        </button>
      </div>
    `;

    this._bindEvents();
  }

  _bindEvents() {
    this.container.querySelector("#btn-run-quick-edit")?.addEventListener("click", async () => {
      await this.executeQuickEdit();
    });
  }

  async executeQuickEdit() {
    const state = store.getState();
    const seq = state.sequence;

    if (!seq) {
      alert("Please open or select an active sequence in Premiere Pro first.");
      return;
    }

    store.setState({ isBusy: true, progress: 5, statusMessage: "Starting Quick Edit pipeline..." });

    try {
      const audioPath = seq.primaryMediaPath;
      if (!audioPath) {
        throw new Error("No media file path found in active sequence audio tracks.");
      }

      // 1. Call Quick Edit backend endpoint
      const initRes = await client.quickEdit({
        audio_path: audioPath,
        model: state.model || "base",
        language: state.language || "auto",
        preset: "balanced",
      });

      const taskId = initRes.task_id;

      // 2. Poll progress
      const result = await taskManager.pollTask(taskId, (pct, stage) => {
        store.setState({ progress: pct, statusMessage: stage });
      });

      // 3. Update store with results
      store.setState({
        transcriptSegments: result.transcription.segments || [],
        silenceIntervals: result.silence.silence_intervals || [],
        subtitles: result.subtitles || [],
        remappedSubtitles: result.remapped_subtitles || [],
      });

      // 4. Apply safe timeline cuts
      const planner = new CutPlanner();
      const allTracks = [...(seq.videoTracks || []), ...(seq.audioTracks || [])];
      const plan = planner.createPlan(result.silence.silence_intervals, allTracks, {
        mode: "cut_remove",
        ripple: true,
      });

      const editor = new TimelineEditor();
      const cutResult = await editor.executeCutPlan(plan, { duplicate: true });

      store.setState({
        isBusy: false,
        progress: 100,
        statusMessage: `Quick Edit Complete! Safe duplicate '${cutResult.sequenceName}' created with ${plan.approvedCutsCount} cuts.`,
      });

      if (this.onComplete) {
        this.onComplete(cutResult);
      }
    } catch (e) {
      Logger.error("Quick Edit failed", e);
      store.setState({
        isBusy: false,
        statusMessage: `Quick Edit Error: ${e.message}`,
      });
    }
  }
}
