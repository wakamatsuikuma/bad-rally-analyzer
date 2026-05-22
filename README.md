# Badminton Rally Analyzer

バドミントン動画からラリー候補区間と打球候補数を推定する PoC です。

現在は以下の2系統を持っています。

- `① Gemini APIのみでの解析`: Streamlit UI から動画をアップロードし、Gemini の構造化 JSON 出力でラリー情報を推定
- `② OpenCVなどを使った動画解析パイプライン`: フレーム差分の `motion_score` と音声ピークから、ラリー候補区間と打球候補数を可視化・出力

今回の主対象は `② OpenCVなどを使った動画解析パイプライン` です。Gemini API 呼び出しはこのCLIでは行いません。

## セットアップ

```bash
uv sync
```

`.env` に API キーを設定します。

```text
GEMINI_API_KEY=xxxxx
```

## 起動方法

ダッシュボード UI:

```bash
uv run streamlit run src/app.py
```

最初のタブ `OpenCV / Audio PoC` では、デフォルトで `data/test_movie.mp4` を読み込みます。画面上の `解析を実行` を押すと、ラリー候補数、音声ピーク由来の打球候補数、`motion_score.png`、CSV/JSONを同じ画面で確認できます。

OpenCV/音声解析パイプライン:

```bash
uv run python src/main.py --video data/sample.mp4
```

主なオプション:

```bash
uv run python src/main.py \
  --video data/sample.mp4 \
  --output-dir outputs \
  --frame-step 5 \
  --roi 100,50,1180,700 \
  --motion-threshold 3.0 \
  --min-rally-duration 2.0 \
  --merge-gap 1.0 \
  --audio-enabled
```

`--roi` を省略した場合は動画全体を解析します。`--motion-threshold` を省略した場合は、`motion_score_smooth` から簡易的に推定します。音声解析を切る場合は `--no-audio-enabled` を指定します。

## ディレクトリ構成

最新のディレクトリ構成は [docs/directory-structure.md](/Users/wakamatsuikuma/workspace/bad-rally-analyzer/docs/directory-structure.md) に記録します。
更新する場合は次を実行してください。

```bash
uv run python scripts/update_directory_structure.py
```

## 出力内容

OpenCV/音声解析パイプラインは `outputs/` 配下に以下を出力します。

- `motion_score.csv`: `time_sec`, `frame_idx`, `motion_score_raw`, `motion_score_smooth`, `is_active`
- `motion_score.png`: motion score の推移とラリー候補区間
- `rally_candidates.json`: ラリー候補区間、音声ピーク由来の `estimated_shots_audio`
- `audio_peaks.csv`: 検出した音声ピークと割り当てラリーID

Gemini API UI の出力:

- 動画全体の平均打数
- 検出ラリー数
- ラリーごとの開始秒・終了秒
- ラリーごとの推定打数
- 信頼度
- 制約事項
- `outputs/` への JSON 保存
- 保存時のモデル名、fps、プロンプト、元動画名などのメタデータ

## 実装メモ

- Gemini API 単独方式では、打数はモデル推定です
- OpenCV/音声解析パイプラインの `estimated_shots_audio` は確定打数ではなく、音声ピークに基づく打球候補数です
- 音声ピークは声、足音、隣コート音、反響の影響を受けるため、後続フェーズで短いラリー候補区間を Gemini API に渡して補正する想定です
- Gemini へ渡す動画メタデータの `fps` は `20` に固定しています
- プロンプトは `ラリー区間検出 → ラリーごとの打数推定 → 全体平均集計` の順で推論させる方針です
- 打数はサーブを含めず、ラリー数は過大推定を避ける保守的な判定を優先します
- 長尺動画はアップロードと解析に時間がかかります
