# Directory Structure

このファイルは `scripts/update_directory_structure.py` から自動生成します。
更新する場合は次を実行してください。

```bash
uv run python scripts/update_directory_structure.py
```

```text
bad-rally-analyzer/
├── docs/
│   └── directory-structure.md
├── outputs/
├── scripts/
│   └── update_directory_structure.py
├── src/
│   ├── gemini/
│   │   ├── __init__.py
│   │   ├── analyzer.py
│   │   └── schemas.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── badminton_rally_prompt.py
│   ├── __init__.py
│   ├── app.py
│   └── main.py
├── .env
├── .gitignore
├── .python-version
├── AGENTS.md
├── index.html
├── pyproject.toml
├── README.md
└── uv.lock
```
