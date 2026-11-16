/**
 * Sequence Inspector for Adobe Premiere Pro.
 *
 * Inspects sequence properties, video/audio tracks, clip items,
 * source media file paths, track locks, and muted tracks.
 */

import { bridge } from "./bridge.js";
import { Timebase } from "../timeline/timebase.js";
import { Logger } from "../utilities/logger.js";

export class SequenceInspector {
  constructor(premiereBridge = bridge) {
    this.bridge = premiereBridge;
  }

  async inspectActiveSequence() {
    const seq = this.bridge.getActiveSequence();

    if (!seq) {
      Logger.warn("No active sequence found in Premiere project.");
      return null;
    }

    try {
      const name = seq.name || "Untitled Sequence";
      const id = seq.id || "seq_default";
      const timebaseVal = seq.timebase ? Number(seq.timebase) : 25.0;
      const fps = this._estimateFps(timebaseVal);
      const timebase = new Timebase(fps);

      // Inspect Video Tracks
      const videoTracks = [];
      if (seq.videoTracks) {
        const vCount = seq.videoTracks.numTracks || seq.videoTracks.length || 0;
        for (let i = 0; i < vCount; i++) {
          const track = seq.videoTracks[i];
          if (!track) continue;
          videoTracks.push(this._parseTrack(track, "video", i, timebase));
        }
      }

      // Inspect Audio Tracks
      const audioTracks = [];
      if (seq.audioTracks) {
        const aCount = seq.audioTracks.numTracks || seq.audioTracks.length || 0;
        for (let i = 0; i < aCount; i++) {
          const track = seq.audioTracks[i];
          if (!track) continue;
          audioTracks.push(this._parseTrack(track, "audio", i, timebase));
        }
      }

      // Determine primary audio source media path
      let primaryMediaPath = null;
      for (const t of audioTracks) {
        for (const c of t.clips) {
          if (c.mediaFilePath) {
            primaryMediaPath = c.mediaFilePath;
            break;
          }
        }
        if (primaryMediaPath) break;
      }

      // Calculate total duration
      let maxDuration = 0;
      [...videoTracks, ...audioTracks].forEach((t) => {
        t.clips.forEach((c) => {
          if (c.end > maxDuration) maxDuration = c.end;
        });
      });

      return {
        id,
        name,
        fps,
        duration: Math.round(maxDuration * 1000) / 1000,
        primaryMediaPath,
        videoTracks,
        audioTracks,
      };
    } catch (e) {
      Logger.error("Error inspecting active sequence", e);
      return null;
    }
  }

  _parseTrack(track, type, index, timebase) {
    const name = track.name || `${type === "video" ? "V" : "A"}${index + 1}`;
    const locked = Boolean(track.isLocked || track.locked);
    const muted = Boolean(track.isMuted || track.muted);
    const selected = Boolean(track.isSelected || track.selected || index === 0);

    const clips = [];
    const items = track.trackItems || track.clips || [];
    const count = items.numItems || items.length || 0;

    for (let j = 0; j < count; j++) {
      const item = items[j];
      if (!item) continue;

      const cStartTicks = item.start ? BigInt(String(item.start.ticks || item.start)) : 0n;
      const cEndTicks = item.end ? BigInt(String(item.end.ticks || item.end)) : 0n;
      const cInTicks = item.inPoint ? BigInt(String(item.inPoint.ticks || item.inPoint)) : 0n;
      const cOutTicks = item.outPoint ? BigInt(String(item.outPoint.ticks || item.outPoint)) : 0n;

      const cStartSec = timebase.ticksToSeconds(cStartTicks);
      const cEndSec = timebase.ticksToSeconds(cEndTicks);
      const cInSec = timebase.ticksToSeconds(cInTicks);
      const cOutSec = timebase.ticksToSeconds(cOutTicks);

      let mediaPath = null;
      if (item.projectItem && item.projectItem.getMediaPath) {
        mediaPath = item.projectItem.getMediaPath();
      } else if (item.mediaFilePath) {
        mediaPath = item.mediaFilePath;
      }

      clips.push({
        id: item.id || `clip_${index}_${j}`,
        name: item.name || `Clip ${j + 1}`,
        start: cStartSec,
        end: cEndSec,
        duration: Math.max(0, cEndSec - cStartSec),
        inPoint: cInSec,
        outPoint: cOutSec,
        mediaFilePath: mediaPath,
        selected: Boolean(item.selected),
        rawItem: item,
      });
    }

    return {
      id: `track_${type}_${index}`,
      index,
      name,
      type,
      locked,
      muted,
      selected,
      clips,
    };
  }

  _estimateFps(timebaseVal) {
    if (timebaseVal >= 250000000000n || timebaseVal > 1000) {
      // Premiere ticks per second representation
      return 25.0;
    }
    return Number(timebaseVal) || 25.0;
  }
}
