"""
Timeline Time Mapper and Subtitle Remapping Engine.

Maps timestamps from the original unedited timeline to the edited timeline
after silence cuts and ripple deletion.
Ensures zero time drift for subtitles, captions, and edit markers.
"""

from typing import List, Dict, Any, Tuple, Optional


class TimelineTimeMapper:
    """Maintains mapping between original sequence time and edited sequence time."""

    def __init__(self, removed_intervals: List[Dict[str, float]]):
        # Normalize and sort removed intervals
        sorted_cuts = sorted(
            [{"start": float(c["start"]), "end": float(c["end"])} for c in removed_intervals if c["end"] > c["start"]],
            key=lambda x: x["start"],
        )

        # Merge overlapping removed intervals
        merged: List[Dict[str, float]] = []
        for c in sorted_cuts:
            if not merged:
                merged.append(dict(c))
            else:
                prev = merged[-1]
                if c["start"] <= prev["end"]:
                    prev["end"] = max(prev["end"], c["end"])
                else:
                    merged.append(dict(c))

        self.cuts = merged

    def get_total_removed_duration(self) -> float:
        return sum(c["end"] - c["start"] for c in self.cuts)

    def original_to_edited_time(self, t_orig: float) -> Tuple[float, bool]:
        """
        Maps original time to edited time.
        Returns (t_edited, is_inside_removed_region).
        """
        t = max(0.0, float(t_orig))
        cumulative_removed = 0.0

        for c in self.cuts:
            if t < c["start"]:
                break
            elif c["start"] <= t <= c["end"]:
                # Point falls inside a cut region
                return round(c["start"] - cumulative_removed, 3), True
            else:
                cumulative_removed += (c["end"] - c["start"])

        return round(max(0.0, t - cumulative_removed), 3), False

    def edited_to_original_time(self, t_edited: float) -> float:
        """Inverse mapping from edited time to original time."""
        t_edit = max(0.0, float(t_edited))
        cur_edit_accum = 0.0
        last_orig = 0.0

        for c in self.cuts:
            span_before = c["start"] - last_orig
            if cur_edit_accum + span_before >= t_edit:
                offset_in_span = t_edit - cur_edit_accum
                return round(last_orig + offset_in_span, 3)
            cur_edit_accum += span_before
            last_orig = c["end"]

        return round(last_orig + (t_edit - cur_edit_accum), 3)

    def remap_subtitles(
        self, subtitles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remaps subtitles to the edited timeline:
        - Drops subtitles completely inside deleted silence regions.
        - Trims subtitles overlapping deleted regions.
        - Splits subtitles cut in half by an edit boundary.
        - Shifts all subtitle timestamps to eliminate silence gaps.
        """
        if not self.cuts:
            return [dict(s) for s in subtitles]

        remapped: List[Dict[str, Any]] = []

        for sub in subtitles:
            s_start = float(sub["start"])
            s_end = float(sub["end"])
            text = sub.get("text", "")

            # Check overlaps with all cuts
            active_pieces = [{"start": s_start, "end": s_end, "text": text}]

            for c in self.cuts:
                c_start = c["start"]
                c_end = c["end"]
                new_pieces = []

                for piece in active_pieces:
                    p_start = piece["start"]
                    p_end = piece["end"]

                    # No overlap
                    if p_end <= c_start or p_start >= c_end:
                        new_pieces.append(piece)
                        continue

                    # Piece is completely inside the cut -> discard
                    if p_start >= c_start and p_end <= c_end:
                        continue

                    # Cut overlaps beginning of piece
                    if p_start < c_start and p_end <= c_end:
                        new_pieces.append({
                            "start": p_start,
                            "end": c_start,
                            "text": piece["text"],
                        })

                    # Cut overlaps end of piece
                    elif p_start >= c_start and p_end > c_end:
                        new_pieces.append({
                            "start": c_end,
                            "end": p_end,
                            "text": piece["text"],
                        })

                    # Cut is in the middle of piece -> split into two
                    elif p_start < c_start and p_end > c_end:
                        new_pieces.append({
                            "start": p_start,
                            "end": c_start,
                            "text": piece["text"],
                        })
                        new_pieces.append({
                            "start": c_end,
                            "end": p_end,
                            "text": piece["text"],
                        })

                active_pieces = new_pieces

            # Now map active piece boundaries to edited timeline
            for p in active_pieces:
                if p["end"] - p["start"] < 0.2:  # Ignore slivers under 200ms
                    continue

                mapped_start, _ = self.original_to_edited_time(p["start"])
                mapped_end, _ = self.original_to_edited_time(p["end"])

                if mapped_end > mapped_start:
                    item = dict(sub)
                    item["start"] = mapped_start
                    item["end"] = mapped_end
                    item["duration"] = round(mapped_end - mapped_start, 3)
                    item["text"] = p["text"]
                    item["original_start"] = s_start
                    item["original_end"] = s_end
                    remapped.append(item)

        # Re-index
        for idx, item in enumerate(remapped, start=1):
            item["id"] = idx

        return remapped
