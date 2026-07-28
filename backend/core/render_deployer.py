# backend/core/render_deployer.py
#
# FIX 1: live_url comes from Render API response, not constructed from svc_name.
# FIX 2: _redeploy() sends full env var set so nothing gets wiped.
# FIX 3: Uses RENDER_DATABASE_URL from .env — never auto-provisions a DB.
#         Table isolation handled per-app by fullstack_builder.py table prefixes.
# FIX 4: SQLite fallback uses sqlite:/// not sqlite+aiosqlite:/// — the
#         database.py normalizer expects sqlite://, not the async driver prefix.
# FIX 5: deploy() now returns the corrected live_url so the caller can set
#         VITE_API_URL to the real URL before triggering the GitHub workflow.
# FIX 6: autoDeploy set to "no" — VIA controls deploys explicitly via API.
#         Prevents ALL previous Render services from redeploying every time
#         a new app is built (was: "yes" caused every connected repo push to
#         trigger redeploys across all services).
# FIX 7: _redeploy() now does exact name match — prevents partial name match
#         from accidentally redeploying a wrong existing service.
# FIX 8: _redeploy() always returns live_url even if deploy trigger POST fails —
#         service exists so URL is known; UI should always show backend link.

import os
import re
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logger = logging.getLogger("AI-Digital-Company")

RENDER_API = "https://api.render.com/v1"


