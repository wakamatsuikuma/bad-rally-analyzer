from __future__ import annotations

from audio.shot_counter import AudioPeak, assign_audio_peaks_to_rallies
from opencv.rally_detector import RallyInterval


def test_assign_audio_peaks_to_rallies() -> None:
    peaks = [
        AudioPeak(time_sec=0.5, peak_strength=0.8),
        AudioPeak(time_sec=1.5, peak_strength=0.9),
        AudioPeak(time_sec=4.0, peak_strength=0.7),
    ]
    rallies = [
        RallyInterval(rally_id=1, start_sec=1.0, end_sec=2.0),
        RallyInterval(rally_id=2, start_sec=3.0, end_sec=5.0),
    ]

    records = assign_audio_peaks_to_rallies(peaks, rallies)

    assert [record.assigned_rally_id for record in records] == [None, 1, 2]
