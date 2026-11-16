/**
 * Central Reactive State Store for Premiere AI Editor Plugin.
 */

export class Store {
  constructor() {
    this.state = {
      activeTab: "analyze",
      isServiceOnline: false,
      hardwareInfo: null,
      sequence: null,
      compatibility: null,
      selectedAudioTrackIndex: 0,

      // Settings
      model: "base",
      language: "auto",
      device: "auto",
      silenceMode: "hybrid",
      silencePreset: "balanced",
      customSilenceParams: {
        threshold_db: -35.0,
        min_silence_ms: 500,
        padding_before_ms: 150,
        padding_after_ms: 200,
        min_speech_ms: 250,
      },
      preserveBreathing: true,

      // Analysis Results
      waveform: null,
      silenceIntervals: [],
      transcriptSegments: [],
      subtitles: [],
      remappedSubtitles: [],

      // Timeline Editing Options
      editMode: "cut_remove", // cut_remove, cut_only, analyze_only
      rippleDelete: true,
      safeDuplicate: true,

      // Progress State
      isBusy: false,
      progress: 0,
      statusMessage: "",
    };

    this.listeners = new Set();
  }

  getState() {
    return this.state;
  }

  setState(partial) {
    this.state = { ...this.state, ...partial };
    this._notify();
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  _notify() {
    for (const listener of this.listeners) {
      try {
        listener(this.state);
      } catch (e) {
        console.error("Store listener error:", e);
      }
    }
  }

  // Helper actions
  toggleSilenceCut(silenceId) {
    const list = this.state.silenceIntervals.map((s) => {
      if (s.id === silenceId) {
        return { ...s, enabled: !s.enabled };
      }
      return s;
    });
    this.setState({ silenceIntervals: list });
  }

  toggleSilenceProtect(silenceId) {
    const list = this.state.silenceIntervals.map((s) => {
      if (s.id === silenceId) {
        const nextProtected = !s.protected;
        return { ...s, protected: nextProtected, enabled: !nextProtected };
      }
      return s;
    });
    this.setState({ silenceIntervals: list });
  }

  setBulkSilenceSelection(action) {
    let list = [...this.state.silenceIntervals];

    if (action === "select_all") {
      list = list.map((s) => ({ ...s, enabled: true, protected: false }));
    } else if (action === "deselect_all") {
      list = list.map((s) => ({ ...s, enabled: false }));
    } else if (action === "confirmed_only") {
      list = list.map((s) => ({
        ...s,
        enabled: s.classification === "confirmed_silence",
        protected: s.classification !== "confirmed_silence",
      }));
    } else if (action === "longer_than_1s") {
      list = list.map((s) => ({
        ...s,
        enabled: s.duration >= 1.0,
      }));
    } else if (action === "protect_under_500ms") {
      list = list.map((s) => ({
        ...s,
        protected: s.duration < 0.5 ? true : s.protected,
        enabled: s.duration < 0.5 ? false : s.enabled,
      }));
    } else if (action === "invert") {
      list = list.map((s) => ({
        ...s,
        enabled: !s.enabled,
      }));
    }

    this.setState({ silenceIntervals: list });
  }
}

export const store = new Store();
