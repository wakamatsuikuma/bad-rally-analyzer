from __future__ import annotations

import os
from pathlib import Path

_mpl_config_dir = Path(os.environ.get("MPLCONFIGDIR", "/tmp/bad-rally-analyzer-matplotlib"))
_mpl_config_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_mpl_config_dir))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from opencv.rally_detector import RallyInterval


def plot_motion_scores(
    *,
    motion_df: pd.DataFrame,
    rally_intervals: list[RallyInterval],
    threshold: float,
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(motion_df["time_sec"], motion_df["motion_score_raw"], label="motion_score_raw", alpha=0.35)
    ax.plot(motion_df["time_sec"], motion_df["motion_score_smooth"], label="motion_score_smooth", linewidth=2)
    ax.axhline(threshold, color="tab:red", linestyle="--", linewidth=1, label="active threshold")

    for interval in rally_intervals:
        ax.axvspan(interval.start_sec, interval.end_sec, color="tab:green", alpha=0.15)

    ax.set_xlabel("time_sec")
    ax.set_ylabel("motion_score")
    ax.set_title("Motion score and rally candidates")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
