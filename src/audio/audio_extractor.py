from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg


@dataclass(frozen=True)
class AudioExtractionResult:
    wav_path: Path | None
    note: str


def extract_audio_to_wav(video_path: Path, output_dir: Path, sample_rate: int = 22050) -> AudioExtractionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    wav_path = output_dir / "extracted_audio.wav"
    try:
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    except RuntimeError as exc:
        return AudioExtractionResult(
            wav_path=None,
            note=f"Audio extraction failed because ffmpeg is unavailable. Detail: {exc}",
        )

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        str(wav_path),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        return AudioExtractionResult(
            wav_path=None,
            note=f"Audio extraction failed; estimated_shots_audio is unavailable. Detail: {exc}",
        )

    if not wav_path.exists() or wav_path.stat().st_size == 0:
        return AudioExtractionResult(
            wav_path=None,
            note="Audio extraction produced no WAV data; estimated_shots_audio is unavailable.",
        )

    return AudioExtractionResult(
        wav_path=wav_path,
        note="Audio peaks were detected from the extracted mono WAV track.",
    )
