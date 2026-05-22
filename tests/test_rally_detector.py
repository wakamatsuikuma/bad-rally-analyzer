from __future__ import annotations

import pandas as pd

from opencv.rally_detector import detect_rally_intervals


def test_detect_rally_intervals_merges_short_inactive_gap() -> None:
    motion_df = pd.DataFrame(
        {
            "time_sec": [0.0, 1.0, 2.0, 2.5, 3.0, 4.0, 8.0, 9.0],
            "is_active": [False, True, True, False, True, True, False, False],
        }
    )

    rallies = detect_rally_intervals(
        motion_df,
        min_rally_duration_sec=2.0,
        merge_gap_sec=1.0,
    )

    assert len(rallies) == 1
    assert rallies[0].start_sec == 1.0
    assert rallies[0].end_sec == 4.0


def test_detect_rally_intervals_discards_short_candidates() -> None:
    motion_df = pd.DataFrame(
        {
            "time_sec": [0.0, 1.0, 2.0],
            "is_active": [False, True, False],
        }
    )

    rallies = detect_rally_intervals(
        motion_df,
        min_rally_duration_sec=2.0,
        merge_gap_sec=1.0,
    )

    assert rallies == []
