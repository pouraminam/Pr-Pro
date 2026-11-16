# User Guide — Premiere AI Editor

Welcome to Premiere AI Editor, your local-first video editing assistant for Adobe Premiere Pro.

---

## 1. Quick Start Workflow (The 30-Second Edit)

For everyday YouTube, educational, or podcast editing, use the **Quick Edit** feature:

1. Open your project in Adobe Premiere Pro and activate your interview or dialogue sequence.
2. In the top menu, click **Window -> Extensions -> Premiere AI Editor**.
3. In the panel header, ensure **Helper Online** is indicated with a green dot.
4. On the **Analyze** tab, verify that your dialogue track is selected.
5. Click **⚡ Run Quick Edit**.
6. Premiere AI Editor will:
   - Extract and transcribe the audio locally using Faster-Whisper.
   - Detect pauses using balanced silence thresholds (500ms pause with 150ms padding).
   - Create a safe duplicate sequence named `YourSequence_AI_Edited`.
   - Remove the silence regions and ripple-delete to close gaps.
   - Generate aligned subtitles.
7. Your edited sequence appears immediately on your Premiere timeline ready for further fine-tuning.

---

## 2. Detailed Step-by-Step Workflow

### Step 1: Sequence & Dialogue Source Selection
On the **Analyze** tab:
- Click **Refresh** to inspect the currently active Premiere timeline.
- Select your primary dialogue track (e.g. `A1 - Boom Mic`). Unrelated background music or sound effects on separate tracks will not trigger false cut decisions.
- Select your Whisper model:
  - **Base (Recommended):** Best balance of speed and accuracy on ordinary laptops.
  - **Small:** Recommended for accented speech or mixed English/Persian dialogue.
  - **Large-v3:** Studio precision for complex recordings.
- Select Language: **Auto Detect**, **Persian (فارسی)**, or **English**.

### Step 2: Silence Detection Presets
Choose a preset matching your content style:
- **Conservative:** 750ms minimum pause, 200ms padding. Keeps natural conversational breath and pauses. Best for tutorials and lectures.
- **Balanced (Default):** 500ms minimum pause, 150ms padding. Removes dead air while keeping speech cadence smooth.
- **Aggressive:** 350ms minimum pause, 100ms padding. Tight edits for fast-paced YouTube and short-form videos.
- **Preserve Natural Breathing:** When checked, adds gentle safety margins before speech onsets and after consonants.

Click **Analyze Speech & Silence**.

---

### Step 3: Interactive Visual Silence Review
Once analysis completes, the panel switches to the **Silence** tab:
- **Audio Waveform:** Displays the audio profile.
  - **Neutral blue/gray:** Speech regions.
  - **Muted red:** Proposed cuts to be removed.
  - **Green outline:** Protected regions that will not be cut.
  - **Blue highlight:** Selected region.
- **Interactive Scrubber:** Click anywhere along the waveform to instantly move the Premiere Pro playhead to that exact timecode.
- **Summary Metrics:** View original sequence duration, number of proposed cuts, total silence duration, and estimated percentage of time saved.
- **Individual Cut Controls:** Toggle any silence region on or off, or click **Protect** to safeguard subtle pauses or quiet words.
- **Bulk Controls:** Select all, deselect all, keep only confirmed silence, or invert selections.

---

### Step 4: Safe Timeline Cutting
Choose your preferred editing mode:
- **Cut Only (Split):** Creates razor edit boundaries at silence borders but leaves all clips on the timeline for manual review.
- **Cut & Remove Silence:** Cuts out silence regions and ripples subsequent clips leftward to close gaps.
- **Safe Duplicate Sequence Checkbox:** Enabled by default. Your original sequence is never altered. Edits are executed on `OriginalName_AI_Edited`.

---

### Step 5: Transcript Editing
Click the **Transcript** tab:
- Full transcript text is organized by time-stamped segments.
- **Persian Text Rendering:** Renders right-to-left (RTL) with proper Persian shaping and zero-width non-joiner (`\u200c`) support.
- **Click to Seek:** Click any segment's timestamp to jump the Premiere playhead directly to that spoken phrase.
- **Edit Text:** Click directly into any text block to correct terminology or spelling.
- **Split & Merge:** Split a segment in two or merge adjacent segments.
- **Export:** Export clean transcripts to `.txt` or `.json`.

---

### Step 6: Bilingual Subtitles & Translation
Click the **Subtitles** tab:
- View structured subtitles with reading speed indicators and validation status.
- **Bilingual Translation:** Click **Translate** to translate Persian to English or English to Persian locally and offline.
- **Side-by-Side View:** Review original text alongside translated text.
- **Edited Sequence Alignment (Zero Drift):** Click **Edited Sequence** to preview subtitles mapped to the edited timeline. Silence gaps are automatically subtracted, ensuring subtitles remain perfectly synchronized with your cuts!
- **Add to Premiere:** Click **Add to Premiere** to export a standard `.srt` file and import it directly into your active Premiere project bin.
