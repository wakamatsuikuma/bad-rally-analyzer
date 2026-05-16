# Badminton Rally Analyzer

Gemini API 単独方式で、アップロードしたバドミントン動画からラリーごとの打数を推定し、動画全体の `1ラリーあたり平均ショット数` を算出する PoC です。

## 対応方式

- `① モデルAPIによる解析`
- Gemini Files API に動画をアップロード
- Gemini の構造化 JSON 出力でラリー情報を取得

## セットアップ

```bash
uv sync
```

`.env` に API キーを設定します。

```text
GEMINI_API_KEY=xxxxx
```

## 起動方法

```bash
uv run streamlit run src/app.py
```

## ディレクトリ構成

最新のディレクトリ構成は [docs/directory-structure.md](/Users/wakamatsuikuma/workspace/bad-rally-analyzer/docs/directory-structure.md) に記録します。
更新する場合は次を実行してください。

```bash
uv run python scripts/update_directory_structure.py
```

## 出力内容

- 動画全体の平均打数
- 検出ラリー数
- ラリーごとの開始秒・終了秒
- ラリーごとの推定打数
- 信頼度
- 制約事項
- `outputs/` への JSON 保存
- 保存時のモデル名、fps、プロンプト、元動画名などのメタデータ

## 実装メモ

- 初版は Gemini API のみを使うため、打数はモデル推定です
- Gemini へ渡す動画メタデータの `fps` は `20` に固定しています
- プロンプトは `ラリー区間検出 → ラリーごとの打数推定 → 全体平均集計` の順で推論させる方針です
- 打数はサーブを含めず、ラリー数は過大推定を避ける保守的な判定を優先します
- OpenCV による前処理や補正はまだ入っていません
- 長尺動画はアップロードと解析に時間がかかります
