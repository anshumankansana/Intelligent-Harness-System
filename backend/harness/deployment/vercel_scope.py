"""Resolve Vercel team scope for non-interactive CLI deploys."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

import httpx

# Default team slug from this account (used if API lookup fails).
_FALLBACK_SCOPE = "anshumans-projects-671c73a5"


def scope_from_project_json(project_dir: Path) -> Optional[str]:
    """Reserved — CLI --scope needs team slug from API/env, not project.json alone."""
    del project_dir
    return None


def scope_from_cli_json_output(output: str) -> Optional[str]:
    """Parse missing_scope JSON from vercel CLI stderr/stdout."""
    try:
        if '"missing_scope"' in output or '"choices"' in output:
            blob = output[output.find("{") : output.rfind("}") + 1]
            data = json.loads(blob)
            choices = data.get("choices") or []
            if choices:
                return choices[0].get("name") or choices[0].get("id")
    except (json.JSONDecodeError, ValueError):
        pass
    m = re.search(r'"name":\s*"(anshumans-[^"]+)"', output)
    if m:
        return m.group(1)
    m = re.search(r"--scope\s+([a-z0-9-]+)", output)
    if m:
        return m.group(1)
    return None


def fetch_vercel_scope(token: str) -> str:
    """Get team slug via Vercel REST API (works with VERCEL_TOKEN only)."""
    if not token:
        return _FALLBACK_SCOPE
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get("https://api.vercel.com/v2/teams", headers=headers)
            if r.status_code == 200:
                payload = r.json()
                teams = payload.get("teams") if isinstance(payload, dict) else payload
                if isinstance(teams, list) and teams:
                    slug = teams[0].get("slug") or teams[0].get("id")
                    if slug:
                        return str(slug)
            r2 = client.get("https://api.vercel.com/v2/user", headers=headers)
            if r2.status_code == 200:
                user = r2.json().get("user") or r2.json()
                username = user.get("username")
                if username:
                    return str(username)
    except Exception:
        pass
    return _FALLBACK_SCOPE


def resolve_vercel_scope(
    token: str,
    project_dir: Path | None = None,
    env_scope: str = "",
    cli_output: str = "",
) -> str:
    scope = (env_scope or os.environ.get("VERCEL_SCOPE", "")).strip()
    if scope:
        return scope
    if cli_output:
        parsed = scope_from_cli_json_output(cli_output)
        if parsed:
            return parsed
    if project_dir:
        scope_from_project_json(project_dir)
    return fetch_vercel_scope(token)
