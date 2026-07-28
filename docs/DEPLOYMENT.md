# VIA Deployment Guide

> Step-by-step instructions to deploy VIA in production.

---

## Architecture Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │     │   Backend    │     │   Database   │
│  (FastAPI    │────▶│  (FastAPI +  │────▶│ (PostgreSQL) │
│   Static)    │     │   Uvicorn)   │     └──────────────┘
└──────────────┘     └──────┬───────┘            │
                           │                     │
                    ┌──────┴───────┐     ┌──────┴──────┐
                    │   Celery     │     │    Redis    │
                    │   Worker     │     │   (Queue)   │
                    └──────────────┘     └─────────────┘
```

---

## Option 1: Docker Compose (Recommended)

### Prerequisites
- Docker Engine 20.10+
- Docker Compose v2+
- 4GB RAM minimum

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-username/via.git
cd via

# 2. Configure environment
cp .env.example .env
# Edit .env with your real credentials:
#   - POSTGRES_PASSWORD (strong password)
#   - JWT_SECRET_KEY (random 64-char string)
#   - GITHUB_TOKEN (GitHub PAT with repo scope)
#   - RENDER_API_KEY (from Render dashboard)
#   - GROQ_API_KEY (if using Groq cloud LLM)

# 3. Start all services
docker-compose up --build -d

# 4. Verify
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"6.0.0","phase":"6"}
```

### Services Started
| Service | URL | Purpose |
|---------|-----|---------|
| API | http://localhost:8000 | FastAPI backend + frontend |
| Swagger | http://localhost:8000/docs | Interactive API docs |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Task queue |
| pgAdmin | http://localhost:5050 | DB admin panel |

### Useful Commands
```bash
# View logs
docker-compose logs -f api

# Restart a service
docker-compose restart api

# Scale workers
docker-compose up -d --scale worker=3

# Stop everything
docker-compose down

# Stop and remove data
docker-compose down -v
```

---

## Option 2: Local Development

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Ollama (for local LLM) or Groq API key

### Steps

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start PostgreSQL
# Ensure PostgreSQL is running and create the database:
createdb ai_digital_team

# 4. Start Redis
redis-server

# 5. Configure environment
cp .env.example .env
# Edit .env with your values

# 6. Start Ollama (if using local LLM)
ollama serve &
ollama pull llama3.2:latest

# 7. Start the API server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 8. Start Celery worker (new terminal)
celery -A backend.tasks.celery_app worker --loglevel=info

# 9. Open http://localhost:8000 in browser
```

---

## Option 3: Cloud Deployment (Render)

### Backend (Web Service)

1. Push code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Create **New Web Service**
4. Connect your GitHub repo
5. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Starter ($7/mo) or Standard ($25/mo)
6. Add environment variables from `.env.example`
7. Deploy

### Database (PostgreSQL)

1. Create **New PostgreSQL** on Render
2. Copy the **Internal Database URL**
3. Set `DATABASE_URL` in your web service env vars

### Redis (Background Worker)

1. Create **New Redis** on Render
2. Copy the Redis URL
3. Set `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_URL`
4. Create a **Background Worker** service with:
   - **Start Command**: `celery -A backend.tasks.celery_app worker --loglevel=info --concurrency=2`

---

## Option 4: AWS Deployment

### Using ECS + RDS

```bash
# 1. Build and push Docker image
aws ecr create-repository --repository-name via-api
docker build -t via-api .
docker tag via-api:latest <account>.dkr.ecr.<region>.amazonaws.com/via-api:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/via-api:latest

# 2. Create RDS PostgreSQL instance
# 3. Create ElastiCache Redis instance
# 4. Create ECS task definition and service
# 5. Configure ALB for HTTPS
```

---

## LLM Configuration

### Option A: Local Ollama (Free, Private)
```env
MODEL_NAME=llama3.2:latest
OLLAMA_URL=http://localhost:11434/api/generate
USE_GROQ=false
```

### Option B: Groq Cloud (Fast, Scalable)
```env
USE_GROQ=true
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

---

## Security Checklist for Production

- [ ] Change `JWT_SECRET_KEY` to a random 64+ character string
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Restrict CORS origins (change `allow_origins=["*"]` to specific domains)
- [ ] Enable HTTPS (automatic on Render/AWS ALB)
- [ ] Rotate `GITHUB_TOKEN` and `RENDER_API_KEY` regularly
- [ ] Set `APP_ENV=production`
- [ ] Configure firewall rules for PostgreSQL/Redis
- [ ] Enable database backups
- [ ] Set up monitoring and alerting
- [ ] Review rate limiting settings

---

## Monitoring

### Health Check
```bash
curl https://your-app.onrender.com/health
```

### System Metrics
```bash
curl -H "Authorization: Bearer <token>" https://your-app.onrender.com/system-health/
```

### Logs
- Docker: `docker-compose logs -f api`
- Render: Dashboard → Service → Logs
- Local: `tail -f logs/via.log`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Connection refused` on PostgreSQL | Ensure PostgreSQL is running and `POSTGRES_HOST` is correct |
| `401 Unauthorized` | Token expired — re-login via `/auth/login` |
| `429 Too Many Requests` | Rate limit hit — wait or increase `RATE_LIMIT_PER_MINUTE` |
| Ollama timeout | Increase `REQUEST_TIMEOUT` or switch to Groq |
| Celery tasks stuck | Check Redis connection and restart worker |
| Build mode no URLs | Verify `GITHUB_TOKEN` has `repo` scope |
