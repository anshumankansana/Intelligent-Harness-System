"""GitHub-only publish — no Vercel, npm build, or deploy steps."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Awaitable, Callable, Optional

from harness.deployment.github_ops import GitHubAutomation
from harness.naming import get_repo_slug
from harness.run_state import load_state, save_state

LogFn = Callable[[str], Awaitable[None]]


async def _print_log(msg: str) -> None:
    print(msg.encode("utf-8", errors="replace").decode("utf-8", errors="replace"), flush=True)


async def publish_run_to_github(
    run_id: str,
    workspace_root: Path,
    github_token: str,
    log: LogFn | None = None,
) -> dict:
    """
    Create/push GitHub repo for workspace/{run_id}/generated only.
    Does not call Vercel or run npm build.
    """
    log_fn = log or _print_log
    if not github_token:
        return {"ok": False, "error": "GITHUB_TOKEN not set in backend .env"}

    run_dir = Path(workspace_root) / run_id
    project_dir = run_dir / "generated"
    if not project_dir.is_dir() or not any(project_dir.iterdir()):
        msg = f"No generated project at {project_dir}"
        await log_fn(f"[ERR] {msg}")
        return {"ok": False, "error": msg}

    state = load_state(run_dir) or {"run_id": run_id}
    repo_name = get_repo_slug(run_dir, run_id)
    prior_stage = state.get("stage", "ready_to_publish")

    state["stage"] = "publishing_github"
    save_state(run_dir, state)

    await log_fn(f"[INFO] GitHub publish only (no Vercel) — repo '{repo_name}'...")

    gh = GitHubAutomation(github_token, log_fn)
    url: Optional[str] = await gh.push_project(project_dir, repo_name)

    if not url:
        state["stage"] = prior_stage if prior_stage != "publishing_github" else "ready_to_publish"
        save_state(run_dir, state)
        return {"ok": False, "error": "GitHub push failed — see logs"}

    state["github_url"] = url
    state["repo_slug"] = repo_name
    # Stay ready to publish until user explicitly deploys; preserve complete if already live
    if prior_stage == "complete":
        state["stage"] = "complete"
    else:
        state["stage"] = "ready_to_publish"
    save_state(run_dir, state)

    await log_fn(f"[OK] GitHub published: {url}")
    return {"ok": True, "github_url": url, "repo_slug": repo_name}


def publish_run_to_github_sync(
    run_id: str,
    workspace_root: Path | str,
    github_token: str,
) -> dict:
    return asyncio.run(
        publish_run_to_github(run_id, Path(workspace_root), github_token, log=_print_log)
    )
