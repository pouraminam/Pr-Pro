/**
 * Main Panel UI Controller and View Orchestrator.
 */

import { store } from "../state/store.js";
import { client } from "../communication/client.js";
import { taskManager } from "../communication/taskManager.js";
import { bridge } from "../premiere/bridge.js";
import { SequenceInspector } from "../premiere/sequenceInspector.js";
import { CompatibilityChecker } from "../premiere/compatibilityChecker.js";
import { CutPlanner } from "../timeline/cutPlanner.js";
import { TimelineEditor } from "../timeline/timelineEditor.js";
import { WaveformRenderer } from "./waveform.js";
import { SilenceView } from "./silenceView.js";
import { TranscriptView } from "./transcriptView.js";
import { SubtitleView } from "./subtitleView.js";
import { SettingsView } from "./settingsView.js";
import { QuickEditView } from "./quickEditView.js";
import { WizardView } from "./wizardView.js";
import { SubtitleGenerator } from "../../../engine/subtitles/generator.js";
import { Logger } from "../utilities/logger.js";

export class PanelController {
  constructor(rootElement) {
    this.root = rootElement;
    this.inspector = new SequenceInspector();
    this.compatChecker = new CompatibilityChecker();
    this.waveformRenderer = null;
    this.silenceView = null;
    this.transcriptView = null;
    this.subtitleView = null;
    this.settingsView = null;
    this.quickEditView = null;
  }

  async init() {
    this._renderBaseLayout();
    this._initViews();
    this._bindTabNavigation();

    // Subscribe to state updates
    store.subscribe((state) => this._onStateUpdate(state));

    // Initial sequence discovery
    await this.refreshSequence();

    // Check helper connection
    await this.checkEngineConnection();
  }

