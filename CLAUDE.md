# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Market Research AI Platform (市场调研 AI 平台) - An AI-powered market research platform that uses LLM Agents to simulate real respondents for surveys, product testing, and user research. Built on the AgentSociety framework from Tsinghua FIB Lab.

## Development Commands

```bash
# Install backend dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# For quick testing without LLM: set AGENT_BACKEND=mock
# For production: set AGENT_BACKEND=agentsociety and OPENAI_API_KEY

# Run development server
python run.py
# API docs available at http://localhost:8000/docs

# Run tests
pytest

# Local frontend testing (separate terminal)
cd frontend
python -m http.server 3000
```

## Architecture

### Backend Structure (FastAPI + Python)

```
backend/
├── app/
│   ├── main.py              # FastAPI app factory with lifespan
│   ├── api/v1/endpoints/    # REST API routes
│   │   ├── projects.py      # Research project CRUD
│   │   ├── questionnaires.py # Survey questionnaire design
│   │   ├── respondents.py   # Respondent config & generation
│   │   ├── runs.py          # Survey execution & results
│   │   └── system.py        # Health checks
│   ├── adapters/            # Agent backend adapter layer (key extension point)
│   │   ├── base.py          # Abstract AgentBackendAdapter interface
│   │   ├── agentsociety_adapter.py  # AgentSociety implementation
│   │   ├── mock_adapter.py  # Mock for dev/testing (no LLM needed)
│   │   └── factory.py       # Factory function get_agent_backend()
│   ├── core/                # Config, database, exceptions
│   ├── models/              # SQLAlchemy ORM models
│   └── schemas/             # Pydantic request/response models
├── api/index.py             # Vercel serverless entry point
└── run.py                   # Local development entry point
```

### Key Patterns

**Adapter Pattern for Agent Backends**: The `app/adapters/` directory implements an adapter pattern allowing seamless switching between different agent backends. To add a new backend:
1. Implement `AgentBackendAdapter` from `base.py`
2. Register in `factory.py`
3. Set `AGENT_BACKEND` env var

**Async Database**: Uses SQLAlchemy 2.0 async with `aiosqlite` (dev) or PostgreSQL (prod). Session management via `get_db()` dependency injection.

**API Response Format**: All endpoints return `ApiResponse[T]` wrapper from `core/response.py` with structure `{code, message, data}`.

### Core Workflow

```
1. POST /api/v1/projects              → Create research project
2. POST /api/v1/questionnaires        → Design questionnaire
3. POST /api/v1/respondent-configs    → Configure target audience
4. POST /api/v1/respondent-configs/{id}/generate → Generate AI respondents
5. PUT  /api/v1/projects/{id}         → Bind questionnaire & respondents
6. POST /api/v1/runs                  → Start survey execution
7. GET  /api/v1/runs/{id}             → Poll progress
8. GET  /api/v1/runs/{id}/analytics   → Get analysis results
```

## Configuration

Environment variables (see `backend/app/core/config.py`):
- `AGENT_BACKEND`: "agentsociety" | "mock" | "custom"
- `OPENAI_API_KEY`: Required for agentsociety backend
- `DATABASE_URL`: SQLite default, PostgreSQL for production
- `DEBUG`: Enable SQL query logging

## Deployment

Vercel serverless deployment configured via `vercel.json`:
- API routes (`/api/v1/*`) → `backend/api/index.py`
- Static routes → `frontend/`

Note: SQLite does not persist on Vercel; use PostgreSQL for production.

## Frontend

Single-page HTML application (`frontend/index.html`) with inline CSS/JS. No build step required. Connects to backend API at `/api/v1`.
