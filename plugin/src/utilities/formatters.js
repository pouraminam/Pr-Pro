/**
 * Formatting and Timecode Utilities.
 */

export function secondsToTimecode(seconds, fps = 25.0) {
  const sec = Math.max(0, Number(seconds) || 0);
  const hrs = Math.floor(sec / 3600);
  const rem = sec % 3600;
  const mins = Math.floor(rem / 60);
  const secs = Math.floor(rem % 60);
  const frames = Math.floor((rem % 1) * fps);

  return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}:${String(frames).padStart(2, "0")}`;
}

export function secondsToMsString(seconds) {
  const sec = Math.max(0, Number(seconds) || 0);
  const mins = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  const ms = Math.floor((sec % 1) * 1000);
  return `${mins}:${String(s).padStart(2, "0")}.${String(ms).padStart(3, "0")}`;
}

export function formatDuration(seconds) {
  const s = Number(seconds) || 0;
  if (s < 60) {
    return `${s.toFixed(1)}s`;
  }
  const mins = Math.floor(s / 60);
  const remSec = (s % 60).toFixed(0);
  return `${mins}m ${remSec}s`;
}

export function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "0 MB";
  const mb = bytes / (1024 * 1024);
  return mb > 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(0)} MB`;
}
