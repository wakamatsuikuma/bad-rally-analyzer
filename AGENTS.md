# AGENTS.md

# プロジェクト概要

本プロジェクトは、バドミントン動画を解析するためのPoC（概念実証）です。

目的：

* ラリー時間の推定
* 打数（ショット数）の推定
* ミスの推定
* 動画からの試合統計生成

本プロジェクトでは、以下の3種類の解析方式を扱います。

## ① モデルAPIによる解析

Gemini API を利用して動画内容を解析する方式です。

主な用途：

* 動画内容理解
* ラリー検出
* ミス判定
* JSON形式の構造化出力
* 自然言語ベースの分析

利用技術：

* Google AI Studio
* Gemini API
* gemini-2.5-flash 系モデル

---

## ② OpenCV等による動画解析パイプライン

OpenCV 等を利用して、動画をフレーム単位・数値処理ベースで解析する方式です。

主な用途：

* フレーム抽出
* 動体検知
* 音声ピーク解析
* ショット数推定
* ラリー開始終了検出
* 高速処理

利用技術：

* OpenCV
* numpy
* pandas

---

## ③ ①と②を組み合わせたハイブリッド解析

OpenCV等で前処理を行い、
Gemini API で高次解析を行う構成です。

例：

* OpenCVでラリー区間抽出
* Geminiでラリー内容解析
* OpenCVで打球候補抽出
* Geminiでミス種別判定

本プロジェクトでは、
最終的にこのハイブリッド構成を主軸候補とします。

---

# 技術スタック

* Python 3.12
* uv
* Gemini API
* OpenCV
* pandas
* numpy
* matplotlib

必要に応じて以下を追加：

* FastAPI
* Streamlit
* Jupyter Notebook

---

# パッケージ管理

パッケージマネージャは `uv` を使用してください。

## セットアップ

```bash
uv sync
```

## Python実行

```bash
uv run python src/main.py
```

## テスト実行

```bash
uv run pytest
```

---

# ディレクトリ構成

最新の実ディレクトリ構成は `docs/directory-structure.md` を参照してください。

更新コマンド：

```bash
uv run python scripts/update_directory_structure.py
```

---

# コーディング方針

* まずはシンプル実装を優先
* 可読性を重視
* premature optimization を避ける
* 小さな関数に分割する
* 必要以上に抽象化しない
* 型ヒントは可能な範囲で利用する

---

# Gemini API方針

* デフォルトモデルは `gemini-2.5-flash`
* JSON structured output を優先
* プロンプトは deterministic に保つ
* 実験時は token 使用量を最小化する

---

# Git運用
* APIキーをcommitしない
* `.env` を利用する

---

# 重要事項

APIキーをコードへ直書きしないこと。

`.env` を利用してください。

例：

```text
GEMINI_API_KEY=xxxxx
```
