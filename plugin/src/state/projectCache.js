/**
 * Project Data Cache and Persistence.
 *
 * Caches transcription results, silence intervals, and subtitle edits
 * per sequence to avoid redundant re-analysis.
 */

const CACHE_PREFIX = "premiere_ai_editor_cache_";

export const ProjectCache = {
  getCacheKey(sequenceName, duration) {
    return `${CACHE_PREFIX}${encodeURIComponent(sequenceName || "default")}_${Math.round(duration || 0)}`;
  },

  save(sequenceName, duration, data) {
    try {
      const key = this.getCacheKey(sequenceName, duration);
      const payload = {
        version: "1.0",
        savedAt: new Date().toISOString(),
        data,
      };
      if (typeof localStorage !== "undefined") {
        localStorage.setItem(key, JSON.stringify(payload));
      }
    } catch (e) {
      // Storage quota or unavailable
    }
  },

  load(sequenceName, duration) {
    try {
      const key = this.getCacheKey(sequenceName, duration);
      if (typeof localStorage !== "undefined") {
        const item = localStorage.getItem(key);
        if (item) {
          const parsed = JSON.parse(item);
          return parsed.data || null;
        }
      }
    } catch (e) {
      return null;
    }
    return null;
  },

  clearAll() {
    try {
      if (typeof localStorage !== "undefined") {
        const keys = Object.keys(localStorage).filter((k) => k.startsWith(CACHE_PREFIX));
        keys.forEach((k) => localStorage.removeItem(k));
      }
    } catch (e) {}
  },

  getCacheSizeEstimate() {
    try {
      if (typeof localStorage !== "undefined") {
        let bytes = 0;
        for (const k of Object.keys(localStorage)) {
          if (k.startsWith(CACHE_PREFIX)) {
            bytes += (localStorage.getItem(k) || "").length * 2;
          }
        }
        return bytes;
      }
    } catch (e) {}
    return 0;
  },
};
