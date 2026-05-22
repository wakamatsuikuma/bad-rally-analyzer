# Directory Structure

このファイルは `scripts/update_directory_structure.py` から自動生成します。
更新する場合は次を実行してください。

```bash
uv run python scripts/update_directory_structure.py
```

```text
bad-rally-analyzer/
├── data/
├── docs/
│   └── directory-structure.md
├── outputs/
├── scripts/
│   └── update_directory_structure.py
├── src/
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── audio_extractor.py
│   │   └── shot_counter.py
│   ├── gemini/
│   │   ├── __init__.py
│   │   ├── analyzer.py
│   │   └── schemas.py
│   ├── opencv/
│   │   ├── __init__.py
│   │   ├── motion_score.py
│   │   ├── plot.py
│   │   ├── rally_detector.py
│   │   └── video_loader.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   └── opencv_audio.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── badminton_rally_prompt.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── result_schema.py
│   ├── __init__.py
│   ├── app.py
│   └── main.py
├── tests/
│   ├── test_rally_detector.py
│   └── test_shot_counter.py
├── .env
├── .gitignore
├── .python-version
├── AGENTS.md
├── index.html
├── pyproject.toml
├── README.md
└── uv.lock
```
