# VIA Architecture

## System Overview

```
┌─────────────────────────────────────────────────┐
│                   FRONTEND                       │
│  index.html + via-chat.css (served by FastAPI)   │
│  Auth │ Chat │ Build │ Projects │ Meetings │ Org │
└────────────────────┬────────────────────────────┘
                     │ HTTP/WS
┌────────────────────┴────────────────────────────┐
│              FASTAPI BACKEND                     │
│  ┌─────────┐ ┌──────────┐ ┌─────────────────┐  │
│  │  Auth   │ │  Chat    │ │  Agent Executor  │  │
│  │  JWT    │ │  Engine  │ │  (10 agents)     │  │
│  └─────────┘ └──────────┘ └────────┬────────┘  │
│  ┌─────────┐ ┌──────────┐         │            │
│  │  Rate   │ │ Intent   │  ┌──────┴───────┐   │
│  │ Limiter │ │ Detector │  │ InterAgent   │   │
│  └─────────┘ └──────────┘  │ Bus          │   │
│                             └──────────────┘   │
└──┬──────────┬──────────┬───────────────────────┘
   │          │          │
┌──┴───┐ ┌───┴───┐ ┌───┴──────┐
│Postgr│ │ Redis │ │  Ollama  │
│ SQL  │ │       │ │ / Groq   │
└──────┘ └───────┘ └──────────┘
```

## Agent Execution Flow

1. User sends task via `/chat/` or `/deploy/`
2. **Intent Detector** classifies: chat / build / analyze
3. **CEO Agent** analyzes task, selects departments
4. **Scaling Engine** adjusts department list
5. **Agent Executor** runs agents in dependency order:
   - architecture → backend → security → devops → ai_research → frontend → hr → finance → marketing → presentation
6. **InterAgent Bus** shares context between agents
7. **WebSocket Manager** streams real-time progress
8. For builds: **GitHub Pusher** → **Render Deployer**
9. Results saved to PostgreSQL

## Data Flow

```
User Message
    │
    ▼
Intent Detection ──→ "chat" ──→ Chat Engine ──→ LLM ──→ Response
    │
    ├──→ "build" ──→ CEO Agent ──→ Agent Pipeline ──→ GitHub Push ──→ Render Deploy
    │
    └──→ "analyze" ──→ CEO Agent ──→ Agent Pipeline ──→ Reports
```

## Database Schema

| Table | Purpose |
|-------|---------|
| `users` | JWT auth accounts |
| `company_history` | All task executions |
| `execution_stats` | Performance metrics |
| `decision_audit` | CEO decision log |
| `async_jobs` | Celery job tracking |
| `agent_memory` | Agent learning store |
| `meetings` | Meeting transcripts |
| `chat_history` | Chat conversations |
