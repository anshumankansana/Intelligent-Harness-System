import re
from typing import Optional


def _base_slug(text: str, max_len: int = 48) -> str:
    s = (text or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    if not s:
        return "harness-project"
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s


def repo_slug_from_title(title: str, run_id: str) -> str:
    """GitHub/Vercel project name: human title + short id for uniqueness."""
    base = _base_slug(title, 40)
    short = (run_id or "")[:6]
    if short:
        return f"{base}-{short}"[: 100]
    return base[:100]


def zip_filename_from_title(title: str, run_id: str = "") -> str:
    """Download filename e.g. todo-app.zip"""
    base = _base_slug(title, 60) or "project"
    if run_id:
        return f"{base}.zip"
    return f"{base}.zip"


def title_from_user_idea(user_idea: str) -> str:
    line = (user_idea or "").strip().split("\n")[0].strip()
    return line[:80] if line else "Untitled project"


def get_repo_slug(run_dir, run_id: str) -> str:
    from harness.run_state import load_state

    state = load_state(run_dir) or {}
    if state.get("repo_slug"):
        return state["repo_slug"]
    raw = state.get("project_title") or state.get("user_idea", "")
    title = raw if len(raw) <= 80 else title_from_user_idea(raw)
    return repo_slug_from_title(title, run_id)
