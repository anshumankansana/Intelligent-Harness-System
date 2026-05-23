"""Shared Vercel deploy path used by CLI, orchestrator, and API."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Awaitable, Callable, Optional

from harness.deployment.project_repair import repair_nextjs_project
from harness.deployment.vercel import VercelDeployer
from harness.naming import get_repo_slug
from harness.run_env import load_project_env, write_local_env_file
from harness.run_state import load_state, save_state

LogFn = Callable[[str], Awaitable[None]]


def _console_safe(msg: str) -> str:
    return msg.encode("utf-8", errors="replace").decode("utf-8", errors="replace")


async def _print_log(msg: str) -> None:
    print(_console_safe(msg), flush=True)


async def deploy_generated_project(
    project_dir: Path,
    project_name: str,
    vercel_token: str,
    log: LogFn | None = None,
    github_repo_url: str = "",
    vercel_scope: str = "",
    project_env: dict | None = None,
) -> Optional[str]:
    """Repair, build, and deploy a generated Next.js folder. Returns production URL."""
    log_fn = log or _print_log
    deployer = VercelDeployer(vercel_token, log_fn, scope=vercel_scope)
    return await deployer.deploy(
        project_name,
        project_dir=Path(project_dir),
        github_repo_url=github_repo_url,
        project_env=project_env or {},
    )


async def deploy_run(
    run_id: str,
    workspace_root: Path,
    vercel_token: str,
    log: LogFn | None = None,
    vercel_scope: str = "",
) -> dict:
    """
    Deploy workspace/{run_id}/generated to Vercel and persist deploy_url in run_state.json.
  """
    log_fn = log or _print_log
    run_dir = Path(workspace_root) / run_id
    project_dir = run_dir / "generated"

    if not project_dir.is_dir() or not any(project_dir.iterdir()):
        msg = f"No generated project at {project_dir}"
        await log_fn(f"[ERR] {msg}")
        return {"ok": False, "error": msg}

    state = load_state(run_dir) or {"run_id": run_id}
    project_name = get_repo_slug(run_dir, run_id)

    state["stage"] = "deploying"
    save_state(run_dir, state)

    fixes = repair_nextjs_project(project_dir)
    if fixes:
        await log_fn("[INFO] " + "; ".join(fixes))

    project_env = load_project_env(run_dir)
    if project_env:
        write_local_env_file(project_dir, project_env)
        await log_fn(f"[INFO] Applied {len(project_env)} project env var(s) for build/deploy.")

    await log_fn(f"[INFO] Vercel deploy only (no GitHub) — run {run_id} as '{project_name}'...")

    try:
        url = await deploy_generated_project(
            project_dir,
            project_name,
            vercel_token,
            log=log_fn,
            github_repo_url=state.get("github_url", "") or "",
            vercel_scope=vercel_scope,
            project_env=project_env,
        )
    except Exception as e:
        state["stage"] = "ready_to_publish"
        save_state(run_dir, state)
        await log_fn(f"[ERR] Vercel deploy error: {e}")
        return {"ok": False, "error": str(e)}

    if not url:
        state["stage"] = "ready_to_publish"
        save_state(run_dir, state)
        return {"ok": False, "error": "Vercel deploy failed — see logs above"}

    state["deploy_url"] = url
    state["stage"] = "complete"
    state["repo_slug"] = project_name
    state.pop("checkpoint", None)
    save_state(run_dir, state)

    await log_fn(f"[OK] Deployed: {url}")
    return {"ok": True, "deploy_url": url, "project_name": project_name}


def deploy_run_sync(
    run_id: str,
    workspace_root: Path | str,
    vercel_token: str,
    vercel_scope: str = "",
) -> dict:
    return asyncio.run(
        deploy_run(
            run_id,
            Path(workspace_root),
            vercel_token,
            log=_print_log,
            vercel_scope=vercel_scope,
        )
    )
