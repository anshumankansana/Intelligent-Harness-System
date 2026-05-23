"""Analyze an imported zip project and write engineering memory."""

from pathlib import Path

from harness.memory.store import MarkdownMemoryStore
from harness.planner.engine import PlannerEngine
from harness.providers.base import ProviderRole
from harness.providers.factory import ProviderFactory
from harness.zip_utils import list_project_tree

IMPORT_SYSTEM = """You analyze an EXISTING codebase the user uploaded as a zip.
Return ONLY valid JSON with keys:
project_spec, architecture, decisions, risks, tasks, test_plan
Each value is clean markdown. Describe what the project IS based on files, not what to build from scratch."""


class ImportAnalyzer:
    def __init__(self, factory: ProviderFactory, memory: MarkdownMemoryStore, log, run_id: str = ""):
        self.factory = factory
        self.memory = memory
        self.log = log
        self.run_id = run_id

    async def analyze(self, project_dir: Path, user_note: str = "") -> None:
        tree = list_project_tree(project_dir)
        pkg = ""
        pkg_path = project_dir / "package.json"
        if pkg_path.exists():
            pkg = pkg_path.read_text(encoding="utf-8", errors="replace")[:2000]

        await self.log("Analyzing imported project structure...")
        prompt = f"""User note: {user_note or "Imported existing project"}

File tree:
{tree}

package.json (if any):
{pkg or "N/A"}

Summarize this codebase for human approval before deploy or updates."""

        resp = await self.factory.complete_with_fallback(
            prompt, IMPORT_SYSTEM, ProviderRole.PLANNER, log=self.log, run_id=self.run_id
        )
        await self.log(f"Import analysis via {resp.provider} ({resp.model})")

        import json
        import re

        match = re.search(r"\{[\s\S]*\}", resp.content)
        if not match:
            self.memory.write(
                "PROJECT_SPEC.md",
                f"# Imported Project\n\n{resp.content}\n",
            )
            return
        data = json.loads(match.group())
        mapping = {
            "project_spec": "PROJECT_SPEC.md",
            "tasks": "TASKS.md",
            "architecture": "ARCHITECTURE.md",
            "decisions": "DECISIONS.md",
            "risks": "RISKS.md",
            "test_plan": "TEST_PLAN.md",
        }
        for key, filename in mapping.items():
            if data.get(key):
                self.memory.write(filename, data[key])
