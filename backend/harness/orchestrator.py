import asyncio
import shutil
import uuid
from pathlib import Path
from typing import Callable, Dict, List, Optional

from harness.approvals.gate import ApprovalGate
from harness.context.manager import HarnessContext
from harness.debate.agents import DebateSystem
from harness.deployment.deploy_service import deploy_generated_project, deploy_run
from harness.deployment.github_publish_service import publish_run_to_github
from harness.execution.builder import BuilderEngine
from harness.fallback.gate import GEMINI_FAILURE_CHAIN, FAST_FAILURE_CHAIN, ProviderFallbackGate
from harness.memory.store import MarkdownMemoryStore
from harness.planner.engine import PlannerEngine
from harness.providers.base import ProviderRole
from harness.providers.factory import ProviderExhaustedError, ProviderFactory
from harness.retries.fix_loop import RetryFixLoop
from harness.run_state import load_state, save_state
from harness.validation.harness import ValidationHarness


class HarnessOrchestrator:
    def __init__(
        self,
        workspace: Path,
        factory: ProviderFactory,
        approval_gate: ApprovalGate,
        fallback_gate: ProviderFallbackGate,
        broadcast_log: Callable,
        broadcast_debate: Optional[Callable] = None,
        github_token: str = "",
        vercel_token: str = "",
        vercel_scope: str = "",
    ):
        self.workspace = workspace
        self.factory = factory
        self.approval_gate = approval_gate
        self.fallback_gate = fallback_gate
        self.broadcast_log = broadcast_log
        self.broadcast_debate = broadcast_debate
        self.github_token = github_token
        self.vercel_token = vercel_token
        self.vercel_scope = vercel_scope
        self.runs: Dict[str, HarnessContext] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    async def log(self, run_id: str, message: str) -> None:
        await self.broadcast_log(run_id, message)

    def _run_dir(self, run_id: str) -> Path:
        d = self.workspace / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _set_stage(self, run_id: str, stage: str, **extra) -> None:
        run_dir = self._run_dir(run_id)
        state = load_state(run_dir) or {"run_id": run_id}
        state["stage"] = stage
        state.update(extra)
        save_state(run_dir, state)

    def _get_checkpoint(self, run_id: str) -> dict:
        state = load_state(self._run_dir(run_id)) or {}
        return state.get("checkpoint", {})

    def _set_checkpoint(self, run_id: str, checkpoint: dict) -> None:
        run_dir = self._run_dir(run_id)
        state = load_state(run_dir) or {"run_id": run_id}
        state["checkpoint"] = checkpoint
        save_state(run_dir, state)

    def _spawn(self, run_id: str, coro) -> None:
        if run_id in self._tasks and not self._tasks[run_id].done():
            return
        self._tasks[run_id] = asyncio.create_task(coro)

    def _repo_name(self, run_id: str) -> str:
        from harness.naming import get_repo_slug

        return get_repo_slug(self._run_dir(run_id), run_id)

    async def start_run(
        self,
        user_idea: str,
        provider_keys: Dict[str, str],
        project_title: str = "",
        document_text: str = "",
        document_name: str = "",
    ) -> str:
        from harness.document_reader import merge_brief
        from harness.naming import repo_slug_from_title, title_from_user_idea

        combined = merge_brief(user_idea, document_text, document_name)
        if not combined.strip():
            raise ValueError("Provide a project description or upload a Word (.docx) brief")

        run_id = str(uuid.uuid4())[:8]
        self.factory.keys.update({k: v for k, v in provider_keys.items() if v})
        title = (project_title or "").strip() or title_from_user_idea(combined)
        slug = repo_slug_from_title(title, run_id)
        run_dir = self._run_dir(run_id)
        if document_text.strip():
            from harness.document_reader import persist_brief_markdown

            persist_brief_markdown(run_dir, document_text, document_name, user_idea)

        ctx = HarnessContext(run_id=run_id, user_idea=combined)
        self.runs[run_id] = ctx
        extra: dict = {
            "user_idea": combined,
            "project_title": title,
            "repo_slug": slug,
        }
        if document_name:
            extra["source_document"] = document_name
        self._set_stage(run_id, "planning", **extra)
        if document_name:
            await self.log(
                run_id,
                f"Using Word brief: {document_name}"
                + (f" + typed notes" if user_idea.strip() else ""),
            )
        self._spawn(run_id, self._execute_pipeline(run_id))
        return run_id

    def _ctx(self, run_id: str) -> HarnessContext:
        if run_id not in self.runs:
            state = load_state(self._run_dir(run_id)) or {}
            self.runs[run_id] = HarnessContext(
                run_id=run_id,
                user_idea=state.get("user_idea", ""),
                human_edits=state.get("human_edits", ""),
                human_instructions=state.get("human_instructions", ""),
                approval_status=state.get("approval_status", "pending"),
                debate_summary=state.get("debate_summary", ""),
                github_url=state.get("github_url", ""),
                deploy_url=state.get("deploy_url", ""),
            )
        return self.runs[run_id]

    async def _run_planner_with_fallback(
        self,
        run_id: str,
        memory: MarkdownMemoryStore,
        log,
        user_idea: str,
        human_context: str,
        step: str = "planning",
    ) -> None:
        """Planner with automatic provider rotation (gemini → openrouter → groq)."""
        planner = PlannerEngine(self.factory, memory, log, run_id=run_id)
        cp = self._get_checkpoint(run_id)
        if cp.get("step") == step and cp.get("chain"):
            planner.set_fallback_chain(cp["chain"])
        await planner.run(user_idea, human_context)
        self.fallback_gate.clear(run_id)
        self.factory.clear_fallback_chain(run_id)

    async def _pause_for_fallback(
        self, run_id: str, step: str, err: ProviderExhaustedError
    ) -> bool:
        """Auto-continue with the next provider chain — no manual Continue click."""
        chain = err.chain or []
        if not chain:
            await self.log(
                run_id,
                f"All providers failed at '{step}' ({err.provider}: {err}). "
                "Add API keys in Environment / backend .env and start a new run.",
            )
            return False

        self.fallback_gate.create(
            run_id, step, err.provider, str(err), fallback_chain=chain
        )
        self.fallback_gate.mark_continued(run_id)
        self.factory.set_fallback_chain(run_id, chain)
        self._set_stage(
            run_id,
            step,
            checkpoint={"step": step, "failed_provider": err.provider, "chain": chain},
        )
        await self.log(
            run_id,
            f"{err.provider} failed at '{step}' — auto-continuing with: {' → '.join(chain)}",
        )
        task = self._tasks.get(run_id)
        if task is None or task.done():
            self._spawn(run_id, self._resume_from_checkpoint(run_id))
        return True

    async def on_fallback_continue(self, run_id: str) -> None:
        req = self.fallback_gate.get(run_id)
        if not req:
            return
        self.fallback_gate.mark_continued(run_id)
        chain = req.fallback_chain
        self.factory.set_fallback_chain(run_id, chain)
        await self.log(
            run_id,
            f"Continuing with fallback providers: {' → '.join(chain)}",
        )
        task = self._tasks.get(run_id)
        if task is None or task.done():
            self._spawn(run_id, self._resume_from_checkpoint(run_id))

    async def on_approval(
        self,
        run_id: str,
        action: str,
        human_edits: str,
        human_instructions: str,
        import_intent: str = "",
        document_edits: dict | None = None,
        document_instructions: dict | None = None,
    ) -> None:
        action = action.strip().lower()
        if action in ("approve", "approved"):
            action = "approved"
        elif action in ("reject", "rejected"):
            action = "rejected"

        run_dir = self._run_dir(run_id)
        memory = MarkdownMemoryStore(run_dir)

        if document_edits:
            for fname, content in document_edits.items():
                if fname.endswith(".md") and content and content.strip():
                    memory.write(fname, content.strip())

        combined_instructions = human_instructions or ""
        if document_instructions:
            parts = [combined_instructions] if combined_instructions.strip() else []
            for fname, text in document_instructions.items():
                if text and str(text).strip():
                    parts.append(f"### Instructions for {fname}\n{text.strip()}")
            combined_instructions = "\n\n".join(parts)

        if not human_edits.strip() and document_edits:
            human_edits = memory.build_context_block()

        ctx = self._ctx(run_id)
        ctx.approval_status = action
        ctx.human_edits = human_edits
        ctx.human_instructions = combined_instructions
        extra: dict = {
            "human_edits": human_edits,
            "human_instructions": combined_instructions,
            "approval_status": ctx.approval_status,
        }
        if import_intent:
            extra["import_intent"] = import_intent
        self._set_stage(
            run_id,
            "approved" if "approved" in action else "rejected",
            **extra,
        )
        state = load_state(self._run_dir(run_id)) or {}
        stage = state.get("stage", "")
        task = self._tasks.get(run_id)
        if task is None or task.done():
            if "approved" in action and stage in ("awaiting_approval", "approved"):
                await self.log(run_id, "Resuming harness after approval...")
                self._spawn(run_id, self._continue_after_approval(run_id))

    def _pipeline_progress_stage(self, run_dir: Path, state: dict) -> str:
        """Where the run actually is on disk — avoid restarting debate/approval after fallback."""
        mem = run_dir / "memory"
        gen = run_dir / "generated"
        approval = (state.get("approval_status") or "").lower()
        has_generated = gen.exists() and any(gen.iterdir())
        has_debate = (mem / "DEBATE_SUMMARY.md").exists()

        if approval in ("approved", "approve") and has_generated:
            return "validating"
        if approval in ("approved", "approve"):
            return "building"
        if has_debate:
            return "awaiting_approval"
        return "planning"

    async def _resume_from_checkpoint(self, run_id: str) -> None:
        ctx = self._ctx(run_id)
        run_dir = self._run_dir(run_id)
        memory = MarkdownMemoryStore(run_dir)
        log = lambda msg: self.log(run_id, msg)
        cp = self._get_checkpoint(run_id)
        step = cp.get("step", "planning")
        chain: List[str] = cp.get("chain", GEMINI_FAILURE_CHAIN)

        try:
            state = load_state(run_dir) or {}
            mode = state.get("project_mode", "new")
            if step == "planning":
                progress = self._pipeline_progress_stage(run_dir, state)
                if progress == "awaiting_approval" and mode != "update":
                    approval = (state.get("approval_status") or "").lower()
                    if approval in ("approved", "approve"):
                        await self.log(run_id, "Resuming build (already approved).")
                        await self._build_validate_deploy(run_id, ctx, run_dir, memory, log)
                        return
                    self._set_stage(run_id, "awaiting_approval", approval_status="pending")
                    await self.log(
                        run_id,
                        "Resuming at approval (debate already done — not re-running planner).",
                    )
                    await self._wait_for_approval(run_id, ctx)
                    if ctx.approval_status == "rejected":
                        self._set_stage(run_id, "rejected")
                        return
                    await self._build_validate_deploy(run_id, ctx, run_dir, memory, log)
                    return
                if progress == "building" and mode != "update":
                    self._set_stage(run_id, "building")
                    await self.log(run_id, "Resuming build after provider fallback…")
                    await self._build_validate_deploy(run_id, ctx, run_dir, memory, log)
                    return
                if progress == "validating" and mode != "update":
                    self._set_stage(run_id, "validating")
                    await self.log(run_id, "Resuming validation after provider fallback…")
                    await self._validate_and_deploy(run_id, ctx, run_dir, log)
                    return

                idea = state.get("user_idea") or ctx.user_idea
                if mode == "update" and not idea.strip().upper().startswith("UPDATE"):
                    idea = await self._build_update_idea(run_id, ctx, run_dir)
                    ctx.user_idea = idea
                await self._run_planner_with_fallback(
                    run_id,
                    memory,
                    log,
                    idea,
                    ctx.inject_human_context(),
                    step="planning",
                )
                if not (run_dir / "memory" / "DEBATE_SUMMARY.md").exists() or mode == "update":
                    await self._run_debate_and_approval(run_id, ctx, run_dir, memory, log)
                elif self._pipeline_progress_stage(run_dir, load_state(run_dir) or {}) == "awaiting_approval":
                    self._set_stage(run_id, "awaiting_approval", approval_status="pending")
                    await self._wait_for_approval(run_id, ctx)
                    if ctx.approval_status != "rejected":
                        await self._build_validate_deploy(run_id, ctx, run_dir, memory, log)
                else:
                    await self._build_validate_deploy(run_id, ctx, run_dir, memory, log)
            elif step == "building":
                self._set_stage(run_id, "building")
                builder = BuilderEngine(self.factory, run_dir / "generated", log, run_id=run_id)
                builder.set_fallback_chain(chain)
                await builder.run(ctx.inject_human_context(), memory.build_context_block())
                self.fallback_gate.clear(run_id)
                self.factory.clear_fallback_chain(run_id)
                await self._validate_and_deploy(run_id, ctx, run_dir, log)
            elif step == "validating":
                self._set_stage(run_id, "validating")
                await self._validate_and_deploy(run_id, ctx, run_dir, log)
        except (ProviderExhaustedError, ValueError) as e:
            if not await self._pause_for_fallback(run_id, step, e if isinstance(e, ProviderExhaustedError) else ProviderExhaustedError("none", step, str(e), [])):
                self._set_stage(run_id, "error", error=str(e))
        except Exception as e:
            self._set_stage(run_id, "error", error=str(e))
            await self.log(run_id, f"Harness error: {e}")

    async def _execute_pipeline(self, run_id: str) -> None:
        ctx = self._ctx(run_id)
        run_dir = self._run_dir(run_id)
        memory = MarkdownMemoryStore(run_dir)
        log = lambda msg: self.log(run_id, msg)

        try:
            self._set_stage(run_id, "planning")
            await self._run_planner_with_fallback(
                run_id,
                memory,
                log,
                ctx.user_idea,
                ctx.inject_human_context(),
                step="planning",
            )
            await self._run_debate_and_approval(run_id, ctx, run_dir, memory, log)
        except (ProviderExhaustedError, ValueError) as e:
            err = e if isinstance(e, ProviderExhaustedError) else ProviderExhaustedError("none", "planning", str(e), [])
            if not await self._pause_for_fallback(run_id, "planning", err):
                self._set_stage(run_id, "error", error=str(e))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._set_stage(run_id, "error", error=str(e))
            await self.log(run_id, f"Harness error: {e}")

    async def _run_debate_and_approval(self, run_id, ctx, run_dir, memory, log):
        self._set_stage(run_id, "debate")
        arch = memory.read("ARCHITECTURE.md") or ""

        async def debate_emit(event: str, data: dict) -> None:
            if self.broadcast_debate:
                await self.broadcast_debate(run_id, event, data)

        debate = DebateSystem(self.factory, log, emit=debate_emit, run_id=run_id)
        ctx.debate_summary = await debate.run(arch, run_dir=run_dir)
        memory.write("DEBATE_SUMMARY.md", ctx.debate_summary)

        debate_block = ctx.debate_summary
        plan_for_approval = (
            f"# Package for Human Approval\n\n"
            f"## Debate outcome & action items\n{debate_block}\n\n"
            f"## Engineering memory\n{memory.build_context_block()}"
        )
        self.approval_gate.create(run_id, "post_debate", plan_for_approval)
        self._set_stage(run_id, "awaiting_approval", approval_status="pending")
        await self.log(run_id, "Awaiting human approval — open Approval Center and click Approve.")
        await self._wait_for_approval(run_id, ctx)

        if ctx.approval_status == "rejected":
            self._set_stage(run_id, "rejected")
            await self.log(run_id, "Run rejected by human.")
            return

        await self._build_validate_deploy(run_id, ctx, run_dir, memory, log)

    async def _continue_after_approval(self, run_id: str) -> None:
        ctx = self._ctx(run_id)
        run_dir = self._run_dir(run_id)
        memory = MarkdownMemoryStore(run_dir)
        log = lambda msg: self.log(run_id, msg)
        req = self.approval_gate.get(run_id)
        if req:
            ctx.approval_status = req.status
            ctx.human_edits = req.human_edits
            ctx.human_instructions = req.human_instructions
        if ctx.approval_status == "rejected":
            return
        await self.log(run_id, "Human approved — continuing workflow.")
        self._set_stage(run_id, "building")
        state = load_state(run_dir) or {}
        mode = state.get("project_mode", "new")
        intent = state.get("import_intent", "")
        try:
            if mode == "import" and intent == "deploy_only":
                await self._import_deploy_only(run_id, ctx, run_dir, log)
            elif mode == "update":
                await self._build_validate_deploy(run_id, ctx, run_dir, memory, log)
            else:
                await self._build_validate_deploy(run_id, ctx, run_dir, memory, log)
        except (ProviderExhaustedError, ValueError) as e:
            err = e if isinstance(e, ProviderExhaustedError) else ProviderExhaustedError("none", "building", str(e), [])
            if not await self._pause_for_fallback(run_id, "building", err):
                self._set_stage(run_id, "error", error=str(e))
        except Exception as e:
            self._set_stage(run_id, "error", error=str(e))
            await self.log(run_id, f"Harness error: {e}")

    async def _build_validate_deploy(self, run_id, ctx, run_dir, memory, log):
        self._set_stage(run_id, "building")
        project_dir = run_dir / "generated"
        project_dir.mkdir(exist_ok=True)
        builder = BuilderEngine(self.factory, project_dir, log, run_id=run_id)
        await builder.run(ctx.inject_human_context(), memory.build_context_block())
        self.fallback_gate.clear(run_id)
        self.factory.clear_fallback_chain(run_id)
        await self._validate_and_deploy(run_id, ctx, run_dir, log)

    async def _validate_and_deploy(self, run_id, ctx, run_dir, log):
        project_dir = run_dir / "generated"
        self._set_stage(run_id, "validating")
        validator = ValidationHarness(project_dir, log)
        fix_loop = RetryFixLoop(self.factory, project_dir, log)

        passed, logs = await validator.run_all()
        ctx.validation_logs.append(logs)

        while not passed and ctx.retry_count < 2:
            ctx.retry_count += 1
            fixed = await fix_loop.analyze_and_fix(logs)
            if not fixed:
                break
            passed, logs = await validator.run_all()
            ctx.validation_logs.append(logs)

        if not passed:
            await self.log(
                run_id,
                "Validation had issues — auto-continuing to publish (you can still deploy from the dashboard).",
            )
            self.fallback_gate.clear(run_id)
        else:
            await self.log(run_id, "Validation passed.")

        self._set_stage(run_id, "ready_to_publish")
        await self.log(
            run_id,
            "Build validated. Click Post to GitHub or Deploy in the dashboard when ready — not automatic.",
        )

    async def _wait_for_approval(self, run_id: str, ctx: HarnessContext) -> None:
        for _ in range(3600):
            req = self.approval_gate.get(run_id)
            status = (req.status if req else "") or ""
            if status in ("approved", "rejected", "approve"):
                normalized = "approved" if "approv" in status else "rejected"
                ctx.approval_status = normalized
                if req:
                    ctx.human_edits = req.human_edits
                    ctx.human_instructions = req.human_instructions
                if normalized == "approved":
                    await self.log(run_id, "Human approved — continuing workflow.")
                return
            await asyncio.sleep(1)

    def get_context(self, run_id: str) -> Optional[HarnessContext]:
        return self.runs.get(run_id) or (
            self._ctx(run_id) if load_state(self._run_dir(run_id)) else None
        )

    def get_stage(self, run_id: str) -> str:
        state = load_state(self._run_dir(run_id))
        return state.get("stage", "unknown") if state else "unknown"

    async def start_import_run(
        self,
        title: str,
        description: str,
        zip_path: Path,
        provider_keys: Dict[str, str],
    ) -> str:
        run_id = str(uuid.uuid4())[:8]
        self.factory.keys.update({k: v for k, v in provider_keys.items() if v})
        run_dir = self._run_dir(run_id)
        gen = run_dir / "generated"
        gen.mkdir(parents=True, exist_ok=True)

        from harness.zip_utils import flatten_single_root_folder, safe_extract_zip

        safe_extract_zip(zip_path, gen)
        flatten_single_root_folder(gen)
        zip_path.unlink(missing_ok=True)

        from harness.naming import repo_slug_from_title

        display_title = (title or "").strip() or "Imported project"
        slug = repo_slug_from_title(display_title, run_id)
        ctx = HarnessContext(run_id=run_id, user_idea=description or display_title)
        self.runs[run_id] = ctx
        self._set_stage(
            run_id,
            "planning",
            user_idea=description or display_title,
            project_title=display_title,
            repo_slug=slug,
            project_mode="import",
            import_intent="",
        )
        self._spawn(run_id, self._execute_import_pipeline(run_id, title, description))
        return run_id

    async def _execute_import_pipeline(self, run_id: str, title: str, description: str) -> None:
        ctx = self._ctx(run_id)
        run_dir = self._run_dir(run_id)
        memory = MarkdownMemoryStore(run_dir)
        log = lambda msg: self.log(run_id, msg)
        try:
            from harness.import_analyzer import ImportAnalyzer

            self._set_stage(run_id, "building")
            await self.log(run_id, "Analyzing imported project for debate & approval...")
            analyzer = ImportAnalyzer(self.factory, memory, log, run_id=run_id)
            await analyzer.analyze(run_dir / "generated", description or title)
            await self._run_debate_and_approval(run_id, ctx, run_dir, memory, log)
        except Exception as e:
            self._set_stage(run_id, "error", error=str(e))
            await self.log(run_id, f"Import pipeline error: {e}")

    async def _import_deploy_only(self, run_id, ctx, run_dir, log) -> None:
        project_dir = run_dir / "generated"
        if project_dir.exists() and (project_dir / "package.json").exists():
            self._set_stage(run_id, "validating")
            validator = ValidationHarness(project_dir, log)
            passed, _ = await validator.run_all()
            if not passed:
                await self.log(run_id, "Validation had issues — you can still publish or fix files.")
        self._set_stage(run_id, "ready_to_publish")
        await self.log(run_id, "Import approved (deploy only). Use Deploy / Post to GitHub when ready.")

    async def start_update_run(
        self,
        run_id: str,
        update_instructions: str,
        provider_keys: Optional[Dict[str, str]] = None,
        document_text: str = "",
        document_name: str = "",
    ) -> None:
        from harness.document_reader import merge_brief

        combined_instructions = merge_brief(
            update_instructions, document_text, document_name
        )
        if not combined_instructions.strip():
            raise ValueError("Provide update instructions or upload a Word (.docx) brief")

        if provider_keys:
            self.factory.keys.update({k: v for k, v in provider_keys.items() if v})
        ctx = self._ctx(run_id)
        run_dir = self._run_dir(run_id)
        ctx.human_instructions = combined_instructions
        if document_text.strip():
            from harness.document_reader import persist_brief_markdown

            persist_brief_markdown(
                run_dir, document_text, document_name, update_instructions
            )
        self.fallback_gate.clear(run_id)
        self.factory.clear_fallback_chain(run_id)
        extra: dict = {
            "project_mode": "update",
            "update_instructions": combined_instructions,
            "approval_status": "",
        }
        if document_name:
            extra["update_document"] = document_name
            extra["update_document_text"] = document_text[:8000]
        self._set_stage(run_id, "planning", **extra)
        self.approval_gate.clear(run_id)
        preview = combined_instructions[:120].replace("\n", " ")
        await self.log(
            run_id,
            f"Update started: {preview}…"
            + (f" (includes {document_name})" if document_name else ""),
        )
        self._spawn(run_id, self._execute_update_pipeline(run_id))

    async def _build_update_idea(self, run_id: str, ctx: HarnessContext, run_dir: Path) -> str:
        from harness.zip_utils import list_project_tree

        state = load_state(run_dir) or {}
        instructions = state.get("update_instructions", ctx.human_instructions)
        tree = list_project_tree(run_dir / "generated")
        original = state.get("user_idea", ctx.user_idea)
        doc_name = state.get("update_document", "")
        doc_block = ""
        if doc_name and state.get("update_document_text"):
            doc_block = (
                f"\n\nAttached update document ({doc_name}):\n"
                f"{state.get('update_document_text', '')[:12000]}"
            )
        return (
            f"UPDATE existing deployed project.\n"
            f"User instructions: {instructions}{doc_block}\n\n"
            f"Current file tree:\n{tree}\n\n"
            f"Original idea: {original}"
        )

    async def _execute_update_pipeline(self, run_id: str) -> None:
        ctx = self._ctx(run_id)
        run_dir = self._run_dir(run_id)
        memory = MarkdownMemoryStore(run_dir)
        log = lambda msg: self.log(run_id, msg)
        try:
            update_idea = await self._build_update_idea(run_id, ctx, run_dir)
            ctx.user_idea = update_idea
            self._set_stage(
                run_id,
                "planning",
                user_idea=update_idea,
                project_mode="update",
            )
            await self._run_planner_with_fallback(
                run_id,
                memory,
                log,
                update_idea,
                ctx.inject_human_context(),
                step="planning",
            )
            await self._run_debate_and_approval(run_id, ctx, run_dir, memory, log)
        except (ProviderExhaustedError, ValueError) as e:
            err = e if isinstance(e, ProviderExhaustedError) else ProviderExhaustedError("none", "planning", str(e), [])
            if not await self._pause_for_fallback(run_id, "planning", err):
                self._set_stage(run_id, "error", error=str(e))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._set_stage(run_id, "error", error=str(e))
            await self.log(run_id, f"Update pipeline error: {e}")

    async def publish_github(self, run_id: str) -> dict:
        """GitHub only — does not deploy to Vercel."""
        workspace_root = self._run_dir(run_id).parent
        result = await publish_run_to_github(
            run_id,
            workspace_root,
            self.github_token,
            log=lambda msg: self.log(run_id, msg),
        )
        if result.get("ok"):
            ctx = self._ctx(run_id)
            ctx.github_url = result["github_url"]
        return result

    async def publish_deploy(self, run_id: str) -> dict:
        """Vercel only — does not push to GitHub."""
        if not self.vercel_token:
            return {"ok": False, "error": "VERCEL_TOKEN not set in backend .env"}
        workspace_root = self._run_dir(run_id).parent
        result = await deploy_run(
            run_id,
            workspace_root,
            self.vercel_token,
            log=lambda msg: self.log(run_id, msg),
            vercel_scope=self.vercel_scope,
        )
        if result.get("ok"):
            ctx = self._ctx(run_id)
            ctx.deploy_url = result["deploy_url"]
        return result

    def project_zip_bytes(self, run_id: str) -> bytes | None:
        from harness.zip_utils import build_zip_bytes

        gen = self._run_dir(run_id) / "generated"
        if not gen.is_dir() or not any(gen.iterdir()):
            return None
        return build_zip_bytes(gen)

    async def redeploy_vercel(self, run_id: str) -> dict:
        """Redeploy generated app to Vercel (fixes stub/404 URLs from earlier runs)."""
        run_dir = self._run_dir(run_id)
        project_dir = run_dir / "generated"
        if not project_dir.is_dir():
            return {"ok": False, "error": "No generated project found for this run."}
        if not self.vercel_token:
            return {"ok": False, "error": "VERCEL_TOKEN is not set in backend .env"}

        ctx = self._ctx(run_id)
        state = load_state(run_dir) or {}
        github_url = ctx.github_url or state.get("github_url", "")

        async def log(msg: str) -> None:
            await self.log(run_id, msg)

        await log("Redeploying to Vercel...")
        from harness.deployment.deploy_service import deploy_run

        workspace_root = run_dir.parent
        result = await deploy_run(
            run_id,
            workspace_root,
            self.vercel_token,
            log=log,
            vercel_scope=self.vercel_scope,
        )
        if not result.get("ok"):
            return {"ok": False, "error": result.get("error", "Vercel deployment failed — check logs.")}

        url = result["deploy_url"]
        ctx.deploy_url = url
        self._set_stage(run_id, "complete", github_url=github_url, deploy_url=url)
        await log(f"Redeploy complete: {url}")
        return {"ok": True, "deploy_url": url}

    async def delete_run(self, run_id: str) -> bool:
        """Cancel task, clear gates, remove workspace data."""
        task = self._tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.pop(run_id, None)
        self.runs.pop(run_id, None)
        self.approval_gate.clear(run_id)
        self.fallback_gate.clear(run_id)
        self.factory.clear_fallback_chain(run_id)

        run_dir = self._run_dir(run_id)
        if run_dir.exists():
            shutil.rmtree(run_dir, ignore_errors=True)
            return True
        return False
