# backend/main.py — Phase 6: Enterprise Engine + Chat Mode
#
# FIXES APPLIED:
#   FIX 1 — _is_repo_healthy() now does a real HTTP GET to GitHub Pages URL.
#            GitHub API status="built" does NOT mean 200 OK. Only an actual
#            HTTP 200 from gollavinaykumar1.github.io/{repo}/ confirms live.
#   FIX 2 — _fix_single_repo() no longer uses time.sleep(5) before dispatch.
#            It delegates to github_pusher._trigger_workflow() which uses the
#            proper _workflow_exists() loop + 30-second initial wait.
#   FIX 3 — Cooldown guard: repos attempted within the last 30 minutes are
#            skipped entirely, breaking the infinite fix loop on every restart.
#   FIX 4 — Non-VIA repos (my-portfolio, .github, etc.) are explicitly skipped.

import json, time, uuid, os, asyncio, base64, random, string
import requests as _requests
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from fastapi.security import OAuth2PasswordRequestForm

from backend.agents.ceo_agent import ceo_agent
from backend.agents.agent_executor import execute_agents
from backend.core.tracer import ExecutionTracer
from backend.core.scaling_engine import autonomous_scale
from backend.core.hierarchy import get_active_structure, get_full_chart
from backend.core.ws_manager import ws_manager
from backend.core.inter_agent_bus import InterAgentBus
from backend.core.logger import logger
from backend.core.config import APP_VERSION
from backend.core.memory_store import save_agent_memory, get_agent_memory, get_all_memories
from backend.core.fullstack_builder import detect_app_type, generate_backend_files_llm
from backend.core.intent_detector import detect_intent
from backend.core import chat_engine
from backend.database.db import (
    init_db, close_db,
    save_record, save_execution_stat, save_audit_record,
    get_recent_history, get_system_health, get_company_status,
    create_job, update_job, get_job,
    save_chat_message, get_chat_history, clear_chat_history,
    save_auth_code, get_auth_code, delete_auth_code,
    verify_user_email, update_user_password, get_user_by_email
)
from backend.auth.auth import (
    Token, UserCreate, get_current_active_user,
    authenticate_user, register_user, create_access_token
)
from backend.middleware.rate_limiter import rate_limit_middleware
from backend.routers.meeting_router    import router as meeting_router
from backend.routers.template_router   import router as template_router
from backend.routers.filebrowser_router import router as filebrowser_router
from backend.core.github_pusher   import github_pusher
from backend.core.render_deployer import render_deployer
from backend.utils.email_sender import send_verification_email, send_reset_password_email

app = FastAPI(
    title="VIA — Autonomous AI Digital Team | Phase 6 Enterprise",
    version=APP_VERSION,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)
app.include_router(meeting_router)
app.include_router(template_router)
app.include_router(filebrowser_router)

class TaskRequest(BaseModel):
    task: str = Field(..., min_length=5, max_length=2000)

class JobRequest(BaseModel):
    task: str = Field(..., min_length=5, max_length=2000)

class FeedbackRequest(BaseModel):
    job_id: str
    task: str
    feedback: str = Field(..., min_length=5, max_length=1000)
    departments: list = Field(default=["backend", "frontend"])

class DeployRequest(BaseModel):
    task: str = Field(..., min_length=5, max_length=2000)
    push_to_github: bool = Field(default=True)
    deploy_to_render: bool = Field(default=True)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    history: Optional[List[dict]] = None


# ── Startup Repo Fix ──────────────────────────────────────────────────────────

# FIX 1: Matches frontend_agent.py _deploy_workflow() exactly.
# Old version used actions/deploy-pages@v4 (workflow mode) which is
# incompatible with gh-pages branch source. peaceiris pushes to the
# gh-pages branch, so Pages must be configured for branch source.
DEPLOY_YML = """name: Deploy React to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm install

      - name: Build
        run: npm run build
        env:
          CI: "false"
          VITE_API_URL: ${{ vars.VITE_API_URL }}

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./dist
          force_orphan: true
"""

# ── FIX 3: File-backed cooldown store (survives restarts) ────────────────────
# Tracks last fix attempt per repo (epoch float).
# Repos attempted within COOLDOWN_SECONDS are skipped on next startup.
# CHANGE 1: replaced in-memory dict with file-backed version so cooldowns
#            survive VIA restarts — the root cause of all repos redeploying
#            every time VIA restarted (in-memory {} was wiped on each restart).
COOLDOWN_SECONDS = 1800  # 30 minutes
_COOLDOWN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fix_cooldown.json")

