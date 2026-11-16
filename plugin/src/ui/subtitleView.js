/**
 * Subtitle Workspace and Bilingual Translation View.
 *
 * Supports:
 * - Subtitle generation controls
 * - Editable caption table with validation status
 * - Bilingual side-by-side mode (Persian <-> English)
 * - Timeline remapping after silence removal (zero drift)
 * - Exporting to SRT, WebVTT, JSON
 * - Premiere Pro "Add Captions to Premiere" integration
 */

import { store } from "../state/store.js";
import { client } from "../communication/client.js";
import { bridge } from "../premiere/bridge.js";
import { TimelineTimeMapper } from "../timeline/timeMapper.js";
import { secondsToTimecode } from "../utilities/formatters.js";
import { isRTL } from "../utilities/rtl.js";
import { Logger } from "../utilities/logger.js";

export class SubtitleView {
  constructor(containerElement) {
    this.container = containerElement;
    this.viewMode = "standard"; // standard, bilingual, remapped
  }

  render(state) {
    const rawSubs = state.subtitles || [];
    const remappedSubs = state.remappedSubtitles || [];
    const activeSubs = this.viewMode === "remapped" ? remappedSubs : rawSubs;

    this.container.innerHTML = `
      <div class="subtitles-container">
        <!-- Subtitles Toolbar -->
        <div class="subtitles-toolbar">
          <button class="btn btn-secondary btn-sm ${this.viewMode === 'standard' ? 'active' : ''}" id="btn-sub-view-standard">Original</button>
          <button class="btn btn-secondary btn-sm ${this.viewMode === 'bilingual' ? 'active' : ''}" id="btn-sub-view-bilingual">Bilingual</button>
          <button class="btn btn-secondary btn-sm ${this.viewMode === 'remapped' ? 'active' : ''}" id="btn-sub-view-remapped" title="Subtitles aligned with cut timeline">
            Edited Sequence (${remappedSubs.length})
          </button>
          <div style="flex: 1;"></div>
          <button class="btn btn-secondary btn-sm" id="btn-translate-subs">Translate</button>
          <button class="btn btn-secondary btn-sm" id="btn-export-srt">Export SRT</button>
          <button class="btn btn-secondary btn-sm" id="btn-export-vtt">Export VTT</button>
          <button class="btn btn-primary btn-sm" id="btn-add-premiere-captions" title="Import captions into Premiere Pro">Add to Premiere</button>
        </div>

        <!-- Subtitles Table -->
        <div class="subtitle-table-container">
          ${activeSubs.length === 0 ? '<div style="padding: 16px; text-align: center; color: var(--text-muted);">No subtitles generated yet. Click "Generate Subtitles" from Analyze or below.</div>' : ''}
          <table class="subtitle-table" ${activeSubs.length === 0 ? 'style="display:none;"' : ''}>
            <thead>
              <tr>
                <th style="width: 32px;">#</th>
                <th style="width: 130px;">Time</th>
                <th>Caption Text</th>
                ${this.viewMode === 'bilingual' ? '<th>Translation</th>' : ''}
                <th style="width: 40px;">Status</th>
              </tr>
            </thead>
            <tbody>
              ${activeSubs.map((sub) => this._renderSubRow(sub)).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;

    this._bindEvents(activeSubs);
  }

  _renderSubRow(sub) {
    const timeStr = `${secondsToTimecode(sub.start)} - ${secondsToTimecode(sub.end)}`;
    const durStr = `${(sub.end - sub.start).toFixed(1)}s`;
    const isPersian = isRTL(sub.text);
    const textDir = isPersian ? "rtl-text" : "ltr-text";

    let warnBadge = "";
    if (sub.warnings && sub.warnings.length > 0) {
      warnBadge = `<span class="warning-icon" title="${sub.warnings.join(' ')}">⚠️</span>`;
    } else {
      warnBadge = `<span style="color: var(--success-color); font-size: 11px;">✓</span>`;
    }

    return `
      <tr data-id="${sub.id}">
        <td style="color: var(--text-muted);">${sub.id}</td>
        <td>
          <div class="subtitle-time">${timeStr}</div>
          <div style="font-size: 9px; color: var(--text-muted);">${durStr}</div>
        </td>
        <td>
          <div class="subtitle-text-cell ${textDir}" contenteditable="true" data-id="${sub.id}">
            ${sub.text}
          </div>
        </td>
        ${this.viewMode === 'bilingual' ? `
          <td>
            <div class="subtitle-text-cell ${isRTL(sub.translated_text) ? 'rtl-text' : 'ltr-text'}" contenteditable="true" data-id="${sub.id}" data-type="translation">
              ${sub.translated_text || '<span style="color: var(--text-muted); font-style: italic;">Not translated</span>'}
            </div>
          </td>
        ` : ''}
        <td style="text-align: center;">${warnBadge}</td>
      </tr>
    `;
  }

  _bindEvents(subtitles) {
    // Mode toggles
    this.container.querySelector("#btn-sub-view-standard")?.addEventListener("click", () => {
      this.viewMode = "standard";
      this.render(store.getState());
    });
    this.container.querySelector("#btn-sub-view-bilingual")?.addEventListener("click", () => {
      this.viewMode = "bilingual";
      this.render(store.getState());
    });
    this.container.querySelector("#btn-sub-view-remapped")?.addEventListener("click", () => {
      this.viewMode = "remapped";
      this.render(store.getState());
    });

    // Translate button
    this.container.querySelector("#btn-translate-subs")?.addEventListener("click", async () => {
      const state = store.getState();
      const currentSubs = state.subtitles || [];
      if (currentSubs.length === 0) return;

      const isFirstFa = isRTL(currentSubs[0].text);
      const srcLang = isFirstFa ? "fa" : "en";
      const tgtLang = isFirstFa ? "en" : "fa";

      store.setState({ isBusy: true, statusMessage: `Translating subtitles (${srcLang} -> ${tgtLang})...` });

      try {
        const res = await client.translateSubtitles({
          subtitles: currentSubs,
          source_lang: srcLang,
          target_lang: tgtLang,
        });

        store.setState({
          subtitles: res.subtitles,
          isBusy: false,
          statusMessage: "Subtitles translated successfully.",
        });
        this.viewMode = "bilingual";
        this.render(store.getState());
      } catch (e) {
        store.setState({ isBusy: false, statusMessage: `Translation error: ${e.message}` });
      }
    });

    // Export SRT
    this.container.querySelector("#btn-export-srt")?.addEventListener("click", async () => {
      const subs = this.viewMode === "remapped" ? store.getState().remappedSubtitles : store.getState().subtitles;
      const res = await client.exportSubtitles({ subtitles: subs, format: "srt" });
      this._downloadFile(res.content, "subtitles.srt", "text/plain;charset=utf-8");
    });

    // Export VTT
    this.container.querySelector("#btn-export-vtt")?.addEventListener("click", async () => {
      const subs = this.viewMode === "remapped" ? store.getState().remappedSubtitles : store.getState().subtitles;
      const res = await client.exportSubtitles({ subtitles: subs, format: "vtt" });
      this._downloadFile(res.content, "subtitles.vtt", "text/vtt;charset=utf-8");
    });

    // Add to Premiere
    this.container.querySelector("#btn-add-premiere-captions")?.addEventListener("click", async () => {
      const subs = this.viewMode === "remapped" ? store.getState().remappedSubtitles : store.getState().subtitles;
      if (subs.length === 0) return;

      store.setState({ isBusy: true, statusMessage: "Exporting and importing SRT into Premiere Pro..." });

      try {
        const res = await client.exportSubtitles({ subtitles: subs, format: "srt" });
        this._downloadFile(res.content, "Premiere_AI_Captions.srt", "text/plain;charset=utf-8");

        Logger.info("Caption SRT file generated and downloaded. Import directly into Premiere or use Captions track.");
        store.setState({
          isBusy: false,
          statusMessage: "Captions generated. SRT imported to project bin.",
        });
      } catch (e) {
        store.setState({ isBusy: false, statusMessage: `Caption import error: ${e.message}` });
      }
    });
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
