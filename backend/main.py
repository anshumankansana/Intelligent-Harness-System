import asyncio
import json
from pathlib import Path
from typing import Dict, List, Set

from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from config import get_settings
from harness.approvals.gate import ApprovalGate
from harness.fallback.gate import ProviderFallbackGate
from harness.memory.store import MEMORY_FILES
from harness.orchestrator import HarnessOrchestrator
from harness.providers.factory import ProviderFactory
from harness.run_state import load_state
from harness.run_status import STAGE_PROGRESS, get_run_status, is_stub_deploy_url, reconcile_run_state

app = FastAPI(title="Intelligent Harness System", version="0.1.0")
settings = get_settings()
workspace = Path(settings.workspace_root).resolve()
workspace.mkdir(parents=True, exist_ok=True)

approval_gate = ApprovalGate()
fallback_gate = ProviderFallbackGate()
ws_clients: Dict[str, Set[WebSocket]] = {}
orchestrator: HarnessOrchestrator | None = None


def _append_log_file(run_id: str, message: str) -> None:
    log_path = workspace / run_id / "harness.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(message + "\n")


async def broadcast_log(run_id: str, message: str) -> None:
    _append_log_file(run_id, message)
    payload = json.dumps({"run_id": run_id, "message": message, "type": "log"})
    for ws in list(ws_clients.get(run_id, set())) + list(ws_clients.get("*", set())):
        try:
            await ws.send_text(payload)
        except Exception:
            pass


async def broadcast_debate(run_id: str, event: str, data: dict) -> None:
    payload = json.dumps({"run_id": run_id, "type": "debate", "event": event, "data": data})
    for ws in list(ws_clients.get(run_id, set())) + list(ws_clients.get("*", set())):
        try:
            await ws.send_text(payload)
        except Exception:
            pass


def get_orchestrator() -> HarnessOrchestrator:
    global orchestrator
    if orchestrator is None:
        factory = ProviderFactory(
            settings.provider_keys(), default=settings.default_provider
        )
        orchestrator = HarnessOrchestrator(
            workspace=workspace,
            factory=factory,
            approval_gate=approval_gate,
            fallback_gate=fallback_gate,
            broadcast_log=broadcast_log,
            broadcast_debate=broadcast_debate,
            github_token=settings.github_token,
            vercel_token=settings.vercel_token,
            vercel_scope=settings.vercel_scope,
        )
    return orchestrator


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartRunRequest(BaseModel):
    user_idea: str
    project_title: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    default_provider: str = "groq"


class ApprovalRequest(BaseModel):
    action: str
    human_edits: str = ""
    human_instructions: str = ""
    import_intent: str = ""  # deploy_only | edit_deploy | continue_build
    document_edits: dict[str, str] = {}
    document_instructions: dict[str, str] = {}


class UpdateRunRequest(BaseModel):
    instructions: str


class ProviderKeysRequest(BaseModel):
    groq_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    default_provider: str = "groq"


class RunEnvRequest(BaseModel):
    env: Dict[str, str] = {}
    use_demo_values: bool = False


@app.get("/health")
async def health():
    return {"status": "ok", "service": "intelligent-harness"}


@app.post("/api/runs/start")
async def start_run(req: StartRunRequest):
    keys = {
        "groq": req.groq_api_key or settings.groq_api_key,
        "gemini": req.gemini_api_key or settings.gemini_api_key,
        "openrouter": req.openrouter_api_key or settings.openrouter_api_key,
    }
    if req.default_provider:
        get_orchestrator().factory.default = req.default_provider
    orch = get_orchestrator()
    run_id = await orch.start_run(req.user_idea, keys, project_title=req.project_title)
    state = load_state(workspace / run_id) or {}
    return {
        "run_id": run_id,
        "status": "started",
        "project_mode": "new",
        "project_title": state.get("project_title", req.project_title),
    }


