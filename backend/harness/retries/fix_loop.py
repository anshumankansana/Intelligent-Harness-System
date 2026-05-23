from pathlib import Path

from harness.providers.base import ProviderRole
from harness.providers.factory import ProviderFactory

MAX_RETRIES = 2


class RetryFixLoop:
    def __init__(self, factory: ProviderFactory, project_path: Path, log):
        self.factory = factory
        self.project_path = project_path
        self.log = log
        self.retry_count = 0

    async def analyze_and_fix(self, failure_logs: str) -> bool:
        if self.retry_count >= MAX_RETRIES:
            await self.log("Max retries (2) reached.")
            return False

        self.retry_count += 1
        await self.log(f"Fixing build... (attempt {self.retry_count}/{MAX_RETRIES})")

        prompt = f"""Analyze these build/validation logs and suggest a minimal fix.
Return ONLY a JSON object: {{"file": "relative/path", "content": "full file content"}}
For a simple demo app fix.

Logs:
{failure_logs[:4000]}
"""
        try:
            resp = await self.factory.complete_with_fallback(
                prompt,
                "You fix build errors for small Node projects.",
                ProviderRole.FAST,
                log=self.log,
            )
            await self._apply_fix(resp.content)
            await self.log(f"Fix applied via {resp.provider}, retrying validation...")
            return True
        except Exception as e:
            await self.log(f"Fix generation failed (all providers): {e}")
            return False

    async def _apply_fix(self, raw: str) -> None:
        import json
        import re

        text = raw.strip()
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return
        data = json.loads(match.group())
        rel = data.get("file", "package.json")
        content = data.get("content", "")
        if not content:
            return
        target = self.project_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
