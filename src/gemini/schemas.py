from __future__ import annotations

from pydantic import BaseModel, Field


class RallyAnalysis(BaseModel):
    rally_index: int = Field(description="1-based rally index within the video.")
    start_time_sec: float = Field(description="Estimated rally start timestamp in seconds.")
    end_time_sec: float = Field(description="Estimated rally end timestamp in seconds.")
    shot_count: int = Field(description="Estimated number of shots in the rally.")
    confidence: float = Field(description="Model confidence from 0.0 to 1.0.")
    notes: str = Field(description="Short explanation or caveat for this rally estimate.")


class VideoAnalysisResult(BaseModel):
    video_summary: str = Field(description="Short summary of the badminton clip.")
    total_rallies: int = Field(description="Number of rallies detected in the whole video.")
    average_shots_per_rally: float = Field(
        description="Average shot count across detected rallies in the whole video."
    )
    rallies: list[RallyAnalysis] = Field(description="Per-rally analysis results.")
    overall_confidence: float = Field(description="Overall confidence from 0.0 to 1.0.")
    limitations: list[str] = Field(description="Known limitations or ambiguities in this analysis.")
