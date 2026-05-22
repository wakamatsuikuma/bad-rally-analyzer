from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RallyInterval:
    rally_id: int
    start_sec: float
    end_sec: float

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)


def detect_rally_intervals(
    motion_df: pd.DataFrame,
    *,
    min_rally_duration_sec: float,
    merge_gap_sec: float,
) -> list[RallyInterval]:
    active_intervals = _active_runs_to_intervals(motion_df)
    merged = _merge_close_intervals(active_intervals, merge_gap_sec=merge_gap_sec)
    filtered = [
        interval
        for interval in merged
        if interval[1] - interval[0] >= min_rally_duration_sec
    ]

    return [
        RallyInterval(rally_id=index + 1, start_sec=start, end_sec=end)
        for index, (start, end) in enumerate(filtered)
    ]


def _active_runs_to_intervals(motion_df: pd.DataFrame) -> list[tuple[float, float]]:
    intervals: list[tuple[float, float]] = []
    start_sec: float | None = None
    previous_time: float | None = None

    for row in motion_df.itertuples(index=False):
        time_sec = float(row.time_sec)
        is_active = bool(row.is_active)

        if is_active and start_sec is None:
            start_sec = time_sec
        elif not is_active and start_sec is not None:
            end_sec = previous_time if previous_time is not None else time_sec
            intervals.append((start_sec, end_sec))
            start_sec = None

        previous_time = time_sec

    if start_sec is not None and previous_time is not None:
        intervals.append((start_sec, previous_time))

    return intervals


def _merge_close_intervals(
    intervals: list[tuple[float, float]],
    *,
    merge_gap_sec: float,
) -> list[tuple[float, float]]:
    if not intervals:
        return []

    merged = [intervals[0]]
    for start, end in intervals[1:]:
        previous_start, previous_end = merged[-1]
        if start - previous_end <= merge_gap_sec:
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))

    return merged