  _renderBaseLayout() {
    this.root.innerHTML = `
      <div id="app-container">
        <!-- Header -->
        <header class="panel-header">
          <div class="panel-title">
            <span>Premiere AI Editor</span>
            <span class="badge" id="sequence-badge">No Sequence</span>
          </div>
          <div class="service-status">
            <div class="status-dot offline" id="service-dot"></div>
            <span id="service-label">Helper Offline</span>
          </div>
        </header>

        <!-- Tab Bar -->
        <nav class="tab-bar">
          <button class="tab-btn active" data-tab="analyze">Analyze</button>
          <button class="tab-btn" data-tab="silence">Silence</button>
          <button class="tab-btn" data-tab="transcript">Transcript</button>
          <button class="tab-btn" data-tab="subtitles">Subtitles</button>
          <button class="tab-btn" data-tab="settings">Settings</button>
        </nav>

        <!-- Progress Banner -->
        <div class="progress-card" id="progress-card" style="margin: 8px 12px 0 12px;">
          <div class="progress-header">
            <span id="progress-stage">Processing...</span>
            <span id="progress-pct">0%</span>
          </div>
          <div class="progress-bar-track">
            <div class="progress-bar-fill" id="progress-fill"></div>
          </div>
        </div>

        <!-- Main Content Area -->
        <main class="panel-content">
          <!-- Tab 1: Analyze -->
          <div class="tab-pane active" id="pane-analyze">
            <!-- Compatibility Banner -->
            <div id="compat-banner" style="display:none; padding: 6px 8px; border-radius: 4px; font-size: 11px;"></div>

            <!-- Quick Edit Card -->
            <div id="quick-edit-container"></div>

            <!-- Sequence and Audio Source -->
            <div class="card">
              <div class="card-title">
                <span>Timeline Audio Source</span>
                <button class="btn btn-secondary btn-sm" id="btn-refresh-seq">Refresh</button>
              </div>
              <div class="form-group">
                <label class="form-label">Dialogue Track</label>
                <select id="select-audio-track" class="form-control"></select>
              </div>
            </div>

            <!-- Speech & Silence Configuration -->
            <div class="card">
              <div class="card-title">Analysis Settings</div>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                <div class="form-group">
                  <label class="form-label">Whisper Model</label>
                  <select id="select-whisper-model" class="form-control">
                    <option value="tiny">Tiny (Fastest)</option>
                    <option value="base" selected>Base (Recommended)</option>
                    <option value="small">Small (High Accuracy)</option>
                    <option value="medium">Medium</option>
                    <option value="large-v3">Large-v3 (Studio)</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">Language</label>
                  <select id="select-language" class="form-control">
                    <option value="auto" selected>Auto Detect</option>
                    <option value="fa">Persian (فارسی)</option>
                    <option value="en">English</option>
                  </select>
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">Silence Preset</label>
                <select id="select-silence-preset" class="form-control">
                  <option value="conservative">Conservative (Natural speech flow)</option>
                  <option value="balanced" selected>Balanced (Standard pauses)</option>
                  <option value="aggressive">Aggressive (Fast-paced)</option>
                </select>
              </div>

              <div class="toggle-row">
                <span class="toggle-label">Preserve Natural Breathing</span>
                <input type="checkbox" id="chk-preserve-breathing" checked>
              </div>

              <button class="btn btn-primary" id="btn-run-analysis" style="width: 100%; margin-top: 10px; padding: 8px;">
                Analyze Speech & Silence
              </button>
            </div>
          </div>

          <!-- Tab 2: Silence Review -->
          <div class="tab-pane" id="pane-silence">
            <div class="waveform-container">
              <div class="waveform-toolbar">
                <span>Waveform & Silence Regions</span>
                <div class="waveform-legend">
                  <div class="legend-item"><div class="legend-color legend-speech"></div>Speech</div>
                  <div class="legend-item"><div class="legend-color legend-cut"></div>Cut</div>
                  <div class="legend-item"><div class="legend-color legend-protected"></div>Protected</div>
                </div>
              </div>
              <div class="waveform-viewport">
                <canvas id="waveform-canvas"></canvas>
              </div>
            </div>
            <div id="silence-view-container" style="display: flex; flex-direction: column; gap: 12px; flex: 1;"></div>
          </div>

          <!-- Tab 3: Transcript -->
          <div class="tab-pane" id="pane-transcript"></div>

          <!-- Tab 4: Subtitles -->
          <div class="tab-pane" id="pane-subtitles"></div>

          <!-- Tab 5: Settings -->
          <div class="tab-pane" id="pane-settings"></div>
        </main>
      </div>
    `;
  }

  _initViews() {
    // Waveform
    const canvas = this.root.querySelector("#waveform-canvas");
    this.waveformRenderer = new WaveformRenderer(canvas, {
      onIntervalSelect: (interval) => {
        store.setState({ selectedIntervalId: interval.id });
      },
    });

    // Quick Edit
    const qeContainer = this.root.querySelector("#quick-edit-container");
    this.quickEditView = new QuickEditView(qeContainer, {
      onComplete: () => this._switchTab("silence"),
    });

    // Silence View
    const silenceContainer = this.root.querySelector("#silence-view-container");
    this.silenceView = new SilenceView(silenceContainer, {
      onCutExecute: async (opts) => await this._executeCutPlan(opts.mode),
    });

    // Transcript View
    const transcriptContainer = this.root.querySelector("#pane-transcript");
    this.transcriptView = new TranscriptView(transcriptContainer);

    // Subtitle View
    const subtitleContainer = this.root.querySelector("#pane-subtitles");
    this.subtitleView = new SubtitleView(subtitleContainer);

    // Settings View
    const settingsContainer = this.root.querySelector("#pane-settings");
    this.settingsView = new SettingsView(settingsContainer);

    this._bindAnalyzeTabControls();
  }

