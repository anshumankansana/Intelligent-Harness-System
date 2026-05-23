# Intelligent Harness System

[![Live Demo](https://img.shields.io/badge/demo-live-00d4aa?style=for-the-badge)](https://intelligent-harness-system-12345.vercel.app/)
[![GitHub](https://img.shields.io/badge/source-GitHub-24292f?style=for-the-badge&logo=github)](https://github.com/anshumankansana/Intelligent-Harness-System)
[![Docs](https://img.shields.io/badge/docs-overview-blue?style=for-the-badge)](docs/PROJECT_OVERVIEW.md)

Autonomous engineering harness — planning, debate, human approvals, validation, and provider-agnostic AI orchestration.

**This is NOT a chatbot.** The harness controls the engineering workflow end-to-end.

| | |
|---|---|
| **Live app** | https://intelligent-harness-system-12345.vercel.app/ |
| **Repository** | https://github.com/anshumankansana/Intelligent-Harness-System |
| **Full overview** | [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) (diagrams, capabilities, pipeline) |

---

## What it does

- Turns an **idea or Word (.docx) brief** into engineering memory, agent debate, and a built Next.js app  
- **Human approval gate** before any code is generated  
- **Live logs** and **Debate Room** with WebSocket updates  
- **Automatic LLM fallback** (Groq → OpenRouter → Gemini) on failures and rate limits  
- Optional **GitHub push** and **Vercel deploy** for generated projects  

See the [project overview](docs/PROJECT_OVERVIEW.md) for architecture diagrams and a full feature list.

---

## Quick Start

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # add GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY
python scripts/check_models.py   # optional: probe free models
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

---

## Workflow

1. **Environment** — configure LLM keys (backend `.env` or UI sync)
2. **Dashboard** — new idea, optional Word brief, or import zip
3. **Logs / Debate** — watch planning and agent discussion
4. **Approval Center** — read-only documents, optional instructions, approve or reject
5. **Memory** — inspect engineering markdown
6. **Deployments** — GitHub + Vercel when ready

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Fast generation |
| `GEMINI_API_KEY` | Planning |
| `OPENROUTER_API_KEY` | Fallback / multi-model |
| `GITHUB_TOKEN` | Optional repo push |
| `VERCEL_TOKEN` | Optional deploy |
| `CORS_ORIGINS` | Frontend URL(s), comma-separated (production) |
| `VERCEL_SCOPE` | Vercel team slug for CLI deploy |

Copy from `backend/.env.example` — **never commit** real `.env` files.

---

## Deploy (production)

### Backend — Render

1. Connect [GitHub repo](https://github.com/anshumankansana/Intelligent-Harness-System); use `backend/render.yaml` (root dir: `backend`).
2. Set at least one of `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`.
3. Set `CORS_ORIGINS=https://intelligent-harness-system-12345.vercel.app` (your frontend URL).
4. Optional: `GITHUB_TOKEN`, `VERCEL_TOKEN`, `VERCEL_SCOPE`.

### Frontend — Vercel

1. Import `frontend/` as a Next.js project (already deployed at the live URL above).
2. `NEXT_PUBLIC_API_URL` = your Render API URL (no trailing `/`, e.g. `https://….onrender.com`)  
3. `NEXT_PUBLIC_WS_URL` = same host with `wss://` (no trailing `/`)

---

## Project Structure

```
backend/harness/   # Core harness modules
backend/scripts/   # deploy_vercel.py, utilities
frontend/          # Next.js UI
workspace/         # Per-run artifacts (local, gitignored)
docs/              # PROJECT_OVERVIEW.md, ARCHITECTURE.md
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | Product overview, mermaid diagrams, capabilities |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical module map and pipeline |

---

## License

Hackathon MVP — see repository for usage. Do not commit API keys or tokens.
