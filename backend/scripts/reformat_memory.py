"""Reformat existing memory/*.md files in workspace runs (fixes raw ** markdown)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from harness.memory.formatter import wrap_with_template  # noqa: E402

WORKSPACE = ROOT / "workspace"


def main() -> None:
    if not WORKSPACE.exists():
        print("No workspace folder found.")
        return
    count = 0
    for mem_dir in WORKSPACE.glob("*/memory"):
        for md in mem_dir.glob("*.md"):
            raw = md.read_text(encoding="utf-8")
            md.write_text(wrap_with_template(md.name, raw), encoding="utf-8")
            print(f"Formatted {md}")
            count += 1
    print(f"Done. {count} file(s) updated.")


if __name__ == "__main__":
    main()
