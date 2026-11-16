/**
 * Sequence Compatibility Analyzer.
 *
 * Checks active sequence complexity prior to cutting.
 * Classifies sequences:
 * - "Fully supported"
 * - "Supported with restrictions"
 * - "Analysis-only"
 * - "Unsupported"
 */

export class CompatibilityChecker {
  analyze(sequenceData) {
    if (!sequenceData) {
      return {
        status: "unsupported",
        label: "No Sequence Loaded",
        canEdit: false,
        reasons: ["No active sequence found in the Premiere project."],
      };
    }

    const reasons = [];
    let isRestricted = false;
    let isAnalysisOnly = false;

    const allTracks = [...(sequenceData.videoTracks || []), ...(sequenceData.audioTracks || [])];
    const totalClips = allTracks.reduce((sum, t) => sum + (t.clips ? t.clips.length : 0), 0);

    if (totalClips === 0) {
      return {
        status: "unsupported",
        label: "Empty Sequence",
        canEdit: false,
        reasons: ["The active sequence contains no clips."],
      };
    }

    // Check for locked tracks
    const lockedTracks = allTracks.filter((t) => t.locked);
    if (lockedTracks.length > 0) {
      isRestricted = true;
      reasons.push(
        `${lockedTracks.length} locked track(s) detected (${lockedTracks.map((t) => t.name).join(", ")}). Locked tracks will be skipped during cutting.`
      );
    }

    // Check for nested sequences / multicam if flagged
    const hasMulticam = allTracks.some((t) =>
      t.clips.some((c) => c.name && (c.name.includes("Multicam") || c.name.includes("Nested")))
    );
    if (hasMulticam) {
      isAnalysisOnly = true;
      reasons.push("Multicam or nested sequence items detected. Recommended for Analysis-Only mode to avoid splitting nested media.");
    }

    if (isAnalysisOnly) {
      return {
        status: "analysis_only",
        label: "Analysis Only",
        canEdit: false,
        reasons,
      };
    }

    if (isRestricted) {
      return {
        status: "supported_with_restrictions",
        label: "Supported with Restrictions",
        canEdit: true,
        reasons,
      };
    }

    return {
      status: "fully_supported",
      label: "Fully Supported",
      canEdit: true,
      reasons: ["Sequence is standard multi-track audio/video. Ready for cutting."],
    };
  }
}
