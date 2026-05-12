from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import streamlit as st

from gemini.analyzer import (
    DEFAULT_MODEL,
    DEFAULT_VIDEO_FPS,
    GeminiAnalyzerError,
    GeminiBadmintonAnalyzer,
)
from prompts.badminton_rally_prompt import SYSTEM_INSTRUCTION, USER_PROMPT

OUTPUTS_DIR = Path("outputs")
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
    return sorted(OUTPUTS_DIR.glob("*.json"), reverse=True)


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


def main() -> None:
    st.set_page_config(page_title="Badminton Rally Analyzer", page_icon="🏸", layout="wide")
    st.title("Badminton Rally Analyzer")
    st.caption("Gemini API 単独で動画からラリーごとの打数を推定し、平均打数を算出します。")

    with st.sidebar:
        st.header("設定")
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

    if st.button("解析を実行", type="primary"):
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


if __name__ == "__main__":
    main()