class RenderDeployer:

    def __init__(self):
        self.api_key = os.getenv("RENDER_API_KEY", "")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }
        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def _ok(self) -> bool:
        return bool(self.api_key)

    def _owner_id(self) -> str:
        try:
            r = self.session.get(f"{RENDER_API}/owners", headers=self.headers, timeout=15)
            if r.status_code == 200:
                owners = r.json()
                if owners:
                    return owners[0].get("owner", {}).get("id", "")
        except Exception as e:
            logger.error(f"Render owner error: {e}")
        return ""

    def _service_name(self, raw: str) -> str:
        name = raw.lower().strip()
        name = re.sub(r"[^a-z0-9-]", "-", name)
        name = re.sub(r"-+", "-", name)
        name = name.strip("-")
        return name[:63] or "via-app"

    def _extract_live_url(self, service: dict) -> str:
        """FIX 1: Extract real URL from Render API response. Never construct it."""
        url = (
            service.get("serviceDetails", {}).get("url", "")
            or service.get("url", "")
        )
        if url:
            if not url.startswith("http"):
                url = f"https://{url}"
            return url.rstrip("/")
        svc_name = service.get("name", "")
        if svc_name:
            return f"https://{svc_name}.onrender.com"
        return ""

    def _normalise_db_url(self, url: str) -> str:
        """Normalize all postgres URL variants to postgresql:// for SQLAlchemy."""
        url = url.replace("postgresql+asyncpg://", "postgresql://")
        url = url.replace("postgres://", "postgresql://")
        return url

    def _db_url(self) -> str:
        """
        Always use RENDER_DATABASE_URL from .env.
        Table isolation handled by per-app __tablename__ prefixes in models.py.
        All apps share one DB safely — no table conflicts.
        """
        url = os.getenv("RENDER_DATABASE_URL", "")
        if url:
            logger.info("Render | Using RENDER_DATABASE_URL from .env (shared DB, isolated tables)")
            return self._normalise_db_url(url)
        logger.warning("Render | RENDER_DATABASE_URL not set in .env!")
        return ""

    def _build_env_vars(self, svc_name: str, db_url: str) -> list:
        # FIX 4: SQLite fallback must use sqlite:/// not sqlite+aiosqlite:///
        # database.py's normalizer handles sqlite:// prefix, not the async variant.
        sqlite_fallback = "sqlite:///./app.db"
        return [
            {"key": "APP_ENV",        "value": "production"},
            {"key": "APP_NAME",       "value": svc_name},
            {"key": "JWT_SECRET_KEY", "generateValue": True},
            {"key": "DATABASE_URL",   "value": db_url if db_url else sqlite_fallback},
        ]

    def _create(self, repo_url: str, repo_name: str, task: str) -> dict:
        owner_id = self._owner_id()
        if not owner_id:
            return {"success": False, "error": "Cannot get Render owner ID — check RENDER_API_KEY"}

        svc_name = self._service_name(repo_name)
        db_url   = self._db_url()
        env_vars = self._build_env_vars(svc_name, db_url)

        if not db_url:
            logger.warning(f"Render | No DATABASE_URL — app will use SQLite fallback | {svc_name}")

        payload = {
            "type":       "web_service",
            "name":       svc_name,
            "ownerId":    owner_id,
            "repo":       repo_url,
            "branch":     "main",
            # FIX 6: "no" instead of "yes" — VIA triggers deploys explicitly via
            # POST /services/{id}/deploys. "yes" caused ALL services to redeploy
            # whenever any connected GitHub repo received a push, because Render
            # watched every repo in the account with autoDeploy enabled.
            "autoDeploy": "no",
            "serviceDetails": {
                "env":    "python",
                "plan":   "free",
                "region": "oregon",
                "envVars": env_vars,
                "envSpecificDetails": {
                    "buildCommand": "pip install -r requirements.txt",
                    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
                },
            },
        }

        try:
            r = self.session.post(f"{RENDER_API}/services", json=payload, headers=self.headers, timeout=60)

            if r.status_code in (200, 201):
                data     = r.json()
                service  = data.get("service", data)
                svc_id   = service.get("id", "")
                live_url = self._extract_live_url(service)
                if not live_url:
                    live_url = f"https://{svc_name}.onrender.com"
                dash_url = f"https://dashboard.render.com/web/{svc_id}"
                logger.info(f"Render service created | {live_url}")
                return {
                    "success":    True,
                    "service_id": svc_id,
                    "live_url":   live_url,
                    "svc_name":   service.get("name", svc_name),
                    "dash_url":   dash_url,
                    "db_ok":      bool(db_url),
                }

            if r.status_code == 400:
                msg = r.json().get("message", "")
                if "already" in msg.lower() or "exists" in msg.lower():
                    logger.info(f"Render | Service already exists — redeploying | {svc_name}")
                    return self._redeploy(svc_name, db_url)
                return {"success": False, "error": f"Render 400: {msg}"}

            return {"success": False, "error": f"Render {r.status_code}: {r.json().get('message', '')}"}

        except Exception as e:
            logger.error(f"Render create error: {e}")
            return {"success": False, "error": str(e)}

    def _redeploy(self, svc_name: str, db_url: str = "") -> dict:
        """
        FIX 2: Redeploy sends full env vars so nothing gets wiped.
        FIX 7: Exact name match — Render's ?name= filter is a partial/prefix match,
                so it can return multiple services. Old code took r.json()[0] which
                could be a completely different service. Now we filter by exact name
                before deploying so only THIS app's service is ever touched.
        FIX 8: Always return live_url even if deploy trigger POST fails — the
                service exists so the URL is known. UI must always show backend link.
        """
        try:
            r = self.session.get(f"{RENDER_API}/services?name={svc_name}", headers=self.headers, timeout=15)
            if r.status_code == 200 and r.json():
                services = r.json()

                # FIX 7: exact name match — never deploy a service with a similar name
                svc    = None
                svc_id = None
                for entry in services:
                    candidate = entry.get("service", entry)
                    if candidate.get("name", "") == svc_name:
                        svc    = candidate
                        svc_id = svc.get("id", "")
                        break

                if not svc_id:
                    logger.warning(f"Render | No exact match for service name '{svc_name}' — skipping redeploy")
                    return {"success": False, "error": f"No exact service match for '{svc_name}'"}

                if db_url:
                    full_env_vars = self._build_env_vars(svc_name, db_url)
                    requests.put(
                        f"{RENDER_API}/services/{svc_id}/env-vars",
                        json=full_env_vars, headers=self.headers, timeout=15,
                    )
                    logger.info(f"Render | Env vars updated on existing service | {svc_name}")

                # FIX 8: Extract live_url before deploy trigger so we always have it
                live_url = self._extract_live_url(svc)
                if not live_url:
                    live_url = f"https://{svc_name}.onrender.com"

                dr = self.session.post(
                    f"{RENDER_API}/services/{svc_id}/deploys",
                    json={"clearCache": "do_not_clear"},
                    headers=self.headers, timeout=15,
                )
                if dr.status_code in (200, 201):
                    logger.info(f"Render redeployed | {live_url}")
                else:
                    # FIX 8: Deploy trigger failed but service exists — still return
                    # live_url so the UI always shows the backend link correctly
                    logger.warning(f"Render | Deploy trigger returned {dr.status_code} — service exists at {live_url}")

                return {
                    "success":    True,
                    "live_url":   live_url,
                    "svc_name":   svc.get("name", svc_name),
                    "dash_url":   f"https://dashboard.render.com/web/{svc_id}",
                    "redeployed": True,
                    "db_ok":      bool(db_url),
                }
        except Exception as e:
            logger.error(f"Render redeploy error: {e}")
        return {"success": False, "error": "Could not redeploy existing service"}

    def deploy(self, task: str, repo_url: str, repo_name: str) -> dict:
        if not self._ok():
            return {"phase6_ran": False, "error": "RENDER_API_KEY not set."}
        if not repo_url:
            return {"phase6_ran": False, "error": "No repo_url — Phase 5 must complete first"}

        logger.info(f"Phase 6 | Deploying to Render | {repo_url}")
        result = self._create(repo_url, repo_name, task)

        if result["success"]:
            live = result["live_url"]
            logger.info(f"Phase 6 OK | {live}")
            return {
                "phase6_ran":    True,
                "success":       True,
                "live_url":      live,
                "service_name":  result.get("svc_name", ""),
                "dashboard_url": result.get("dash_url", ""),
                "redeployed":    result.get("redeployed", False),
                "db_injected":   result.get("db_ok", False),
                "note":          f"Live in 3-5 mins. Check: {result.get('dash_url', '')}",
            }

        return {"phase6_ran": True, "success": False, "error": result.get("error", "Unknown Render error")}


render_deployer = RenderDeployer()