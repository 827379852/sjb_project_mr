# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Market Research AI Platform (市场调研 AI 平台) - An AI-powered market research platform that uses LLM Agents to simulate real respondents for surveys, product testing, and user research.

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
python run.py                    # Dev server at http://localhost:8000/docs

# Vue Frontend (main frontend)
cd frontend-vue
npm install
npm run dev                      # Dev server at http://localhost:5173

# Simple HTML Frontend (legacy)
cd frontend && python -m http.server 3000

# Tests
pytest                           # Run from backend directory
```

## Architecture

### Two Frontend Applications

- **`frontend-vue/`**: Vue 3 + Vite + TypeScript + Pinia (primary frontend)
- **`frontend/`**: Single-page HTML with inline CSS/JS (legacy/simple frontend)

The Vue frontend uses SSE (Server-Sent Events) for real-time streaming from backend research flow endpoints.

### Backend Structure

```
backend/app/
├── api/v1/endpoints/
│   ├── research_flow.py     # Main research workflow API (5-step flow)
│   ├── projects.py          # Research project CRUD
│   ├── questionnaires.py    # Survey questionnaire design
│   └── respondents.py       # Respondent config & generation
├── adapters/                # Agent backend adapter layer
│   ├── base.py              # Abstract AgentBackendAdapter interface
│   ├── agentsociety_adapter.py
│   └── mock_adapter.py      # Mock for dev/testing (no LLM needed)
├── core/                    # Config, database, exceptions
├── models/                  # SQLAlchemy ORM models
└── schemas/                 # Pydantic request/response models
```

### Research Flow API (Primary Workflow)

`/api/v1/research-flow/` implements a streaming 5-step research workflow using SSE:

```
1. POST /design-study        → Design interview framework, return study_id
2. POST /search-personas     → Generate AI respondent personas
3. POST /scout-and-build     → Social media reconnaissance + persona enrichment
4. POST /interview/stream    → One-on-one interview (streaming)
   or POST /auto-interview   → Automated batch interviews
5. POST /generate-report     → Synthesize final report
```

All endpoints return `text/event-stream` (SSE) with JSON events. See `research_flow.py` for event schemas.

### Key Patterns

**Adapter Pattern**: `app/adapters/` allows switching agent backends by setting `AGENT_BACKEND` env var. Add new backends by implementing `AgentBackendAdapter` from `base.py`.

**Streaming Responses**: Research flow endpoints use FastAPI `StreamingResponse` with SSE. Frontend consumes via `EventSource` or `fetch` with `useSSE.ts` composable.

**In-Memory Storage**: `_studies` dict in `research_flow.py` stores session state. For production, migrate to database.

## Configuration

Environment variables (see `backend/app/core/config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_BACKEND` | `agentsociety` | `agentsociety` \| `mock` \| `custom` |
| `OPENAI_API_KEY` | - | Required for LLM calls |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | LLM API endpoint |
| `AGENTSOCIETY_DEFAULT_LLM` | `gpt-4o-mini` | Model for research tasks |
| `DATABASE_URL` | SQLite | PostgreSQL for production |

For quick testing without LLM: set `AGENT_BACKEND=mock` and use mock adapter.

## Deployment

Vercel serverless deployment. See `DEPLOYMENT.md` for detailed instructions.

**Note**: SQLite doesn't persist on Vercel; use PostgreSQL for production. The in-memory `_studies` storage in `research_flow.py` will not persist across serverless invocations.
