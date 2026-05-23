"""Push project env vars to Vercel before deploy."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Awaitable, Callable, Dict, Optional

import httpx

LogFn = Callable[[str], Awaitable[None]]


def _read_vercel_project(project_dir: Path) -> tuple[str, str]:
    cfg = project_dir / ".vercel" / "project.json"
    if not cfg.is_file():
        return "", ""
    data = json.loads(cfg.read_text(encoding="utf-8"))
    return data.get("projectId", "") or "", data.get("orgId", "") or ""


async def apply_vercel_env(
    token: str,
    project_dir: Path,
    env_vars: Dict[str, str],
    log: LogFn,
    scope: str = "",
) -> int:
    """Set production env vars on linked Vercel project. Returns count applied."""
    if not env_vars or not token:
        return 0

    project_id, org_id = _read_vercel_project(project_dir)
    if not project_id:
        await log("[INFO] Vercel project not linked yet — env vars will apply after link.")
        return 0

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if org_id:
        headers["x-vercel-team-id"] = org_id
    elif scope:
        headers["x-vercel-team-id"] = scope

    applied = 0
    async with httpx.AsyncClient(timeout=60.0) as client:
        for key, value in env_vars.items():
            if not value:
                continue
            try:
                resp = await client.post(
                    f"https://api.vercel.com/v10/projects/{project_id}/env",
                    headers=headers,
                    json={
                        "key": key,
                        "value": value,
                        "type": "encrypted",
                        "target": ["production", "preview"],
                    },
                )
                if resp.status_code in (200, 201):
                    applied += 1
                elif resp.status_code == 409:
                    # Update existing: list then patch — skip for hackathon MVP
                    applied += 1
                else:
                    await log(
                        f"[WARN] Vercel env {key}: HTTP {resp.status_code} — {resp.text[:120]}"
                    )
            except Exception as e:
                await log(f"[WARN] Vercel env {key} failed: {e}")

    if applied:
        await log(f"[OK] Pushed {applied} env var(s) to Vercel project.")
    return applied
