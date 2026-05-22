from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import pandas as pd

from audio.audio_extractor import extract_audio_to_wav
from audio.shot_counter import (
    assign_audio_peaks_to_rallies,
    detect_audio_peaks,
    records_to_dataframe,
)
from opencv.motion_score import calculate_motion_scores, infer_motion_threshold
from opencv.plot import plot_motion_scores
from opencv.rally_detector import RallyInterval, detect_rally_intervals
from opencv.video_loader import Roi, VideoLoadError, VideoMetadata, get_video_metadata, parse_roi
from schemas.result_schema import AnalysisConfig, AnalysisResult, RallyCandidate


DEFAULT_OUTPUT_DIR = Path("outputs")
DEFAULT_FRAME_STEP = 5
DEFAULT_MIN_RALLY_DURATION_SEC = 2.0
DEFAULT_MERGE_GAP_SEC = 1.0
DEFAULT_SMOOTH_WINDOW = 5


@dataclass(frozen=True)
class AnalysisOutputPaths:
    output_dir: Path
    motion_csv_path: Path
    motion_png_path: Path
    rally_json_path: Path
    audio_csv_path: Path


@dataclass(frozen=True)
class PipelineRunResult:
    result: AnalysisResult
    paths: AnalysisOutputPaths
    motion_df: pd.DataFrame
    audio_peaks_df: pd.DataFrame


def run_opencv_audio_analysis(
    *,
    video_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    frame_step: int = DEFAULT_FRAME_STEP,
    roi_text: str | None = None,
    motion_threshold: float | None = None,
    min_rally_duration: float = DEFAULT_MIN_RALLY_DURATION_SEC,
    merge_gap: float = DEFAULT_MERGE_GAP_SEC,
    audio_enabled: bool = True,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
) -> PipelineRunResult:
    output_dir.mkdir(parents=True, exist_ok=True)

    motion_video_path, metadata = _get_motion_video(video_path, output_dir)
    roi = parse_roi(roi_text, metadata.width, metadata.height)
    motion_df = calculate_motion_scores(
        video_path=motion_video_path,
        metadata=metadata,
        frame_step=frame_step,
        roi=roi,
        smooth_window=smooth_window,
    )

    resolved_motion_threshold = motion_threshold
    if resolved_motion_threshold is None:
        resolved_motion_threshold = infer_motion_threshold(motion_df["motion_score_smooth"].to_numpy())

    motion_df["is_active"] = motion_df["motion_score_smooth"] > resolved_motion_threshold
    rally_intervals = detect_rally_intervals(
        motion_df,
        min_rally_duration_sec=min_rally_duration,
        merge_gap_sec=merge_gap,
    )

    audio_records_df = pd.DataFrame(columns=["time_sec", "peak_strength", "assigned_rally_id"])
    audio_note = "Audio peak detection was disabled."
    audio_success = False

    if audio_enabled:
        extraction = extract_audio_to_wav(video_path, output_dir)
        audio_note = extraction.note
        if extraction.wav_path is not None:
            peaks = detect_audio_peaks(extraction.wav_path)
            assigned_records = assign_audio_peaks_to_rallies(peaks, rally_intervals)
            audio_records_df = records_to_dataframe(assigned_records)
            audio_success = True

    paths = AnalysisOutputPaths(
        output_dir=output_dir,
        motion_csv_path=output_dir / "motion_score.csv",
        motion_png_path=output_dir / "motion_score.png",
        rally_json_path=output_dir / "rally_candidates.json",
        audio_csv_path=output_dir / "audio_peaks.csv",
    )

    motion_df.to_csv(paths.motion_csv_path, index=False)
    plot_motion_scores(
        motion_df=motion_df,
        rally_intervals=rally_intervals,
        threshold=resolved_motion_threshold,
        output_path=paths.motion_png_path,
    )
    audio_records_df.to_csv(paths.audio_csv_path, index=False)

    result = build_analysis_result(
        video_path=video_path,
        metadata=metadata,
        roi=roi,
        frame_step=frame_step,
        motion_threshold=resolved_motion_threshold,
        min_rally_duration=min_rally_duration,
        merge_gap=merge_gap,
        audio_enabled=audio_enabled,
        audio_success=audio_success,
        audio_note=audio_note,
        rally_intervals=rally_intervals,
        audio_records_df=audio_records_df,
    )
    paths.rally_json_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return PipelineRunResult(
        result=result,
        paths=paths,
        motion_df=motion_df,
        audio_peaks_df=audio_records_df,
    )


def _get_motion_video(video_path: Path, output_dir: Path) -> tuple[Path, VideoMetadata]:
    try:
        return video_path, get_video_metadata(video_path)
    except VideoLoadError:
        normalized_path = output_dir / "opencv_input.avi"
        _transcode_for_opencv(video_path, normalized_path)
        try:
            return normalized_path, get_video_metadata(normalized_path)
        except VideoLoadError as normalized_error:
            raise VideoLoadError(
                f"Failed to open video with OpenCV, including after ffmpeg normalization: {video_path}"
            ) from normalized_error


def _transcode_for_opencv(video_path: Path, output_path: Path) -> None:
    try:
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    except RuntimeError as exc:
        raise VideoLoadError("OpenCV failed to open the video and ffmpeg is unavailable for normalization.") from exc

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(video_path),
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v",
        "mjpeg",
        "-q:v",
        "3",
        str(output_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VideoLoadError(f"Failed to normalize video for OpenCV: {video_path}") from exc


def build_analysis_result(
    *,
    video_path: Path,
    metadata: VideoMetadata,
    roi: Roi,
    frame_step: int,
    motion_threshold: float,
    min_rally_duration: float,
    merge_gap: float,
    audio_enabled: bool,
    audio_success: bool,
    audio_note: str,
    rally_intervals: list[RallyInterval],
    audio_records_df: pd.DataFrame,
) -> AnalysisResult:
    rallies: list[RallyCandidate] = []
    for interval in rally_intervals:
        assigned = audio_records_df[audio_records_df["assigned_rally_id"] == interval.rally_id]
        peak_times = [round(float(value), 3) for value in assigned["time_sec"].tolist()]
        confidence = "medium" if audio_success and peak_times else "low"
        note = (
            "音声ピークに基づく打球候補数。周囲の声や隣コート音の影響を受ける可能性あり。"
            if audio_success
            else audio_note
        )
        rallies.append(
            RallyCandidate(
                rally_id=interval.rally_id,
                start_sec=round(interval.start_sec, 3),
                end_sec=round(interval.end_sec, 3),
                duration_sec=round(interval.duration_sec, 3),
                estimated_shots_audio=len(peak_times),
                audio_peak_times_sec=peak_times,
                confidence=confidence,
                note=note,
            )
        )

    return AnalysisResult(
        video_path=str(video_path),
        rally_count=len(rallies),
        rallies=rallies,
        analysis_config=AnalysisConfig(
            fps=metadata.fps,
            frame_count=metadata.frame_count,
            duration_sec=metadata.duration_sec,
            frame_step=frame_step,
            roi=roi.to_list(),
            motion_threshold=round(float(motion_threshold), 6),
            min_rally_duration_sec=min_rally_duration,
            merge_gap_sec=merge_gap,
            audio_enabled=audio_enabled,
            audio_note=audio_note,
        ),
    )
