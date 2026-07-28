<<<<<<< HEAD
# 🚀 VIA — Virtual Intelligence Agents

> **Autonomous AI Digital Enterprise Platform** — A fully autonomous AI-powered MNC that builds, deploys, and manages software through coordinated multi-agent execution.

[![Phase](https://img.shields.io/badge/Phase-6-00d4ff?style=for-the-badge)](/)
[![Agents](https://img.shields.io/badge/AI_Agents-10-7c3aed?style=for-the-badge)](/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00ff9d?style=for-the-badge)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-ff006e?style=for-the-badge)](/)

---

## ✨ What is VIA?

VIA is an **AI-powered autonomous digital enterprise** that operates like a high-performance MNC software company. Give it a task — it delegates to specialized AI departments, builds the code, pushes to GitHub, deploys to production, and delivers live URLs.

### 🎯 Three Modes

| Mode | Trigger | What Happens |
|------|---------|-------------|
| 💬 **Chat** | Ask any question | Conversational AI assistant |
| 🏗️ **Build** | "Build me a..." | Full app generation → GitHub → Deploy |
| 🔍 **Analyze** | "Analyze my..." | Multi-department strategic reports |

---

## 🏢 AI Department Structure

```
                    ┌─────────┐
                    │  🏛️ CEO  │
                    └────┬────┘
         ┌───────────────┼───────────────┐
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    │  TECH   │    │BUSINESS │    │ SPECIAL │
    └────┬────┘    └────┬────┘    └────┬────┘
    ┌────┼────┐    ┌────┼────┐        │
    │    │    │    │    │    │        │
  ⚙️BE 🎨FE 🔒SEC 👥HR 💰FIN 📣MKT  📊PRES
  🚀DO 🧠AI 📐ARC
```

| Agent | Role |
|-------|------|
| 🏛️ CEO | Strategy, delegation, conflict resolution |
| ⚙️ Backend | FastAPI APIs, database architecture |
| 🎨 Frontend | React/Vite UI with Tailwind CSS |
| 🔒 Security | Threat modeling, auth, encryption |
| 🚀 DevOps | Docker, CI/CD, deployment |
| 🧠 AI Research | LLM strategy, ML optimization |
| 📐 Architecture | System design, data flow |
| 👥 HR | Team structure, hiring plans |
| 💰 Finance | Budget, ROI, pricing strategy |
| 📣 Marketing | GTM, branding, SEO |

---

## 🚀 Quick Start

### Option A: Docker (Recommended)

```bash
cp .env.example .env
# Edit .env with your credentials
docker-compose up --build
```

Services:
- **API**: http://localhost:8000
- **Frontend**: http://localhost:8000 (served by FastAPI)
- **pgAdmin**: http://localhost:5050
- **Swagger**: http://localhost:8000/docs

### Option B: Local Development

```bash
# 1. Start PostgreSQL and Redis
# 2. Install Python deps
pip install -r requirements.txt

# 3. Start Ollama (or set USE_GROQ=true in .env)
ollama serve && ollama pull llama3

# 4. Start API
uvicorn backend.main:app --reload

# 5. Start Celery worker (separate terminal)
celery -A backend.tasks.celery_app worker --loglevel=info

# 6. Open http://localhost:8000 in browser
```

---

## 📡 API Endpoints

### Public
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Get JWT token |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

### Protected (JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/` | Unified chat/build/analyze |
| POST | `/start-company/` | Run agent pipeline |
| POST | `/deploy/` | Build + GitHub + Render |
| POST | `/feedback/` | Revision feedback loop |
| GET | `/company-history/` | Execution history |
| GET | `/system-health/` | System metrics |
| GET | `/org-chart/` | Organization hierarchy |
| GET | `/agent-memory/` | Agent memory store |

### WebSocket
| Endpoint | Description |
|----------|-------------|
| WS `/ws/{job_id}` | Real-time pipeline streaming |

---

## 🛡️ Security Features

- JWT authentication with configurable expiration
- bcrypt password hashing
- Rate limiting (configurable per minute)
- CORS middleware
- Input validation via Pydantic
- Path traversal protection in file browser
- SQL injection prevention (parameterized queries)

---

## 🧪 Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

---

## 📁 Project Structure

```
via/
├── backend/
│   ├── main.py              # FastAPI app + all endpoints
│   ├── agents/              # 10 AI department agents
│   ├── core/                # LLM, config, engines, deployers
│   ├── database/            # PostgreSQL + asyncpg
│   ├── auth/                # JWT authentication
│   ├── middleware/           # Rate limiting
│   ├── routers/             # Meeting, template, file browser APIs
│   └── tasks/               # Celery async job queue
├── tests/                   # Test suite
├── projects/                # Generated project outputs
├── index.html               # Frontend dashboard
├── via-chat.css             # Stylesheet
├── docker-compose.yml       # Full stack orchestration
├── Dockerfile               # API container
└── requirements.txt         # Python dependencies
```

---

## 🔧 Environment Variables

See `.env.example` for all required variables. Key ones:

| Variable | Description |
|----------|-------------|
| `MODEL_NAME` | Ollama model (default: llama3.2:latest) |
| `USE_GROQ` | Set `true` to use Groq cloud LLM |
| `GROQ_API_KEY` | Groq API key (if using Groq) |
| `POSTGRES_*` | PostgreSQL connection settings |
| `JWT_SECRET_KEY` | JWT signing secret |
| `GITHUB_TOKEN` | GitHub PAT for auto-push |
| `RENDER_API_KEY` | Render API key for auto-deploy |

---

## 📊 Phase History

| Phase | Features |
|-------|----------|
| 1 | PostgreSQL, JWT auth, rate limiting, Docker |
| 2 | WebSocket streaming, inter-agent bus, Celery |
| 3 | Business agents (HR/Finance/Marketing), meetings |
| 4 | Presentation generation, templates |
| 5 | Chat mode, intent detection, fullstack builder |
| **6** | **Premium UI, testing, docs, CI/CD, hardening** |

---

*Built with ❤️ by VIA — Autonomous AI Digital Team*
=======
# via
>>>>>>> 2600c44eb1ab270bb4abe61696ef73b485a8dc0f
