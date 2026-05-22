from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path("outputs")
DEFAULT_FRAME_STEP = 5
DEFAULT_MIN_RALLY_DURATION_SEC = 2.0
DEFAULT_MERGE_GAP_SEC = 1.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate badminton rally candidates from motion scores and audio peaks.",
    )
    parser.add_argument("--video", type=Path, required=True, help="Input video path.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for output files.")
    parser.add_argument("--frame-step", type=int, default=DEFAULT_FRAME_STEP, help="Analyze every Nth frame.")
    parser.add_argument("--roi", type=str, default=None, help="Manual ROI as x1,y1,x2,y2. Defaults to full frame.")
    parser.add_argument(
        "--motion-threshold",
        type=float,
        default=None,
        help="Active threshold for smoothed motion score. Defaults to an inferred threshold.",
    )
    parser.add_argument(
        "--min-rally-duration",
        type=float,
        default=DEFAULT_MIN_RALLY_DURATION_SEC,
        help="Discard rally candidates shorter than this many seconds.",
    )
    parser.add_argument(
        "--merge-gap",
        type=float,
        default=DEFAULT_MERGE_GAP_SEC,
        help="Merge active intervals separated by gaps up to this many seconds.",
    )
    parser.add_argument(
        "--audio-enabled",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable audio peak based shot candidates. Use --no-audio-enabled to skip.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    from opencv.video_loader import VideoLoadError
    from pipeline.opencv_audio import run_opencv_audio_analysis

    try:
        run = run_opencv_audio_analysis(
            video_path=args.video,
            output_dir=args.output_dir,
            frame_step=args.frame_step,
            roi_text=args.roi,
            motion_threshold=args.motion_threshold,
            min_rally_duration=args.min_rally_duration,
            merge_gap=args.merge_gap,
            audio_enabled=args.audio_enabled,
        )
    except VideoLoadError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"motion score CSV: {run.paths.motion_csv_path}")
    print(f"motion score plot: {run.paths.motion_png_path}")
    print(f"rally candidates JSON: {run.paths.rally_json_path}")
    print(f"audio peaks CSV: {run.paths.audio_csv_path}")


if __name__ == "__main__":
    main()