  _bindTabNavigation() {
    this.root.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.tab;
        this._switchTab(tab);
      });
    });
  }

  _switchTab(tabName) {
    store.setState({ activeTab: tabName });

    this.root.querySelectorAll(".tab-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === tabName);
    });

    this.root.querySelectorAll(".tab-pane").forEach((p) => {
      p.classList.toggle("active", p.id === `pane-${tabName}`);
    });

    // Trigger specific view renders on switch
    const state = store.getState();
    if (tabName === "silence") {
      this.waveformRenderer.render();
      this.silenceView.render(state);
    } else if (tabName === "transcript") {
      this.transcriptView.render(state);
    } else if (tabName === "subtitles") {
      this.subtitleView.render(state);
    } else if (tabName === "settings") {
      this.settingsView.render(state);
      this.settingsView.loadModels();
    }
  }

  _bindAnalyzeTabControls() {
    this.root.querySelector("#btn-refresh-seq")?.addEventListener("click", () => this.refreshSequence());

    this.root.querySelector("#select-whisper-model")?.addEventListener("change", (e) => {
      store.setState({ model: e.target.value });
    });

    this.root.querySelector("#select-language")?.addEventListener("change", (e) => {
      store.setState({ language: e.target.value });
    });

    this.root.querySelector("#select-silence-preset")?.addEventListener("change", (e) => {
      store.setState({ silencePreset: e.target.value });
    });

    this.root.querySelector("#chk-preserve-breathing")?.addEventListener("change", (e) => {
      store.setState({ preserveBreathing: e.target.checked });
    });

    this.root.querySelector("#btn-run-analysis")?.addEventListener("click", async () => {
      await this.runFullAnalysis();
    });
  }

  async checkEngineConnection() {
    try {
      const res = await client.checkHealth();
      if (res.online) {
        store.setState({ isServiceOnline: true, hardwareInfo: res.data.hardware });
        this._updateServiceIndicator(true);
      } else {
        store.setState({ isServiceOnline: false });
        this._updateServiceIndicator(false);
      }
    } catch (e) {
      this._updateServiceIndicator(false);
    }
  }

  _updateServiceIndicator(online) {
    const dot = this.root.querySelector("#service-dot");
    const label = this.root.querySelector("#service-label");
    if (dot && label) {
      dot.className = `status-dot ${online ? "online" : "offline"}`;
      label.innerText = online ? "Helper Online" : "Helper Offline";
    }
  }

  async refreshSequence() {
    const seq = await this.inspector.inspectActiveSequence();
    const badge = this.root.querySelector("#sequence-badge");
    const trackSelect = this.root.querySelector("#select-audio-track");

    if (seq) {
      const compat = this.compatChecker.analyze(seq);
      store.setState({ sequence: seq, compatibility: compat });

      if (badge) {
        badge.innerText = seq.name;
        badge.className = "badge badge-info";
      }

      this._renderCompatBanner(compat);

      // Populate audio tracks dropdown
      if (trackSelect && seq.audioTracks) {
        trackSelect.innerHTML = seq.audioTracks
          .map((t, idx) => `<option value="${idx}">${t.name} (${t.clips.length} clips)</option>`)
          .join("");
      }
    } else {
      if (badge) {
        badge.innerText = "No Sequence";
        badge.className = "badge";
      }
      this._renderCompatBanner(this.compatChecker.analyze(null));
    }
  }

  _renderCompatBanner(compat) {
    const banner = this.root.querySelector("#compat-banner");
    if (!banner) return;

    if (!compat || compat.status === "fully_supported") {
      banner.style.display = "none";
    } else {
      banner.style.display = "block";
      banner.style.background = compat.status === "unsupported" ? "#4d181b" : "#4a3411";
      banner.style.color = compat.status === "unsupported" ? "#fca5a5" : "#fcd34d";
      banner.innerHTML = `<strong>${compat.label}:</strong> ${compat.reasons.join(" ")}`;
    }
  }

  async runFullAnalysis() {
    const state = store.getState();
    const seq = state.sequence;

    if (!seq) {
      alert("No active sequence found. Please open a sequence in Premiere Pro.");
      return;
    }

    const audioPath = seq.primaryMediaPath;
    if (!audioPath) {
      alert("No media audio file could be identified in the active sequence.");
      return;
    }

    store.setState({ isBusy: true, progress: 10, statusMessage: "Transcribing speech..." });

    try {
      // 1. Transcribe speech
      const transInit = await client.transcribe({
        audio_path: audioPath,
        model: state.model,
        language: state.language,
        device: state.device,
        word_timestamps: true,
      });

      const transResult = await taskManager.pollTask(transInit.task_id, (pct, msg) => {
        store.setState({ progress: 10 + pct * 0.5, statusMessage: msg });
      });

      // 2. Detect silence
      store.setState({ progress: 65, statusMessage: "Analyzing audio waveforms and detecting silence..." });
      const silenceResult = await client.detectSilence({
        audio_path: audioPath,
        mode: state.silenceMode,
        preset: state.silencePreset,
        preserve_breathing: state.preserveBreathing,
        transcript_segments: transResult.segments,
      });

      // 3. Generate waveform envelope
      const waveformResult = await client.getWaveform(audioPath, 1200);

      // 4. Generate subtitles
      const subResult = await client.generateSubtitles({
        segments: transResult.segments,
        language: transResult.language || "en",
      });

      // 5. Update store
      store.setState({
        isBusy: false,
        progress: 100,
        statusMessage: "Analysis complete.",
        waveform: waveformResult,
        silenceIntervals: silenceResult.silence_intervals,
        transcriptSegments: transResult.segments,
        subtitles: subResult.subtitles,
      });

      // Switch to Silence review tab
      this._switchTab("silence");
    } catch (e) {
      Logger.error("Analysis failed", e);
      store.setState({
        isBusy: false,
        statusMessage: `Analysis error: ${e.message}`,
      });
      alert(`Analysis failed: ${e.message}`);
    }
  }

  async _executeCutPlan(mode) {
    const state = store.getState();
    const seq = state.sequence;
    if (!seq) return;

    const planner = new CutPlanner();
    const allTracks = [...(seq.videoTracks || []), ...(seq.audioTracks || [])];

    const plan = planner.createPlan(state.silenceIntervals, allTracks, {
      mode,
      ripple: state.rippleDelete,
    });

    if (plan.approvedCutsCount === 0) {
      alert("No silence cuts are currently approved.");
      return;
    }

    const editor = new TimelineEditor();
    store.setState({ isBusy: true, statusMessage: "Applying timeline edits in Premiere Pro..." });

    try {
      const res = await editor.executeCutPlan(plan, {
        duplicate: state.safeDuplicate,
        suffix: "_AI_Edited",
      });

      store.setState({
        isBusy: false,
        statusMessage: `Cuts applied successfully to '${res.sequenceName}'.`,
      });

      alert(`Successfully created '${res.sequenceName}' with ${plan.approvedCutsCount} cuts! Original sequence remained untouched.`);
      await this.refreshSequence();
    } catch (e) {
      store.setState({ isBusy: false, statusMessage: `Cutting failed: ${e.message}` });
      alert(`Timeline editing error: ${e.message}`);
    }
  }

  _onStateUpdate(state) {
    // Update progress banner
    const progCard = this.root.querySelector("#progress-card");
    const progStage = this.root.querySelector("#progress-stage");
    const progPct = this.root.querySelector("#progress-pct");
    const progFill = this.root.querySelector("#progress-fill");

    if (progCard && progStage && progPct && progFill) {
      if (state.isBusy) {
        progCard.style.display = "block";
        progStage.innerText = state.statusMessage || "Processing...";
        progPct.innerText = `${Math.round(state.progress)}%`;
        progFill.style.width = `${state.progress}%`;
      } else {
        progCard.style.display = "none";
      }
    }

    if (this.waveformRenderer && state.waveform) {
      this.waveformRenderer.setData(state.waveform, state.silenceIntervals);
    }
  }
}
