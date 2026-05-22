from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import pandas as pd
import streamlit as st

from gemini.analyzer import (
    DEFAULT_MODEL,
    DEFAULT_VIDEO_FPS,
    GeminiAnalyzerError,
    GeminiBadmintonAnalyzer,
)
from opencv.video_loader import VideoLoadError
from pipeline.opencv_audio import (
    DEFAULT_FRAME_STEP,
    DEFAULT_MERGE_GAP_SEC,
    DEFAULT_MIN_RALLY_DURATION_SEC,
    DEFAULT_OUTPUT_DIR,
    PipelineRunResult,
    run_opencv_audio_analysis,
)
from prompts.badminton_rally_prompt import SYSTEM_INSTRUCTION, USER_PROMPT

OUTPUTS_DIR = Path("outputs")
DASHBOARD_DEFAULT_VIDEO_PATH = Path("data/test_movie.mp4")
DASHBOARD_OUTPUT_ROOT = DEFAULT_OUTPUT_DIR / "opencv_dashboard"
MODEL_OPTIONS = [
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
]


def save_uploaded_file(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix or ".mp4"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        return Path(temp_file.name)


def persist_result(original_name: str, result_json: dict) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = Path(original_name).stem.replace(" ", "_")
    output_path = OUTPUTS_DIR / f"{timestamp}-{safe_name}.json"
    output_path.write_text(json.dumps(result_json, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def list_saved_results() -> list[Path]:
    if not OUTPUTS_DIR.exists():
        return []
    saved_results = []
    for path in OUTPUTS_DIR.glob("*.json"):
        try:
            payload = load_saved_result(path)
        except (OSError, json.JSONDecodeError):
            continue
        if "average_shots_per_rally" in payload and "total_rallies" in payload:
            saved_results.append(path)
    return sorted(saved_results, reverse=True)


def load_saved_result(saved_path: Path) -> dict[str, Any]:
    return json.loads(saved_path.read_text(encoding="utf-8"))


def build_analysis_config(analyzer: GeminiBadmintonAnalyzer) -> dict[str, Any]:
    if hasattr(analyzer, "get_analysis_config"):
        return analyzer.get_analysis_config()

    return {
        "model_name": analyzer.model_name,
        "video_fps": DEFAULT_VIDEO_FPS,
        "system_instruction": SYSTEM_INSTRUCTION,
        "user_prompt": USER_PROMPT,
    }


def render_summary(result_json: dict) -> None:
    st.subheader("解析結果")
    metric_columns = st.columns(3)
    metric_columns[0].metric("平均打数", result_json["average_shots_per_rally"])
    metric_columns[1].metric("ラリー数", result_json["total_rallies"])
    metric_columns[2].metric("全体信頼度", result_json["overall_confidence"])

    st.write(result_json["video_summary"])

    if result_json["rallies"]:
        st.subheader("ラリー一覧")
        table_rows = [
            {
                "rally_index": rally["rally_index"],
                "start_time_sec": rally["start_time_sec"],
                "end_time_sec": rally["end_time_sec"],
                "shot_count": rally["shot_count"],
                "confidence": rally["confidence"],
                "notes": rally["notes"],
            }
            for rally in result_json["rallies"]
        ]
        st.dataframe(table_rows, use_container_width=True)
    else:
        st.info("ラリーが検出されませんでした。")

    if result_json["limitations"]:
        st.subheader("注意点")
        for item in result_json["limitations"]:
            st.write(f"- {item}")


def build_dashboard_output_dir(output_root: Path, video_name: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = Path(video_name).stem.replace(" ", "_")
    return output_root / f"{timestamp}-{safe_name}"


def render_opencv_dashboard() -> None:
    st.subheader("OpenCV / Audio PoC")

    source_mode = st.radio(
        "動画ソース",
        options=["data/test_movie.mp4", "アップロード"],
        horizontal=True,
    )

    uploaded_file = None
    temp_video_path: Path | None = None
    video_path = DASHBOARD_DEFAULT_VIDEO_PATH
    source_name = DASHBOARD_DEFAULT_VIDEO_PATH.name

    if source_mode == "アップロード":
        uploaded_file = st.file_uploader(
            "動画ファイル",
            type=["mp4", "mov", "avi", "mkv", "webm"],
            accept_multiple_files=False,
            key="opencv_video_upload",
        )
        video_ready = uploaded_file is not None
        if uploaded_file is not None:
            source_name = uploaded_file.name
            st.video(uploaded_file)
    else:
        video_path = Path(st.text_input("動画ファイル", value=str(DASHBOARD_DEFAULT_VIDEO_PATH)))
        source_name = video_path.name
        video_ready = video_path.exists()
        if video_ready:
            st.video(str(video_path))
        else:
            st.warning(f"動画ファイルが見つかりません: {video_path}")

    with st.expander("解析パラメータ", expanded=True):
        col1, col2, col3 = st.columns(3)
        frame_step = col1.number_input("frame-step", min_value=1, value=DEFAULT_FRAME_STEP, step=1)
        min_rally_duration = col2.number_input(
            "min-rally-duration",
            min_value=0.1,
            value=DEFAULT_MIN_RALLY_DURATION_SEC,
            step=0.5,
        )
        merge_gap = col3.number_input("merge-gap", min_value=0.0, value=DEFAULT_MERGE_GAP_SEC, step=0.5)

        roi_text = st.text_input("roi", value="", placeholder="例: 100,50,1180,700")
        auto_threshold = st.checkbox("motion-threshold を自動推定", value=True)
        motion_threshold = None
        if not auto_threshold:
            motion_threshold = st.number_input("motion-threshold", min_value=0.0, value=3.0, step=0.5)

        col4, col5 = st.columns(2)
        audio_enabled = col4.checkbox("audio-enabled", value=True)
        output_root = Path(col5.text_input("output-dir", value=str(DASHBOARD_OUTPUT_ROOT)))

    if st.button("解析を実行", type="primary", disabled=not video_ready, key="run_opencv_analysis"):
        if uploaded_file is not None:
            temp_video_path = save_uploaded_file(uploaded_file)
            video_path = temp_video_path

        output_dir = build_dashboard_output_dir(output_root, source_name)
        try:
            with st.spinner("解析中です。動画長によって時間がかかります。"):
                run = run_opencv_audio_analysis(
                    video_path=video_path,
                    output_dir=output_dir,
                    frame_step=int(frame_step),
                    roi_text=roi_text.strip() or None,
                    motion_threshold=motion_threshold,
                    min_rally_duration=float(min_rally_duration),
                    merge_gap=float(merge_gap),
                    audio_enabled=audio_enabled,
                )
                st.session_state["opencv_last_run"] = run
        except VideoLoadError as exc:
            st.error(str(exc))
        except Exception as exc:  # pragma: no cover
            st.exception(exc)
        finally:
            if temp_video_path is not None:
                temp_video_path.unlink(missing_ok=True)

    last_run = st.session_state.get("opencv_last_run")
    if last_run is not None:
        render_opencv_result(last_run)


def render_opencv_result(run: PipelineRunResult) -> None:
    result = run.result
    total_audio_shots = sum(rally.estimated_shots_audio for rally in result.rallies)
    config = result.analysis_config

    st.divider()
    st.subheader("解析結果")
    metric_columns = st.columns(4)
    metric_columns[0].metric("ラリー候補数", result.rally_count)
    metric_columns[1].metric("音声ピーク打球候補", total_audio_shots)
    metric_columns[2].metric("動画秒数", round(config.duration_sec, 2))
    metric_columns[3].metric("motion-threshold", config.motion_threshold)

    st.caption(f"保存先: {run.paths.output_dir}")

    if result.rallies:
        rally_rows = [
            {
                "rally_id": rally.rally_id,
                "start_sec": rally.start_sec,
                "end_sec": rally.end_sec,
                "duration_sec": rally.duration_sec,
                "estimated_shots_audio": rally.estimated_shots_audio,
                "confidence": rally.confidence,
            }
            for rally in result.rallies
        ]
        st.dataframe(pd.DataFrame(rally_rows), use_container_width=True, hide_index=True)
    else:
        st.info("ラリー候補は検出されませんでした。")

    if run.paths.motion_png_path.exists():
        st.image(str(run.paths.motion_png_path), use_container_width=True)

    with st.expander("rally_candidates.json", expanded=True):
        st.json(result.model_dump(mode="json"))

    col1, col2, col3 = st.columns(3)
    col1.download_button(
        "rally_candidates.json",
        data=run.paths.rally_json_path.read_bytes(),
        file_name=run.paths.rally_json_path.name,
        mime="application/json",
    )
    col2.download_button(
        "motion_score.csv",
        data=run.paths.motion_csv_path.read_bytes(),
        file_name=run.paths.motion_csv_path.name,
        mime="text/csv",
    )
    col3.download_button(
        "audio_peaks.csv",
        data=run.paths.audio_csv_path.read_bytes(),
        file_name=run.paths.audio_csv_path.name,
        mime="text/csv",
    )

    with st.expander("motion_score.csv"):
        st.dataframe(run.motion_df, use_container_width=True, height=320)

    with st.expander("audio_peaks.csv"):
        if run.audio_peaks_df.empty:
            st.info(result.analysis_config.audio_note)
        else:
            st.dataframe(run.audio_peaks_df, use_container_width=True, height=260)


def render_saved_result_selector() -> None:
    saved_results = list_saved_results()
    if not saved_results:
        return

    st.divider()
    st.subheader("保存済み解析結果")
    selected_path = st.selectbox(
        "過去の解析結果を表示",
        options=saved_results,
        format_func=lambda path: path.name,
    )

    saved_payload = load_saved_result(selected_path)
    metadata = saved_payload.get("analysis_metadata", {})

    if metadata:
        st.caption(
            " / ".join(
                [
                    f"保存日時: {metadata.get('saved_at', '-')}",
                    f"動画: {metadata.get('source_video_name', '-')}",
                    f"モデル: {metadata.get('model_name', '-')}",
                    f"fps: {metadata.get('video_fps', '-')}",
                ]
            )
        )

    render_summary(saved_payload)

    with st.expander("保存済みプロンプトと設定"):
        st.json(metadata)


def render_gemini_app() -> None:
    st.subheader("Gemini API")

    with st.expander("設定", expanded=True):
        selected_model = st.selectbox(
            "Gemini model",
            options=MODEL_OPTIONS,
            index=MODEL_OPTIONS.index(DEFAULT_MODEL) if DEFAULT_MODEL in MODEL_OPTIONS else 0,
        )
        custom_model_name = st.text_input("Custom model name", value=selected_model)
        st.write("`.env` の `GEMINI_API_KEY` を利用します。")

    render_saved_result_selector()

    uploaded_file = st.file_uploader(
        "試合動画をアップロードしてください",
        type=["mp4", "mov", "avi", "mkv", "webm"],
        accept_multiple_files=False,
    )

    st.markdown(
        """
        **平均打数の定義**: 動画全体に含まれる全ラリーについて、`1ラリーあたり平均ショット数` を算出します。
        """
    )

    if not uploaded_file:
        return

    st.video(uploaded_file)

    if st.button("解析を実行", type="primary", key="run_gemini_analysis"):
        temp_video_path = save_uploaded_file(uploaded_file)

        try:
            with st.spinner("Gemini で動画を解析しています。動画長によって時間がかかります。"):
                analyzer = GeminiBadmintonAnalyzer(
                    model_name=custom_model_name.strip() or selected_model or DEFAULT_MODEL
                )
                result, raw_json = analyzer.analyze_video(temp_video_path)
                result_json = result.model_dump()
                analysis_config = build_analysis_config(analyzer)
                persisted_payload = {
                    **result_json,
                    "analysis_metadata": {
                        "saved_at": datetime.now().isoformat(timespec="seconds"),
                        "source_video_name": uploaded_file.name,
                        "source_video_size_bytes": uploaded_file.size,
                        **analysis_config,
                    },
                    "raw_model_output": raw_json,
                }
                saved_path = persist_result(uploaded_file.name, persisted_payload)
        except GeminiAnalyzerError as exc:
            st.error(str(exc))
            return
        except Exception as exc:  # pragma: no cover
            st.exception(exc)
            return
        finally:
            temp_video_path.unlink(missing_ok=True)

        render_summary(result_json)
        st.success(f"解析結果を保存しました: {saved_path}")
        with st.expander("今回のプロンプトと設定"):
            st.json(persisted_payload["analysis_metadata"])
        st.download_button(
            label="JSONをダウンロード",
            data=json.dumps(persisted_payload, ensure_ascii=False, indent=2),
            file_name=saved_path.name,
            mime="application/json",
        )


def main() -> None:
    st.set_page_config(page_title="Badminton Rally Analyzer", page_icon="🏸", layout="wide")
    st.title("Badminton Rally Analyzer")
    st.caption("OpenCV/音声解析PoCとGemini API解析を確認できます。")

    opencv_tab, gemini_tab = st.tabs(["OpenCV / Audio PoC", "Gemini API"])
    with opencv_tab:
        render_opencv_dashboard()
    with gemini_tab:
        render_gemini_app()


if __name__ == "__main__":
    main()
