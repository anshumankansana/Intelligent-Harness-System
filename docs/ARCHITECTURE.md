# Intelligent Harness System — Architecture

## Overview

The **Intelligent Harness System** is an autonomous engineering harness—not a chatbot. It orchestrates planning, multi-agent debate, human approvals, small demo builds, validation with retries, and optional GitHub/Vercel deployment.

## Harness Pipeline

```
User Idea
  → Planner Engine (Gemini preferred)
  → Markdown Memory (TASKS, ARCHITECTURE, etc.)
  → Multi-Agent Debate (Groq/fast)
  → Human Approval + per-document instructions
  → Builder Engine (Groq/fast)
  → Validation Harness (npm lint/test/build)
  → Retry/Fix Loop (max 2)
  → GitHub Push
  → Optional Vercel Deploy
```

## Provider Abstraction

| Role     | Default Provider | Use case              |
|----------|------------------|-----------------------|
| FAST     | Groq             | Builder, debate, fixes|
| PLANNER  | Gemini           | Specs, architecture   |
| FALLBACK | OpenRouter       | When primary fails    |

Switch providers via `ProviderFactory` without changing harness logic.

## Module Map

| Module        | Path                          |
|---------------|-------------------------------|
| Planner       | `harness/planner/`            |
| Memory        | `harness/memory/`             |
| Debate        | `harness/debate/`             |
| Approvals     | `harness/approvals/`          |
| Builder       | `harness/execution/`          |
| Validation    | `harness/validation/`         |
| Retries       | `harness/retries/`            |
| Deployment    | `harness/deployment/`         |
| Providers     | `harness/providers/`          |
| Orchestrator  | `harness/orchestrator.py`     |

## Frontend Pages

- Dashboard — start runs
- Live Logs — WebSocket feed
- Approval Center — read-only docs, instructions, approve/reject
- Debate Room — live agent conversation
- Environment — harness + project API keys
- Deployments — GitHub / Vercel URLs
- Markdown Viewer — engineering memory

## Hosting (target)

- Frontend: Vercel
- Backend: Render
- DB: Neon PostgreSQL (optional for future run persistence)
