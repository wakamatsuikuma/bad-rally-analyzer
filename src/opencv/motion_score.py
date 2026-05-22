from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from opencv.video_loader import Roi, VideoLoadError, VideoMetadata


def calculate_motion_scores(
    *,
    video_path: Path,
    metadata: VideoMetadata,
    frame_step: int,
    roi: Roi,
    smooth_window: int,
) -> pd.DataFrame:
    if frame_step <= 0:
        raise VideoLoadError("--frame-step must be greater than 0")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise VideoLoadError(f"Failed to open video: {video_path}")

    rows: list[dict[str, float | int]] = []
    previous_gray: np.ndarray | None = None

    try:
        for frame_idx in range(0, metadata.frame_count, frame_step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ok, frame = cap.read()
            if not ok:
                continue

            cropped = frame[roi.y1 : roi.y2, roi.x1 : roi.x2]
            gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)

            if previous_gray is None:
                raw_score = 0.0
            else:
                diff = cv2.absdiff(gray, previous_gray)
                raw_score = float(np.mean(diff))

            rows.append(
                {
                    "time_sec": round(frame_idx / metadata.fps, 6),
                    "frame_idx": frame_idx,
                    "motion_score_raw": raw_score,
                }
            )
            previous_gray = gray
    finally:
        cap.release()

    if not rows:
        raise VideoLoadError("No frames were read from the video")

    df = pd.DataFrame(rows)
    window = max(1, smooth_window)
    df["motion_score_smooth"] = (
        df["motion_score_raw"].rolling(window=window, center=True, min_periods=1).mean()
    )
    return df


def infer_motion_threshold(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0

    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    robust_std = 1.4826 * mad
    percentile_70 = float(np.percentile(values, 70))
    threshold = max(percentile_70, median + 1.5 * robust_std)

    if threshold <= 0:
        return 0.0
    return threshold