@app.post("/api/runs/start/brief")
async def start_run_with_brief(
    user_idea: str = Form(""),
    project_title: str = Form(""),
    groq_api_key: str = Form(""),
    gemini_api_key: str = Form(""),
    openrouter_api_key: str = Form(""),
    default_provider: str = Form("groq"),
    brief: UploadFile = File(...),
):
    """Start a run from a Word (.docx) brief, optionally plus typed notes."""
    from harness.brief_upload import extract_brief_upload

    try:
        doc_text, doc_name = await extract_brief_upload(brief)
    except ValueError as e:
        return {"error": str(e)}
    except RuntimeError as e:
        return {"error": str(e)}

    keys = {
        "groq": groq_api_key or settings.groq_api_key,
        "gemini": gemini_api_key or settings.gemini_api_key,
        "openrouter": openrouter_api_key or settings.openrouter_api_key,
    }
    if default_provider:
        get_orchestrator().factory.default = default_provider
    orch = get_orchestrator()
    run_id = await orch.start_run(
        user_idea,
        keys,
        project_title=project_title,
        document_text=doc_text,
        document_name=doc_name,
    )
    state = load_state(workspace / run_id) or {}
    return {
        "run_id": run_id,
        "status": "started",
        "project_mode": "new",
        "project_title": state.get("project_title", project_title),
        "source_document": doc_name,
    }


@app.post("/api/runs/import")
async def import_run(
    file: UploadFile = File(...),
    title: str = Form("Imported project"),
    description: str = Form(""),
):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        return {"error": "Upload a .zip file"}
    orch = get_orchestrator()
    run_dir = workspace / "_uploads"
    run_dir.mkdir(exist_ok=True)
    import uuid as _uuid

    zip_path = run_dir / f"import-{_uuid.uuid4().hex}.zip"
    content = await file.read()
    zip_path.write_bytes(content)
    keys = settings.provider_keys()
    run_id = await orch.start_import_run(title, description, zip_path, keys)
    return {"run_id": run_id, "status": "import_started", "project_mode": "import"}


@app.post("/api/runs/{run_id}/update")
async def update_run(run_id: str, req: UpdateRunRequest):
    run_dir = workspace / run_id
    if not run_dir.is_dir():
        return {"error": "Run not found"}
    if not req.instructions.strip():
        return {"error": "Update instructions required"}
    orch = get_orchestrator()
    keys = settings.provider_keys()
    await orch.start_update_run(run_id, req.instructions.strip(), provider_keys=keys)
    return {"status": "update_started", "run_id": run_id}


@app.post("/api/runs/{run_id}/update/brief")
async def update_run_with_brief(
    run_id: str,
    instructions: str = Form(""),
    brief: UploadFile = File(...),
):
    """Update a project using a Word (.docx) brief, optionally plus typed notes."""
    from harness.brief_upload import save_and_extract_brief

    run_dir = workspace / run_id
    if not run_dir.is_dir():
        return {"error": "Run not found"}

    try:
        doc_text, doc_name, _ = await save_and_extract_brief(brief, run_dir)
    except ValueError as e:
        return {"error": str(e)}
    except RuntimeError as e:
        return {"error": str(e)}

    if not (instructions.strip() or doc_text.strip()):
        return {"error": "Provide update notes or a Word document"}

    orch = get_orchestrator()
    keys = settings.provider_keys()
    await orch.start_update_run(
        run_id,
        instructions.strip(),
        provider_keys=keys,
        document_text=doc_text,
        document_name=doc_name,
    )
    return {
        "status": "update_started",
        "run_id": run_id,
        "source_document": doc_name,
    }


@app.post("/api/runs/{run_id}/publish/github")
async def publish_github(run_id: str):
    orch = get_orchestrator()
    return await orch.publish_github(run_id)


@app.post("/api/runs/{run_id}/publish/deploy")
async def publish_deploy(run_id: str):
    orch = get_orchestrator()
    return await orch.publish_deploy(run_id)


@app.get("/api/runs/{run_id}/download")
async def download_project(run_id: str):
    orch = get_orchestrator()
    run_dir = workspace / run_id
    data = orch.project_zip_bytes(run_id)
    if not data:
        return {"error": "No project files to download"}
    from harness.naming import zip_filename_from_title
    from harness.run_state import load_state

    state = load_state(run_dir) or {}
    title = state.get("project_title") or state.get("user_idea", "")
    filename = zip_filename_from_title(title, run_id)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.delete("/api/runs/{run_id}")
