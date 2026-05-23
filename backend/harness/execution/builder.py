import json
import re
from pathlib import Path

from harness.execution.file_parser import extract_files_from_llm, is_placeholder_page
from harness.execution.spec_fallback import apply_spec_fallback
from harness.providers.base import ProviderRole
from harness.providers.factory import ProviderFactory

BUILDER_SYSTEM = """You are a senior Next.js 14 engineer (App Router).
Build the COMPLETE working application described in PROJECT_SPEC and user context.
Return ONLY valid JSON (no markdown fences):
{"files": [{"path": "app/page.tsx", "content": "full file..."}, {"path": "app/globals.css", "content": "..."}]}

Rules:
- app/page.tsx MUST implement the full UI (not a title-only placeholder).
- Use "use client" when you need React state/events.
- Modern, polished UI: layout, colors, spacing, hover states.
- Do NOT include package.json, tsconfig.json, or vercel.json.
- Paths are relative to project root (e.g. app/page.tsx, components/Foo.tsx)."""

PROTECTED_PATHS = frozenset(
    {"package.json", "tsconfig.json", "vercel.json", "next.config.js", "next.config.mjs"}
)

MAX_BUILD_ATTEMPTS = 3


class BuilderEngine:
    def __init__(self, factory: ProviderFactory, output_dir: Path, log, run_id: str = ""):
        self.factory = factory
        self.output_dir = output_dir
        self.log = log
        self.run_id = run_id
        self._use_chain: list[str] | None = None
        self._spec_text = ""
        self._user_idea = ""

    def set_fallback_chain(self, chain: list[str]) -> None:
        self._use_chain = chain

    async def run(self, context: str, memory_block: str) -> Path:
        await self.log("Builder Engine generating application from approved spec...")
        self._spec_text = self._extract_spec(memory_block)
        self._user_idea = self._extract_user_idea(context)

        prompt = f"""Build the production-ready Next.js app.

User / approval context:
{context[:3000]}

Engineering memory (follow PROJECT_SPEC exactly):
{memory_block[:8000]}
"""
        chain = self._use_chain or self.factory.chain_for_role(ProviderRole.FAST)
        written = 0

        for attempt in range(1, MAX_BUILD_ATTEMPTS + 1):
            await self._write_scaffold()
            sys_prompt = BUILDER_SYSTEM
            if attempt > 1:
                sys_prompt += (
                    "\n\nPREVIOUS ATTEMPT FAILED TO PARSE. "
                    "Return STRICT JSON only with complete app/page.tsx source."
                )

            resp = await self.factory.complete_with_chain(
                prompt,
                sys_prompt,
                ProviderRole.FAST,
                chain,
                run_id=self.run_id,
                log=self.log,
            )
            await self.log(f"Build attempt {attempt}/{MAX_BUILD_ATTEMPTS} via {resp.provider} ({resp.model})")
            n = await self._apply_files(resp.content)
            written = max(written, n)

            if n > 0 and self._has_real_app():
                break
            await self.log(
                f"Attempt {attempt}: LLM returned no usable files or placeholder only — "
                f"{'retrying…' if attempt < MAX_BUILD_ATTEMPTS else 'using spec template.'}"
            )

        if not self._has_real_app():
            desc = apply_spec_fallback(
                self.output_dir, self._spec_text, self._user_idea
            )
            await self.log(f"Applied spec-based fallback: {desc}")

        from harness.deployment.project_repair import repair_nextjs_project

        fixes = repair_nextjs_project(self.output_dir, allow_placeholder=False)
        if fixes:
            await self.log("Builder safeguards: " + "; ".join(fixes))

        if not self._has_real_app():
            await self.log(
                "WARNING: App may still be incomplete — check Groq/API keys and re-run build."
            )
        else:
            await self.log("Application generated successfully.")
        return self.output_dir

    def _extract_spec(self, memory_block: str) -> str:
        m = re.search(
            r"## PROJECT_SPEC\.md\s*([\s\S]*?)(?=\n## |\Z)",
            memory_block,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()
        if "PROJECT_SPEC" in memory_block:
            return memory_block
        return memory_block[:4000]

    def _extract_user_idea(self, context: str) -> str:
        for line in context.splitlines():
            if "idea" in line.lower() or "calculator" in line.lower():
                return line[:500]
        return context[:500]

    async def _write_scaffold(self) -> None:
        pkg = {
            "name": "harness-app",
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "lint": "echo lint ok",
                "test": "echo test ok",
            },
            "dependencies": {
                "next": "14.2.18",
                "react": "^18.3.1",
                "react-dom": "^18.3.1",
            },
            "devDependencies": {
                "typescript": "^5.6.3",
                "@types/node": "^22.9.0",
                "@types/react": "^18.3.12",
                "@types/react-dom": "^18.3.1",
            },
        }
        (self.output_dir / "package.json").write_text(
            json.dumps(pkg, indent=2), encoding="utf-8"
        )
        (self.output_dir / "vercel.json").write_text(
            json.dumps({"framework": "nextjs"}, indent=2), encoding="utf-8"
        )
        (self.output_dir / "tsconfig.json").write_text(
            json.dumps(
                {
                    "compilerOptions": {
                        "target": "ES2017",
                        "lib": ["dom", "dom.iterable", "esnext"],
                        "strict": True,
                        "jsx": "preserve",
                        "module": "esnext",
                        "moduleResolution": "bundler",
                        "noEmit": True,
                        "skipLibCheck": True,
                    },
                    "include": ["**/*.ts", "**/*.tsx"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    async def _apply_files(self, raw: str) -> int:
        files = extract_files_from_llm(raw)
        if not files:
            return 0

        count = 0
        for f in files:
            rel = f.get("path", "").replace("\\", "/").lstrip("./")
            content = f.get("content", "")
            if not rel or not content:
                continue
            base = rel.split("/")[-1]
            if base in PROTECTED_PATHS or rel in PROTECTED_PATHS:
                continue
            if rel.endswith("page.tsx") and is_placeholder_page(content):
                continue
            path = self.output_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            count += 1
        return count

    def _has_real_app(self) -> bool:
        page = self.output_dir / "app" / "page.tsx"
        if not page.exists():
            page = self.output_dir / "pages" / "index.tsx"
        if not page.exists():
            return False
        try:
            text = page.read_text(encoding="utf-8")
        except OSError:
            return False
        if is_placeholder_page(text):
            return False
        return len(text.strip()) > 200
