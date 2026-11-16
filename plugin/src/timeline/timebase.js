/**
 * Premiere Pro Exact Rational Timebase and Tick Conversions.
 *
 * Premiere Pro internal timebase: 254,016,000,000 ticks per second.
 * Supports standard video frame rates without floating-point accumulation errors:
 * - 23.976 fps (24000/1001)
 * - 24.0 fps
 * - 25.0 fps (PAL)
 * - 29.97 fps (30000/1001 NTSC)
 * - 30.0 fps
 * - 50.0 fps
 * - 59.94 fps (60000/1001)
 * - 60.0 fps
 */

export const TICKS_PER_SECOND = 254016000000n;

// Standard frame rate rational representations (numerator, denominator)
const FPS_RATIONALS = {
  "23.976": { num: 24000n, den: 1001n },
  "24":     { num: 24n,    den: 1n },
  "25":     { num: 25n,    den: 1n },
  "29.97":  { num: 30000n, den: 1001n },
  "30":     { num: 30n,    den: 1n },
  "50":     { num: 50n,    den: 1n },
  "59.94":  { num: 60000n, den: 1001n },
  "60":     { num: 60n,    den: 1n },
};

export class Timebase {
  constructor(fps = 25.0) {
    this.fps = Number(fps) || 25.0;
    this.fpsKey = this._findFpsKey(this.fps);
    this.rational = FPS_RATIONALS[this.fpsKey] || { num: BigInt(Math.round(this.fps * 1000)), den: 1000n };
    // ticks_per_frame = (TICKS_PER_SECOND * den) / num
    this.ticksPerFrame = (TICKS_PER_SECOND * this.rational.den) / this.rational.num;
  }

  _findFpsKey(fpsVal) {
    const rounded = Math.round(fpsVal * 1000) / 1000;
    if (Math.abs(rounded - 23.976) < 0.01) return "23.976";
    if (Math.abs(rounded - 24.0) < 0.01) return "24";
    if (Math.abs(rounded - 25.0) < 0.01) return "25";
    if (Math.abs(rounded - 29.97) < 0.01) return "29.97";
    if (Math.abs(rounded - 30.0) < 0.01) return "30";
    if (Math.abs(rounded - 50.0) < 0.01) return "50";
    if (Math.abs(rounded - 59.94) < 0.01) return "59.94";
    if (Math.abs(rounded - 60.0) < 0.01) return "60";
    return String(fpsVal);
  }

  secondsToTicks(seconds) {
    const s = Math.max(0, Number(seconds) || 0);
    // Convert to microseconds BigInt to avoid float overflow
    const microSec = BigInt(Math.round(s * 1000000));
    const ticks = (microSec * TICKS_PER_SECOND) / 1000000n;
    return this.alignTicksToFrame(ticks);
  }

  ticksToSeconds(ticks) {
    const t = typeof ticks === "bigint" ? ticks : BigInt(String(ticks));
    // microsec = (t * 1000000) / TICKS_PER_SECOND
    const microSec = (t * 1000000n) / TICKS_PER_SECOND;
    return Number(microSec) / 1000000.0;
  }

  alignTicksToFrame(ticks) {
    const t = typeof ticks === "bigint" ? ticks : BigInt(String(ticks));
    // Round to nearest frame boundary
    const halfFrame = this.ticksPerFrame / 2n;
    const frameNum = (t + halfFrame) / this.ticksPerFrame;
    return frameNum * this.ticksPerFrame;
  }

  roundSecondsToFrame(seconds) {
    const ticks = this.secondsToTicks(seconds);
    return this.ticksToSeconds(ticks);
  }

  frameToSeconds(frameNumber) {
    const f = BigInt(Math.max(0, Math.floor(frameNumber)));
    const ticks = f * this.ticksPerFrame;
    return this.ticksToSeconds(ticks);
  }
}
