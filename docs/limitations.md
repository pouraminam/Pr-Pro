# Known Limitations — Premiere AI Editor

This document outlines current architectural and technical boundaries of the plugin.

---

## 1. Complex Sequence Structures

### Nested Sequences
- Sequences containing nested sequence items cannot be cut at arbitrary points without risking source offset corruption inside the pre-composition.
- **Handling:** The Compatibility Analyzer flags nested sequences and switches the plugin to **Analysis-Only** mode to protect complex timeline structures.

### Multicam Clips
- Multicam tracks contain synchronized multi-angle camera mappings. Direct clip splitting on multicam items can desynchronize auxiliary camera angles if not cut across all camera sources simultaneously.
- **Handling:** Flagged as Analysis-Only unless all associated camera tracks are selected.

---

## 2. Speed Ramps and Variable Playback Speed
- Clips with non-linear time remapping (speed ramps) or reverse playback feature non-linear source-to-timeline tick mappings.
- **Handling:** Constant-speed clips (100% or fixed percentage) are fully supported. Variable speed-ramped clips are flagged with restrictions.

---

## 3. Hardware Constraints
- Speech inference with the `large-v3` Whisper model on CPU requires approximately 10 GB of available system memory. On low-memory machines (under 16 GB), running `large-v3` without an NVIDIA GPU can cause high memory pressure.
- **Recommendation:** Use the `base` or `small` model on CPU for optimal performance and rapid turnaround.
