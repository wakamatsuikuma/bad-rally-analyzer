from __future__ import annotations

import json
import mimetypes
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from pydantic import ValidationError

from gemini.schemas import VideoAnalysisResult
from prompts.badminton_rally_prompt import SYSTEM_INSTRUCTION, USER_PROMPT

DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiAnalyzerError(RuntimeError):
    """Raised when Gemini-based video analysis fails."""


class GeminiBadmintonAnalyzer:
    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise GeminiAnalyzerError("`GEMINI_API_KEY` が設定されていません。`.env` を確認してください。")

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def analyze_video(self, video_path: Path) -> tuple[VideoAnalysisResult, dict]:
        if not video_path.exists():
            raise GeminiAnalyzerError(f"動画ファイルが見つかりません: {video_path}")

        uploaded_file = self._upload_and_wait(video_path)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[uploaded_file, USER_PROMPT],
            config={
                "system_instruction": SYSTEM_INSTRUCTION,
                "temperature": 0,
                "response_mime_type": "application/json",
                "response_schema": VideoAnalysisResult,
            },
        )

        try:
            parsed = response.parsed
            if parsed is None:
                parsed = VideoAnalysisResult.model_validate_json(response.text)
        except ValidationError as exc:
            raise GeminiAnalyzerError("Gemini の構造化出力を解析できませんでした。") from exc

        normalized = self._normalize_result(parsed)
        raw_payload = json.loads(response.text)
        return normalized, raw_payload

    def _upload_and_wait(self, video_path: Path):
        mime_type = mimetypes.guess_type(video_path.name)[0] or "video/mp4"
        uploaded_file = self.client.files.upload(file=str(video_path), config={"mime_type": mime_type})

        while not uploaded_file.state or uploaded_file.state.name != "ACTIVE":
            if uploaded_file.state and uploaded_file.state.name == "FAILED":
                raise GeminiAnalyzerError("動画のアップロード後処理に失敗しました。")
            time.sleep(5)
            uploaded_file = self.client.files.get(name=uploaded_file.name)

        return uploaded_file

    def _normalize_result(self, result: VideoAnalysisResult) -> VideoAnalysisResult:
        if result.total_rallies <= 0 or not result.rallies:
            return result.model_copy(update={"total_rallies": 0, "average_shots_per_rally": 0.0, "rallies": []})

        computed_average = round(
            sum(rally.shot_count for rally in result.rallies) / len(result.rallies),
            2,
        )
        return result.model_copy(
            update={
                "total_rallies": len(result.rallies),
                "average_shots_per_rally": computed_average,
            }
        )
