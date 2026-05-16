from __future__ import annotations

from pydantic import BaseModel, Field


class RallyAnalysis(BaseModel):
    rally_index: int = Field(description="動画内での1始まりのラリー番号。")
    start_time_sec: float = Field(description="推定したラリー開始時刻。単位は秒。")
    end_time_sec: float = Field(description="推定したラリー終了時刻。単位は秒。")
    shot_count: int = Field(description="そのラリーの推定打数。サーブは含めない整数。")
    confidence: float = Field(description="そのラリー解析の信頼度。0.0 から 1.0。")
    notes: str = Field(description="判定根拠や曖昧さを示す短い日本語メモ。")


class VideoAnalysisResult(BaseModel):
    video_summary: str = Field(description="動画全体の内容を表す短い日本語要約。")
    total_rallies: int = Field(description="動画全体で検出したラリー数。")
    average_shots_per_rally: float = Field(
        description="検出した全ラリーにおける1ラリーあたり平均打数。"
    )
    rallies: list[RallyAnalysis] = Field(description="ラリーごとの解析結果一覧。")
    overall_confidence: float = Field(description="動画全体の解析信頼度。0.0 から 1.0。")
    limitations: list[str] = Field(description="解析上の制約や曖昧さを表す日本語リスト。")