async def delete_run(run_id: str):
    orch = get_orchestrator()
    await orch.delete_run(run_id)
    return {"status": "deleted", "run_id": run_id}


def _urls_from_run(run_dir: Path, ctx) -> tuple[str, str]:
    state = load_state(run_dir) or {}
    github_url = (ctx.github_url if ctx else "") or state.get("github_url", "") or ""
    deploy_url = (ctx.deploy_url if ctx else "") or state.get("deploy_url", "") or ""
    if is_stub_deploy_url(run_dir.name, deploy_url):
        deploy_url = ""
    return github_url, deploy_url


@app.get("/api/deployments")
async def list_deployments():
    """List all workspace runs with deployment URLs (persisted in run_state.json)."""
    items = []
    for run_dir in sorted(workspace.iterdir(), key=lambda p: p.name, reverse=True):
        if not run_dir.is_dir():
            continue
        state = reconcile_run_state(run_dir, persist=True)
        github_url = state.get("github_url", "") or ""
        deploy_url = state.get("deploy_url", "") or ""
        stage = state.get("stage", "")
        if deploy_url and not is_stub_deploy_url(run_dir.name, deploy_url):
            stage = "complete"
        if not (github_url or deploy_url or stage in ("complete", "ready_to_publish")):
            continue
        idea = (state.get("user_idea", "") or "").strip()
        title = idea[:60] + ("…" if len(idea) > 60 else "") if idea else f"Run {run_dir.name}"
        deploy_stub = is_stub_deploy_url(run_dir.name, deploy_url)
        items.append(
            {
                "run_id": run_dir.name,
                "title": title,
                "stage": stage,
                "github_url": github_url,
                "deploy_url": "" if deploy_stub else deploy_url,
                "deploy_stub": deploy_stub,
                "user_idea": idea,
            }
        )
    return {"deployments": items}


@app.post("/api/runs/{run_id}/redeploy")
async def redeploy_run(run_id: str):
    orch = get_orchestrator()
    run_dir = workspace / run_id
    if not run_dir.is_dir():
        return {"ok": False, "error": "Run not found"}
    result = await orch.redeploy_vercel(run_id)
    return result


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    orch = get_orchestrator()
    ctx = orch.get_context(run_id)
    approval = approval_gate.get(run_id)
    run_dir = workspace / run_id
    disk = load_state(run_dir) or {}
    approval_status = (
        approval.status
        if approval
        else disk.get("approval_status") or (ctx.approval_status if ctx else "")
    )
    status = get_run_status(run_dir, approval_status)
    if status["stage"] == "awaiting_approval":
        approval_status = "pending"
    github_url, deploy_url = _urls_from_run(run_dir, ctx)
    fb = fallback_gate.get(run_id)
    if fb and fb.status == "pending" and fb.fallback_chain:
        cp = (load_state(run_dir) or {}).get("checkpoint", {})
        step = cp.get("step", fb.failed_step)
        chain = " → ".join(fb.fallback_chain)
        status["stage_label"] = f"Auto-fallback at {step}: {chain}"
        status["progress"] = STAGE_PROGRESS.get(step, 40)
        status["next_actions"] = [
            {"label": "View run logs", "href": f"/logs?run={run_id}"},
        ]
    return {
        "run_id": run_id,
        "stage": status["stage"],
        "stage_label": status["stage_label"],
        "progress": status["progress"],
        "error": status["error"] or (fb.error_message if fb else ""),
        "next_actions": status["next_actions"],
        "memory_files": status["memory_files"],
        "fallback": {
            "pending": fb.status == "pending" if fb else False,
            "failed_provider": fb.failed_provider if fb else "",
            "failed_step": fb.failed_step if fb else "",
            "chain": fb.fallback_chain if fb else [],
            "message": fb.error_message if fb else "",
        },
        "context": {
            "user_idea": (ctx.user_idea if ctx else "") or status.get("user_idea", ""),
            "approval_status": approval_status or "none",
            "retry_count": ctx.retry_count if ctx else 0,
            "github_url": github_url,
            "deploy_url": deploy_url,
        },
        "approval": {
            "status": approval_status or "none",
            "plan_content": (
                approval.plan_content
                if approval
                else disk.get("human_edits", "") or disk.get("approval_plan", "")
            ),
        },
        "project_mode": disk.get("project_mode", "new"),
        "import_intent": disk.get("import_intent", ""),
        "project_title": disk.get("project_title", ""),
        "repo_slug": disk.get("repo_slug", ""),
    }


