/**
 * Timeline Time Mapper for Premiere Pro Plugin UI.
 *
 * Synchronously maps timestamps between original sequence and edited sequence
 * after silence removal and ripple deletes.
 */

export class TimelineTimeMapper {
  constructor(removedIntervals = []) {
    // Sort and merge overlapping cut intervals
    const valid = removedIntervals
      .filter((c) => c && c.end > c.start && (c.enabled !== false) && !c.protected)
      .map((c) => ({ start: Number(c.start), end: Number(c.end) }))
      .sort((a, b) => a.start - b.start);

    const merged = [];
    for (const c of valid) {
      if (merged.length === 0) {
        merged.push({ ...c });
      } else {
        const prev = merged[merged.length - 1];
        if (c.start <= prev.end) {
          prev.end = Math.max(prev.end, c.end);
        } else {
          merged.push({ ...c });
        }
      }
    }
    this.cuts = merged;
  }

  getTotalRemovedDuration() {
    return this.cuts.reduce((sum, c) => sum + (c.end - c.start), 0);
  }

  originalToEditedTime(tOrig) {
    const t = Math.max(0, Number(tOrig) || 0);
    let cumulativeRemoved = 0;

    for (const c of this.cuts) {
      if (t < c.start) {
        break;
      } else if (t >= c.start && t <= c.end) {
        return {
          editedTime: Math.round((c.start - cumulativeRemoved) * 1000) / 1000,
          isRemoved: true,
        };
      } else {
        cumulativeRemoved += (c.end - c.start);
      }
    }

    return {
      editedTime: Math.max(0, Math.round((t - cumulativeRemoved) * 1000) / 1000),
      isRemoved: false,
    };
  }

  editedToOriginalTime(tEdited) {
    const t = Math.max(0, Number(tEdited) || 0);
    let accum = 0;
    let lastOrig = 0;

    for (const c of this.cuts) {
      const span = c.start - lastOrig;
      if (accum + span >= t) {
        return Math.round((lastOrig + (t - accum)) * 1000) / 1000;
      }
      accum += span;
      lastOrig = c.end;
    }

    return Math.round((lastOrig + (t - accum)) * 1000) / 1000;
  }

  remapSubtitles(subtitles = []) {
    if (!this.cuts.length) return [...subtitles];

    const remapped = [];

    for (const sub of subtitles) {
      let pieces = [{ start: Number(sub.start), end: Number(sub.end), text: sub.text }];

      for (const c of this.cuts) {
        const nextPieces = [];
        for (const p of pieces) {
          if (p.end <= c.start || p.start >= c.end) {
            nextPieces.push(p);
            continue;
          }
          if (p.start >= c.start && p.end <= c.end) {
            continue; // Dropped completely
          }
          if (p.start < c.start && p.end <= c.end) {
            nextPieces.push({ start: p.start, end: c.start, text: p.text });
          } else if (p.start >= c.start && p.end > c.end) {
            nextPieces.push({ start: c.end, end: p.end, text: p.text });
          } else if (p.start < c.start && p.end > c.end) {
            nextPieces.push({ start: p.start, end: c.start, text: p.text });
            nextPieces.push({ start: c.end, end: p.end, text: p.text });
          }
        }
        pieces = nextPieces;
      }

      for (const p of pieces) {
        if (p.end - p.start < 0.2) continue; // Skip slivers under 200ms
        const mStart = this.originalToEditedTime(p.start).editedTime;
        const mEnd = this.originalToEditedTime(p.end).editedTime;

        if (mEnd > mStart) {
          remapped.push({
            ...sub,
            start: mStart,
            end: mEnd,
            duration: Math.round((mEnd - mStart) * 1000) / 1000,
            text: p.text,
          });
        }
      }
    }

    return remapped.map((s, idx) => ({ ...s, id: idx + 1 }));
  }
}
