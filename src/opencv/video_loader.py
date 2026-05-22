from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2


class VideoLoadError(RuntimeError):
    """Raised when the video cannot be read for frame-based analysis."""


@dataclass(frozen=True)
class VideoMetadata:
    path: Path
    fps: float
    frame_count: int
    width: int
    height: int

    @property
    def duration_sec(self) -> float:
        if self.fps <= 0:
            return 0.0
        return self.frame_count / self.fps


@dataclass(frozen=True)
class Roi:
    x1: int
    y1: int
    x2: int
    y2: int

    def to_list(self) -> list[int]:
        return [self.x1, self.y1, self.x2, self.y2]


def get_video_metadata(video_path: Path) -> VideoMetadata:
    if not video_path.exists():
        raise VideoLoadError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise VideoLoadError(f"Failed to open video: {video_path}")

        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    finally:
        cap.release()

    if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        raise VideoLoadError(f"Invalid video metadata: {video_path}")

    return VideoMetadata(
        path=video_path,
        fps=fps,
        frame_count=frame_count,
        width=width,
        height=height,
    )


def parse_roi(roi_text: str | None, frame_width: int, frame_height: int) -> Roi:
    if roi_text is None:
        return Roi(0, 0, frame_width, frame_height)

    parts = [part.strip() for part in roi_text.split(",")]
    if len(parts) != 4:
        raise VideoLoadError("--roi must be formatted as x1,y1,x2,y2")

    try:
        x1, y1, x2, y2 = [int(part) for part in parts]
    except ValueError as exc:
        raise VideoLoadError("--roi values must be integers") from exc

    x1 = max(0, min(frame_width, x1))
    x2 = max(0, min(frame_width, x2))
    y1 = max(0, min(frame_height, y1))
    y2 = max(0, min(frame_height, y2))

    if x2 <= x1 or y2 <= y1:
        raise VideoLoadError("--roi must define a non-empty area inside the frame")

    return Roi(x1, y1, x2, y2)
