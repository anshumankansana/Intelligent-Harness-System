from pathlib import Path
from typing import Dict, List, Optional

from harness.memory.formatter import wrap_with_template

MEMORY_FILES = [
    "TASKS.md",
    "PROJECT_SPEC.md",
    "ARCHITECTURE.md",
    "DECISIONS.md",
    "RISKS.md",
    "TEST_PLAN.md",
]


class MarkdownMemoryStore:
    def __init__(self, workspace_root: Path):
        self.root = workspace_root / "memory"
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, filename: str) -> Path:
        return self.root / filename

    def write(self, filename: str, content: str) -> Path:
        path = self.path_for(filename)
        formatted = wrap_with_template(filename, content)
        path.write_text(formatted, encoding="utf-8")
        return path

    def read(self, filename: str) -> Optional[str]:
        path = self.path_for(filename)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def read_all(self) -> Dict[str, str]:
        result = {}
        names = set(MEMORY_FILES) | {"DEBATE_SUMMARY.md"}
        for name in names:
            content = self.read(name)
            if content:
                result[name] = content
        for path in self.root.glob("*.md"):
            if path.name not in result:
                result[path.name] = path.read_text(encoding="utf-8")
        return result

    def list_files(self) -> List[str]:
        return [f.name for f in self.root.glob("*.md")]

    def build_context_block(self) -> str:
        parts = []
        for name in MEMORY_FILES:
            content = self.read(name)
            if content:
                parts.append(f"## {name}\n{content}")
        return "\n\n".join(parts)
