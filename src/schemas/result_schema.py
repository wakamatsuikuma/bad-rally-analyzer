from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RallyCandidate(BaseModel):
    rally_id: int
    start_sec: float
    end_sec: float
    duration_sec: float
    estimated_shots_audio: int = Field(ge=0)
    audio_peak_times_sec: list[float]
    confidence: Literal["low", "medium", "high"]
    note: str


class AnalysisConfig(BaseModel):
    fps: float
    frame_count: int
    duration_sec: float
    frame_step: int
    roi: list[int]
    motion_threshold: float
    min_rally_duration_sec: float
    merge_gap_sec: float
    audio_enabled: bool
    audio_note: str


class AnalysisResult(BaseModel):
    video_path: str
    rally_count: int
    rallies: list[RallyCandidate]
    analysis_config: AnalysisConfig
