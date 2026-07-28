# VIA API Reference

> Complete API documentation for VIA — Autonomous AI Digital Enterprise Platform

---

## Base URL

```
Development: http://localhost:8000
Production:  https://your-render-app.onrender.com
```

## Authentication

VIA uses **JWT (JSON Web Tokens)** for authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

---

## Public Endpoints

### `POST /auth/register`

Create a new user account.

**Request:**
```json
{
  "username": "string (required)",
  "password": "string (required)"
}
```

**Response:** `200 OK`
```json
{
  "message": "User created successfully",
  "username": "john"
}
```

---

### `POST /auth/login`

Authenticate and receive a JWT token.

**Request:** `application/x-www-form-urlencoded`
```
username=john&password=secret123
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

---

### `GET /health`

Health check endpoint.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "6.0.0",
  "phase": "6"
}
```

---

### `GET /api/info`

Platform metadata.

**Response:** `200 OK`
```json
{
  "app": "VIA",
  "version": "6.0.0",
  "phase": "6",
  "agents": 10,
  "app_types": ["frontend", "fullstack", "fullstack_db"],
  "modes": ["chat", "build", "analyze"]
}
```

---

## Protected Endpoints (JWT Required)

### `POST /chat/`

**Unified chat endpoint** — automatically routes to Chat, Build, or Analyze mode based on intent detection.

**Request:**
```json
{
  "message": "string (1-5000 chars, required)",
  "history": [{"role": "user", "message": "..."}]  // optional
}
```

**Response (Chat Mode):**
```json
{
  "response": "Here's what I think about...",
  "intent": "chat",
  "mode": "chat",
  "duration_seconds": 2.3
}
```

**Response (Build Mode):**
```json
{
  "response": "🚀 Build Complete!...",
  "intent": "build",
  "mode": "build",
  "job_id": "uuid",
  "app_type": "fullstack",
  "departments": ["backend", "frontend", "security"],
  "dept_results": {"backend": "success", "frontend": "success"},
  "live_urls": {
    "frontend": "https://user.github.io/repo/",
    "backend": "https://app.onrender.com",
    "api_docs": "https://app.onrender.com/docs"
  },
  "duration_seconds": 45.2
}
```

**Response (Analyze Mode):**
```json
{
  "response": "🔍 Analysis Complete!...",
  "intent": "analyze",
  "mode": "analyze",
  "job_id": "uuid",
  "departments": ["backend", "security", "architecture"],
  "dept_results": {...},
  "duration_seconds": 30.1
}
```

---

### `POST /start-company/`

Run the full agent pipeline without deployment.

**Request:**
```json
{
  "task": "string (5-2000 chars)"
}
```

**Response:** `200 OK`
```json
{
  "job_id": "uuid",
  "task": "Build a todo app",
  "requested_by": "john",
  "ceo_strategy": {
    "short_term_strategy": "...",
    "long_term_vision": "..."
  },
  "selected_departments": ["backend", "frontend", "security"],
  "departments": {
    "backend": {"status": "success", "execution_time_seconds": 12.3, "confidence": 0.92, "output": {...}},
    "frontend": {"status": "success", "execution_time_seconds": 15.1, "confidence": 0.97, "output": {...}}
  }
}
```

---

### `POST /deploy/`

Full build → GitHub push → Render deploy pipeline.

**Request:**
```json
{
  "task": "string (5-2000 chars)",
  "push_to_github": true,
  "deploy_to_render": true
}
```

**Response:** `200 OK`
```json
{
  "job_id": "uuid",
  "task": "...",
  "app_type": "fullstack",
  "github": {"repo_url": "https://github.com/...", "repo_name": "..."},
  "render": {"live_url": "https://app.onrender.com"},
  "live_urls": {
    "frontend": "https://user.github.io/repo/",
    "backend": "https://app.onrender.com",
    "api_docs": "https://app.onrender.com/docs"
  }
}
```

---

### `POST /feedback/`

Submit revision feedback for a previous build.

**Request:**
```json
{
  "job_id": "previous-job-uuid",
  "task": "original task description",
  "feedback": "Please add dark mode support (5-1000 chars)",
  "departments": ["backend", "frontend"]
}
```

---

### `GET /chat/history/`

Retrieve chat history for the authenticated user.

**Response:**
```json
{
  "history": [
    {"role": "user", "message": "...", "intent": "chat", "timestamp": "..."},
    {"role": "assistant", "message": "...", "intent": "chat", "timestamp": "..."}
  ],
  "total": 42
}
```

### `DELETE /chat/history/`

Clear all chat history for the authenticated user.

---

### `GET /company-history/`

Returns recent task execution history.

### `GET /system-health/`

Returns system performance metrics (total runs, success rate, avg duration).

### `GET /company-status/`

Returns company operational status dashboard.

### `GET /org-chart/`

Returns the full organizational hierarchy of AI departments.

### `GET /agent-memory/`

Returns all agent memories (last 50).

### `GET /agent-memory/{agent_name}/`

Returns memories for a specific agent.

---

## Meetings Endpoints

### `POST /meetings/generate/`

Generate an AI boardroom meeting discussion.

**Request:**
```json
{
  "task": "Discuss the architecture for a real-time chat app",
  "departments": ["ceo", "backend", "frontend", "security", "devops"]
}
```

### `GET /meetings/`

List all past meetings.

### `GET /meetings/{meeting_id}/`

Get a specific meeting transcript.

---

## File Browser Endpoints

### `GET /files/projects/`

List all generated projects.

### `GET /files/projects/{project_name}/tree/`

Get the file tree structure for a project.

### `GET /files/projects/{project_name}/read/?file_path=...`

Read a specific file from a project.

### `GET /files/projects/{project_name}/download/`

Download a project as a ZIP archive.

---

## WebSocket

### `WS /ws/{job_id}`

Real-time pipeline streaming. Receives JSON messages:

```json
{"type": "agent_start", "agent": "backend", "timestamp": "..."}
{"type": "agent_done", "agent": "backend", "status": "success", "duration": 12.3, "confidence": 0.92}
{"type": "inter_agent", "from": ["architecture"], "to": ["backend"], "context": "..."}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error description"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request / validation error |
| 401 | Unauthorized (invalid/expired JWT) |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Rate Limiting

- Default: **20 requests per minute** per IP
- Configurable via `RATE_LIMIT_PER_MINUTE` env var
- Returns `429 Too Many Requests` when exceeded
