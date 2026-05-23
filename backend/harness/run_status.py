from pathlib import Path
from typing import Any, Dict, List

from harness.run_state import load_state, save_state

STAGE_LABELS = {
    "planning": "Planning — generating engineering docs",
    "debate": "Live debate — agents conversing (open Debate Room)",
    "awaiting_approval": "Awaiting your approval",
    "approved": "Approved — waiting to resume build",
    "building": "Development — generating demo app",
    "validating": "Validating — npm lint / test / build",
    "publishing_github": "Publishing to GitHub only",
    "deploying": "Deploying to Vercel only",
    "ready_to_publish": "Ready — publish when you choose",
    "complete": "Complete",
    "rejected": "Rejected by human",
    "error": "Failed",
    "validation_failed": "Validation failed",
    "awaiting_fallback": "Switching to fallback providers…",
    "unknown": "Unknown — server may have restarted",
}

# Stages where the harness is actively working — do not auto-promote to "complete" because deploy_url exists
ACTIVE_PIPELINE_STAGES = frozenset(
    {
        "planning",
        "debate",
        "awaiting_approval",
        "approved",
        "building",
        "validating",
        "validation_failed",
        "awaiting_fallback",
        "deploying",
        "publishing_github",
        "ready_to_publish",
        "rejected",
        "error",
    }
)


STAGE_PROGRESS = {
    "planning": 15,
    "debate": 35,
    "awaiting_approval": 50,
    "approved": 55,
    "building": 70,
    "validating": 85,
    "publishing_github": 92,
    "deploying": 95,
    "ready_to_publish": 90,
    "complete": 100,
    "error": 0,
    "validation_failed": 80,
    "rejected": 0,
    "unknown": 0,
}


def is_stub_deploy_url(run_id: str, deploy_url: str) -> bool:
    """Old MVP returned a guessed URL without deploying."""
    if not deploy_url:
        return False
    return deploy_url.rstrip("/") == f"https://harness-demo-{run_id}.vercel.app"


def reconcile_run_state(run_dir: Path, persist: bool = True) -> dict:
    """
    Fix stale stages (e.g. stage=deploying but deploy_url already set).
    Returns updated state dict.
    """
    state = load_state(run_dir) or {}
    run_id = run_dir.name
    deploy_url = (state.get("deploy_url") or "").strip()
    github_url = (state.get("github_url") or "").strip()
    stage = (state.get("stage") or "").strip()
    changed = False

    has_real_deploy = bool(deploy_url) and not is_stub_deploy_url(run_id, deploy_url)

    # Deploy finished but stage file still says deploying (common after Vercel CLI success)
    if has_real_deploy and stage in ("deploying", "publishing_github"):
        state["stage"] = "complete"
        stage = "complete"
        changed = True
    elif (
        has_real_deploy
        and stage not in ACTIVE_PIPELINE_STAGES
        and stage in ("", "unknown")
    ):
        state["stage"] = "complete"
        stage = "complete"
        changed = True
    elif has_real_deploy and stage == "ready_to_publish":
        state["stage"] = "complete"
        stage = "complete"
        changed = True

    if github_url and not has_real_deploy and stage == "publishing_github":
        state["stage"] = "ready_to_publish"
        stage = "ready_to_publish"
        changed = True

    if stage == "deploying" and not has_real_deploy:
        gen = run_dir / "generated"
        if gen.exists() and any(gen.iterdir()) and github_url:
            pass
        elif gen.exists() and any(gen.iterdir()) and stage == "deploying":
            pass

    if changed and persist:
        save_state(run_dir, state)

    return state


def infer_stage_from_disk(run_dir: Path) -> str:
    mem = run_dir / "memory"
    gen = run_dir / "generated"
    state = load_state(run_dir) or {}

    if not run_dir.exists():
        return "unknown"

    persisted = (state.get("stage") or "").strip()
    if persisted:
        return persisted

    deploy_url = (state.get("deploy_url") or "").strip()
    if deploy_url and not is_stub_deploy_url(run_dir.name, deploy_url):
        return "complete"

    approval = (state.get("approval_status") or "").lower()
    has_generated = gen.exists() and any(gen.iterdir())

    md_files = list(mem.glob("*.md")) if mem.exists() else []
    if len(md_files) < 3:
        if state.get("project_mode") == "import" and has_generated:
            return "building"
        return "planning"

    if not (mem / "DEBATE_SUMMARY.md").exists():
        return "debate"

    if approval in ("approved", "approve") and has_generated:
        return "building"

    if not has_generated:
        return "awaiting_approval"

    if approval in ("approved", "approve"):
        return "building"

    return "awaiting_approval"


