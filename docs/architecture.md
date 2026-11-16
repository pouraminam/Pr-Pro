# Architecture Documentation — Premiere AI Editor

## 1. System Overview

Premiere AI Editor is a local-first video editing extension designed for Adobe Premiere Pro. It combines automated speech transcription, voice activity and energy-based silence detection, safe timeline cutting, and bilingual subtitle workflows into a dockable UXP panel.

The architecture strictly adheres to three foundational principles:
1. **Local-First & Offline:** Speech inference, silence analysis, and translation run locally on loopback (`127.0.0.1`) without mandatory cloud APIs, external accounts, or remote audio uploads.
2. **Safe & Reversible Editing:** Original sequences remain untouched by default. Edits are executed on safe duplicated sequences (`OriginalName_AI_Edited`) inside atomic Premiere undo transactions.
3. **Exact Timebase Synchronization:** All cuts and subtitles align to sequence frame boundaries (23.976, 24, 25, 29.97, 30, 50, 59.94, 60 fps) using Premiere's internal `254016000000` ticks-per-second timebase to eliminate cumulative drift.

```
┌────────────────────────────────────────────────────────┐
│               Adobe Premiere Pro (Host)                │
│                                                        │
│  ┌──────────────────────┐    ┌──────────────────────┐  │
│  │   Active Sequence    │    │  Sequence Duplicate  │  │
│  │  (Original Preserved)│    │ (_AI_Edited Target)  │  │
│  └──────────┬───────────┘    └──────────▲───────────┘  │
│             │                           │              │
│             │ Sequence Inspection       │ Edit Plan    │
│             ▼                           │ Transactions │
│  ┌──────────────────────────────────────┴───────────┐  │
│  │         UXP Panel (Adobe Spectrum UI)            │  │
│  │   - Tab 1: Analyze (Model, Preset, Quick Edit)   │  │
│  │   - Tab 2: Silence (Waveform, Cut Approval)      │  │
│  │   - Tab 3: Transcript (RTL/LTR, Edit, Search)    │  │
│  │   - Tab 4: Subtitles (Bilingual, Retiming)       │  │
│  │   - Tab 5: Settings (Model Manager, Hardware)    │  │
│  └──────────────────────▲───────────────────────────┘  │
└─────────────────────────┼──────────────────────────────┘
                          │ HTTP / REST (Loopback 127.0.0.1)
                          │ Headers: X-Session-Token
                          ▼
┌────────────────────────────────────────────────────────┐
│             Local Engine Helper Service                │
│             (Python 3 / CTranslate2)                   │
│                                                        │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  Faster-Whisper   │  │    Silero VAD    │            │
│  │ (CPU / CUDA GPU) │  │  (Energy + ONNX) │            │
│  └────────┬─────────┘  └────────┬─────────┘            │
│           │                     │                      │
│           ▼                     ▼                      │
│  ┌────────────────────────────────────────┐            │
│  │ Hybrid Detector & Timeline Time Mapper │            │
│  │ - Padded Speech & Silence Interval Calc│            │
│  │ - Sentence-Aware Subtitle Generator    │            │
│  │ - Offline Persian <-> English Engine   │            │
│  └────────────────────────────────────────┘            │
└────────────────────────────────────────────────────────┘
```

---

## 2. Component Boundaries

### Component A — Adobe Premiere UI (UXP Panel)
- **Technology:** HTML5, CSS3 (Adobe Spectrum Dark Theme), Modern JavaScript ES Modules.
- **Location:** `plugin/src/ui/`, `plugin/styles/`
- **Responsibilities:**
  - Dockable panel inside Premiere Pro workspace.
  - Interactive HTML5 Canvas audio waveform visualizer.
  - Real-time summary calculation (original duration, cuts count, silence removed, % saved).
  - Persian RTL text rendering with proper shaping and half-space (`\u200c`) support.
  - Tab views: Analyze, Silence, Transcript, Subtitles, Settings, Quick Edit.

### Component B — Local Processing Engine
- **Technology:** Python 3 standard library `ThreadingHTTPServer`, Faster-Whisper, Silero VAD, wave/struct PCM processing.
- **Location:** `engine/`
- **Responsibilities:**
  - 16kHz mono audio extraction and normalization.
  - Sample-accurate RMS and dBFS frame energy calculation with hysteresis.
  - Silero VAD voice activity detection.
  - Hybrid silence detection combining energy thresholds, VAD probabilities, and Whisper word timestamps.
  - Sentence-aware subtitle segmentation (max chars per line, max lines, reading speed limits).
  - Offline bidirectional Persian <-> English translation with technical glossary protection.

### Component C — Communication Layer
- **Location:** `plugin/src/communication/`, `engine/security/`
- **Responsibilities:**
  - Loopback-only binding (`127.0.0.1`).
  - Cryptographically secure session token authentication (`X-Session-Token`).
  - Path traversal validation against allowed project media directories.
  - Asynchronous background task polling (`/tasks/:id`) with cancellation support.

### Component D — Timeline Editing Engine
- **Location:** `plugin/src/premiere/`, `plugin/src/timeline/`
- **Responsibilities:**
  - Sequence inspection (video tracks, audio tracks, clips, lock states).
  - Sequence cloning (`OriginalName_AI_Edited`).
  - Cut planning across synchronized audio and video tracks.
  - Native Premiere transaction execution (`app.project.executeTransaction`).
  - Safe rollback and error recovery.

### Component E — Subtitle Engine
- **Location:** `engine/subtitles/`, `plugin/src/ui/subtitleView.js`
- **Responsibilities:**
  - Subtitle generation conforming to reading speed and line length rules.
  - Formatting to SRT, WebVTT, Plain Text, and JSON.
  - **Shared Original-to-Edited Time Mapping:** Automatically retimes captions when silence is cut or rippled out so subtitles never drift.
  - "Add Captions to Premiere" project bin import workflow.

---

## 3. Communication Protocols

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health check and hardware discovery (CPU, CUDA GPU, VRAM). |
| `GET` | `/models` | Catalog of Whisper models, download status, and disk sizes. |
| `POST` | `/models/download` | Initiates background download for specified model. |
| `DELETE` | `/models/:name` | Removes local model files from disk. |
| `POST` | `/audio/extract` | Converts media file to 16kHz mono PCM WAV. |
| `POST` | `/audio/waveform` | Generates downsampled peak/RMS envelopes for UI waveform. |
| `POST` | `/analysis/transcribe`| Asynchronous Faster-Whisper speech transcription. |
| `POST` | `/analysis/silence` | Energy, Silero VAD, or Hybrid silence detection. |
| `POST` | `/analysis/quick-edit`| One-call pipeline: transcribe + detect silence + plan cuts. |
| `POST` | `/subtitles/generate` | Generates segmented subtitle items from transcript. |
| `POST` | `/subtitles/translate`| Offline Persian <-> English translation. |
| `POST` | `/subtitles/remap` | Retimes subtitles to match edited timeline cuts. |
| `POST` | `/subtitles/export` | Formats subtitles to SRT, WebVTT, Plain Text, or JSON. |
| `GET` | `/tasks/:id` | Polls progress (0-100%) and stage of active tasks. |
| `POST` | `/tasks/:id/cancel` | Requests cancellation of running task. |
| `POST` | `/shutdown` | Gracefully shuts down helper service. |
