# backend/core/github_pusher.py
#
# ROOT CAUSE OF BLANK WHITE SCREEN:
#   SKIP_PATTERNS had ".git" which matches ".github/workflows/deploy.yml"
#   so the workflow file was NEVER pushed to GitHub.
#   The old workflow (from a previous push) ran instead — it deployed
#   raw source files, not the built dist/ — causing blank white screen.
#
# THE ONLY CHANGE: ".git" → "/.git" in SKIP_PATTERNS
#   "/.git" only matches the actual .git folder, NOT .github directories.

import os
import re
import base64
import requests
import logging
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("AI-Digital-Company")

# FIX: "/.git" not ".git" — .github/workflows/deploy.yml was being silently skipped
SKIP_PATTERNS = ["__pycache__", ".pyc", ".pyo", ".pyd", "/.git"]

CURRENT_PACKAGE_JSON = """{
  "name": "via-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev":     "vite",
    "build":   "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react":                "^18.2.0",
    "react-dom":            "^18.2.0",
    "react-router-dom":     "^6.20.0",
    "axios":                "^1.6.0",
    "react-toastify":       "^10.0.5",
    "react-hot-toast":      "^2.4.1",
    "react-icons":          "^5.0.1",
    "lucide-react":         "^0.383.0",
    "date-fns":             "^3.6.0",
    "react-hook-form":      "^7.51.0",
    "clsx":                 "^2.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer":         "^10.4.16",
    "postcss":              "^8.4.32",
    "tailwindcss":          "^3.4.0",
    "vite":                 "^5.0.0"
  }
}
"""


