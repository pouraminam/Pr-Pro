"""
Unit Tests for Timeline Time Mapping and Subtitle Retiming.
"""

import unittest
from engine.subtitles.remapper import TimelineTimeMapper


class TestTimeMapper(unittest.TestCase):

    def test_original_to_edited_time(self):
        # Two removed cuts:
        # Cut 1: 2.0s to 4.0s (2.0s removed)
        # Cut 2: 7.0s to 8.0s (1.0s removed)
        cuts = [
            {"start": 2.0, "end": 4.0},
            {"start": 7.0, "end": 8.0},
        ]
        mapper = TimelineTimeMapper(cuts)
        self.assertEqual(mapper.get_total_removed_duration(), 3.0)

        # Before cut 1
        t_edit, is_cut = mapper.original_to_edited_time(1.0)
        self.assertEqual(t_edit, 1.0)
        self.assertFalse(is_cut)

        # Inside cut 1
        t_edit, is_cut = mapper.original_to_edited_time(3.0)
        self.assertEqual(t_edit, 2.0)
        self.assertTrue(is_cut)

        # Between cut 1 and cut 2
        # Original 5.0 -> 5.0 - 2.0 = 3.0
        t_edit, is_cut = mapper.original_to_edited_time(5.0)
        self.assertEqual(t_edit, 3.0)
        self.assertFalse(is_cut)

        # After cut 2
        # Original 9.0 -> 9.0 - (2.0 + 1.0) = 6.0
        t_edit, is_cut = mapper.original_to_edited_time(9.0)
        self.assertEqual(t_edit, 6.0)
        self.assertFalse(is_cut)

    def test_edited_to_original_time_inverse(self):
        cuts = [
            {"start": 2.0, "end": 4.0},
            {"start": 7.0, "end": 8.0},
        ]
        mapper = TimelineTimeMapper(cuts)

        # Edited 1.0 -> Original 1.0
        self.assertEqual(mapper.edited_to_original_time(1.0), 1.0)
        # Edited 3.0 -> Original 5.0
        self.assertEqual(mapper.edited_to_original_time(3.0), 5.0)
        # Edited 6.0 -> Original 9.0
        self.assertEqual(mapper.edited_to_original_time(6.0), 9.0)

    def test_subtitle_remapping_eliminates_drift(self):
        cuts = [
            {"start": 2.0, "end": 4.0},  # 2.0s pause removed
        ]
        mapper = TimelineTimeMapper(cuts)

        subs = [
            {"id": 1, "start": 0.5, "end": 1.8, "text": "Before cut"},
            {"id": 2, "start": 2.2, "end": 3.8, "text": "Inside cut"},  # Should be dropped
            {"id": 3, "start": 4.5, "end": 6.0, "text": "After cut"},   # Should shift left by 2.0s
        ]

        remapped = mapper.remap_subtitles(subs)

        self.assertEqual(len(remapped), 2)
        # Subtitle 1 is unchanged
        self.assertEqual(remapped[0]["text"], "Before cut")
        self.assertEqual(remapped[0]["start"], 0.5)
        self.assertEqual(remapped[0]["end"], 1.8)

        # Subtitle 3 is shifted from [4.5, 6.0] to [2.5, 4.0]
        self.assertEqual(remapped[1]["text"], "After cut")
        self.assertEqual(remapped[1]["start"], 2.5)
        self.assertEqual(remapped[1]["end"], 4.0)


if __name__ == "__main__":
    unittest.main()
