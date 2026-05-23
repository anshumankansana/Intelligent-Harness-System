import asyncio
import json
import re

from harness.memory.formatter import FORMAT_RULES, clean_markdown
from harness.memory.store import MarkdownMemoryStore
from harness.providers.base import ProviderRole
from harness.providers.factory import ProviderFactory

PLANNER_SYSTEM = f"""You are an engineering planner for an autonomous harness.
Write clean, human-readable markdown documents.
{FORMAT_RULES}"""

COMBINED_SYSTEM = f"""You are an engineering planner. Return ONLY valid JSON (no markdown fences) with keys:
project_spec, tasks, architecture, decisions, risks, test_plan
Each value is a clean markdown string following these rules:
{FORMAT_RULES}"""

STEP_TIMEOUT = 90.0

FILE_PROMPTS = {
    "PROJECT_SPEC.md": "Write PROJECT_SPEC: goal, audience, MVP features (bullets), tech stack, out of scope.",
    "TASKS.md": "Write TASKS: numbered ## sections with - checkboxes as bullet tasks for implementation order.",
    "ARCHITECTURE.md": "Write ARCHITECTURE: components, data flow (numbered steps), stack — simple ## sections.",
    "DECISIONS.md": "Write DECISIONS: table-style list as bullets — Decision | Rationale (one per line).",
    "RISKS.md": "Write RISKS: Risk | Impact | Mitigation as clear bullet groups.",
    "TEST_PLAN.md": "Write TEST_PLAN: smoke tests and acceptance criteria as checklists.",
}


class PlannerEngine:
    def __init__(self, factory: ProviderFactory, memory: MarkdownMemoryStore, log, run_id: str = ""):
        self.factory = factory
        self.memory = memory
        self.log = log
        self.run_id = run_id
        self._use_chain: list[str] | None = None

    def set_fallback_chain(self, chain: list[str]) -> None:
        self._use_chain = chain

    async def run(self, user_idea: str, human_context: str = "") -> dict:
        await self.log("Planner running...")
        context = f"{user_idea}\n\n{human_context}" if human_context else user_idea

        try:
            return await self._run_combined(context)
        except Exception as e:
            await self.log(f"Combined planner failed ({e}), using step-by-step fallback...")
            return await self._run_sequential(context)

    async def _complete(self, prompt: str, system: str) -> str:
        chain = self._use_chain or self.factory.chain_for_role(ProviderRole.PLANNER)
        resp = await self.factory.complete_with_chain(
            prompt,
            system,
            ProviderRole.PLANNER,
            chain,
            run_id=self.run_id,
            log=self.log,
        )
        return resp.content

    async def _run_combined(self, context: str) -> dict:
        await self.log("Generating all engineering docs (single pass)...")
        prompt = f"Create full engineering memory for this project:\n{context}"
        content = await asyncio.wait_for(
            self._complete(prompt, COMBINED_SYSTEM), timeout=STEP_TIMEOUT
        )
        data = self._parse_combined_json(content)
        mapping = {
            "project_spec": "PROJECT_SPEC.md",
            "tasks": "TASKS.md",
            "architecture": "ARCHITECTURE.md",
            "decisions": "DECISIONS.md",
            "risks": "RISKS.md",
            "test_plan": "TEST_PLAN.md",
        }
        for key, filename in mapping.items():
            raw = data.get(key, "")
            self.memory.write(filename, raw)
            await self.log(f"Saved {filename}")
        await self.log("Markdown engineering memory generated.")
        return {
            "spec": data.get("project_spec", ""),
            "tasks": data.get("tasks", ""),
            "architecture": data.get("architecture", ""),
        }

    async def _run_sequential(self, context: str) -> dict:
        results = {}
        prior = context
        for filename, hint in FILE_PROMPTS.items():
            await self.log(f"Generating {filename}...")
            prompt = f"Project:\n{prior[:8000]}\n\n{hint}"
            text = await asyncio.wait_for(
                self._complete(prompt, PLANNER_SYSTEM), timeout=STEP_TIMEOUT
            )
            self.memory.write(filename, text)
            await self.log(f"Done {filename}")
            prior = f"{prior}\n\n{filename}:\n{text}"[:10000]
            key = filename.replace(".md", "").lower().replace("project_spec", "spec")
            if "spec" in key and "project" in filename.lower():
                results["spec"] = text
            elif key == "tasks":
                results["tasks"] = text
            elif key == "architecture":
                results["architecture"] = text
        await self.log("Markdown engineering memory generated.")
        return results

    def _parse_combined_json(self, raw: str) -> dict:
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError("No JSON in planner response")
        data = json.loads(match.group())
        for k in ["project_spec", "tasks", "architecture", "decisions", "risks", "test_plan"]:
            data[k] = clean_markdown(data.get(k, ""), None)
        return data