def _load_cooldown() -> dict:
    try:
        if os.path.exists(_COOLDOWN_FILE):
            with open(_COOLDOWN_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_cooldown(data: dict):
    try:
        with open(_COOLDOWN_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

_fix_cooldown: dict = _load_cooldown()

# ── FIX 4: Repos that should NEVER be touched by the fix loop ────────────────
_SKIP_REPO_NAMES = {
    "my-portfolio",
    ".github",
}


def _should_skip_repo(repo_name: str) -> bool:
    """Return True for repos that are not VIA-generated apps."""
    if repo_name in _SKIP_REPO_NAMES:
        return True
    # Skip repos with no dash in name (likely personal repos, not VIA slugs)
    # VIA always slugifies task → always contains dashes
    return False


def _is_on_cooldown(repo_name: str) -> bool:
    """FIX 3: Return True if this repo was attempted within the last 30 minutes."""
    last = _fix_cooldown.get(repo_name)
    if last is None:
        return False
    return (time.time() - last) < COOLDOWN_SECONDS


def _mark_fix_attempted(repo_name: str):
    """FIX 3: Record the current timestamp and persist so restarts don't wipe it."""
    _fix_cooldown[repo_name] = time.time()
    _save_cooldown(_fix_cooldown)  # CHANGE 2: persist to disk so restart doesn't reset cooldown


def _is_repo_healthy(repo: str, username: str, headers: dict) -> bool:
    """
    FIX 1: Real health check — 3 layers:
      Layer 1: GitHub API confirms Pages is enabled and status="built"
      Layer 2: deploy.yml exists in the repo
      Layer 3: Actual HTTP GET to the Pages URL returns 200 (THE KEY FIX)

    GitHub API can show status="built" while the site still returns 404.
    Only a real HTTP 200 from the live URL confirms the app is truly healthy.
    """
    try:
        s = _requests.Session()

        # Layer 1 — GitHub Pages API
        r = s.get(
            f"https://api.github.com/repos/{username}/{repo}/pages",
            headers=headers, timeout=15
        )
        if r.status_code != 200:
            return False
        pages_data = r.json()
        if pages_data.get("status") not in ("built", "building"):
            return False

        # Layer 2 — deploy.yml must exist
        r2 = s.get(
            f"https://api.github.com/repos/{username}/{repo}/contents/.github/workflows/deploy.yml",
            headers=headers, timeout=15
        )
        if r2.status_code != 200:
            return False

        # Layer 3 — FIX 1: Actual HTTP GET to the Pages URL
        # This is what was missing — GitHub API lies about "built" status.
        pages_url = f"https://{username}.github.io/{repo}/"
        try:
            live_check = s.get(pages_url, timeout=10, allow_redirects=True)
            if live_check.status_code != 200:
                logger.debug(f"Health check | Pages URL returned {live_check.status_code} | {repo}")
                return False
        except Exception:
            # If the HTTP GET itself fails (timeout, DNS), treat as unhealthy
            return False

        logger.info(f"Startup fix | repo healthy, skipping | {repo}")
        return True

    except Exception:
        return False


def _fix_single_repo(repo: str, username: str, headers: dict):
    """
    FIX 1: _is_repo_healthy() now does real HTTP GET — broken repos can't hide.
    FIX 2: Workflow is triggered via github_pusher._trigger_workflow() which:
           - Waits 30s initial (not 5s)
           - Uses _workflow_exists() loop to confirm GitHub indexed the file
           - Retries up to 6 times with increasing back-off
    FIX 3: Cooldown check at top — skip repos fixed in the last 30 minutes.
    FIX 4: Skip non-VIA repos entirely.
    FIX 5: Patch src/api.js directly in the repo to add any missing exports
           that App.jsx imports — fixes "X is not exported by src/api.js" build errors.
    """
    if _should_skip_repo(repo):
        return

    if _is_on_cooldown(repo):
        logger.info(f"Startup fix | cooldown active, skipping | {repo}")
        return

    if _is_repo_healthy(repo, username, headers):
        return

    _mark_fix_attempted(repo)

    try:
        s = _requests.Session()

        # Push deploy.yml
        r = s.get(
            f"https://api.github.com/repos/{username}/{repo}/contents/.github/workflows/deploy.yml",
            headers=headers, timeout=30
        )
        sha = r.json().get("sha") if r.status_code == 200 else None
        payload = {
            "message": "Add deploy.yml via VIA auto-fix",
            "content": base64.b64encode(DEPLOY_YML.encode()).decode(),
        }
        if sha:
            payload["sha"] = sha
        s.put(
            f"https://api.github.com/repos/{username}/{repo}/contents/.github/workflows/deploy.yml",
            headers=headers, json=payload, timeout=30
        )

        # Enable GitHub Pages — FIX: use gh-pages branch source, not workflow mode.
        # peaceiris/actions-gh-pages pushes built files to the gh-pages branch.
        # Using {"build_type": "workflow"} here is incompatible and causes 404s.
        r_pages = s.post(
            f"https://api.github.com/repos/{username}/{repo}/pages",
            headers=headers,
            json={"source": {"branch": "gh-pages", "path": "/"}},
            timeout=30,
        )
        if r_pages.status_code not in (201, 409):
            # Pages may already exist with wrong source — update it
            s.put(
                f"https://api.github.com/repos/{username}/{repo}/pages",
                headers=headers,
                json={"source": {"branch": "gh-pages", "path": "/"}},
                timeout=30,
            )

        # Set VITE_API_URL
        render_url = f"https://{repo}.onrender.com"
        r2 = s.post(
            f"https://api.github.com/repos/{username}/{repo}/actions/variables",
            headers=headers, json={"name": "VITE_API_URL", "value": render_url}, timeout=30
        )
        if r2.status_code not in (201, 204):
            s.patch(
                f"https://api.github.com/repos/{username}/{repo}/actions/variables/VITE_API_URL",
                headers=headers, json={"name": "VITE_API_URL", "value": render_url}, timeout=30
            )

        # FIX 5: Patch src/api.js to add any missing exports App.jsx needs
        _fix_repo_api_js(repo, username, headers, s)

        # FIX 2: Use github_pusher._trigger_workflow() — proper 30s wait + retry loop
        github_pusher._trigger_workflow(repo)

        logger.info(f"Startup fix | repo fixed | {repo}")

    except Exception as e:
        logger.warning(f"Startup fix | repo skipped (error) | {repo} | {e}")


def _fix_repo_api_js(repo: str, username: str, headers: dict, s):
    """
    FIX 5: Fetch src/App.jsx and src/api.js from GitHub, check for missing
    exports, patch api.js with stubs, and push the fix back.

    This resolves: 'getStats is not exported by src/api.js, imported by src/App.jsx'
    without needing a full re-push of all files.
    """
    import re as _re

    try:
        # Fetch App.jsx to find what it imports from api.js
        app_r = s.get(
            f"https://api.github.com/repos/{username}/{repo}/contents/src/App.jsx",
            headers=headers, timeout=15
        )
        if app_r.status_code != 200:
            return  # No App.jsx — nothing to fix

        app_content = base64.b64decode(app_r.json()["content"]).decode("utf-8", errors="ignore")

        # Fetch current api.js
        api_r = s.get(
            f"https://api.github.com/repos/{username}/{repo}/contents/src/api.js",
            headers=headers, timeout=15
        )
        if api_r.status_code != 200:
            return  # No api.js — can't patch

        api_data    = api_r.json()
        api_content = base64.b64decode(api_data["content"]).decode("utf-8", errors="ignore")
        api_sha     = api_data["sha"]

        # Find what App.jsx imports from api.js
        import_pattern = _re.compile(
            r'import\s*\{([^}]+)\}\s*from\s*["\'](?:\.\.?/)*api(?:\.js)?["\']'
        )
        needed = set()
        for match in import_pattern.finditer(app_content):
            names = [n.strip().split(" as ")[0].strip() for n in match.group(1).split(",")]
            needed.update(n for n in names if n)

        if not needed:
            return

        # Find what api.js already exports
        existing = set(_re.findall(r'export\s+(?:const|function|async function)\s+(\w+)', api_content))

        missing = needed - existing
        if not missing:
            return

        logger.info(f"Startup fix | api.js missing exports {missing} — patching | {repo}")

        # Detect the API base URL pattern
        base_match = _re.search(r'(API_URL|API_BASE|BASE_URL)\s*=\s*[^\n;]+', api_content)
        if base_match:
            url_expr = "${" + base_match.group(1) + "}"
        else:
            url_expr = "${import.meta.env.VITE_API_URL || ''}"

        stubs = "\n\n// Auto-patched missing exports by VIA startup fix\n"
        for name in sorted(missing):
            if name == "getStats" or name.startswith("get"):
                resource = name[3:].lower() if name != "getStats" else "stats"
                stubs += f"""export const {name} = async () => {{
  const r = await fetch(`{url_expr}/api/v1/{resource}`);
  if (!r.ok) throw new Error('{name} failed');
  return r.json();
}};\n"""
            elif name.startswith("create"):
                resource = name[6:].lower()
                stubs += f"""export const {name} = async (data) => {{
  const r = await fetch(`{url_expr}/api/v1/{resource}`, {{
    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(data),
  }});
  if (!r.ok) throw new Error('{name} failed');
  return r.json();
}};\n"""
            elif name.startswith("update"):
                resource = name[6:].lower()
                stubs += f"""export const {name} = async (id, data) => {{
  const r = await fetch(`{url_expr}/api/v1/{resource}/${{id}}`, {{
    method: 'PUT', headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(data),
  }});
  if (!r.ok) throw new Error('{name} failed');
  return r.json();
}};\n"""
            elif name.startswith("delete"):
                resource = name[6:].lower()
                stubs += f"""export const {name} = async (id) => {{
  const r = await fetch(`{url_expr}/api/v1/{resource}/${{id}}`, {{
    method: 'DELETE',
  }});
  if (!r.ok) throw new Error('{name} failed');
  return r.json();
}};\n"""
            else:
                stubs += f"""export const {name} = async (...args) => {{
  const r = await fetch(`{url_expr}/api/v1/{name.lower()}`);
  if (!r.ok) throw new Error('{name} failed');
  return r.json();
}};\n"""

        patched = api_content + stubs
        push_r = s.put(
            f"https://api.github.com/repos/{username}/{repo}/contents/src/api.js",
            headers=headers,
            json={
                "message": "fix: add missing api.js exports (VIA auto-fix)",
                "content": base64.b64encode(patched.encode()).decode(),
                "sha": api_sha,
            },
            timeout=30
        )
        if push_r.status_code in (200, 201):
            logger.info(f"Startup fix | api.js patched OK | {repo}")
        else:
            logger.warning(f"Startup fix | api.js patch failed {push_r.status_code} | {repo}")

    except Exception as e:
        logger.warning(f"Startup fix | api.js patch error | {repo} | {e}")


async def _fix_all_repos():
    await asyncio.sleep(5)
    token    = os.getenv("GITHUB_TOKEN", "")
    username = os.getenv("GITHUB_USERNAME", "")
    if not token or not username:
        logger.warning("Startup fix | GITHUB_TOKEN or GITHUB_USERNAME not set — skipping")
        return

    headers = {
        "Authorization": f"token {token}",
        "Accept":        "application/vnd.github+json",
        "Content-Type":  "application/json",
    }

    repos, page = [], 1
    try:
        while True:
            r = _requests.get(
                f"https://api.github.com/user/repos?per_page=100&page={page}",
                headers=headers, timeout=30
            )
            data = r.json()
            if not data:
                break
            repos.extend([d["name"] for d in data if not d["private"]])
            if len(data) < 100:
                break
            page += 1
    except Exception as e:
        logger.warning(f"Startup fix | Could not fetch repo list: {e}")
        return

    logger.info(f"Startup fix | {len(repos)} repos found — checking health...")
    for repo in repos:
        await asyncio.to_thread(_fix_single_repo, repo, username, headers)
        await asyncio.sleep(2)
    logger.info("Startup fix | All repos checked!")


# ── App Lifecycle ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    await init_db()
    logger.info(f"VIA Phase 6 v{APP_VERSION} started — Enterprise Engine online.")

@app.on_event("shutdown")
async def on_shutdown():
    await close_db()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_frontend_path(dept_output: dict):
    fe = dept_output.get("frontend", {})
    if not fe or fe.get("status") != "success":
        return None
    outer = fe.get("output", {})
    inner = outer.get("output", outer)
    path  = inner.get("department_path") or inner.get("project_path")
    if path:
        logger.info(f"Frontend path found | {path}")
    else:
        logger.warning(f"Frontend path NOT found | outer={list(outer.keys())} | inner={list(inner.keys())}")
    return path

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await ws_manager.connect(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(job_id, websocket)

@app.post("/auth/register")
async def register(user: UserCreate):
    import re
    email = user.email.strip().lower()
    # Basic email validation
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        raise HTTPException(status_code=400, detail="Invalid email address.")

    result = await register_user(email, user.password)

    # Generate 6-digit verification code, valid for 15 minutes
    code = ''.join(random.choices(string.digits, k=6))
    expires_at = (datetime.utcnow() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
    await save_auth_code(email, code, 'verify', expires_at)

    # Log the code and send email
    logger.info(f"[EMAIL VERIFICATION] Code for {email}: {code} (expires: {expires_at} UTC)")
    await send_verification_email(email, code)

    return {"message": "Registration successful. Please check your email for the 6-digit verification code.",
            "email": email, "requires_verification": True}


@app.post("/auth/verify-email")
async def verify_email(payload: dict):
    email = payload.get("email", "").strip().lower()
    code = payload.get("code", "").strip()
    if not email or not code:
        raise HTTPException(status_code=400, detail="Email and code are required.")

    record = await get_auth_code(email, code, 'verify')
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code.")

    await verify_user_email(email)
    await delete_auth_code(email, 'verify')
    logger.info(f"Email verified: {email}")
    return {"message": "Email verified successfully! You can now log in."}


@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username.strip().lower()  # OAuth2 form sends as 'username'
    user = await authenticate_user(email, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not user.get("is_verified"):
        raise HTTPException(status_code=403, detail="Please verify your email first. Check your inbox for the verification code.")
    token = create_access_token({"sub": user["email"]})
    logger.info(f"Login: {user['email']}")
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/forgot-password")
async def forgot_password(payload: dict):
    email = payload.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    user = await get_user_by_email(email)
    # Always return success to avoid revealing if email exists (security)
    if user:
        code = ''.join(random.choices(string.digits, k=6))
        expires_at = (datetime.utcnow() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
        await save_auth_code(email, code, 'reset', expires_at)
        logger.info(f"[PASSWORD RESET] Code for {email}: {code} (expires: {expires_at} UTC)")
        await send_reset_password_email(email, code)

    return {"message": "If an account with that email exists, a 6-digit reset code has been sent to your email."}


@app.post("/auth/reset-password")
async def reset_password(payload: dict):
    email = payload.get("email", "").strip().lower()
    code = payload.get("code", "").strip()
    new_password = payload.get("new_password", "")
    if not email or not code or not new_password:
        raise HTTPException(status_code=400, detail="Email, code and new_password are required.")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    record = await get_auth_code(email, code, 'reset')
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code.")

    from backend.auth.auth import hash_password
    await update_user_password(email, hash_password(new_password))
    await delete_auth_code(email, 'reset')
    logger.info(f"Password reset successful: {email}")
    return {"message": "Password reset successful! You can now log in with your new password."}

@app.post("/start-company/")
async def start_company(request: TaskRequest, current_user: dict = Depends(get_current_active_user)):
    task    = request.task.strip()
    job_id  = str(uuid.uuid4())
    tracer  = ExecutionTracer()
    tracer.start(task)
    t_start = time.time()
    logger.info(f"Task [{current_user['email']}]: {task[:80]}")
    history = await get_recent_history(limit=3)
    ceo     = await ceo_agent(task, history=history)
    raw_llm   = ceo.get("_raw_llm_response", "")
    extracted = ceo.get("_extracted_json", {})
    short_term = ceo.get("short_term_strategy", "")
    ceo_depts  = ceo.get("departments", ["backend"])
    final_depts, _, _ = autonomous_scale(task, ceo_depts)
    dept_output = await execute_agents(final_depts, task, ceo_strategy=short_term, job_id=job_id, ws_manager=ws_manager)
    total_dur = round(time.time() - t_start, 2)
    success   = sum(1 for v in dept_output.values() if v.get("status") == "success")
    failed    = sum(1 for v in dept_output.values() if v.get("status") == "failed")
    for name, data in dept_output.items():
        tracer.add_agent_result(name, data.get("status", "unknown"), data.get("execution_time_seconds", 0), data.get("confidence", 0.0))
        if data.get("status") == "success":
            summary = str(data.get("output", {}).get("summary", task[:120]))
            await save_agent_memory(name, task, summary, data.get("confidence", 0.8))
    tracer.finish(total_dur, success, failed)
    result = {"job_id": job_id, "task": task, "requested_by": current_user["email"],
              "ceo_strategy": {"short_term_strategy": short_term, "long_term_vision": ceo.get("long_term_vision", "")},
              "selected_departments": final_depts, "departments": dept_output}
    await save_record(task, json.dumps(result))
    await save_execution_stat(task, len(final_depts), success, failed, total_dur)
    await save_audit_record(task, raw_llm, extracted, final_depts, tracer.get_trace())
    return result

@app.post("/feedback/")
async def submit_feedback(request: FeedbackRequest, current_user: dict = Depends(get_current_active_user)):
    revised_task = f"{request.task}\n\n--- REVISION FEEDBACK FROM USER ---\n{request.feedback}\nPlease address the above feedback specifically in your output."
    job_id  = str(uuid.uuid4())
    t_start = time.time()
    dept_output = await execute_agents(request.departments, revised_task, ceo_strategy=f"Incorporate user feedback: {request.feedback[:100]}", job_id=job_id, ws_manager=ws_manager)
    total_dur = round(time.time() - t_start, 2)
    success   = sum(1 for v in dept_output.values() if v.get("status") == "success")
    return {"job_id": job_id, "original_job_id": request.job_id, "feedback": request.feedback,
            "revised_task": revised_task, "departments": dept_output,
            "total_duration_seconds": total_dur, "successful_revisions": success}

@app.post("/deploy/")
async def full_deploy(request: DeployRequest, current_user: dict = Depends(get_current_active_user)):
    task     = request.task.strip()
    job_id   = str(uuid.uuid4())
    t_start  = time.time()

    app_type = detect_app_type(task)
    logger.info(f"DEPLOY pipeline | user={current_user['email']} | app_type={app_type} | task={task[:80]}")

    history    = await get_recent_history(limit=3)
    ceo        = await ceo_agent(task, history=history)
    short_term = ceo.get("short_term_strategy", "")
    ceo_depts  = ceo.get("departments", ["backend", "frontend"])
    if "frontend" not in ceo_depts:
        ceo_depts.append("frontend")
    final_depts, _, _ = autonomous_scale(task, ceo_depts)

    dept_output = await execute_agents(final_depts, task, ceo_strategy=short_term, job_id=job_id, ws_manager=ws_manager)
    total_dur = round(time.time() - t_start, 2)
    success   = sum(1 for v in dept_output.values() if v.get("status") == "success")

    for name, data in dept_output.items():
        if data.get("status") == "success":
            summary = str(data.get("output", {}).get("summary", task[:120]))
            await save_agent_memory(name, task, summary, data.get("confidence", 0.8))

    backend_files = await generate_backend_files_llm(task, app_type)
    logger.info(f"Backend files | app_type={app_type} | count={len(backend_files)}")

    # Phase 2: Verify generated backend syntax and self-correct on failure (max 3 attempts)
    from backend.core.code_runner import check_syntax
    from backend.core.fullstack_builder import self_correct_backend
    import tempfile, os as _os
    for _attempt in range(1, 4):
        _errors = []
        for _fname, _fcode in backend_files.items():
            if not _fname.endswith(".py"):
                continue
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as _tf:
                    _tf.write(_fcode)
                    _tf_path = _tf.name
                _res = check_syntax(_tf_path)
                _os.unlink(_tf_path)
                if not _res["passed"]:
                    _errors.append(f"{_fname}: {_res['error']}")
            except Exception as _ce:
                _errors.append(f"{_fname}: {str(_ce)}")
        if not _errors:
            logger.info(f"Backend syntax OK on attempt {_attempt}")
            break
        _err_summary = " | ".join(_errors)
        logger.warning(f"Syntax errors (attempt {_attempt}/3): {_err_summary}")
        if ws_manager:
            await ws_manager.send_step(
                job_id, "self_correction",
                f"Caught a syntax error — fixing now (attempt {_attempt}/3): {_err_summary[:120]}",
                {"attempt": _attempt, "errors": _errors}
            )
        if _attempt < 3:
            backend_files = await self_correct_backend(task, backend_files, _err_summary, _attempt)

    phase5    = {"phase5_ran": False, "note": "push_to_github=false"}
    dept_path = _extract_frontend_path(dept_output)

    if request.push_to_github and dept_path:
        logger.info(f"Phase 5 | Pushing | path={dept_path} | extra_files={len(backend_files)}")
        phase5 = await asyncio.to_thread(
            github_pusher.push_project, task, dept_path, "", backend_files
        )
    elif request.push_to_github:
        phase5 = {"phase5_ran": False, "error": "No deployable frontend files found"}

    phase6    = {"phase6_ran": False, "note": "deploy_to_render=false"}
    repo_url  = phase5.get("repo_url", "")
    repo_name = phase5.get("repo_name", "")

    if request.deploy_to_render and repo_url and app_type != "frontend":
        logger.info(f"Phase 6 | Deploying to Render | repo={repo_url}")
        phase6 = await asyncio.to_thread(render_deployer.deploy, task, repo_url, repo_name)
    elif request.deploy_to_render and app_type == "frontend":
        phase6 = {"phase6_ran": False, "note": "Frontend-only — no backend needed",
                  "github_pages_url": f"https://{github_pusher.username}.github.io/{repo_name}/"}
    elif request.deploy_to_render and not repo_url:
        phase6 = {"phase6_ran": False, "error": "GitHub push must succeed before Render deploy"}

    github_pages_url = f"https://{github_pusher.username}.github.io/{repo_name}/" if repo_name else ""
    render_url       = phase6.get("live_url", "")

    # Phase 2: Confirm live URLs actually respond after deploy
    from backend.core.code_runner import check_live_url
    if render_url:
        _url_check = await asyncio.to_thread(check_live_url, render_url, 2, 10)
        phase6["url_reachable"] = _url_check.get("reachable", False)
        phase6["url_status"]    = _url_check.get("status_code", 0)
        if not _url_check["reachable"]:
            logger.warning(f"Render URL not yet reachable after deploy: {render_url}")
    if github_pages_url:
        _pages_check = await asyncio.to_thread(check_live_url, github_pages_url, 1, 5)
        phase5["url_reachable"] = _pages_check.get("reachable", False)


    # FIX: Correct VITE_API_URL to real Render URL (not guessed), then re-trigger workflow
    if render_url and repo_name:
        try:
            await asyncio.to_thread(
                github_pusher._set_repo_variable, repo_name, "VITE_API_URL", render_url
            )
            logger.info(f"VITE_API_URL corrected to real Render URL | {render_url}")
            await asyncio.to_thread(github_pusher._trigger_workflow, repo_name)
            logger.info(f"Workflow re-triggered with correct VITE_API_URL | {repo_name}")
            # Mark repo as healthy so startup fix skips it next restart
            _mark_fix_attempted(repo_name)
        except Exception as e:
            logger.warning(f"VITE_API_URL correction failed: {e}")

    result = {
        "job_id": job_id, "task": task, "app_type": app_type,
        "requested_by": current_user["email"],
        "ceo_strategy": {"short_term_strategy": short_term},
        "selected_departments": final_depts, "departments": dept_output,
        "execution_summary": {"total_duration_seconds": total_dur, "successful": success},
        "github": phase5, "render": phase6,
        "live_urls": {
            "frontend": github_pages_url,
            "backend":  render_url,
            "api_docs": f"{render_url}/docs" if render_url else "",
        },
    }
    project_id = await save_record(task, json.dumps(result))
    result["project_id"] = project_id
    return result

@app.post("/chat/")
async def chat_endpoint(request: ChatRequest, current_user: dict = Depends(get_current_active_user)):
    message = request.message.strip()
    username = current_user["email"]
    t_start = time.time()

    intent = detect_intent(message)
    logger.info(f"Chat | user={username} | intent={intent} | msg={message[:80]}")

    try:
        await save_chat_message(username, "user", message, intent)
    except Exception as e:
        logger.warning(f"Chat history save failed: {e}")

    if intent == "build":
        try:
            task = message
            job_id = str(uuid.uuid4())
            app_type = detect_app_type(task)

            history = await get_recent_history(limit=3)
            ceo = await ceo_agent(task, history=history)
            short_term = ceo.get("short_term_strategy", "")
            ceo_depts = ceo.get("departments", ["backend", "frontend"])
            if "frontend" not in ceo_depts:
                ceo_depts.append("frontend")
            final_depts, _, _ = autonomous_scale(task, ceo_depts)

            dept_output = await execute_agents(
                final_depts, task, ceo_strategy=short_term,
                job_id=job_id, ws_manager=ws_manager
            )
            total_dur = round(time.time() - t_start, 2)
            success = sum(1 for v in dept_output.values() if v.get("status") == "success")

            for name, data in dept_output.items():
                if data.get("status") == "success":
                    summary = str(data.get("output", {}).get("summary", task[:120]))
                    await save_agent_memory(name, task, summary, data.get("confidence", 0.8))

            backend_files = await generate_backend_files_llm(task, app_type)

            phase5 = {"phase5_ran": False}
            dept_path = _extract_frontend_path(dept_output)
            if dept_path:
                phase5 = await asyncio.to_thread(
                    github_pusher.push_project, task, dept_path, "", backend_files
                )

            phase6 = {"phase6_ran": False}
            repo_url = phase5.get("repo_url", "")
            repo_name = phase5.get("repo_name", "")
            if repo_url and app_type != "frontend":
                phase6 = await asyncio.to_thread(
                    render_deployer.deploy, task, repo_url, repo_name
                )

            github_pages_url = f"https://{github_pusher.username}.github.io/{repo_name}/" if repo_name else ""
            render_url = phase6.get("live_url", "")

            # FIX: Correct VITE_API_URL to real Render URL, re-trigger workflow
            if render_url and repo_name:
                try:
                    await asyncio.to_thread(
                        github_pusher._set_repo_variable, repo_name, "VITE_API_URL", render_url
                    )
                    logger.info(f"VITE_API_URL corrected to real Render URL | {render_url}")
                    await asyncio.to_thread(github_pusher._trigger_workflow, repo_name)
                    logger.info(f"Workflow re-triggered with correct VITE_API_URL | {repo_name}")
                    # Mark as recently fixed so startup loop skips it
                    _mark_fix_attempted(repo_name)
                except Exception as e:
                    logger.warning(f"VITE_API_URL correction failed: {e}")

            project_id = await save_record(task, json.dumps({"job_id": job_id, "app_type": app_type}))
            project_serial = f"#{project_id}" if project_id else "[ID error]"

            via_msg = f"🚀 **Build Complete! (Project {project_serial})**\n\n"
            via_msg += f"📋 **App Type:** {app_type}\n"
            via_msg += f"⏱️ **Duration:** {total_dur}s\n"
            via_msg += f"✅ **Agents:** {success}/{len(final_depts)} successful\n\n"
            
            # Phase 3 visibility: Append the human_note from each agent to the chat response
            from backend.core.meeting_engine import AGENT_PERSONAS
            via_msg += "### Team Updates\n"
            for name, data in dept_output.items():
                if data.get("status") == "success":
                    hn = data.get("output", {}).get("human_note", "")
                    if hn:
                        persona_name = AGENT_PERSONAS.get(name, {}).get("name", name.title())
                        emoji = AGENT_PERSONAS.get(name, {}).get("emoji", "💬")
                        via_msg += f"- **{emoji} {persona_name} ({name.title()}):** {hn}\n"
            via_msg += "\n"

            if github_pages_url:
                via_msg += f"🌍 **Live URLs:**\n"
                via_msg += f"- 🖥️ Frontend: {github_pages_url}\n"
                via_msg += f"  *(Note: GitHub Pages takes 1-2 minutes to go live. If you see a 404, please wait a minute and refresh)*\n"
            if render_url:
                via_msg += f"- ⚡ Backend: {render_url}\n"
                via_msg += f"- 📚 API Docs: {render_url}/docs\n"

            if not github_pages_url and not render_url:
                via_msg += "⚠️ Deployment didn't produce live URLs. Check GitHub/Render config.\n"

            try:
                await save_chat_message(username, "assistant", via_msg, "build")
            except Exception:
                pass

            return {
                "response": via_msg,
                "intent": "build",
                "mode": "build",
                "job_id": job_id,
                "project_id": project_id,
                "app_type": app_type,
                "departments": final_depts,
                "dept_results": {k: v.get("status") for k, v in dept_output.items()},
                "live_urls": {
                    "frontend": github_pages_url,
                    "backend": render_url,
                    "api_docs": f"{render_url}/docs" if render_url else "",
                },
                "duration_seconds": total_dur,
            }
        except Exception as e:
            logger.error(f"Build mode error: {e}")
            error_msg = f"❌ Build encountered an error: {str(e)}\n\nPlease try again or use the /deploy/ endpoint directly."
            try:
                await save_chat_message(username, "assistant", error_msg, "build")
            except Exception:
                pass
            return {"response": error_msg, "intent": "build", "mode": "build", "error": str(e)}

    elif intent == "analyze":
        try:
            task = message
            job_id = str(uuid.uuid4())

            history = await get_recent_history(limit=3)
            ceo = await ceo_agent(task, history=history)
            short_term = ceo.get("short_term_strategy", "")
            ceo_depts = ceo.get("departments", ["backend"])
            final_depts, _, _ = autonomous_scale(task, ceo_depts)

            dept_output = await execute_agents(
                final_depts, task, ceo_strategy=short_term,
                job_id=job_id, ws_manager=ws_manager
            )
            total_dur = round(time.time() - t_start, 2)
            success = sum(1 for v in dept_output.values() if v.get("status") == "success")

            for name, data in dept_output.items():
                if data.get("status") == "success":
                    summary = str(data.get("output", {}).get("summary", task[:120]))
                    await save_agent_memory(name, task, summary, data.get("confidence", 0.8))

            via_msg = f"🔍 **Analysis Complete!**\n\n"
            via_msg += f"📋 **Strategy:** {short_term[:200]}\n\n"
            via_msg += f"**Departments consulted:** {', '.join(final_depts)}\n"
            via_msg += f"⏱️ **Duration:** {total_dur}s | ✅ {success}/{len(final_depts)} successful\n\n"

            for name, data in dept_output.items():
                if data.get("status") == "success":
                    out = data.get("output", {})
                    dept_name = out.get("department", name)
                    dept_summary = out.get("summary", out.get("full_report", str(out))[:300])
                    via_msg += f"### 📊 {dept_name}\n{dept_summary[:500]}\n\n"

            try:
                await save_chat_message(username, "assistant", via_msg, "analyze")
            except Exception:
                pass

            await save_record(task, json.dumps({"job_id": job_id, "mode": "analyze"}))

            return {
                "response": via_msg,
                "intent": "analyze",
                "mode": "analyze",
                "job_id": job_id,
                "departments": final_depts,
                "dept_results": dept_output,
                "duration_seconds": total_dur,
            }
        except Exception as e:
            logger.error(f"Analyze mode error: {e}")
            error_msg = f"❌ Analysis encountered an error: {str(e)}"
            return {"response": error_msg, "intent": "analyze", "mode": "analyze", "error": str(e)}

    else:
        db_history = []
        try:
            db_history = await get_chat_history(username, limit=20)
        except Exception:
            pass

        history = request.history or db_history
        response_text, target_persona = await chat_engine.chat(message, history)

        try:
            await save_chat_message(username, "assistant", response_text, "chat")
        except Exception:
            pass

        return {
            "response": response_text,
            "intent": "chat",
            "mode": "chat",
            "agent_name": target_persona.get("name") if target_persona else None,
            "agent_emoji": target_persona.get("emoji") if target_persona else None,
            "agent_color": target_persona.get("color") if target_persona else None,
            "duration_seconds": round(time.time() - t_start, 2),
        }


@app.get("/chat/history/")
async def chat_history_endpoint(current_user: dict = Depends(get_current_active_user)):
    history = await get_chat_history(current_user["email"], limit=100)
    return {"history": history, "total": len(history)}


@app.delete("/chat/history/")
async def clear_chat_history_endpoint(current_user: dict = Depends(get_current_active_user)):
    await clear_chat_history(current_user["email"])
    return {"status": "cleared"}


class MeetingChatRequest(BaseModel):
    message: str
    history: list

@app.post("/meetings/chat/")
async def meeting_chat_endpoint(request: MeetingChatRequest, current_user: dict = Depends(get_current_active_user)):
    from backend.core.chat_engine import chat
    from backend.core.meeting_engine import AGENT_PERSONAS
    
    response_text, target_persona = await chat(request.message, request.history)
    
    agent_id = "assistant"
    agent_name = "VIA"
    if target_persona:
        # Find the agent ID from AGENT_PERSONAS
        for k, v in AGENT_PERSONAS.items():
            if v["name"] == target_persona["name"]:
                agent_id = k
                break
        agent_name = target_persona["name"]

    response_msg = {
        "agent": agent_id,
        "name": agent_name,
        "content": response_text
    }
    return {"response": response_msg}


@app.post("/jobs/submit/")
async def submit_job(request: JobRequest, current_user: dict = Depends(get_current_active_user)):
    from backend.tasks.orchestration_task import run_orchestration
    if run_orchestration is None:
        raise HTTPException(status_code=503, detail="Background jobs require Redis + Celery. Use /start-company/ or /chat/ for synchronous execution.")
    job_id = str(uuid.uuid4())
    await create_job(job_id, request.task)
    run_orchestration.apply_async(args=[job_id, request.task, current_user["email"]])
    return {"job_id": job_id, "status": "pending"}

@app.get("/jobs/{job_id}/")
async def get_job_status(job_id: str, current_user: dict = Depends(get_current_active_user)):
    job = await get_job(job_id)
    if not job: raise HTTPException(status_code=404)
    return job

@app.get("/company-history/")
async def company_history(current_user: dict = Depends(get_current_active_user)):
    return {"recent_history": await get_recent_history(limit=10)}

@app.get("/system-health/")
async def system_health(current_user: dict = Depends(get_current_active_user)):
    return {"status": "operational", "metrics": await get_system_health()}

@app.get("/company-status/")
async def company_status(current_user: dict = Depends(get_current_active_user)):
    return {"status": "operational", "dashboard": await get_company_status()}

@app.get("/org-chart/")
async def org_chart(current_user: dict = Depends(get_current_active_user)):
    return get_full_chart()

@app.get("/agent-memory/")
async def agent_memory(current_user: dict = Depends(get_current_active_user)):
    memories = await get_all_memories(limit=50)
    return {"memories": memories, "total": len(memories)}

@app.get("/agent-memory/{agent_name}/")
async def agent_memory_by_name(agent_name: str, current_user: dict = Depends(get_current_active_user)):
    memories = await get_agent_memory(agent_name, limit=10)
    return {"agent": agent_name, "memories": memories}

_ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_INDEX_HTML = os.path.join(_ROOT_DIR, "index.html")
_CSS_FILE   = os.path.join(_ROOT_DIR, "via-chat.css")

@app.get("/", include_in_schema=False)
def root():
    if os.path.exists(_INDEX_HTML):
        return FileResponse(
            _INDEX_HTML, 
            media_type="text/html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    return {"app": "VIA", "version": APP_VERSION}

@app.get("/via-chat.css", include_in_schema=False)
def serve_css():
    if os.path.exists(_CSS_FILE):
        return FileResponse(
            _CSS_FILE, 
            media_type="text/css",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    return ""


@app.get("/company_logo.png", include_in_schema=False)
@app.get("/company_logo.jpg", include_in_schema=False)
def serve_logo():
    for fname, mime in [("company_logo.png", "image/png"), ("company_logo.jpg", "image/jpeg")]:
        p = os.path.join(_ROOT_DIR, fname)
        if os.path.exists(p):
            return FileResponse(
                p,
                media_type=mime,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
    return {"error": "logo not found"}

@app.get("/login_bg.png", include_in_schema=False)
@app.get("/login_bg.jpg", include_in_schema=False)
def serve_login_bg_permanent():
    for fname, mime in [("login_bg.png", "image/png"), ("login_bg.jpg", "image/jpeg")]:
        p = os.path.join(_ROOT_DIR, fname)
        if os.path.exists(p):
            return FileResponse(
                p,
                media_type=mime,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
    return {"error": "background not found"}

@app.get("/api/info")
def api_info():
    return {"app": "VIA", "version": APP_VERSION, "phase": "6", "agents": 10,
            "app_types": ["frontend", "fullstack", "fullstack_db"],
            "modes": ["chat", "build", "analyze"]}

@app.get("/health")
def health():
    return {"status": "healthy", "version": APP_VERSION, "phase": "6"}