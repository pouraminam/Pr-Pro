/**
 * Persian and Multilingual RTL Text Handling.
 * Handles Unicode shaping, right-to-left detection, and zero-width non-joiner (half-space).
 */

const PERSIAN_ARABIC_REGEX = /[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]/;

export function isRTL(text) {
  if (!text || typeof text !== "string") return false;
  return PERSIAN_ARABIC_REGEX.test(text);
}

export function wrapRTL(text) {
  if (!text) return "";
  if (isRTL(text)) {
    // Unicode Right-to-Left Embedding (U+202B) and Pop Directional Formatting (U+202C)
    return `\u202B${text}\u202C`;
  }
  return text;
}

export function normalizePersian(text) {
  if (!text) return "";
  let out = text;
  // Replace Arabic Yeh (ي) with Persian Yeh (ی)
  out = out.replace(/\u064A/g, "\u06CC");
  // Replace Arabic Kaf (ك) with Persian Kaf (ک)
  out = out.replace(/\u0643/g, "\u06A9");
  // Normalize Persian half-space (ZWNJ \u200C)
  out = out.replace(/\s+می\s+/g, " می\u200C");
  out = out.replace(/\s+نمی\s+/g, " نمی\u200C");
  return out;
}