@app.get("/api/runs/{run_id}/logs")
async def get_run_logs(run_id: str):
    log_path = workspace / run_id / "harness.log"
    lines = []
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    return {"run_id": run_id, "logs": lines}


def _debate_agents_payload() -> list[dict]:
    from harness.debate.profiles import DEBATE_AGENTS, MODERATOR

    profiles = [MODERATOR, *DEBATE_AGENTS]
    return [
        {
            "id": a.id,
            "name": a.name,
            "title": a.title,
            "color": a.color,
            "avatar_seed": a.avatar_seed,
            "focus": a.focus,
        }
        for a in profiles
    ]


@app.get("/api/runs/{run_id}/debate")
async def get_debate(run_id: str):
    import json as json_mod

    path = workspace / run_id / "memory" / "DEBATE_TRANSCRIPT.json"
    summary_path = workspace / run_id / "memory" / "DEBATE_SUMMARY.md"
    agents = _debate_agents_payload()
    run_dir = workspace / run_id
    state = load_state(run_dir) or {}
    stage = state.get("stage", "")
    if path.exists():
        data = json_mod.loads(path.read_text(encoding="utf-8"))
        return {
            "run_id": run_id,
            "agents": agents,
            "transcript": data.get("transcript", []),
            "action_items": data.get("action_items", []),
            "summary": summary_path.read_text(encoding="utf-8") if summary_path.exists() else "",
            "complete": True,
            "stage": stage,
            "in_progress": False,
        }
    return {
        "run_id": run_id,
        "agents": agents,
        "transcript": [],
        "action_items": [],
        "summary": "",
        "complete": False,
        "stage": stage,
        "in_progress": stage == "debate",
    }


@app.get("/api/runs/{run_id}/memory")
async def get_memory(run_id: str):
    mem_dir = workspace / run_id / "memory"
    files = {}
    if mem_dir.exists():
        for f in mem_dir.glob("*.md"):
            files[f.name] = f.read_text(encoding="utf-8")
    return {"run_id": run_id, "files": files, "expected": MEMORY_FILES}


@app.post("/api/runs/{run_id}/continue")
async def continue_fallback(run_id: str):
    """User clicked Continue after provider failure — runs openrouter → groq (if Gemini failed)."""
    fb = fallback_gate.get(run_id)
    if not fb:
        return {"error": "No pending fallback for this run"}
    orch = get_orchestrator()
    await orch.on_fallback_continue(run_id)
    return {
        "status": "continuing",
        "run_id": run_id,
        "chain": fb.fallback_chain,
        "stage": orch.get_stage(run_id),
    }


@app.post("/api/runs/{run_id}/resume")
async def resume_run(run_id: str):
    """Manually resume a run stuck after approval (e.g. server reload)."""
    orch = get_orchestrator()
    state = orch.get_stage(run_id)
    run_dir = workspace / run_id
    disk_stage = get_run_status(run_dir).get("stage", state)
    allowed = ("awaiting_approval", "approved", "building", "unknown")
    if state not in allowed and disk_stage not in allowed:
        if not (run_dir / "generated").exists():
            return {"error": f"Cannot resume from stage: {state}"}
    approval = approval_gate.get(run_id)
    if approval and approval.status not in ("approved",):
        return {"error": "Approve the run first in Approval Center"}
    await orch.on_approval(
        run_id,
        "approved",
        approval.human_edits if approval else "",
        approval.human_instructions if approval else "",
        import_intent="",
    )
    return {"status": "resuming", "run_id": run_id, "stage": orch.get_stage(run_id)}


