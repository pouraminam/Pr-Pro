# Adobe Premiere Pro Extensibility & API Compatibility Matrix

This document provides technical verification details for Adobe Premiere Pro APIs, version support, and UXP DOM methods utilized by Premiere AI Editor.

---

## 1. Supported Host Versions

| Premiere Pro Version | Extensibility Platform | Support Status | Key Capabilities Utilized |
|---|---|---|---|
| **v25.x (2025)** | UXP (v5 manifest) | **Fully Supported** | Direct UXP DOM, `executeTransaction`, `Sequence.clone()`, `SequenceEditor` |
| **v24.x (2024)** | UXP (v5 manifest) | **Fully Supported (Primary Target)** | UXP DOM, `executeTransaction`, TrackItem manipulation, project import |
| **v23.5 - v23.6** | UXP (Early Release) | **Supported with Restrictions** | Basic UXP DOM; fallback ExtendScript bridge utilized for complex splitting |
| **v22.x & Older** | CEP / ExtendScript | **Unsupported** | Requires modern UXP runtime |

---

## 2. Documented Premiere DOM APIs Utilized

### Project & Sequence Management
- `app.project.activeSequence`: Returns the currently active sequence item.
- `Sequence.clone()`: Creates an identical duplicate sequence. Used for safe editing policy (`OriginalName_AI_Edited`).
- `Sequence.setPlayerPosition(ticks)`: Sets the current playhead position in ticks (`254016000000` ticks per second).
- `app.project.executeTransaction(callback, undoLabel)`: Executes all sequence modifications inside an atomic, single-step undo transaction.
- `app.project.importFiles([filePath], ...)`: Imports generated SRT captions or extracted audio mixdowns into the project root bin.

### Track & Item Manipulation
- `Sequence.videoTracks` & `Sequence.audioTracks`: Inspects track hierarchy, names, muted states, and locked states.
- `TrackItem.start` & `TrackItem.end`: Reads and sets clip timeline boundaries in ticks.
- `TrackItem.inPoint` & `TrackItem.outPoint`: Reads and sets source in/out offsets to preserve synchronization during splitting.
- `TrackItem.projectItem`: Inspects underlying media file paths for audio extraction.

---

## 3. Clip Splitting & Reconstruction Strategy

Premiere Pro's UXP DOM does not expose an arbitrary interactive razor tool method directly via scripting. To achieve split cuts without relying on fragile keyboard macros or undocumented QE calls:

1. **Left Segment:** The existing clip item is trimmed by setting its `end` to the cut start and its `outPoint` to `inPoint + (cutStart - clipStart)`.
2. **Right Segment:** A duplicate clip reference of the same `projectItem` is positioned at the cut end point, with its `inPoint` set to `inPoint + (cutEnd - clipStart)`.
3. **Ripple Deletion:** In Cut & Remove mode, all subsequent clips on selected tracks are shifted leftward by the removed silence duration.
4. **Transaction Wrapping:** All actions are executed inside `app.project.executeTransaction` ensuring atomic execution and instant rollback on error.
