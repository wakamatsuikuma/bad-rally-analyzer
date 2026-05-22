from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
from scipy.signal import find_peaks

from opencv.rally_detector import RallyInterval


@dataclass(frozen=True)
class AudioPeak:
    time_sec: float
    peak_strength: float


@dataclass(frozen=True)
class AssignedAudioPeak:
    time_sec: float
    peak_strength: float
    assigned_rally_id: int | None


def detect_audio_peaks(
    wav_path: Path,
    *,
    min_peak_distance_sec: float = 0.18,
) -> list[AudioPeak]:
    samples, sample_rate = sf.read(wav_path, always_2d=False)
    if samples.size == 0:
        return []

    if samples.ndim > 1:
        samples = np.mean(samples, axis=1)

    samples = samples.astype(np.float64)
    if np.max(np.abs(samples)) > 0:
        samples = samples / np.max(np.abs(samples))

    envelope, hop_length = _rms_envelope(samples, sample_rate)
    if envelope.size < 3:
        return []

    onset = np.diff(envelope, prepend=envelope[0])
    onset = np.maximum(onset, 0.0)
    onset = _moving_average(onset, window=3)

    threshold = _infer_audio_peak_threshold(onset)
    distance_frames = max(1, int(min_peak_distance_sec * sample_rate / hop_length))
    peak_indices, properties = find_peaks(onset, height=threshold, distance=distance_frames)
    strengths = properties.get("peak_heights", np.array([], dtype=np.float64))

    return [
        AudioPeak(
            time_sec=round(float(index * hop_length / sample_rate), 6),
            peak_strength=round(float(strength), 6),
        )
        for index, strength in zip(peak_indices, strengths, strict=True)
    ]


def assign_audio_peaks_to_rallies(
    peaks: list[AudioPeak],
    rally_intervals: list[RallyInterval],
) -> list[AssignedAudioPeak]:
    records: list[AssignedAudioPeak] = []
    for peak in peaks:
        assigned_rally_id = None
        for interval in rally_intervals:
            if interval.start_sec <= peak.time_sec <= interval.end_sec:
                assigned_rally_id = interval.rally_id
                break
        records.append(
            AssignedAudioPeak(
                time_sec=peak.time_sec,
                peak_strength=peak.peak_strength,
                assigned_rally_id=assigned_rally_id,
            )
        )
    return records


def records_to_dataframe(records: list[AssignedAudioPeak]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "time_sec": record.time_sec,
                "peak_strength": record.peak_strength,
                "assigned_rally_id": record.assigned_rally_id,
            }
            for record in records
        ],
        columns=["time_sec", "peak_strength", "assigned_rally_id"],
    )


def _rms_envelope(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, int]:
    frame_length = max(1, int(sample_rate * 0.02))
    hop_length = max(1, int(sample_rate * 0.01))
    values = []

    for start in range(0, max(1, len(samples) - frame_length + 1), hop_length):
        frame = samples[start : start + frame_length]
        if frame.size == 0:
            continue
        values.append(float(np.sqrt(np.mean(np.square(frame)))))

    return np.asarray(values, dtype=np.float64), hop_length


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1 or values.size == 0:
        return values
    kernel = np.ones(window, dtype=np.float64) / window
    return np.convolve(values, kernel, mode="same")


def _infer_audio_peak_threshold(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    robust_std = 1.4826 * mad
    percentile_90 = float(np.percentile(values, 90))
    return max(percentile_90, median + 3.0 * robust_std)
