/**
 * Node.js Unit Tests for Timeline CutPlanner, Timebase, and TimeMapper.
 */

import assert from "node:assert";
import { Timebase } from "../../plugin/src/timeline/timebase.js";
import { CutPlanner } from "../../plugin/src/timeline/cutPlanner.js";
import { TimelineTimeMapper } from "../../plugin/src/timeline/timeMapper.js";
import { CompatibilityChecker } from "../../plugin/src/premiere/compatibilityChecker.js";

console.log("Running Timeline CutPlanner & Timebase Unit Tests...");

// 1. Test Timebase
const tb25 = new Timebase(25.0);
assert.strictEqual(tb25.ticksPerFrame, 10160640000n, "25fps ticks per frame must be 10160640000n");
assert.strictEqual(tb25.roundSecondsToFrame(0.041), 0.04, "0.041s rounded to 25fps must be 0.04s");

const tb24 = new Timebase(24.0);
assert.strictEqual(tb24.ticksPerFrame, 10584000000n, "24fps ticks per frame must be 10584000000n");

// 2. Test CutPlanner
const planner = new CutPlanner(tb25);

const mockTracks = [
  {
    id: "track_v_0",
    name: "V1",
    type: "video",
    locked: false,
    selected: true,
    clips: [
      { id: "clip_v1", name: "Camera_A", start: 0.0, end: 10.0, inPoint: 0.0, outPoint: 10.0 },
    ],
  },
  {
    id: "track_a_0",
    name: "A1",
    type: "audio",
    locked: false,
    selected: true,
    clips: [
      { id: "clip_a1", name: "Dialogue", start: 0.0, end: 10.0, inPoint: 0.0, outPoint: 10.0 },
    ],
  },
];

const mockSilences = [
  { id: "sil_1", start: 2.0, end: 3.5, duration: 1.5, enabled: true, protected: false },
  { id: "sil_2", start: 6.0, end: 7.0, duration: 1.0, enabled: true, protected: false },
  { id: "sil_3", start: 8.0, end: 8.4, duration: 0.4, enabled: false, protected: true }, // disabled
];

// Test Mode: Cut and Remove with Ripple Delete
const planRemove = planner.createPlan(mockSilences, mockTracks, {
  mode: "cut_remove",
  ripple: true,
});

assert.strictEqual(planRemove.approvedCutsCount, 2, "Should approve 2 enabled cuts");
// In 25fps, 1.5s rounds to 38 frames (1.52s) + 1.0s (25 frames) = 2.52s frame-aligned
assert.strictEqual(planRemove.totalRemovedDuration, 2.52, "Total removed duration should be 2.52s frame-aligned");

const vTrackEdits = planRemove.tracks.find((t) => t.trackId === "track_v_0");
assert.ok(vTrackEdits, "Video track edits must exist");
assert.strictEqual(vTrackEdits.plannedClips.length, 3, "Splits 1 clip into 3 kept pieces");

// Verify piece 1: [0.0, 2.0]
assert.strictEqual(vTrackEdits.plannedClips[0].start, 0.0);
assert.strictEqual(vTrackEdits.plannedClips[0].end, 2.0);

// Verify piece 2: [2.0, 4.48] (was [3.52, 6.0], shifted left by 1.52s)
assert.strictEqual(vTrackEdits.plannedClips[1].start, 2.0);
assert.strictEqual(vTrackEdits.plannedClips[1].end, 4.48);
assert.strictEqual(vTrackEdits.plannedClips[1].inPoint, 3.52, "Source inPoint must be preserved at 3.52s");

// Verify piece 3: [4.48, 7.48] (was [7.0, 10.0], shifted left by 2.52s)
assert.strictEqual(vTrackEdits.plannedClips[2].start, 4.48);
assert.strictEqual(vTrackEdits.plannedClips[2].end, 7.48);
assert.strictEqual(vTrackEdits.plannedClips[2].inPoint, 7.0, "Source inPoint must be preserved at 7.0s");

// Test Mode: Cut Only
const planCutOnly = planner.createPlan(mockSilences, mockTracks, {
  mode: "cut_only",
});
const vTrackCutOnly = planCutOnly.tracks.find((t) => t.trackId === "track_v_0");
assert.strictEqual(vTrackCutOnly.plannedClips.length, 5, "Splits into 5 contiguous pieces including silent regions");

// 3. Test TimeMapper
const mapper = new TimelineTimeMapper(mockSilences);
assert.strictEqual(mapper.originalToEditedTime(1.0).editedTime, 1.0);
assert.strictEqual(mapper.originalToEditedTime(5.0).editedTime, 3.5); // 5.0 - 1.5
assert.strictEqual(mapper.originalToEditedTime(9.0).editedTime, 6.5); // 9.0 - 2.5

// 4. Test CompatibilityChecker
const checker = new CompatibilityChecker();
const goodCompat = checker.analyze({ videoTracks: mockTracks, audioTracks: [] });
assert.strictEqual(goodCompat.status, "fully_supported");

const lockedTracks = [
  { ...mockTracks[0], locked: true },
];
const restrictedCompat = checker.analyze({ videoTracks: lockedTracks, audioTracks: [] });
assert.strictEqual(restrictedCompat.status, "supported_with_restrictions");

console.log("All Timeline CutPlanner, Timebase & TimeMapper tests passed successfully!");
