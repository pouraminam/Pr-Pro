/**
 * Transcript Workspace and Editor View.
 *
 * Supports:
 * - Full transcript display with segment timestamps
 * - Persian RTL and English LTR rendering
 * - In-place text editing
 * - Search & replace
 * - Split and merge segments
 * - Click-to-seek playhead navigation
 * - Transcript export (TXT, JSON)
 */

import { store } from "../state/store.js";
import { bridge } from "../premiere/bridge.js";
import { isRTL, normalizePersian } from "../utilities/rtl.js";
import { secondsToTimecode } from "../utilities/formatters.js";

export class TranscriptView {
  constructor(containerElement) {
    this.container = containerElement;
    this.searchQuery = "";
  }

  render(state) {
    const segments = state.transcriptSegments || [];
    const filtered = this.searchQuery
      ? segments.filter((s) => s.text.toLowerCase().includes(this.searchQuery.toLowerCase()))
      : segments;

    this.container.innerHTML = `
      <div class="transcript-container">
        <!-- Search and Actions Toolbar -->
        <div class="transcript-toolbar">
          <input type="text" class="form-control search-box" id="transcript-search" placeholder="Search transcript..." value="${this.searchQuery}">
          <button class="btn btn-secondary btn-sm" id="btn-copy-transcript" title="Copy transcript to clipboard">Copy</button>
          <button class="btn btn-secondary btn-sm" id="btn-export-txt" title="Export as plain text">TXT</button>
          <button class="btn btn-secondary btn-sm" id="btn-export-json" title="Export as JSON">JSON</button>
        </div>

        <!-- Segments List -->
        <div class="transcript-list" id="transcript-segments-container">
          ${filtered.length === 0 ? '<div style="padding: 12px; text-align: center; color: var(--text-muted);">No transcript available. Run Analyze to transcribe.</div>' : ''}
          ${filtered.map((seg, idx) => this._renderSegmentCard(seg, idx, segments.length)).join("")}
        </div>
      </div>
    `;

    this._bindEvents(segments);
  }

  _renderSegmentCard(seg, index, totalCount) {
    const isPersian = isRTL(seg.text);
    const dirClass = isPersian ? "rtl-text" : "ltr-text";
    const timeStr = `${secondsToTimecode(seg.start)} - ${secondsToTimecode(seg.end)}`;

    return `
      <div class="transcript-segment" data-id="${seg.id}" data-start="${seg.start}">
        <div class="segment-header">
          <span class="segment-timestamp" title="Click to jump timeline">${timeStr}</span>
          <div class="segment-actions">
            <button class="btn btn-secondary btn-sm btn-split-seg" data-id="${seg.id}" title="Split segment at cursor">Split</button>
            ${index < totalCount - 1 ? `<button class="btn btn-secondary btn-sm btn-merge-seg" data-id="${seg.id}" title="Merge with next">Merge</button>` : ''}
          </div>
        </div>
        <div class="segment-text ${dirClass}" contenteditable="true" data-id="${seg.id}" spellcheck="false">
          ${seg.text}
        </div>
      </div>
    `;
  }

  _bindEvents(segments) {
    // Search input
    const searchInput = this.container.querySelector("#transcript-search");
    searchInput?.addEventListener("input", (e) => {
      this.searchQuery = e.target.value;
      this.render(store.getState());
      // Re-focus search
      const input = this.container.querySelector("#transcript-search");
      if (input) {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
      }
    });

    // Jump to timeline on timestamp click
    this.container.querySelectorAll(".segment-timestamp").forEach((el) => {
      el.addEventListener("click", (e) => {
        const segCard = e.target.closest(".transcript-segment");
        const startSec = Number(segCard.dataset.start) || 0;
        bridge.setPlayheadPosition(Math.round(startSec * 254016000000));
      });
    });

    // In-place text edit blur
    this.container.querySelectorAll(".segment-text").forEach((el) => {
      el.addEventListener("blur", (e) => {
        const id = Number(e.target.dataset.id);
        const newText = normalizePersian(e.target.innerText.trim());
        const updated = segments.map((s) => (s.id === id ? { ...s, text: newText } : s));
        store.setState({ transcriptSegments: updated });
      });
    });

    // Split segment
    this.container.querySelectorAll(".btn-split-seg").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const id = Number(e.target.dataset.id);
        this._splitSegment(id, segments);
      });
    });

    // Merge segment
    this.container.querySelectorAll(".btn-merge-seg").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const id = Number(e.target.dataset.id);
        this._mergeWithNext(id, segments);
      });
    });

    // Copy to clipboard
    this.container.querySelector("#btn-copy-transcript")?.addEventListener("click", () => {
      const fullText = segments.map((s) => s.text).join("\n");
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        navigator.clipboard.writeText(fullText);
      }
    });

    // Export TXT / JSON
    this.container.querySelector("#btn-export-txt")?.addEventListener("click", () => {
      const text = segments.map((s) => s.text).join("\n");
      this._downloadFile(text, "transcript.txt", "text/plain;charset=utf-8");
    });

    this.container.querySelector("#btn-export-json")?.addEventListener("click", () => {
      const jsonStr = JSON.stringify(segments, null, 2);
      this._downloadFile(jsonStr, "transcript.json", "application/json;charset=utf-8");
    });
  }

  _splitSegment(id, segments) {
    const idx = segments.findIndex((s) => s.id === id);
    if (idx === -1) return;

    const target = segments[idx];
    const midTime = (target.start + target.end) / 2;
    const words = target.text.split(" ");
    const midWord = Math.floor(words.length / 2);

    const part1 = {
      ...target,
      end: Math.round(midTime * 1000) / 1000,
      text: words.slice(0, midWord).join(" ") || target.text,
    };

    const part2 = {
      id: Math.max(...segments.map((s) => s.id), 0) + 1,
      start: Math.round(midTime * 1000) / 1000,
      end: target.end,
      text: words.slice(midWord).join(" ") || "[continued]",
      words: [],
    };

    const updated = [...segments.slice(0, idx), part1, part2, ...segments.slice(idx + 1)];
    store.setState({ transcriptSegments: updated });
  }

  _mergeWithNext(id, segments) {
    const idx = segments.findIndex((s) => s.id === id);
    if (idx === -1 || idx >= segments.length - 1) return;

    const cur = segments[idx];
    const next = segments[idx + 1];

    const merged = {
      ...cur,
      end: next.end,
      text: `${cur.text} ${next.text}`.trim(),
      words: [...(cur.words || []), ...(next.words || [])],
    };

    const updated = [...segments.slice(0, idx), merged, ...segments.slice(idx + 2)];
    store.setState({ transcriptSegments: updated });
  }

  _downloadFile(content, fileName, mimeType) {
    if (typeof document === "undefined") return;
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  }
}