def _stage_from_artifacts(run_dir: Path, state: dict) -> str:
    """Best-effort stage when persisted stage is stale (e.g. planning during inactive fallback)."""
    mem = run_dir / "memory"
    gen = run_dir / "generated"
    approval = (state.get("approval_status") or approval_status_from_state(state)).lower()
    has_generated = gen.exists() and any(gen.iterdir())
    deploy_url = (state.get("deploy_url") or "").strip()
    if deploy_url and not is_stub_deploy_url(run_dir.name, deploy_url):
        return "complete"
    if state.get("stage") in ("ready_to_publish", "publishing_github", "deploying"):
        return state.get("stage")
    if approval in ("approved", "approve") and has_generated:
        return state.get("stage") if state.get("stage") in ACTIVE_PIPELINE_STAGES else "ready_to_publish"
    if approval in ("approved", "approve"):
        return "building"
    if (mem / "DEBATE_SUMMARY.md").exists():
        if approval in ("rejected",):
            return "rejected"
        return "awaiting_approval"
    md_count = len(list(mem.glob("*.md"))) if mem.exists() else 0
    if md_count >= 3:
        return "debate"
    return "planning"


def approval_status_from_state(state: dict) -> str:
    return (state.get("approval_status") or "").strip()


def get_run_status(run_dir: Path, approval_status: str = "") -> Dict[str, Any]:
    state = reconcile_run_state(run_dir, persist=True)
    stage = state.get("stage") or infer_stage_from_disk(run_dir)

    # Stale "planning" on disk while artifacts show we're further along (poll was resetting UI)
    if stage == "planning":
        artifact_stage = _stage_from_artifacts(run_dir, state)
        if STAGE_PROGRESS.get(artifact_stage, 0) > STAGE_PROGRESS.get("planning", 0):
            stage = artifact_stage

    # Stage on disk wins — do not downgrade awaiting_approval because of stale "approved"
    if stage == "awaiting_approval":
        approval_status = "pending"
    elif approval_status == "rejected":
        stage = "rejected"

    deploy_url = (state.get("deploy_url") or "").strip()
    if (
        deploy_url
        and not is_stub_deploy_url(run_dir.name, deploy_url)
        and stage not in ACTIVE_PIPELINE_STAGES
    ):
        stage = "complete"

    error = state.get("error", "")
    progress = STAGE_PROGRESS.get(stage, 0)
    next_actions = _next_actions(stage, run_dir)

    return {
        "stage": stage,
        "stage_label": STAGE_LABELS.get(stage, stage),
        "progress": progress,
        "error": error,
        "user_idea": state.get("user_idea", ""),
        "next_actions": next_actions,
        "has_memory": (run_dir / "memory").exists(),
        "has_generated": (run_dir / "generated").exists(),
        "memory_files": [f.name for f in (run_dir / "memory").glob("*.md")]
        if (run_dir / "memory").exists()
        else [],
    }


def _next_actions(stage: str, run_dir: Path) -> List[Dict[str, str]]:
    actions: List[Dict[str, str]] = []

    if stage == "debate":
        actions.append({"label": "Watch live debate", "href": f"/debate?run={run_dir.name}"})
    elif stage == "awaiting_fallback":
        actions.append({"label": "View run logs", "href": f"/logs?run={run_dir.name}"})
    elif stage == "awaiting_approval":
        actions.append({"label": "Open Approval Center", "href": f"/approval?run={run_dir.name}"})
        actions.append({"label": "Review Memory", "href": "/memory"})
    elif stage in ("approved", "building", "unknown") and (run_dir / "generated").exists():
        actions.append({"label": "Resume harness (validate & deploy)", "action": "resume"})
        actions.append({"label": "View Memory", "href": "/memory"})
    elif stage == "building":
        actions.append({"label": "Resume harness", "action": "resume"})
    elif stage == "approved":
        actions.append({"label": "Resume harness", "action": "resume"})
    elif stage == "error":
        actions.append({"label": "Start new project", "href": "/new"})
    elif stage == "ready_to_publish":
        actions.append({"label": "Post to GitHub", "action": "publish_github"})
        actions.append({"label": "Deploy to Vercel", "action": "publish_deploy"})
        actions.append({"label": "Download ZIP", "action": "download_zip"})
    elif stage == "complete":
        actions.append({"label": "View deployments", "href": "/deployments"})
        actions.append({"label": "Download ZIP", "action": "download_zip"})
        actions.append({"label": "Update project", "action": "update"})
        actions.append({"label": "View memory", "href": "/memory"})
    else:
        actions.append({"label": "Start new project", "href": "/new"})

    if stage not in ("complete", "error"):
        actions.append({"label": "New project (abandon)", "href": "/new"})

    return actions
