============================================================
  AI DIGITAL TEAM — Phase 2: Full MNC Engine
  Version 4.0.0
============================================================

PHASE 2 NEW FEATURES
---------------------
[x] WebSocket real-time streaming — every pipeline step broadcast live
[x] Inter-Agent Communication Bus — departments share context with each other
[x] Async Task Queue — Celery + Redis background job processing
[x] Live agent progress cards in frontend
[x] New endpoints: WS /ws/{job_id}, POST /jobs/submit/, GET /jobs/{job_id}/
[x] Execution order awareness — backend/architecture run first, feed context downstream
[x] All Phase 1 features preserved (PostgreSQL, JWT, rate limiting, Docker)

============================================================
OPTION A: Docker (Recommended — starts everything)
============================================================

cp .env.example .env
docker-compose up --build

Services started:
  - API:      http://localhost:8000
  - Frontend: open frontend/index.html in browser
  - pgAdmin:  http://localhost:5050
  - Redis:    localhost:6379
  - Celery Worker: runs in background automatically

============================================================
OPTION B: Local (manual)
============================================================

1. Start PostgreSQL + create DB
2. Start Redis:
      redis-server

3. Install deps:
      pip install -r requirements.txt

4. Start Ollama:
      ollama serve
      ollama pull llama3

5. Start API:
      uvicorn backend.main:app --reload

6. Start Celery Worker (separate terminal):
      celery -A backend.tasks.celery_app worker --loglevel=info

7. Open frontend/index.html in browser

============================================================
PHASE 2 API ENDPOINTS
============================================================

PUBLIC:
  POST /auth/register     Register new user
  POST /auth/login        Get JWT token
  GET  /health            Health check
  GET  /                  API info + endpoint list
  GET  /docs              Swagger UI

WEBSOCKET:
  WS /ws/{job_id}         Real-time pipeline event stream
  Events: pipeline_step, ceo_decision, agent_start,
          inter_agent_context, agent_done, complete, error

PROTECTED (JWT required):
  POST /start-company/    Sync orchestration + WS streaming
  POST /jobs/submit/      Submit async background job
  GET  /jobs/{job_id}/    Poll async job status + result
  GET  /company-history/  Execution history
  GET  /system-health/    Metrics
  GET  /company-status/   Dashboard
  GET  /org-chart/        Org hierarchy

============================================================
HOW INTER-AGENT COMMUNICATION WORKS
============================================================

Departments execute in dependency order:
  1. backend       → deposits: architecture, API style, DB choice
  2. architecture  → deposits: system design pattern, data flow
  3. security      → reads backend context → tailored threat model
  4. devops        → reads backend + architecture → aligned infra plan
  5. ai_research   → reads architecture + backend → coherent AI strategy

Result: departments produce a COHERENT unified plan,
not just isolated reports.

============================================================
PROJECT STRUCTURE
============================================================

via/
├── .env
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.txt
├── frontend/
│   └── index.html          ← Complete dashboard (open in browser)
└── backend/
    ├── main.py              ← FastAPI app + all endpoints
    ├── core/
    │   ├── config.py        ← Loads from .env
    │   ├── logger.py
    │   ├── llm_provider.py  ← Ollama with retry
    │   ├── tracer.py        ← Execution trace (Phase 2: inter-agent events)
    │   ├── hierarchy.py
    │   ├── scaling_engine.py
    │   ├── ws_manager.py    ← [NEW] WebSocket connection manager
    │   └── inter_agent_bus.py ← [NEW] Agent-to-agent context sharing
    ├── database/
    │   └── db.py            ← PostgreSQL + async_jobs table
    ├── auth/
    │   └── auth.py
    ├── middleware/
    │   └── rate_limiter.py
    ├── agents/
    │   ├── ceo_agent.py
    │   ├── backend_agent.py     ← Phase 2: accepts inter_context param
    │   ├── security_agent.py    ← reads backend context
    │   ├── devops_agent.py      ← reads backend + architecture context
    │   ├── ai_research_agent.py ← reads architecture + backend context
    │   ├── architecture_agent.py← reads backend context
    │   └── agent_executor.py    ← [NEW] ordered execution + WS streaming
    └── tasks/
        ├── celery_app.py        ← [NEW] Celery config
        └── orchestration_task.py← [NEW] Background orchestration task

============================================================
FRONTEND FEATURES
============================================================

Pages:
  Dashboard        - Stats + Quick Launch + Recent Activity
  Run Task         - Live stream feed + agent progress cards + results
  Async Jobs       - Submit jobs + poll status + view results
  History          - All past execution records
  Metrics          - Dept activity bars + health charts + full stats
  Company Status   - Department breakdown
  Org Chart        - CEO → 5 departments

Phase 2 UI highlights:
  - 📡 Live WebSocket event feed (colored by event type)
  - 🤖 Agent progress cards (Waiting → Running → Done/Failed)
  - 🔗 Inter-agent context events shown in stream
  - ⏳ Async job queue with polling
  - ⚡ Scaling notifications in result view

============================================================
PHASE COMPARISON
============================================================

Feature                    Phase 1   Phase 2
-----------------------    -------   -------
PostgreSQL + JWT              ✓         ✓
Rate limiting                 ✓         ✓
Docker + Compose              ✓         ✓
WebSocket streaming           ✗         ✓
Inter-agent communication     ✗         ✓
Async job queue (Celery)      ✗         ✓
Redis                         ✗         ✓
Celery worker                 ✗         ✓
Live agent progress UI        ✗         ✓
Frontend dashboard            ✗         ✓

============================================================
