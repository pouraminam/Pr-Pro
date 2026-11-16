/**
 * Timeline Cut Planning Engine.
 *
 * Translates approved silence intervals and sequence tracks into an atomic,
 * frame-aligned editing execution plan with multi-track synchronization.
 */

import { Timebase } from "./timebase.js";

export class CutPlanner {
  constructor(timebase = new Timebase(25.0)) {
    this.timebase = timebase;
  }

  /**
   * Generates a concrete timeline cut plan.
   *
   * @param {Array} silenceIntervals - Approved silence intervals
   * @param {Array} sequenceTracks - List of tracks and their clip items
   * @param {Object} options - { mode: 'cut_remove'|'cut_only'|'analyze_only', ripple: true, scope: 'sequence'|'selected' }
   * @returns {Object} Structured cut plan
   */
  createPlan(silenceIntervals, sequenceTracks, options = {}) {
    const mode = options.mode || "cut_remove";
    const ripple = options.ripple !== false;
    const scope = options.scope || "sequence";

    // 1. Filter enabled and non-protected silence intervals
    const approvedCuts = silenceIntervals
      .filter((s) => s && s.enabled && !s.protected && s.end > s.start)
      .map((s) => ({
        id: s.id,
        start: this.timebase.roundSecondsToFrame(Number(s.start)),
        end: this.timebase.roundSecondsToFrame(Number(s.end)),
      }))
      .filter((s) => s.end > s.start)
      .sort((a, b) => a.start - b.start);

    // Merge any overlapping or adjacent frame-aligned cuts
    const mergedCuts = [];
    for (const c of approvedCuts) {
      if (mergedCuts.length === 0) {
        mergedCuts.push({ ...c });
      } else {
        const prev = mergedCuts[mergedCuts.length - 1];
        if (c.start <= prev.end) {
          prev.end = Math.max(prev.end, c.end);
        } else {
          mergedCuts.push({ ...c });
        }
      }
    }

    // 2. Identify target tracks based on scope
    const targetTracks = sequenceTracks.filter((track) => {
      if (track.locked) return false; // Never touch locked tracks
      if (scope === "selected") return track.selected;
      return true;
    });

    // 3. Calculate clip edits for each target track
    const trackPlans = [];
    let totalRemovedDuration = 0;

    for (const track of targetTracks) {
      const trackEdits = this._planTrackEdits(track, mergedCuts, mode, ripple);
      trackPlans.push(trackEdits);
    }

    if (mergedCuts.length > 0 && mode === "cut_remove") {
      totalRemovedDuration = mergedCuts.reduce((acc, c) => acc + (c.end - c.start), 0);
    }

    return {
      mode,
      ripple,
      scope,
      fps: this.timebase.fps,
      approvedCutsCount: mergedCuts.length,
      cuts: mergedCuts,
      tracks: trackPlans,
      totalRemovedDuration: Math.round(totalRemovedDuration * 1000) / 1000,
    };
  }

  _planTrackEdits(track, cuts, mode, ripple) {
    const clips = track.clips || [];
    const plannedClips = [];

    let cumulativeShift = 0;

    for (const clip of clips) {
      const clipStart = this.timebase.roundSecondsToFrame(clip.start);
      const clipEnd = this.timebase.roundSecondsToFrame(clip.end);
      const clipIn = clip.inPoint || 0;

      // Find cuts that intersect this clip
      const intersectingCuts = cuts.filter(
        (c) => c.start < clipEnd && c.end > clipStart
      );

      if (intersectingCuts.length === 0) {
        // Clip does not intersect any silence cut
        const shiftedStart = ripple ? Math.max(0, clipStart - cumulativeShift) : clipStart;
        const shiftedEnd = ripple ? shiftedStart + (clipEnd - clipStart) : clipEnd;

        plannedClips.push({
          action: "keep",
          originalClip: clip,
          start: shiftedStart,
          end: shiftedEnd,
          inPoint: clipIn,
          outPoint: clipIn + (clipEnd - clipStart),
        });
        continue;
      }

      // Clip intersects one or more cuts
      if (mode === "cut_only") {
        // Mode 2: Create boundaries at cut start and end, keep all media on timeline
        const splitPoints = new Set();
        for (const c of intersectingCuts) {
          if (c.start > clipStart && c.start < clipEnd) splitPoints.add(c.start);
          if (c.end > clipStart && c.end < clipEnd) splitPoints.add(c.end);
        }

        const sortedPoints = [clipStart, ...Array.from(splitPoints).sort((a, b) => a - b), clipEnd];
        for (let i = 0; i < sortedPoints.length - 1; i++) {
          const segStart = sortedPoints[i];
          const segEnd = sortedPoints[i + 1];
          if (segEnd <= segStart) continue;

          const segIn = clipIn + (segStart - clipStart);
          const isSilent = intersectingCuts.some((c) => c.start <= segStart && c.end >= segEnd);

          plannedClips.push({
            action: isSilent ? "mark_silent" : "keep",
            originalClip: clip,
            start: segStart,
            end: segEnd,
            inPoint: segIn,
            outPoint: segIn + (segEnd - segStart),
            isSilent,
          });
        }
      } else if (mode === "cut_remove") {
        // Mode 3: Keep speech pieces, discard silence pieces
        let currentPos = clipStart;

        for (const c of intersectingCuts) {
          if (c.start > currentPos) {
            // Speech piece before this cut
            const speechDur = c.start - currentPos;
            const newStart = ripple ? Math.max(0, currentPos - cumulativeShift) : currentPos;
            const newEnd = newStart + speechDur;
            const pieceIn = clipIn + (currentPos - clipStart);

            plannedClips.push({
              action: "keep",
              originalClip: clip,
              start: newStart,
              end: newEnd,
              inPoint: pieceIn,
              outPoint: pieceIn + speechDur,
            });
          }

          // Discard the cut region
          const cutDurationInClip = Math.min(clipEnd, c.end) - Math.max(clipStart, c.start);
          if (ripple && cutDurationInClip > 0) {
            cumulativeShift += cutDurationInClip;
          }

          currentPos = Math.max(currentPos, c.end);
        }

        // Remaining piece after the last cut in this clip
        if (currentPos < clipEnd) {
          const remainingDur = clipEnd - currentPos;
          const newStart = ripple ? Math.max(0, currentPos - cumulativeShift) : currentPos;
          const newEnd = newStart + remainingDur;
          const pieceIn = clipIn + (currentPos - clipStart);

          plannedClips.push({
            action: "keep",
            originalClip: clip,
            start: newStart,
            end: newEnd,
            inPoint: pieceIn,
            outPoint: pieceIn + remainingDur,
          });
        }
      }
    }

    return {
      trackId: track.id,
      trackName: track.name,
      trackType: track.type, // "video" or "audio"
      plannedClips,
    };
  }
}