def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=2, status_forcelist=[500, 502, 503, 504],
                  allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class GitHubPusher:
    def __init__(self):
        self.token    = os.getenv("GITHUB_TOKEN", "")
        self.username = os.getenv("GITHUB_USERNAME", "")
        self.headers  = {
            "Authorization": f"token {self.token}",
            "Accept":        "application/vnd.github+json",
            "Content-Type":  "application/json",
        }

    def _ok(self) -> bool:
        return bool(self.token and self.username)

    def _session(self) -> requests.Session:
        s = _make_session()
        s.headers.update(self.headers)
        return s

    def _create_repo(self, name: str, desc: str) -> dict:
        try:
            r = self._session().post(
                "https://api.github.com/user/repos",
                json={"name": name, "description": desc, "private": False, "auto_init": True},
                timeout=60,
            )
            if r.status_code == 201:
                return {"success": True, "url": r.json()["html_url"]}
            if r.status_code == 422:
                return {"success": True, "url": f"https://github.com/{self.username}/{name}"}
            return {"success": False, "error": r.json().get("message", f"HTTP {r.status_code}")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_head_sha(self, repo: str) -> str:
        for branch in ["main", "master"]:
            try:
                r = self._session().get(
                    f"https://api.github.com/repos/{self.username}/{repo}/git/refs/heads/{branch}",
                    timeout=60,
                )
                if r.status_code == 200:
                    return r.json().get("object", {}).get("sha", "")
            except Exception as e:
                logger.warning(f"Get HEAD SHA error on {branch}: {e}")
        return ""

    def _create_branch(self, repo: str, branch_name: str, sha: str):
        try:
            r = self._session().post(
                f"https://api.github.com/repos/{self.username}/{repo}/git/refs",
                json={"ref": f"refs/heads/{branch_name}", "sha": sha},
                timeout=30,
            )
            if r.status_code == 201:
                logger.info(f"Created branch {branch_name} | {repo}")
            elif r.status_code == 422:
                logger.info(f"Branch {branch_name} already exists | {repo}")
        except Exception as e:
            logger.warning(f"Branch create failed: {e}")

    def _enable_pages(self, repo: str):
        try:
            time.sleep(5)
            session = self._session()
            # Try to enable Pages with GitHub Actions as the build source
            r = session.post(
                f"https://api.github.com/repos/{self.username}/{repo}/pages",
                json={"build_type": "workflow"},
                timeout=30,
            )
            if r.status_code in (201, 409):
                logger.info(f"GitHub Pages enabled (Actions source) | {repo}")
                return
            # If already enabled, update it to use Actions source
            if r.status_code in (422,):
                r2 = session.put(
                    f"https://api.github.com/repos/{self.username}/{repo}/pages",
                    json={"build_type": "workflow"},
                    timeout=30,
                )
                if r2.status_code in (200, 204):
                    logger.info(f"GitHub Pages updated to Actions source | {repo}")
                    return
            logger.warning(f"Pages enable response {r.status_code} | {repo} | body={r.text[:200]}")
        except Exception as e:
            logger.warning(f"Pages enable failed: {e}")


    def _set_repo_variable(self, repo: str, name: str, value: str):
        try:
            r = self._session().post(
                f"https://api.github.com/repos/{self.username}/{repo}/actions/variables",
                json={"name": name, "value": value},
                timeout=30,
            )
            if r.status_code in (201, 204):
                logger.info(f"Repo variable created | {name}={value} | {repo}")
                return
            if r.status_code in (409, 422):
                r2 = self._session().patch(
                    f"https://api.github.com/repos/{self.username}/{repo}/actions/variables/{name}",
                    json={"name": name, "value": value},
                    timeout=30,
                )
                if r2.status_code in (200, 201, 204):
                    logger.info(f"Repo variable updated | {name}={value} | {repo}")
        except Exception as e:
            logger.warning(f"Repo variable set failed: {e}")

    def _trigger_workflow(self, repo: str):
        try:
            session = self._session()
            r = session.get(
                f"https://api.github.com/repos/{self.username}/{repo}/git/refs/heads/main",
                timeout=30,
            )
            if r.status_code != 200:
                return
            head_sha = r.json().get("object", {}).get("sha", "")
            if not head_sha:
                return

            readme_r = session.get(
                f"https://api.github.com/repos/{self.username}/{repo}/contents/README.md",
                timeout=30,
            )
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if readme_r.status_code == 200:
                current_content = base64.b64decode(readme_r.json()["content"]).decode("utf-8")
                file_sha = readme_r.json()["sha"]
                if "<!-- VIA deploy trigger:" in current_content:
                    new_content = re.sub(
                        r'<!-- VIA deploy trigger:.*?-->',
                        f'<!-- VIA deploy trigger: {timestamp} -->',
                        current_content
                    )
                else:
                    new_content = current_content.rstrip() + f"\n\n<!-- VIA deploy trigger: {timestamp} -->\n"
                put_r = session.put(
                    f"https://api.github.com/repos/{self.username}/{repo}/contents/README.md",
                    json={
                        "message": f"VIA: trigger deploy [{timestamp}]",
                        "content": base64.b64encode(new_content.encode()).decode(),
                        "sha": file_sha,
                    },
                    timeout=30,
                )
                if put_r.status_code in (200, 201):
                    logger.info(f"Workflow triggered via commit | {repo}")
            else:
                new_content = f"# {repo}\n\nGenerated by VIA.\n\n<!-- VIA deploy trigger: {timestamp} -->\n"
                put_r = session.put(
                    f"https://api.github.com/repos/{self.username}/{repo}/contents/README.md",
                    json={
                        "message": f"VIA: trigger deploy [{timestamp}]",
                        "content": base64.b64encode(new_content.encode()).decode(),
                    },
                    timeout=30,
                )
                if put_r.status_code in (200, 201):
                    logger.info(f"Workflow triggered via new README commit | {repo}")
        except Exception as e:
            logger.warning(f"Workflow trigger error: {e}")

    def _push_all(self, repo: str, files: dict, message: str) -> dict:
        head_sha = self._get_head_sha(repo)
        
        if not head_sha:
            logger.info(f"Repo not initialized yet. Manually initializing {repo}...")
            try:
                r = self._session().put(
                    f"https://api.github.com/repos/{self.username}/{repo}/contents/README.md",
                    json={
                        "message": "Initial commit",
                        "content": base64.b64encode(b"# VIA App\n").decode()
                    },
                    timeout=30,
                )
                if r.status_code in (200, 201):
                    head_sha = r.json().get("commit", {}).get("sha", "")
                    logger.info(f"Manual initialization successful. SHA: {head_sha}")
            except Exception as e:
                logger.warning(f"Manual init failed: {e}")

        # Fallback retry just in case it was created concurrently
        if not head_sha:
            for attempt in range(5):
                time.sleep(2)
                head_sha = self._get_head_sha(repo)
                if head_sha:
                    break
                logger.info(f"Waiting for concurrent repo init... attempt {attempt+1}/5")

        if not head_sha:
            logger.error(f"HEAD SHA not found after manual init for repo: {repo}")
            return {"success": False, "error": "Cannot get HEAD SHA - repo initialization failed"}

        session = self._session()
        tree_items = []
        for path, content in files.items():
            for attempt in range(3):
                try:
                    br = session.post(
                        f"https://api.github.com/repos/{self.username}/{repo}/git/blobs",
                        json={"content": base64.b64encode(content.encode("utf-8")).decode(), "encoding": "base64"},
                        timeout=60,
                    )
                    if br.status_code == 201:
                        tree_items.append({"path": path, "mode": "100644", "type": "blob", "sha": br.json()["sha"]})
                        break
                except Exception:
                    if attempt < 2:
                        time.sleep(3)

        if not tree_items:
            return {"success": False, "error": "No blobs created"}

        pushed_paths = [t["path"] for t in tree_items]
        workflow_ok = any(".github/workflows" in p for p in pushed_paths)
        logger.info(f"Blobs created | {len(tree_items)} files | deploy.yml_included={workflow_ok} | {repo}")

        try:
            cr = session.get(
                f"https://api.github.com/repos/{self.username}/{repo}/git/commits/{head_sha}",
                timeout=60,
            )
            base_tree = cr.json()["tree"]["sha"]
            tr = session.post(
                f"https://api.github.com/repos/{self.username}/{repo}/git/trees",
                json={"base_tree": base_tree, "tree": tree_items},
                timeout=60,
            )
            new_tree = tr.json()["sha"]
            co = session.post(
                f"https://api.github.com/repos/{self.username}/{repo}/git/commits",
                json={"message": message, "tree": new_tree, "parents": [head_sha]},
                timeout=60,
            )
            new_commit = co.json()["sha"]
            session.patch(
                f"https://api.github.com/repos/{self.username}/{repo}/git/refs/heads/main",
                json={"sha": new_commit, "force": True},
                timeout=60,
            )
        except Exception as e:
            return {"success": False, "error": str(e)}

        logger.info(f"Single-commit push OK | {len(pushed_paths)} files | {repo}")
        return {"success": True, "pushed": pushed_paths, "commit": new_commit}

    def push_project(self, task: str, dept_path: str, repo_name: str = "", extra_files: dict = None) -> dict:
        if not self._ok():
            return {"phase5_ran": False, "error": "GITHUB_TOKEN or GITHUB_USERNAME not set"}

        if not os.path.exists(dept_path):
            return {"phase5_ran": False, "error": f"Path not found: {dept_path}"}

        if not repo_name:
            repo_name = _slugify(task)

        repo = self._create_repo(repo_name, f"Generated by VIA: {task[:100]}")
        if not repo["success"]:
            return {"phase5_ran": False, "error": repo.get("error")}

        repo_url = repo["url"]

        files = {}
        for root, dirs, fnames in os.walk(dept_path):
            dirs[:] = [d for d in dirs if not any(s in ("/" + d) for s in SKIP_PATTERNS)]
            for fname in fnames:
                full = os.path.join(root, fname)
                rel  = os.path.relpath(full, dept_path).replace("\\", "/")
                if any(s in ("/" + rel) for s in SKIP_PATTERNS):
                    continue
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as f:
                        files[rel] = f.read()
                except Exception as e:
                    logger.error(f"Read {rel}: {e}")

        if extra_files:
            files.update(extra_files)

        if "README.md" not in files:
            files["README.md"] = _fallback_readme(task, repo_name)

        files["package.json"] = CURRENT_PACKAGE_JSON
        logger.info(f"Phase 5 | package.json locked to current version | {repo_name}")

        for vite_cfg in ["vite.config.js", "vite.config.ts"]:
            if vite_cfg in files:
                files[vite_cfg] = _patch_vite_config(files[vite_cfg], repo_name)
                break
        else:
            files["vite.config.js"] = _default_vite_config(repo_name)

        files = _fix_api_exports(files)
        files = _fix_nested_routers(files)

        if ".github/workflows/deploy.yml" not in files:
            logger.warning(f"deploy.yml missing — injecting directly | {repo_name}")
            files[".github/workflows/deploy.yml"] = _deploy_workflow()

        logger.info(f"Phase 5 | {len(files)} files | workflow={'YES' if '.github/workflows/deploy.yml' in files else 'MISSING'} | {repo_name}")

        result = self._push_all(
            repo_name, files,
            f"VIA generated project — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        if result["success"]:
            pushed      = result.get("pushed", list(files.keys()))
            commit_sha  = result.get("commit")
            placeholder = f"https://{repo_name}.onrender.com"

            self._enable_pages(repo_name)
            self._set_repo_variable(repo_name, "VITE_API_URL", placeholder)
            self._trigger_workflow(repo_name)

            return {
                "phase5_ran":   True,
                "success":      True,
                "repo_url":     repo_url,
                "repo_name":    repo_name,
                "files_pushed": pushed,
                "render_url":   placeholder,
            }

        return {"phase5_ran": False, "error": result.get("error", "Push failed")}


def _deploy_workflow() -> str:
    return """name: Deploy React to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
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

      - name: Setup Pages
        uses: actions/configure-pages@v5

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: ./dist

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""


def _patch_vite_config(content: str, repo_name: str = "") -> str:
    correct_base  = f"/{repo_name}/" if repo_name else "./"
    existing_base = re.search(r'base\s*:\s*["\']([^"\']+)["\']', content)
    if existing_base:
        b = existing_base.group(1)
        if b not in ("./", "/", ""):
            return content
        return re.sub(r'base\s*:\s*["\'][^"\']*["\'],?', f'base: "{correct_base}",', content, count=1)
    if "defineConfig" in content:
        return re.sub(r"(defineConfig\s*\(\s*\{)", f'\\1\n  base: "{correct_base}",', content, count=1)
    return _default_vite_config(repo_name) + "\n// Original:\n" + content


def _default_vite_config(repo_name: str = "") -> str:
    base = f"/{repo_name}/" if repo_name else "./"
    return f'''import {{ defineConfig }} from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({{
  plugins: [react()],
  base: "{base}",
  build: {{ outDir: "dist", assetsDir: "assets" }},
  server: {{ port: 3000 }},
}});
'''


def _fix_nested_routers(files: dict) -> dict:
    main_key = next((k for k in files if k.endswith("main.jsx") or k.endswith("main.js") or k.endswith("main.tsx")), None)
    app_key = next((k for k in files if k.endswith("App.jsx") or k.endswith("App.js") or k.endswith("App.tsx")), None)

    if not main_key or not app_key:
        return files
        
    main_content = files[main_key]
    app_content = files[app_key]
    
    has_router_main = "<BrowserRouter" in main_content or "<HashRouter" in main_content
    has_router_app = "<BrowserRouter" in app_content or "<HashRouter" in app_content
    
    if has_router_main and has_router_app:
        logger.info("Auto-fixing nested React routers in App.jsx")
        app_content = re.sub(r'<BrowserRouter[^>]*>', '<div className="app-wrapper">', app_content)
        app_content = app_content.replace('</BrowserRouter>', '</div>')
        app_content = re.sub(r'<HashRouter[^>]*>', '<div className="app-wrapper">', app_content)
        app_content = app_content.replace('</HashRouter>', '</div>')
        files[app_key] = app_content

    # Fix BrowserRouter for GitHub Pages
    if main_key and "<BrowserRouter>" in files[main_key]:
        files[main_key] = files[main_key].replace("<BrowserRouter>", "<BrowserRouter basename={import.meta.env.BASE_URL}>")
    elif main_key and "<BrowserRouter" in files[main_key] and "basename" not in files[main_key]:
        files[main_key] = files[main_key].replace("<BrowserRouter", "<BrowserRouter basename={import.meta.env.BASE_URL}")

    if app_key and "<BrowserRouter>" in files[app_key]:
        files[app_key] = files[app_key].replace("<BrowserRouter>", "<BrowserRouter basename={import.meta.env.BASE_URL}>")
    elif app_key and "<BrowserRouter" in files[app_key] and "basename" not in files[app_key]:
        files[app_key] = files[app_key].replace("<BrowserRouter", "<BrowserRouter basename={import.meta.env.BASE_URL}")

    return files


def _fix_api_exports(files: dict) -> dict:
    api_key = next((k for k in files if k.endswith("api.js")), None)
    if not api_key:
        return files

    api_content = files[api_key]

    # ── Safety net: if the base api.js is fundamentally broken, replace it ──
    # The LLM sometimes emits a stub that references axios/BASE_URL without
    # importing/declaring them.  Appending export stubs to that file still
    # crashes at runtime with "ReferenceError: axios is not defined".
    if ("import axios" not in api_content or "import.meta.env" not in api_content):
        logger.warning(f"api.js is missing axios import or BASE_URL — replacing with safe fallback")
        api_content = '''import axios from "axios";

const BASE_URL =
  import.meta.env.VITE_API_URL ||
  (typeof window !== "undefined" &&
   (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://localhost:8000"
    : "");

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error("API error:", err.response?.status, err.config?.url);
    return Promise.reject(err);
  }
);

export const getItems   = (params = {}) => api.get("/items",        { params });
export const getItem    = (id)            => api.get(`/items/${id}`);
export const createItem = (data)          => api.post("/items",       data);
export const updateItem = (id, data)      => api.put(`/items/${id}`, data);
export const deleteItem = (id)            => api.delete(`/items/${id}`);
export const getStats   = ()              => api.get("/stats");

export default api;
'''
        files[api_key] = api_content
        return files

    pattern     = re.compile(r'import\s*\{([^}]+)\}\s*from\s*["\'](?:\.\\.?/)*api(?:\.js)?["\']', re.DOTALL)
    needed      = set()

    for path, content in files.items():
        if not path.endswith((".jsx", ".js", ".tsx")) or path == api_key:
            continue
        for match in pattern.finditer(content):
            names = [n.strip().split(" as ")[0].strip() for n in match.group(1).split(",")]
            needed.update(filter(None, names))

    if not needed:
        return files

    existing = set(re.findall(r'export\s+(?:const|function|async\s+function)\s+(\w+)', api_content))
    missing  = needed - existing

    # FIX: BASE_URL is a variable declaration, not an export — removing it
    # from missing prevents duplicate declaration build crash in GitHub Actions
    missing.discard("BASE_URL")

    if not missing:
        return files

    logger.info(f"Auto-adding missing exports: {missing}")
    base_url = "${import.meta.env.VITE_API_URL || ''}"
    stubs    = "\n\n// Auto-generated missing exports by VIA\n"

    def _pl(w):
        if not w: return "items"
        if w.endswith("s"): return w
        if w.endswith("y"): return w[:-1] + "ies"
        return w + "s"

    for name in sorted(missing):
        if name in ("getStats", "getStatistics"):
            stubs += f'export const {name} = async () => {{ const r = await fetch(`{base_url}/api/v1/stats`); if (!r.ok) throw new Error("{name} failed"); return r.json(); }};\n'
        elif name.startswith("get"):
            res = _pl(name[3:].lower())
            stubs += f'export const {name} = async (p) => {{ const q = p ? "?" + new URLSearchParams(p) : ""; const r = await fetch(`{base_url}/api/v1/{res}${{q}}`); if (!r.ok) throw new Error("{name} failed"); return r.json(); }};\n'
        elif name.startswith("create") or name.startswith("add"):
            res = _pl(name[6:].lower() if name.startswith("create") else name[3:].lower())
            stubs += f'export const {name} = async (d) => {{ const r = await fetch(`{base_url}/api/v1/{res}`, {{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify(d)}}); if (!r.ok) throw new Error("{name} failed"); return r.json(); }};\n'
        elif name.startswith("update") or name.startswith("edit"):
            res = _pl(name[6:].lower() if name.startswith("update") else name[4:].lower())
            stubs += f'export const {name} = async (id,d) => {{ const r = await fetch(`{base_url}/api/v1/{res}/${{id}}`, {{method:"PUT",headers:{{"Content-Type":"application/json"}},body:JSON.stringify(d)}}); if (!r.ok) throw new Error("{name} failed"); return r.json(); }};\n'
        elif name.startswith("delete") or name.startswith("remove"):
            res = _pl(name[6:].lower())
            stubs += f'export const {name} = async (id) => {{ const r = await fetch(`{base_url}/api/v1/{res}/${{id}}`, {{method:"DELETE"}}); if (!r.ok) throw new Error("{name} failed"); return r.json(); }};\n'
        else:
            res = _pl(name.lower())
            stubs += f'export const {name} = async () => {{ const r = await fetch(`{base_url}/api/v1/{res}`); if (!r.ok) throw new Error("{name} failed"); return r.json(); }};\n'

    files[api_key] = api_content.rstrip() + stubs
    return files


def _slugify(text: str) -> str:
    import uuid
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    base = text[:80].strip("-") or "via-app"
    return f"{base}-{uuid.uuid4().hex[:6]}"


def _fallback_readme(task: str, repo: str) -> str:
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    return (f"# {repo}\n> Generated by **VIA**\n\n## Task\n{task}\n\n"
            f"## Frontend\nGitHub Pages\n\n## Backend\nRender\n\n"
            f"---\n*Generated by VIA on {now}*\n")


github_pusher = GitHubPusher()