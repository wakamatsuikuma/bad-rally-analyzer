from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "docs" / "directory-structure.md"

SKIP_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".DS_Store",
}
PRUNE_CONTENTS = {"data", "outputs"}


def should_skip(path: Path) -> bool:
    return path.name in SKIP_NAMES


def iter_visible_children(path: Path) -> list[Path]:
    children = [child for child in path.iterdir() if not should_skip(child)]
    return sorted(children, key=lambda child: (not child.is_dir(), child.name.lower()))


def render_tree(path: Path, prefix: str = "") -> list[str]:
    lines: list[str] = []
    children = iter_visible_children(path)

    for index, child in enumerate(children):
        is_last = index == len(children) - 1
        connector = "└── " if is_last else "├── "
        suffix = "/" if child.is_dir() else ""
        lines.append(f"{prefix}{connector}{child.name}{suffix}")

        if child.is_dir() and child.name not in PRUNE_CONTENTS:
            extension = "    " if is_last else "│   "
            lines.extend(render_tree(child, prefix + extension))

    return lines


def build_document() -> str:
    tree_lines = ["bad-rally-analyzer/"]
    tree_lines.extend(render_tree(ROOT))
    tree_text = "\n".join(tree_lines)

    return "\n".join(
        [
            "# Directory Structure",
            "",
            "このファイルは `scripts/update_directory_structure.py` から自動生成します。",
            "更新する場合は次を実行してください。",
            "",
            "```bash",
            "uv run python scripts/update_directory_structure.py",
            "```",
            "",
            "```text",
            tree_text,
            "```",
            "",
        ]
    )


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_document(), encoding="utf-8")


if __name__ == "__main__":
    main()
