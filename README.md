# Intelligent Harness System

Autonomous Engineering Harness MVP — planning, debate, human approvals, validation loops, and provider-agnostic AI orchestration.

**This is NOT a chatbot.** The harness controls engineering workflow end-to-end.

## Quick Start

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env   # add GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY
python scripts/check_models.py   # probes free models, writes selected_models.json
uvicorn main:app --reload --port 8000
```

### Frontend (Next.js)

```bash
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Open http://localhost:3000

## Workflow

1. **Environment** — backend `.env` keys or browser sync (Groq, Gemini, OpenRouter)
2. **Dashboard** — describe your idea, upload optional Word brief (.docx), start harness run
3. **Live Logs** — watch planner, debate, validation messages
4. **Approval Center** — edit plan, add constraints, approve/reject
5. **Markdown Viewer** — inspect TASKS.md, ARCHITECTURE.md, etc.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Fast generation |
| `GEMINI_API_KEY` | Planning (free tier) |
| `OPENROUTER_API_KEY` | Fallback / multi-model |
| `GITHUB_TOKEN` | Optional repo push |
| `VERCEL_TOKEN` | Optional deploy |
| `CORS_ORIGINS` | Frontend URL(s), comma-separated (required in production) |
| `VERCEL_SCOPE` | Vercel team slug for CLI deploy |

## Deploy (production)

### Backend — Render

1. Connect repo; use `backend/render.yaml` (or set **Root Directory** to `backend`).
2. Set env vars: at least one of `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`.
3. Set `CORS_ORIGINS` to your frontend URL, e.g. `https://your-app.vercel.app`.
4. Optional: `GITHUB_TOKEN`, `VERCEL_TOKEN`, `VERCEL_SCOPE` for publish/deploy from the UI.
5. `WORKSPACE_ROOT` defaults to `../workspace` (persists runs on Render disk).

### Frontend — Vercel

1. Import `frontend/` as a Next.js project.
2. Set `NEXT_PUBLIC_API_URL` = your Render API URL (`https://….onrender.com`).
3. Set `NEXT_PUBLIC_WS_URL` = same host with `wss://` (e.g. `wss://….onrender.com`).

### Deploy generated apps to Vercel (CLI)

Same pipeline as the dashboard **Deploy** button (repair → npm install → build → Vercel CLI):

```bash
cd backend
.\.venv\Scripts\activate
python scripts/deploy_vercel.py <run_id>
python scripts/deploy_vercel.py --list   # runs with generated/
```

Requires Node.js/npm on PATH and `VERCEL_TOKEN` in `backend/.env`.

## Project Structure

```
backend/harness/   # Core harness modules
backend/scripts/   # deploy_vercel.py, utilities
frontend/          # Next.js UI
workspace/         # Per-run artifacts & memory
docs/              # Architecture docs
```

## Hackathon Notes

- Builder generates **small demo apps only**
- Validation retries capped at **2**
- Human edits are **injected into downstream context**
- Providers are swappable via abstraction layer