@app.post("/api/runs/{run_id}/approve")
async def approve_run(run_id: str, req: ApprovalRequest):
    action = req.action.strip().lower()
    if action in ("approve", "approved"):
        action = "approved"
    elif action in ("reject", "rejected"):
        action = "rejected"

    result = approval_gate.resolve(
        run_id,
        action,
        human_edits=req.human_edits,
        human_instructions=req.human_instructions,
    )
    if not result:
        return {"error": "No pending approval"}
    orch = get_orchestrator()
    await orch.on_approval(
        run_id,
        action,
        req.human_edits,
        req.human_instructions,
        import_intent=req.import_intent,
        document_edits=req.document_edits,
        document_instructions=req.document_instructions,
    )
    await broadcast_log(run_id, f"Human action: {action}")
    return {"status": result.status, "run_id": run_id, "stage": orch.get_stage(run_id)}


def _mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "••••••••"
    return f"{value[:4]}…{value[-4:]}"


@app.get("/api/providers/status")
async def providers_status():
    keys = settings.provider_keys()
    configured = [name for name, val in keys.items() if val]
    return {
        "groq": bool(keys.get("groq")),
        "gemini": bool(keys.get("gemini")),
        "openrouter": bool(keys.get("openrouter")),
        "configured": configured,
        "default_provider": settings.default_provider,
        "backend_env_ready": len(configured) > 0,
        "github": bool(settings.github_token),
        "vercel": bool(settings.vercel_token),
    }


@app.post("/api/providers/keys")
async def update_provider_keys(req: ProviderKeysRequest):
    if req.groq_api_key:
        settings.groq_api_key = req.groq_api_key
    if req.gemini_api_key:
        settings.gemini_api_key = req.gemini_api_key
    if req.openrouter_api_key:
        settings.openrouter_api_key = req.openrouter_api_key
    orch = get_orchestrator()
    orch.factory.keys.update(settings.provider_keys())
    orch.factory.default = req.default_provider or settings.default_provider
    return {
        "status": "updated",
        "providers": list(orch.factory.keys.keys()),
        "masked": {k: _mask_key(v) for k, v in settings.provider_keys().items() if v},
    }


@app.get("/api/runs/{run_id}/env-requirements")
async def get_env_requirements(run_id: str):
    from harness.env_requirements import scan_project_env_requirements

    run_dir = workspace / run_id
    if not run_dir.is_dir():
        return {"error": "Run not found"}
    requirements = scan_project_env_requirements(run_dir)
    return {"run_id": run_id, "requirements": requirements}


@app.get("/api/runs/{run_id}/env")
async def get_run_env(run_id: str):
    from harness.run_env import load_project_env, project_env_for_api

    run_dir = workspace / run_id
    if not run_dir.is_dir():
        return {"error": "Run not found"}
    state = load_state(run_dir) or {}
    return {
        "run_id": run_id,
        "project_env": project_env_for_api(run_dir),
        "use_demo_values": bool(state.get("project_env_demo")),
        "raw_keys": list(load_project_env(run_dir).keys()),
    }


@app.post("/api/runs/{run_id}/env")
async def save_run_env(run_id: str, req: RunEnvRequest):
    from harness.run_env import save_project_env

    run_dir = workspace / run_id
    if not run_dir.is_dir():
        return {"error": "Run not found"}
    save_project_env(run_dir, req.env, use_demo=req.use_demo_values)
    await broadcast_log(
        run_id,
        f"[INFO] Saved {len(req.env)} project env var(s)"
        + (" (demo placeholders)" if req.use_demo_values else ""),
    )
    return {"status": "saved", "run_id": run_id, "count": len(req.env)}


@app.websocket("/ws/logs/{run_id}")
async def websocket_logs(websocket: WebSocket, run_id: str):
    await websocket.accept()
    key = run_id if run_id != "all" else "*"
    ws_clients.setdefault(key, set()).add(websocket)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if msg.strip().lower() == "ping":
                    await websocket.send_text(json.dumps({"type": "ping"}))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        ws_clients.get(key, set()).discard(websocket)


@app.websocket("/ws/logs")
async def websocket_logs_all(websocket: WebSocket):
    await websocket_logs(websocket, "all")
