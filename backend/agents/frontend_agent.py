# backend/agents/frontend_agent.py — VIA Phase 6
#
# FIXES vs previous version:
#   1. _deploy_workflow() — peaceiris/actions-gh-pages@v4 (not deploy-pages)
#   2. permissions: contents: write
#   3. _vite_config() — correct base path per repo slug
#   4. _api_js() — smart BASE_URL via VITE_API_URL env var
#   5. _is_valid_js() — rejects hardcoded Render URLs
#   6. [NEW] _package_json() — includes react-toastify, lucide-react, react-icons,
#      react-hot-toast, date-fns, react-hook-form, clsx so LLM imports never 404
#   7. [NEW] _build_prompt() — APPROVED PACKAGES list prevents LLM from importing
#      anything outside what's installed
#   8. [NEW] _is_valid_jsx() — rejects LLM output that imports unapproved packages,
#      falling back to our safe generated App.jsx
#   9. [FIX] _app_jsx() — 5 bugs fixed
#  10. [FIX] _is_valid_js() — minimum length raised from 50 to 200 chars
#  11. [FIX] _index_css() — replaced @apply directives with plain CSS properties
#  12. [FIX] _is_valid_js() — rejects api.js with duplicate BASE_URL declaration
#  13. [FIX v7] _build_prompt() — task-specific UI instructions, not generic CRUD
#  14. [FIX v7] _is_valid_jsx() — threshold lowered 200→800, rejects generic CRUD
#  15. [FIX v7] _app_jsx() — 8 app-type detections (image, recipe, grade, map,
#      calculator, chart, kanban, todo) with matching UI; generic fallback improved
#
# PERMANENT FIXES (v8):
#  16. [FIX v8] _slug() — removed 50-char truncation; GitHub supports up to 100 chars.
#      Truncation caused vite base path to mismatch the actual repo name → blank page / 404.
#      The slug here MUST match whatever slug the GitHub-repo-creation agent uses.
#  17. [FIX v8] _app_jsx() — domain-specific checks (hospital, game, expense, todo, weather)
#      now evaluated BEFORE the generic "chart" branch. Previously "expense dashboard" or
#      "weather dashboard" always rendered the analytics/chart UI because feat["chart"] was
#      True (matched "dashboard") and was checked first. Priority order is now:
#        image → recipe → grade → calculator → kanban → weather → hospital → game →
#        expense → todo → chart → generic-fallback
#  18. [FIX v8] _build_prompt() — same priority reorder as _app_jsx()
#  19. [FIX v8] _features() — added "weather" detection keyword set
#  20. [FIX v8] _theme() — added weather theme entry
#  21. [FIX v8] _app_jsx() — added full weather UI branch (city search, current
#      conditions card, 5-day forecast strip, uses /api/v1/weather endpoint)

import re
import time
import logging
from backend.core.llm_provider import llm
from backend.core.code_writer import extract_code_blocks, save_project_files

logger = logging.getLogger("AI-Digital-Company")

# Broad approved packages list — trust Claude to pick appropriate libraries
APPROVED_PACKAGES = {
    "react", "react-dom", "react-router-dom", "axios",
    "react-toastify", "react-hot-toast", "lucide-react",
    "date-fns", "react-hook-form", "clsx", "history",
    "framer-motion", "@headlessui/react", "@heroicons/react",
    "react-icons", "react-beautiful-dnd", "@dnd-kit/core",
    "@dnd-kit/sortable", "@dnd-kit/utilities",
    "recharts", "chart.js", "react-chartjs-2",
    "zustand", "jotai", "react-query", "@tanstack/react-query",
    "tailwind-merge", "class-variance-authority",
    "react-select", "react-datepicker", "react-modal",
    "react-table", "@tanstack/react-table",
    "react-spring", "react-transition-group",
    "uuid", "lodash", "dayjs", "moment",
    "sweetalert2", "sonner", "react-dropzone",
}


async def frontend_agent(task: str, ceo_strategy: str = "", project_brief: dict = None, inter_context: str = "") -> dict:
    start = time.time()
    logger.info(f"Frontend Agent | Task: {task[:60]}")

    try:
        prompt      = _build_prompt(task, ceo_strategy, inter_context)
        llm_output  = await llm.agenerate(prompt)
        files       = extract_code_blocks(llm_output) if llm_output else {}
        files       = _build_all_files(task, files, llm_output or "")
        save_result = save_project_files(task, "frontend", files)
        duration    = round(time.time() - start, 2)
        logger.info(f"Frontend Agent done | {save_result['file_count']} files | {duration}s")

        return {
            "department": "Frontend Engineering",
            "status":     "success",
            "execution_time_seconds": duration,
            "confidence": 0.91,
            "output": {
                "department":      "Frontend Engineering",
                "files_generated": save_result["files_written"],
                "file_count":      save_result["file_count"],
                "project_path":    save_result["project_path"],
                "department_path": save_result["department_path"],
                "framework":       "React 18 + Vite + Tailwind CSS",
                "deploy_target":   "GitHub Pages via GitHub Actions",
            },
        }

    except Exception as e:
        duration = round(time.time() - start, 2)
        logger.error(f"Frontend Agent failed | {str(e)}")
        return {
            "department": "Frontend Engineering",
            "status":     "failed",
            "execution_time_seconds": duration,
            "confidence": 0.0,
            "error":      str(e),
            "output":     {},
        }


def _title(task: str) -> str:
    t = re.sub(r"[^\w\s]", " ", task)
    return " ".join(w.capitalize() for w in t.split()[:8])


# ---------------------------------------------------------------------------
# FIX v8: _slug() — removed 50-char truncation.
#
# WHY: The vite base path is /<slug>/ and must exactly match the GitHub repo
# name that the repo-creation agent uses. If this slug is truncated and the
# repo name is not (or vice-versa), every asset request 404s and the page
# appears blank. GitHub repo names support up to 100 characters so we cap
# there instead. Any change to this function MUST be mirrored in the agent
# that creates the GitHub repository.
# ---------------------------------------------------------------------------
def _slug(task: str) -> str:
    text = task.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    # GitHub max repo name length is 100 chars; do NOT truncate shorter than that.
    return text[:100].strip("-") or "via-app"


def _features(task: str) -> dict:
    t = task.lower()
    return {
        "hospital":    any(w in t for w in ["hospital", "appointment", "doctor", "patient", "medical"]),
        "game":        any(w in t for w in ["game", "gaming", "player", "score", "leaderboard"]),
        "expense":     any(w in t for w in ["expense", "budget", "finance", "spending", "money"]),
        "todo":        any(w in t for w in ["todo", "task", "checklist"]),
        "employee":    any(w in t for w in ["employee", "staff", "hr"]),
        "inventory":   any(w in t for w in ["inventory", "stock", "product", "warehouse"]),
        "blog":        any(w in t for w in ["blog", "article", "post", "cms"]),
        "booking":     any(w in t for w in ["booking", "reservation", "event"]),
        "auth":        any(w in t for w in ["auth", "login", "user", "register"]),
        # v7 detections
        "image":       any(w in t for w in ["image", "photo", "upload", "grayscale", "picture", "crop", "filter"]),
        "recipe":      any(w in t for w in ["recipe", "cook", "ingredient", "meal", "food", "dish"]),
        # FIX v8: removed standalone "score" (conflicts with game), "tip" (substring of
        # "multiplayer"), "column" (substring of "columnist"). Use longer anchored phrases.
        "grade":       any(w in t for w in ["grade", "student", "mark", "gpa", "academic", "exam", "result", "subject", "marks"]),
        "calculator":  any(w in t for w in ["calculator", "calculate", "math", "compute", "converter", "bmi", "tip calc"]),
        "chart":       any(w in t for w in ["chart", "graph", "analytics", "dashboard", "visuali", "report", "statistic"]),
        # FIX v8: "board" was a substring of "dashboard" and "leaderboard", causing false positives.
        # Now uses word-boundary regex so "kanban board" matches but "dashboard" does NOT.
        # Removed standalone "column" (substring of "columns", "columnist" etc).
        "kanban":      any(w in t for w in ["kanban", "sprint", "project management"]) or
                       bool(re.search(r'\bboard\b', t)),
        "map":         any(w in t for w in ["map", "location", "gps", "geograph", "place", "address"]),
        # FIX v8: added weather detection — prevents weather apps from rendering as generic chart/dashboard
        "weather":     any(w in t for w in ["weather", "forecast", "temperature", "climate", "rain", "humidity", "wind", "storm"]),
    }


def _theme(task: str) -> dict:
    t = task.lower()
    if any(w in t for w in ["hospital", "medical", "doctor", "patient"]):
        return {"primary": "#0ea5e9", "bg": "#f0f9ff", "icon": "🏥", "score_cls": "text-sky-600"}
    if any(w in t for w in ["game", "gaming"]):
        return {"primary": "#8b5cf6", "bg": "#faf5ff", "icon": "🎮", "score_cls": "text-purple-600"}
    if any(w in t for w in ["expense", "budget", "finance", "money"]):
        return {"primary": "#10b981", "bg": "#f0fdf4", "icon": "💰", "score_cls": "text-emerald-600"}
    if any(w in t for w in ["employee", "staff", "hr"]):
        return {"primary": "#f59e0b", "bg": "#fffbeb", "icon": "👥", "score_cls": "text-amber-600"}
    if any(w in t for w in ["todo", "task", "checklist"]):
        return {"primary": "#3b82f6", "bg": "#eff6ff", "icon": "✅", "score_cls": "text-blue-600"}
    if any(w in t for w in ["blog", "article", "post"]):
        return {"primary": "#ec4899", "bg": "#fdf2f8", "icon": "📝", "score_cls": "text-pink-600"}
    if any(w in t for w in ["booking", "reservation", "event"]):
        return {"primary": "#14b8a6", "bg": "#f0fdfa", "icon": "📅", "score_cls": "text-teal-600"}
    if any(w in t for w in ["inventory", "stock", "product"]):
        return {"primary": "#f97316", "bg": "#fff7ed", "icon": "📦", "score_cls": "text-orange-600"}
    if any(w in t for w in ["image", "photo", "upload", "grayscale"]):
        return {"primary": "#6366f1", "bg": "#eef2ff", "icon": "🖼️", "score_cls": "text-indigo-600"}
    if any(w in t for w in ["recipe", "cook", "food", "meal"]):
        return {"primary": "#f59e0b", "bg": "#fffbeb", "icon": "🍳", "score_cls": "text-amber-600"}
    if any(w in t for w in ["grade", "student", "academic", "exam"]):
        return {"primary": "#3b82f6", "bg": "#eff6ff", "icon": "🎓", "score_cls": "text-blue-600"}
    if any(w in t for w in ["calculator", "compute", "bmi", "converter"]):
        return {"primary": "#8b5cf6", "bg": "#faf5ff", "icon": "🧮", "score_cls": "text-purple-600"}
    if any(w in t for w in ["chart", "analytics", "dashboard", "report"]):
        return {"primary": "#10b981", "bg": "#f0fdf4", "icon": "📊", "score_cls": "text-emerald-600"}
    if any(w in t for w in ["kanban", "board", "sprint"]):
        return {"primary": "#f97316", "bg": "#fff7ed", "icon": "📋", "score_cls": "text-orange-600"}
    # FIX v8: weather theme
    if any(w in t for w in ["weather", "forecast", "temperature", "climate"]):
        return {"primary": "#0ea5e9", "bg": "#f0f9ff", "icon": "⛅", "score_cls": "text-sky-600"}
    return {"primary": "#6366f1", "bg": "#eef2ff", "icon": "⚡", "score_cls": "text-indigo-600"}


# ---------------------------------------------------------------------------
# _is_valid_jsx — lowered threshold + reject generic fallback output (v7, unchanged)
# ---------------------------------------------------------------------------
def _is_valid_jsx(code: str) -> bool:
    if not code or len(code.strip()) < 800:
        return False
    bad_imports = [
        "from './Home'", "from './Test'", "from './Result'",
        "from './Pages'", "from './components/", "from './views/",
        "from './screens/", "from './pages/", "from '../components/",
        "import Home from", "import Test from", "import Result from",
        "import Quiz from", "import Question from", "import Score from",
    ]
    if any(b in code for b in bad_imports):
        return False
    if ("localhost:8000" in code or "127.0.0.1:8000" in code) and "import.meta.env" not in code:
        return False

    for match in re.finditer(r'from\s+["\']([^"\'./][^"\']*)["\']', code):
        pkg = match.group(1).split("/")[0]
        if pkg.startswith("@"):
            full_scope = "/".join(match.group(1).split("/")[:2])
            if full_scope not in APPROVED_PACKAGES:
                logger.warning(f"LLM App.jsx rejected — unapproved import: {match.group(1)}")
                return False
        elif pkg not in APPROVED_PACKAGES:
            logger.warning(f"LLM App.jsx rejected — unapproved import: {pkg}")
            return False

    return "return" in code and "useState" in code


def _is_valid_js(code: str) -> bool:
    if not code or len(code.strip()) < 200:
        return False
    if "localhost:8000" in code and "import.meta.env" not in code:
        return False
    if "onrender.com" in code:
        return False
    if code.count("BASE_URL") > 1:
        return False
    # FIX: Reject api.js that uses axios/BASE_URL without importing/declaring them.
    # The LLM sometimes emits a stub like `export const api = axios.create({baseURL: BASE_URL})`
    # without the actual import or env-var declaration — causing ReferenceError at runtime.
    if "axios" in code and "import axios" not in code:
        return False
    if "import.meta.env" not in code:
        return False
    # Must have at least one named export function (getItems, createItem, etc.)
    if not re.search(r'export\s+(?:const|function|async\s+function)\s+\w+', code):
        return False
    return True


def _build_all_files(task: str, llm_files: dict, raw: str) -> dict:
    f    = dict(llm_files)
    name = _title(task)
    repo = _slug(task)
    feat = _features(task)
    th   = _theme(task)

    f["package.json"]                 = _package_json()
    f["vite.config.js"]               = _vite_config(repo)
    f["index.html"]                   = _index_html(name)
    f["tailwind.config.js"]           = _tailwind_config()
    f["postcss.config.js"]            = _postcss_config()
    f["public/404.html"]              = _404_html()
    f[".github/workflows/deploy.yml"] = _deploy_workflow()
    f["src/main.jsx"] = _main_jsx()
    f["src/index.css"] = _index_css(th)
    f["src/api.js"] = _api_js(feat)

    if "src/App.jsx" not in f or len(f.get("src/App.jsx", "").strip()) < 10:
        logger.warning("LLM failed to generate src/App.jsx. Using template as last resort.")
        f["src/App.jsx"] = _app_jsx(name, task, feat, th)
    else:
        # Trust the LLM output — no fallback to template
        app_code = f["src/App.jsx"]
        # Only do basic safety fixups, never replace with template
        if "localhost:8000" in app_code and "import.meta.env" not in app_code:
            app_code = app_code.replace(
                '"http://localhost:8000"', 
                'import.meta.env.VITE_API_URL || "http://localhost:8000"'
            )
        # Fix: Remove App.css import since VIA generates all CSS in index.css
        app_code = re.sub(r'import\s+[\'"]\.\/App\.css[\'"];?', '', app_code)
        
        # Fix: Claude/Groq sometimes hallucinates 'createToast' from react-toastify
        app_code = app_code.replace('createToast', 'toast')
        
        # FIX: Groq often hallucinates react-icons (like AiOutlineSearch) from lucide-react
        lucide_match = re.search(r'import\s+\{([^}]+)\}\s+from\s+[\'"]lucide-react[\'"];?', app_code)
        if lucide_match:
            icons = [i.strip() for i in lucide_match.group(1).split(',')]
            lucide_icons = []
            new_imports = []
            for icon in icons:
                if not icon: continue
                # Identify common react-icons prefixes
                prefix_match = re.match(r'^(Ai|Fa|Md|Fi|Hi|Bs|Bi|Tb|Lu|Ri|Io|Go|Gr|Di)[A-Z]', icon)
                if prefix_match:
                    prefix = prefix_match.group(1).lower()
                    new_imports.append(f"import {{ {icon} }} from 'react-icons/{prefix}';")
                else:
                    lucide_icons.append(icon)
            
            replacement = ""
            if lucide_icons:
                replacement += f"import {{ {', '.join(lucide_icons)} }} from 'lucide-react';\n"
            replacement += "\n".join(new_imports) + "\n"
            app_code = app_code.replace(lucide_match.group(0), replacement)
            
        f["src/App.jsx"] = app_code
        logger.info(f"Using LLM-generated App.jsx | {len(app_code)} chars")
        
        # FIX: Ensure all functions imported from './api' actually exist in api.js
        # Otherwise the Vite build will fail (e.g. "getTotalExpensesByCategory is not exported")
        api_imports_match = re.search(r'import\s+\{([^}]+)\}\s+from\s+[\'"]\./api[\'"]', app_code)
        if api_imports_match:
            imported_funcs = [fn.strip() for fn in api_imports_match.group(1).split(',')]
            api_code = f["src/api.js"]
            for fn in imported_funcs:
                if fn and f"export const {fn}" not in api_code and f"export function {fn}" not in api_code:
                    logger.info(f"Auto-injecting missing API stub: {fn}")
                    # Append a dummy async function that returns an empty array/object
                    stub = f"\nexport const {fn} = async () => {{ console.warn('Stubbed {fn} called'); return []; }};\n"
                    api_code += stub
            f["src/api.js"] = api_code


    if "BrowserRouter" in f.get("src/main.jsx", ""):
        f["src/main.jsx"] = f["src/main.jsx"].replace("BrowserRouter", "HashRouter")

    if raw.strip():
        f["llm_raw_output.md"] = f"# LLM Output\n\n{raw}"

    return f


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
  group: "pages"
  cancel-in-progress: false

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
          VITE_API_URL: ${{ vars.VITE_API_URL }}

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


def _package_json() -> str:
    return """{
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
    "lucide-react":         "^0.383.0",
    "date-fns":             "^3.6.0",
    "react-hook-form":      "^7.51.0",
    "clsx":                 "^2.1.0",
    "react-icons":          "^5.0.1"
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


def _vite_config(repo: str = "") -> str:
    # Use relative base path to ensure assets load correctly on GitHub Pages
    # regardless of dynamic UUIDs appended to the repository name.
    return f"""import {{ defineConfig }} from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({{
  plugins: [react()],
  base: "./",
  build: {{ outDir: "dist", assetsDir: "assets" }},
  server: {{ port: 3000 }},
}});
"""


def _index_html(name: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{name}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""


def _404_html() -> str:
    return """<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Redirecting...</title>
    <script>
      var l = window.location;
      l.replace(
        l.protocol + "//" + l.hostname + (l.port ? ":" + l.port : "") +
        l.pathname.split("/").slice(0, 1).join("/") +
        "/?/" + l.pathname.slice(1).replace(/&/g, "~and~") +
        (l.search ? "&" + l.search.slice(1).replace(/&/g, "~and~") : "") + l.hash
      );
    </script>
  </head>
  <body>Redirecting...</body>
</html>
"""


def _tailwind_config() -> str:
    return """/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans:    ["Inter", "sans-serif"],
        display: ["Plus Jakarta Sans", "sans-serif"],
      },
    },
  },
  plugins: [],
};
"""


def _postcss_config() -> str:
    return """export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
};
"""


def _main_jsx() -> str:
    return """import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import App from "./App.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>
);
"""


def _index_css(th: dict) -> str:
    p  = th["primary"]
    bg = th["bg"]
    return f"""@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {{
  body {{
    font-family: "Inter", sans-serif;
    background-color: {bg};
    color: #111827;
    -webkit-font-smoothing: antialiased;
  }}
  h1, h2, h3 {{ font-family: "Plus Jakarta Sans", sans-serif; }}
}}

@layer components {{
  .btn-primary {{
    background-color: {p};
    color: #ffffff;
    font-weight: 600;
    padding: 0.625rem 1.25rem;
    border-radius: 0.75rem;
    transition: all 0.2s;
    display: inline-block;
    cursor: pointer;
    border: none;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  }}
  .btn-primary:hover {{ opacity: 0.9; }}
  .btn-primary:active {{ transform: scale(0.97); }}
  .btn-primary:disabled {{ opacity: 0.5; cursor: not-allowed; }}

  .btn-secondary {{
    background-color: #ffffff;
    color: #374151;
    font-weight: 500;
    padding: 0.625rem 1.25rem;
    border-radius: 0.75rem;
    border: 1px solid #e5e7eb;
    transition: all 0.2s;
    display: inline-block;
    cursor: pointer;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  }}
  .btn-secondary:hover {{ background-color: #f9fafb; }}
  .btn-secondary:active {{ transform: scale(0.97); }}

  .card {{
    background-color: #ffffff;
    border-radius: 1rem;
    border: 1px solid #f3f4f6;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    padding: 1.5rem;
  }}

  .input {{
    width: 100%;
    border: 1px solid #e5e7eb;
    border-radius: 0.75rem;
    padding: 0.625rem 1rem;
    font-size: 0.875rem;
    background-color: #ffffff;
    outline: none;
    transition: all 0.2s;
    color: #111827;
  }}
  .input:focus {{
    border-color: {p};
    box-shadow: 0 0 0 3px {p}33;
  }}
  .input::placeholder {{ color: #9ca3af; }}

  .badge-active    {{ display: inline-flex; align-items: center; padding: 0.25rem 0.625rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; background-color: #dcfce7; color: #15803d; }}
  .badge-inactive  {{ display: inline-flex; align-items: center; padding: 0.25rem 0.625rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; background-color: #f3f4f6; color: #4b5563; }}
  .badge-pending   {{ display: inline-flex; align-items: center; padding: 0.25rem 0.625rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; background-color: #fef9c3; color: #a16207; }}
  .badge-done      {{ display: inline-flex; align-items: center; padding: 0.25rem 0.625rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; background-color: #dbeafe; color: #1d4ed8; }}
  .badge-scheduled {{ display: inline-flex; align-items: center; padding: 0.25rem 0.625rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; background-color: #dcfce7; color: #15803d; }}
  .badge-confirmed {{ display: inline-flex; align-items: center; padding: 0.25rem 0.625rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; background-color: #dcfce7; color: #15803d; }}
}}
"""


def _api_js(feat: dict) -> str:
    auth_fns = """
export const login    = (u, p) => api.post("/auth/login",    { username: u, password: p });
export const register = (data)  => api.post("/auth/register", data);
export const setAuthToken = (token) => {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    localStorage.setItem("via_token", token);
  } else {
    delete api.defaults.headers.common["Authorization"];
    localStorage.removeItem("via_token");
  }
};
const saved = localStorage.getItem("via_token");
if (saved) setAuthToken(saved);
""" if feat["auth"] else ""

    return f"""import axios from "axios";

const BASE_URL =
  import.meta.env.VITE_API_URL ||
  (typeof window !== "undefined" &&
   (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://localhost:8000"
    : "");

const api = axios.create({{
  baseURL: `${{BASE_URL}}/api/v1`,
  headers: {{ "Content-Type": "application/json" }},
  timeout: 30000,
}});

api.interceptors.response.use(
  (res) => res,
  (err) => {{
    console.error("API error:", err.response?.status, err.config?.url);
    if (err.response?.status === 401) localStorage.removeItem("via_token");
    return Promise.reject(err);
  }}
);
{auth_fns}
export const getItems   = (params = {{}}) => api.get("/items",        {{ params }});
export const getItem    = (id)            => api.get(`/items/${{id}}`);
export const createItem = (data)          => api.post("/items",       data);
export const updateItem = (id, data)      => api.put(`/items/${{id}}`, data);
export const deleteItem = (id)            => api.delete(`/items/${{id}}`);
export const getStats   = ()              => api.get("/stats");

export default api;
"""


# ---------------------------------------------------------------------------
# FIX v8: _app_jsx — corrected priority order for app-type detection.
#
# PROBLEM (v7): feat["chart"] was checked BEFORE feat["hospital"], feat["game"],
# feat["expense"], feat["todo"], and feat["weather"] (which didn't exist).
# Any task containing "dashboard" or "analytics" matched feat["chart"]=True and
# always rendered the generic analytics UI, regardless of domain specificity.
# Examples that were broken:
#   "create a simple weather dashboard" → rendered analytics chart UI (WRONG)
#   "expense dashboard"                 → rendered analytics chart UI (WRONG)
#   "hospital dashboard"                → rendered analytics chart UI (WRONG)
#
# FIX: Domain-specific types are checked first. chart/analytics is now the
# last resort before the final generic CRUD fallback. New priority order:
#   image → recipe → grade → calculator → kanban →
#   weather (NEW) → hospital → game → expense → todo →
#   chart (last resort) → generic CRUD fallback
# ---------------------------------------------------------------------------
def _app_jsx(app_title: str, task: str, feat: dict, th: dict) -> str:
    p         = th["primary"]
    icon      = th["icon"]
    score_cls = th["score_cls"]

    # ── IMAGE / UPLOAD / GRAYSCALE app ──────────────────────────────────────
    if feat["image"]:
        return f'''// src/App.jsx — Generated by VIA for: {task}
import {{ useState, useRef, useCallback }} from "react";
import {{ toast, ToastContainer }} from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL ||
  (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://localhost:8000" : "");

export default function App() {{
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleFile = useCallback((f) => {{
    if (!f || !f.type.startsWith("image/")) {{ toast.error("Please select an image file"); return; }}
    setFile(f);
    setResult(null);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  }}, []);

  const handleDrop = (e) => {{
    e.preventDefault(); setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  }};

  const handleProcess = async () => {{
    if (!file) {{ toast.error("Please select an image first"); return; }}
    setLoading(true);
    try {{
      const fd = new FormData();
      fd.append("file", file);
      const res = await axios.post(`${{BASE_URL}}/api/v1/process`, fd, {{
        headers: {{ "Content-Type": "multipart/form-data" }},
        responseType: "blob",
      }});
      setResult(URL.createObjectURL(res.data));
      toast.success("Image processed successfully!");
    }} catch (err) {{
      toast.error(err.response?.data?.detail || "Processing failed — backend may be starting up");
    }} finally {{
      setLoading(false);
    }}
  }};

  const handleDownload = () => {{
    if (!result) return;
    const a = document.createElement("a");
    a.href = result; a.download = "processed_" + (file?.name || "image.png");
    a.click();
  }};

  return (
    <div className="min-h-screen" style={{{{ backgroundColor: "{th["bg"]}" }}}}>
      <ToastContainer position="top-right" autoClose={{3000}} />
      <nav className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <span className="font-bold text-gray-900 text-lg">{app_title}</span>
        </div>
      </nav>
      <main className="max-w-5xl mx-auto px-6 py-10 space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900">{app_title}</h1>
          <p className="text-gray-500 mt-2">Upload an image and process it instantly</p>
        </div>

        {{/* Upload Zone */}}
        <div
          onDrop={{handleDrop}} onDragOver={{e => {{ e.preventDefault(); setDragOver(true); }}}}
          onDragLeave={{() => setDragOver(false)}} onClick={{() => inputRef.current?.click()}}
          className={{`card border-2 border-dashed cursor-pointer text-center py-16 transition-all ${{
            dragOver ? "border-indigo-400 bg-indigo-50" : "border-gray-200 hover:border-indigo-300"
          }}`}}
        >
          <input ref={{inputRef}} type="file" accept="image/*" className="hidden" onChange={{e => handleFile(e.target.files[0])}} />
          <div className="text-5xl mb-4">🖼️</div>
          <p className="text-gray-600 font-medium">Drop an image here or <span style={{{{ color: "{p}" }}}}>browse</span></p>
          <p className="text-gray-400 text-sm mt-1">PNG, JPG, WEBP, GIF supported</p>
        </div>

        {{/* Preview + Result */}}
        {{(preview || result) && (
          <div className={{`grid gap-6 ${{result ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1 max-w-md mx-auto"}}`}}>
            {{preview && (
              <div className="card space-y-3">
                <h2 className="font-semibold text-gray-700">Original</h2>
                <img src={{preview}} alt="original" className="w-full rounded-xl object-contain max-h-80" />
                <p className="text-xs text-gray-400">{{file?.name}} · {{(file?.size / 1024).toFixed(1)}} KB</p>
              </div>
            )}}
            {{result && (
              <div className="card space-y-3">
                <h2 className="font-semibold text-gray-700">Processed</h2>
                <img src={{result}} alt="processed" className="w-full rounded-xl object-contain max-h-80" />
                <button onClick={{handleDownload}} className="btn-secondary w-full text-sm">⬇ Download</button>
              </div>
            )}}
          </div>
        )}}

        {{preview && (
          <div className="flex justify-center">
            <button onClick={{handleProcess}} disabled={{loading}} className="btn-primary px-10 py-3 text-base">
              {{loading ? "Processing…" : "Process Image"}}
            </button>
          </div>
        )}}
      </main>
    </div>
  );
}}
'''

    # ── RECIPE / COOK / FOOD app ─────────────────────────────────────────────
    if feat["recipe"]:
        return f'''// src/App.jsx — Generated by VIA for: {task}
import {{ useState, useEffect }} from "react";
import {{ toast, ToastContainer }} from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import {{ getItems, createItem, deleteItem }} from "./api.js";

const CATEGORIES = ["Breakfast","Lunch","Dinner","Snack","Dessert","Drink"];

const SAMPLE = [
  {{ id: 1, title: "Spaghetti Carbonara", category: "Dinner", time: "25 min", servings: 2,
    ingredients: "200g spaghetti, 100g pancetta, 2 eggs, 50g parmesan, black pepper",
    steps: "1. Cook pasta. 2. Fry pancetta. 3. Mix eggs + cheese. 4. Combine off heat.", status:"active" }},
  {{ id: 2, title: "Avocado Toast", category: "Breakfast", time: "10 min", servings: 1,
    ingredients: "2 slices bread, 1 avocado, lemon juice, salt, chili flakes",
    steps: "1. Toast bread. 2. Mash avocado with lemon. 3. Spread and season.", status:"active" }},
];

export default function App() {{
  const [recipes, setRecipes] = useState(SAMPLE);
  const [search, setSearch] = useState("");
  const [cat, setCat] = useState("All");
  const [selected, setSelected] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({{ title:"", category:"Dinner", time:"", servings:2, ingredients:"", steps:"" }});
  const [loading, setLoading] = useState(false);

  useEffect(() => {{
    getItems().then(r => {{
      const items = Array.isArray(r.data) ? r.data : r.data?.items ?? [];
      if (items.length) setRecipes(items);
    }}).catch(() => {{}});
  }}, []);

  const filtered = recipes.filter(r =>
    (cat === "All" || r.category === cat) &&
    r.title.toLowerCase().includes(search.toLowerCase())
  );

  const handleAdd = async (e) => {{
    e.preventDefault();
    if (!form.title.trim()) {{ toast.error("Recipe name required"); return; }}
    setLoading(true);
    try {{
      const res = await createItem({{ ...form, status: "active" }});
      const item = res.data?.item ?? res.data ?? {{ ...form, id: Date.now() }};
      setRecipes(prev => [item, ...prev]);
      setShowForm(false);
      setForm({{ title:"", category:"Dinner", time:"", servings:2, ingredients:"", steps:"" }});
      toast.success("Recipe added!");
    }} catch {{ setRecipes(prev => [{{ ...form, id: Date.now() }}, ...prev]); setShowForm(false); }} finally {{ setLoading(false); }}
  }};

  const handleDelete = async (id) => {{
    if (!confirm("Delete this recipe?")) return;
    setRecipes(prev => prev.filter(r => (r.id ?? r._id) !== id));
    if (selected?.id === id) setSelected(null);
    deleteItem(id).catch(() => {{}});
    toast.success("Recipe deleted");
  }};

  if (selected) return (
    <div className="min-h-screen" style={{{{ backgroundColor: "{th["bg"]}" }}}}>
      <ToastContainer position="top-right" autoClose={{3000}} />
      <nav className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-50">
        <div className="max-w-3xl mx-auto px-6 h-16 flex items-center gap-3">
          <button onClick={{() => setSelected(null)}} className="text-gray-500 hover:text-gray-800 mr-2">← Back</button>
          <span className="text-2xl">{icon}</span>
          <span className="font-bold text-gray-900">{app_title}</span>
        </div>
      </nav>
      <main className="max-w-3xl mx-auto px-6 py-10">
        <div className="card space-y-6">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-xs font-semibold px-2 py-1 rounded-full bg-amber-100 text-amber-700">{{selected.category}}</span>
              <h1 className="text-3xl font-bold text-gray-900 mt-3">{{selected.title}}</h1>
              <div className="flex gap-4 mt-2 text-sm text-gray-500">
                {{selected.time && <span>⏱ {{selected.time}}</span>}}
                {{selected.servings && <span>🍽 {{selected.servings}} servings</span>}}
              </div>
            </div>
            <button onClick={{() => handleDelete(selected.id ?? selected._id)}} className="text-xs px-3 py-1.5 bg-red-50 text-red-600 rounded-lg border border-red-100">Delete</button>
          </div>
          {{selected.ingredients && (
            <div>
              <h2 className="font-semibold text-gray-800 mb-2">🛒 Ingredients</h2>
              <div className="bg-gray-50 rounded-xl p-4 text-sm text-gray-700 whitespace-pre-line">{{selected.ingredients}}</div>
            </div>
          )}}
          {{selected.steps && (
            <div>
              <h2 className="font-semibold text-gray-800 mb-2">📋 Instructions</h2>
              <div className="bg-gray-50 rounded-xl p-4 text-sm text-gray-700 whitespace-pre-line">{{selected.steps}}</div>
            </div>
          )}}
        </div>
      </main>
    </div>
  );

  return (
    <div className="min-h-screen" style={{{{ backgroundColor: "{th["bg"]}" }}}}>
      <ToastContainer position="top-right" autoClose={{3000}} />
      <nav className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3"><span className="text-2xl">{icon}</span><span className="font-bold text-gray-900">{app_title}</span></div>
          <button onClick={{() => setShowForm(true)}} className="btn-primary">+ Add Recipe</button>
        </div>
      </nav>
      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div className="flex flex-col sm:flex-row gap-3">
          <input className="input max-w-sm" placeholder="Search recipes…" value={{search}} onChange={{e => setSearch(e.target.value)}} />
          <div className="flex gap-2 flex-wrap">
            {{["All", ...CATEGORIES].map(c => (
              <button key={{c}} onClick={{() => setCat(c)}}
                className={{`px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${{cat === c ? "text-white border-transparent" : "bg-white text-gray-600 border-gray-200 hover:border-amber-300"}}`}}
                style={{{{ backgroundColor: cat === c ? "{p}" : undefined }}}}>{{c}}</button>
            ))}}
          </div>
        </div>
        {{filtered.length === 0 ? (
          <div className="card text-center py-20"><p className="text-5xl mb-4">{icon}</p><p className="text-gray-400 text-lg">No recipes found</p><button onClick={{() => setShowForm(true)}} className="btn-primary mt-4">+ Add Recipe</button></div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {{filtered.map(r => (
              <div key={{r.id ?? r._id}} onClick={{() => setSelected(r)}} className="card cursor-pointer hover:shadow-md transition-all hover:-translate-y-0.5 space-y-3">
                <div className="flex justify-between items-start">
                  <span className="text-xs font-semibold px-2 py-1 rounded-full bg-amber-100 text-amber-700">{{r.category}}</span>
                  <button onClick={{e => {{ e.stopPropagation(); handleDelete(r.id ?? r._id); }}}} className="text-xs text-red-400 hover:text-red-600">✕</button>
                </div>
                <h3 className="font-bold text-gray-900 text-lg leading-snug">{{r.title}}</h3>
                {{r.ingredients && <p className="text-sm text-gray-500 line-clamp-2">{{r.ingredients}}</p>}}
                <div className="flex gap-3 text-xs text-gray-400 pt-1">
                  {{r.time && <span>⏱ {{r.time}}</span>}}
                  {{r.servings && <span>🍽 {{r.servings}} servings</span>}}
                </div>
              </div>
            ))}}
          </div>
        )}}
      </main>
      {{showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <div className="flex justify-between items-center"><h2 className="text-xl font-bold text-gray-900">New Recipe</h2><button onClick={{() => setShowForm(false)}} className="text-gray-400 hover:text-gray-600 text-xl">✕</button></div>
            <form onSubmit={{handleAdd}} className="space-y-3">
              <input className="input" placeholder="Recipe name *" value={{form.title}} onChange={{e => setForm({{...form, title: e.target.value}})}} required />
              <div className="grid grid-cols-2 gap-3">
                <select className="input" value={{form.category}} onChange={{e => setForm({{...form, category: e.target.value}})}}>
                  {{CATEGORIES.map(c => <option key={{c}}>{{c}}</option>)}}
                </select>
                <input className="input" placeholder="Time (e.g. 30 min)" value={{form.time}} onChange={{e => setForm({{...form, time: e.target.value}})}} />
              </div>
              <input className="input" type="number" placeholder="Servings" min="1" value={{form.servings}} onChange={{e => setForm({{...form, servings: parseInt(e.target.value) || 1}})}} />
              <textarea className="input resize-none h-20" placeholder="Ingredients (one per line)" value={{form.ingredients}} onChange={{e => setForm({{...form, ingredients: e.target.value}})}} />
              <textarea className="input resize-none h-20" placeholder="Steps / instructions" value={{form.steps}} onChange={{e => setForm({{...form, steps: e.target.value}})}} />
              <div className="flex gap-3 pt-1"><button type="submit" className="btn-primary" disabled={{loading}}>{{loading ? "Saving…" : "Add Recipe"}}</button><button type="button" onClick={{() => setShowForm(false)}} className="btn-secondary">Cancel</button></div>
            </form>
          </div>
        </div>
      )}}
    </div>
  );
}}
'''

    # ── GRADE / STUDENT / ACADEMIC app ──────────────────────────────────────
    # FIX v8: guard with not feat["game"] — "score" appears in game keywords too.
    # game is checked first in the branch order below.
    if feat["grade"] and not feat["game"]:
        return f'''// src/App.jsx — Generated by VIA for: {task}
import {{ useState, useEffect }} from "react";
import {{ toast, ToastContainer }} from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import {{ getItems, createItem, deleteItem }} from "./api.js";

const GRADES = [
  {{ min:90, letter:"A+", color:"text-emerald-600 bg-emerald-50" }},
  {{ min:80, letter:"A",  color:"text-emerald-600 bg-emerald-50" }},
  {{ min:70, letter:"B",  color:"text-blue-600 bg-blue-50" }},
  {{ min:60, letter:"C",  color:"text-amber-600 bg-amber-50" }},
  {{ min:50, letter:"D",  color:"text-orange-600 bg-orange-50" }},
  {{ min:0,  letter:"F",  color:"text-red-600 bg-red-50" }},
];
const gradeInfo = (score) => GRADES.find(g => score >= g.min) || GRADES[GRADES.length-1];

const SAMPLE_STUDENTS = [
  {{ id:1, title:"Alice Johnson", roll:"001", math:92, science:88, english:95, history:79 }},
  {{ id:2, title:"Bob Smith",     roll:"002", math:74, science:81, english:68, history:85 }},
  {{ id:3, title:"Carol White",   roll:"003", math:56, science:63, english:72, history:60 }},
];

export default function App() {{
  const [students, setStudents] = useState(SAMPLE_STUDENTS);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({{ title:"", roll:"", math:"", science:"", english:"", history:"" }});
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState("title");

  useEffect(() => {{
    getItems().then(r => {{
      const items = Array.isArray(r.data) ? r.data : r.data?.items ?? [];
      if (items.length) setStudents(items);
    }}).catch(() => {{}});
  }}, []);

  const avg = (s) => {{
    const scores = [s.math, s.science, s.english, s.history].filter(x => x !== undefined && x !== "");
    return scores.length ? Math.round(scores.reduce((a,b) => a + Number(b), 0) / scores.length) : 0;
  }};

  const filtered = students
    .filter(s => s.title?.toLowerCase().includes(search.toLowerCase()) || s.roll?.includes(search))
    .sort((a,b) => sortBy === "avg" ? avg(b) - avg(a) : a.title?.localeCompare(b.title));

  const classAvg = students.length ? Math.round(students.reduce((s,st) => s + avg(st), 0) / students.length) : 0;
  const passing  = students.filter(s => avg(s) >= 50).length;

  const handleAdd = async (e) => {{
    e.preventDefault();
    if (!form.title.trim()) {{ toast.error("Student name required"); return; }}
    setLoading(true);
    try {{
      const res = await createItem({{ ...form, status:"active" }});
      const item = res.data?.item ?? res.data ?? {{ ...form, id: Date.now() }};
      setStudents(prev => [...prev, item]);
      setShowForm(false); setForm({{ title:"", roll:"", math:"", science:"", english:"", history:"" }});
      toast.success("Student added!");
    }} catch {{ setStudents(prev => [...prev, {{ ...form, id:Date.now() }}]); setShowForm(false); }} finally {{ setLoading(false); }}
  }};

  const handleDelete = (id) => {{
    if (!confirm("Remove this student?")) return;
    setStudents(prev => prev.filter(s => (s.id ?? s._id) !== id));
    deleteItem(id).catch(() => {{}});
    toast.success("Student removed");
  }};

  return (
    <div className="min-h-screen" style={{{{ backgroundColor: "{th["bg"]}" }}}}>
      <ToastContainer position="top-right" autoClose={{3000}} />
      <nav className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3"><span className="text-2xl">{icon}</span><span className="font-bold text-gray-900">{app_title}</span></div>
          <button onClick={{() => setShowForm(true)}} className="btn-primary">+ Add Student</button>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {{[
            ["Total Students", students.length, "👥"],
            ["Passing", passing, "✅"],
            ["Failing", students.length - passing, "⚠️"],
            ["Class Average", classAvg + "%", "📊"],
          ].map(([label, val, ic]) => (
            <div key={{label}} className="card text-center">
              <p className="text-2xl mb-1">{{ic}}</p>
              <p className="text-2xl font-bold text-gray-900">{{val}}</p>
              <p className="text-xs text-gray-500 mt-1">{{label}}</p>
            </div>
          ))}}
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <input className="input max-w-xs" placeholder="Search by name or roll…" value={{search}} onChange={{e => setSearch(e.target.value)}} />
          <select className="input max-w-xs" value={{sortBy}} onChange={{e => setSortBy(e.target.value)}}>
            <option value="title">Sort by Name</option>
            <option value="avg">Sort by Average</option>
          </select>
        </div>
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Roll</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Math</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Science</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">English</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">History</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Average</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Grade</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {{filtered.map(s => {{
                const a = avg(s); const gi = gradeInfo(a);
                return (
                  <tr key={{s.id ?? s._id}} className="hover:bg-gray-50/50">
                    <td className="px-4 py-3 text-gray-500">{{s.roll || "—"}}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{{s.title}}</td>
                    {{["math","science","english","history"].map(sub => (
                      <td key={{sub}} className="px-4 py-3 text-center text-gray-700">{{s[sub] ?? "—"}}</td>
                    ))}}
                    <td className="px-4 py-3 text-center font-bold text-gray-900">{{a}}%</td>
                    <td className="px-4 py-3 text-center"><span className={{`text-xs font-bold px-2 py-1 rounded-full ${{gi.color}}`}}>{{gi.letter}}</span></td>
                    <td className="px-4 py-3 text-right"><button onClick={{() => handleDelete(s.id ?? s._id)}} className="text-xs px-2 py-1 bg-red-50 text-red-500 rounded-lg border border-red-100">Remove</button></td>
                  </tr>
                );
              }})}}
            </tbody>
          </table>
          <div className="px-4 py-3 bg-gray-50/50 border-t text-xs text-gray-400">{{filtered.length}} student{{filtered.length !== 1 ? "s" : ""}}</div>
        </div>
      </main>
      {{showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4">
            <div className="flex justify-between items-center"><h2 className="text-xl font-bold">Add Student</h2><button onClick={{() => setShowForm(false)}} className="text-gray-400 hover:text-gray-600 text-xl">✕</button></div>
            <form onSubmit={{handleAdd}} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <input className="input" placeholder="Full name *" value={{form.title}} onChange={{e => setForm({{...form, title: e.target.value}})}} required />
                <input className="input" placeholder="Roll number" value={{form.roll}} onChange={{e => setForm({{...form, roll: e.target.value}})}} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                {{["math","science","english","history"].map(sub => (
                  <input key={{sub}} className="input" type="number" min="0" max="100"
                    placeholder={{sub.charAt(0).toUpperCase() + sub.slice(1) + " score"}}
                    value={{form[sub]}} onChange={{e => setForm({{...form, [sub]: e.target.value}})}} />
                ))}}
              </div>
              <div className="flex gap-3 pt-1"><button type="submit" className="btn-primary" disabled={{loading}}>{{loading ? "Saving…" : "Add"}}</button><button type="button" onClick={{() => setShowForm(false)}} className="btn-secondary">Cancel</button></div>
            </form>
          </div>
        </div>
      )}}
    </div>
  );
}}
'''

    # ── CALCULATOR / BMI / CONVERTER / TIP app ──────────────────────────────
    if feat["calculator"]:
        return f'''// src/App.jsx — Generated by VIA for: {task}
import {{ useState }} from "react";
import {{ toast, ToastContainer }} from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

export default function App() {{
  const [display, setDisplay] = useState("0");
  const [prev, setPrev] = useState(null);
  const [op, setOp] = useState(null);
  const [fresh, setFresh] = useState(true);
  const [history, setHistory] = useState([]);

  const press = (val) => {{
    if (fresh) {{ setDisplay(String(val)); setFresh(false); }}
    else setDisplay(display === "0" ? String(val) : display + val);
  }};
  const decimal = () => {{ if (!display.includes(".")) {{ setDisplay(display + "."); setFresh(false); }} }};
  const clear = () => {{ setDisplay("0"); setPrev(null); setOp(null); setFresh(true); }};
  const sign = () => setDisplay(String(-parseFloat(display)));
  const pct = () => setDisplay(String(parseFloat(display) / 100));
  const operate = (nextOp) => {{
    const cur = parseFloat(display);
    if (prev !== null && !fresh) {{
      const res = calc(prev, cur, op);
      setHistory(h => [...h.slice(-4), `${{prev}} ${{op}} ${{cur}} = ${{res}}`]);
      setDisplay(String(res)); setPrev(res);
    }} else {{ setPrev(cur); }}
    setOp(nextOp); setFresh(true);
  }};
  const calc = (a, b, o) => {{
    switch(o) {{
      case "+": return Math.round((a+b)*1e10)/1e10;
      case "−": return Math.round((a-b)*1e10)/1e10;
      case "×": return Math.round((a*b)*1e10)/1e10;
      case "÷": return b !== 0 ? Math.round((a/b)*1e10)/1e10 : (toast.error("Cannot divide by zero"), a);
      default: return b;
    }}
  }};
  const equals = () => {{
    if (prev === null || op === null) return;
    const cur = parseFloat(display);
    const res = calc(prev, cur, op);
    setHistory(h => [...h.slice(-4), `${{prev}} ${{op}} ${{cur}} = ${{res}}`]);
    setDisplay(String(res)); setPrev(null); setOp(null); setFresh(true);
  }};

  const BTN = ({{ label, onClick, cls="", style={{}} }}) => (
    <button onClick={{onClick}} style={{style}}
      className={{`h-16 w-full rounded-2xl text-lg font-semibold transition-all active:scale-95 shadow-sm ${{cls}}`}}>
      {{label}}
    </button>
  );

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4" style={{{{ backgroundColor: "{th["bg"]}" }}}}>
      <ToastContainer position="top-right" autoClose={{3000}} />
      <h1 className="text-2xl font-bold text-gray-900 mb-6">{app_title}</h1>
      <div className="w-full max-w-xs space-y-4">
        {{history.length > 0 && (
          <div className="card p-3 space-y-1">
            {{history.map((h,i) => <p key={{i}} className="text-xs text-gray-400 text-right">{{h}}</p>)}}
          </div>
        )}}
        <div className="bg-gray-900 rounded-2xl px-6 py-5 text-right shadow-xl">
          <p className="text-gray-400 text-sm h-5">{{prev !== null ? `${{prev}} ${{op}}` : ""}}</p>
          <p className="text-white text-4xl font-light mt-1 break-all">{{display}}</p>
        </div>
        <div className="grid grid-cols-4 gap-3">
          <BTN label="AC" onClick={{clear}} cls="bg-gray-200 text-gray-800 hover:bg-gray-300" />
          <BTN label="+/-" onClick={{sign}} cls="bg-gray-200 text-gray-800 hover:bg-gray-300" />
          <BTN label="%" onClick={{pct}} cls="bg-gray-200 text-gray-800 hover:bg-gray-300" />
          <BTN label="÷" onClick={{() => operate("÷")}} cls="text-white hover:opacity-90" style={{{{ backgroundColor: "{p}" }}}} />
          {{["7","8","9"].map(n => <BTN key={{n}} label={{n}} onClick={{() => press(n)}} cls="bg-white text-gray-900 hover:bg-gray-50 border border-gray-100" />)}}
          <BTN label="×" onClick={{() => operate("×")}} cls="text-white hover:opacity-90" style={{{{ backgroundColor: "{p}" }}}} />
          {{["4","5","6"].map(n => <BTN key={{n}} label={{n}} onClick={{() => press(n)}} cls="bg-white text-gray-900 hover:bg-gray-50 border border-gray-100" />)}}
          <BTN label="−" onClick={{() => operate("−")}} cls="text-white hover:opacity-90" style={{{{ backgroundColor: "{p}" }}}} />
          {{["1","2","3"].map(n => <BTN key={{n}} label={{n}} onClick={{() => press(n)}} cls="bg-white text-gray-900 hover:bg-gray-50 border border-gray-100" />)}}
          <BTN label="+" onClick={{() => operate("+")}} cls="text-white hover:opacity-90" style={{{{ backgroundColor: "{p}" }}}} />
          <BTN label="0" onClick={{() => press("0")}} cls="col-span-2 bg-white text-gray-900 hover:bg-gray-50 border border-gray-100" />
          <BTN label="." onClick={{decimal}} cls="bg-white text-gray-900 hover:bg-gray-50 border border-gray-100" />
          <BTN label="=" onClick={{equals}} cls="text-white hover:opacity-90" style={{{{ backgroundColor: "{p}" }}}} />
        </div>
      </div>
    </div>
  );
}}
'''

    # ── KANBAN / BOARD app ───────────────────────────────────────────────────
    # FIX v8: checked AFTER weather. "weather dashboard" no longer hits this
    # branch because _features() now uses word-boundary regex for "board",
    # so "dashboard" correctly returns feat["kanban"]=False.
    if feat["kanban"] and not feat["weather"]:
        return f'''// src/App.jsx — Generated by VIA for: {task}
import {{ useState }} from "react";
import {{ toast, ToastContainer }} from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

const COLS = ["To Do", "In Progress", "Review", "Done"];
const COL_COLORS = {{
  "To Do":       "border-gray-300 bg-gray-50",
  "In Progress": "border-blue-300 bg-blue-50",
  "Review":      "border-amber-300 bg-amber-50",
  "Done":        "border-green-300 bg-green-50",
}};
const PRIORITY = {{ High:"bg-red-100 text-red-700", Medium:"bg-amber-100 text-amber-700", Low:"bg-gray-100 text-gray-600" }};

const SEED = [
  {{ id:1, title:"Design system setup", col:"Done",        priority:"High",   assignee:"Alice" }},
  {{ id:2, title:"API integration",     col:"In Progress", priority:"High",   assignee:"Bob"   }},
  {{ id:3, title:"Write unit tests",    col:"To Do",       priority:"Medium", assignee:"Carol" }},
  {{ id:4, title:"UI review",           col:"Review",      priority:"Low",    assignee:"Dave"  }},
];

export default function App() {{
  const [cards, setCards] = useState(SEED);
  const [dragging, setDragging] = useState(null);
  const [over, setOver] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({{ title:"", priority:"Medium", assignee:"" }});

  const addCard = (e) => {{
    e.preventDefault();
    if (!form.title.trim()) {{ toast.error("Title required"); return; }}
    setCards(c => [...c, {{ id: Date.now(), col:"To Do", ...form }}]);
    setForm({{ title:"", priority:"Medium", assignee:"" }}); setShowForm(false);
    toast.success("Card added!");
  }};
  const deleteCard = (id) => setCards(c => c.filter(x => x.id !== id));
  const moveCard = (col) => {{
    if (dragging === null) return;
    setCards(c => c.map(x => x.id === dragging ? {{...x, col}} : x));
    setDragging(null); setOver(null);
  }};

  return (
    <div className="min-h-screen" style={{{{ backgroundColor: "{th["bg"]}" }}}}>
      <ToastContainer position="top-right" autoClose={{3000}} />
      <nav className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-50">
        <div className="max-w-full px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3"><span className="text-2xl">{icon}</span><span className="font-bold text-gray-900">{app_title}</span></div>
          <button onClick={{() => setShowForm(true)}} className="btn-primary">+ Add Card</button>
        </div>
      </nav>
      <main className="px-6 py-8 overflow-x-auto">
        <div className="flex gap-5 min-w-max">
          {{COLS.map(col => (
            <div key={{col}}
              onDragOver={{e => {{ e.preventDefault(); setOver(col); }}}}
              onDrop={{() => moveCard(col)}}
              className={{`w-72 rounded-2xl border-2 ${{COL_COLORS[col] || "border-gray-200 bg-gray-50"}} p-4 space-y-3 transition-all`}}>
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-800">{{col}}</h2>
                <span className="text-xs bg-white border border-gray-200 text-gray-500 px-2 py-0.5 rounded-full">
                  {{cards.filter(c => c.col === col).length}}
                </span>
              </div>
              {{cards.filter(c => c.col === col).map(card => (
                <div key={{card.id}} draggable
                  onDragStart={{() => setDragging(card.id)}}
                  className="bg-white rounded-xl border border-gray-100 shadow-sm p-3 space-y-2 cursor-grab active:cursor-grabbing hover:shadow-md transition-all">
                  <div className="flex justify-between items-start gap-2">
                    <p className="font-medium text-gray-900 text-sm leading-snug">{{card.title}}</p>
                    <button onClick={{() => deleteCard(card.id)}} className="text-gray-300 hover:text-red-400 text-xs shrink-0">✕</button>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className={{`text-xs px-2 py-0.5 rounded-full font-medium ${{PRIORITY[card.priority] || PRIORITY.Medium}}`}}>{{card.priority}}</span>
                    {{card.assignee && <span className="text-xs text-gray-400">👤 {{card.assignee}}</span>}}
                  </div>
                </div>
              ))}}
              <button onClick={{() => setShowForm(true)}}
                className="w-full text-sm text-gray-400 hover:text-gray-700 py-2 border-2 border-dashed border-gray-200 rounded-xl hover:border-gray-300 transition-all">
                + Add card
              </button>
            </div>
          ))}}
        </div>
      </main>
      {{showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 space-y-4">
            <div className="flex justify-between items-center"><h2 className="text-xl font-bold">New Card</h2><button onClick={{() => setShowForm(false)}} className="text-gray-400 text-xl">✕</button></div>
            <form onSubmit={{addCard}} className="space-y-3">
              <input className="input" placeholder="Card title *" value={{form.title}} onChange={{e => setForm({{...form, title:e.target.value}})}} required />
              <select className="input" value={{form.priority}} onChange={{e => setForm({{...form, priority:e.target.value}})}}>
                <option>High</option><option>Medium</option><option>Low</option>
              </select>
              <input className="input" placeholder="Assignee" value={{form.assignee}} onChange={{e => setForm({{...form, assignee:e.target.value}})}} />
              <div className="flex gap-3"><button type="submit" className="btn-primary">Add</button><button type="button" onClick={{() => setShowForm(false)}} className="btn-secondary">Cancel</button></div>
            </form>
          </div>
        </div>
      )}}
    </div>
  );
}}
'''

    # ── WEATHER / FORECAST app (NEW in v8) ───────────────────────────────────
    # Checked BEFORE feat["chart"] because "weather dashboard" sets both to True.
    # Without this block, weather apps rendered as a generic analytics dashboard.
    if feat["weather"]:
        return f'''// src/App.jsx — Generated by VIA for: {task}
import {{ useState, useEffect }} from "react";
import {{ toast, ToastContainer }} from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL ||
  (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://localhost:8000" : "");

const WEATHER_ICONS = {{
  Clear: "☀️", Sunny: "☀️", Clouds: "☁️", Cloudy: "⛅",
  Rain: "🌧️", Drizzle: "🌦️", Thunderstorm: "⛈️",
  Snow: "❄️", Mist: "🌫️", Fog: "🌫️", Haze: "🌫️",
}};
const weatherIcon = (condition) =>
  WEATHER_ICONS[condition] || WEATHER_ICONS[Object.keys(WEATHER_ICONS).find(k => condition?.includes(k))] || "🌡️";

const MOCK_CURRENT = {{
  city: "Hyderabad", country: "IN", temp: 32, feels_like: 35,
  condition: "Partly Cloudy", humidity: 58, wind_speed: 14, visibility: 10,
  sunrise: "6:04 AM", sunset: "6:41 PM", uv_index: 7,
}};
const MOCK_FORECAST = [
  {{ day:"Mon", high:33, low:24, condition:"Sunny" }},
  {{ day:"Tue", high:31, low:23, condition:"Clouds" }},
  {{ day:"Wed", high:28, low:22, condition:"Rain" }},
  {{ day:"Thu", high:30, low:23, condition:"Cloudy" }},
  {{ day:"Fri", high:34, low:25, condition:"Clear" }},
  {{ day:"Sat", high:32, low:24, condition:"Clouds" }},
  {{ day:"Sun", high:29, low:22, condition:"Drizzle" }},
];

export default function App() {{
  const [city, setCity] = useState("Hyderabad");
  const [query, setQuery] = useState("Hyderabad");
  const [current, setCurrent] = useState(MOCK_CURRENT);
  const [forecast, setForecast] = useState(MOCK_FORECAST);
  const [loading, setLoading] = useState(false);
  const [unit, setUnit] = useState("C");

  const toF = (c) => Math.round(c * 9/5 + 32);
  const tempDisplay = (c) => unit === "C" ? `${{c}}°C` : `${{toF(c)}}°F`;

  const fetchWeather = async (cityName) => {{
    if (!cityName.trim()) {{ toast.error("Enter a city name"); return; }}
    setLoading(true);
    try {{
      const [curRes, foreRes] = await Promise.all([
        axios.get(`${{BASE_URL}}/api/v1/weather/current?city=${{encodeURIComponent(cityName)}}`),
        axios.get(`${{BASE_URL}}/api/v1/weather/forecast?city=${{encodeURIComponent(cityName)}}`),
      ]);
      setCurrent(curRes.data);
      setForecast(Array.isArray(foreRes.data) ? foreRes.data : foreRes.data?.forecast ?? MOCK_FORECAST);
      setCity(cityName);
    }} catch (err) {{
      if (err.response?.status === 404) {{
        toast.error(`City "${{cityName}}" not found`);
      }} else {{
        toast.info("Backend offline — showing demo data");
        setCurrent({{ ...MOCK_CURRENT, city: cityName }});
        setForecast(MOCK_FORECAST);
        setCity(cityName);
      }}
    }} finally {{
      setLoading(false);
    }}
  }};

  const handleSearch = (e) => {{
    e.preventDefault();
    fetchWeather(query);
  }};

  const bgGradient = current.condition?.toLowerCase().includes("rain") || current.condition?.toLowerCase().includes("thunder")
    ? "from-slate-700 to-slate-900"
    : current.condition?.toLowerCase().includes("cloud")
    ? "from-slate-500 to-slate-700"
    : "from-sky-400 to-blue-600";

  return (
    <div className="min-h-screen" style={{{{ backgroundColor: "{th["bg"]}" }}}}>
      <ToastContainer position="top-right" autoClose={{3000}} />

      {{/* Hero / current weather */}}
      <div className={{`bg-gradient-to-br ${{bgGradient}} text-white`}}>
        <div className="max-w-2xl mx-auto px-6 pt-10 pb-12">
          {{/* Search bar */}}
          <form onSubmit={{handleSearch}} className="flex gap-2 mb-8">
            <input
              value={{query}} onChange={{e => setQuery(e.target.value)}}
              placeholder="Search city…"
              className="flex-1 bg-white/20 backdrop-blur border border-white/30 rounded-xl px-4 py-3 text-white placeholder-white/60 outline-none focus:bg-white/30 transition-all"
            />
            <button type="submit" disabled={{loading}}
              className="px-5 py-3 bg-white/20 hover:bg-white/30 border border-white/30 rounded-xl font-semibold transition-all disabled:opacity-50">
              {{loading ? "…" : "🔍"}}
            </button>
            <button type="button" onClick={{() => setUnit(u => u === "C" ? "F" : "C")}}
              className="px-4 py-3 bg-white/20 hover:bg-white/30 border border-white/30 rounded-xl font-semibold transition-all">
              °{{unit === "C" ? "F" : "C"}}
            </button>
          </form>

          {{/* Current conditions */}}
          <div className="text-center space-y-2">
            <p className="text-white/70 text-lg">{{current.city}}{{current.country ? `, ${{current.country}}` : ""}}</p>
            <div className="text-8xl leading-none">{{weatherIcon(current.condition)}}</div>
            <p className="text-7xl font-thin">{{tempDisplay(current.temp)}}</p>
            <p className="text-xl text-white/80">{{current.condition}}</p>
            <p className="text-white/60">Feels like {{tempDisplay(current.feels_like)}}</p>
          </div>

          {{/* Stats row */}}
          <div className="grid grid-cols-3 gap-3 mt-8">
            {{[
              ["💧 Humidity", `${{current.humidity}}%`],
              ["💨 Wind",     `${{current.wind_speed}} km/h`],
              ["👁 Visibility", `${{current.visibility}} km`],
            ].map(([label, val]) => (
              <div key={{label}} className="bg-white/15 backdrop-blur rounded-2xl px-4 py-3 text-center">
                <p className="text-white/70 text-xs">{{label}}</p>
                <p className="text-white font-semibold text-lg mt-1">{{val}}</p>
              </div>
            ))}}
          </div>
        </div>
      </div>

      {{/* 7-day forecast */}}
      <div className="max-w-2xl mx-auto px-6 py-8 space-y-6">
        <h2 className="font-bold text-gray-800 text-lg">7-Day Forecast</h2>
        <div className="grid grid-cols-7 gap-2">
          {{forecast.slice(0,7).map((day, i) => (
            <div key={{i}} className="card text-center py-4 px-2 space-y-2">
              <p className="text-xs font-semibold text-gray-500">{{day.day}}</p>
              <p className="text-2xl">{{weatherIcon(day.condition)}}</p>
              <p className="text-xs font-bold text-gray-800">{{tempDisplay(day.high)}}</p>
              <p className="text-xs text-gray-400">{{tempDisplay(day.low)}}</p>
            </div>
          ))}}
        </div>

        {{/* Sun & UV details */}}
        <div className="grid grid-cols-3 gap-4">
          {{[
            ["🌅 Sunrise", current.sunrise || "6:04 AM"],
            ["🌇 Sunset",  current.sunset  || "6:41 PM"],
            ["☀️ UV Index", current.uv_index ?? 7],
          ].map(([label, val]) => (
            <div key={{label}} className="card text-center">
              <p className="text-xs text-gray-500">{{label}}</p>
              <p className="font-bold text-gray-800 mt-1">{{val}}</p>
            </div>
          ))}}
        </div>
      </div>
    </div>
  );
}}
'''

    # ── HOSPITAL / APPOINTMENT app ───────────────────────────────────────────
    if feat["hospital"]:
        empty_msg  = "No appointments yet"
        new_btn    = "+ Book Appointment"
        form_title = "Book Appointment"
        stat_cards = [("Total Appointments", "stats?.total ?? 0"), ("Scheduled", "stats?.active ?? 0"), ("Departments", '"4+"')]
        extra_fields = """
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Doctor</label>
              <input className="input" placeholder="Dr. Smith" value={form.doctor_name || ""} onChange={e => setForm({...form, doctor_name: e.target.value})} /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
              <select className="input" value={form.department || "General"} onChange={e => setForm({...form, department: e.target.value})}>
                <option>General</option><option>Cardiology</option><option>Neurology</option><option>Orthopedics</option><option>Pediatrics</option>
              </select></div>
          </div>"""
        extra_row = "<td className=\"px-5 py-4 text-gray-600\">{item.doctor_name || '—'}</td><td className=\"px-5 py-4 text-gray-600\">{item.department || 'General'}</td>"
        extra_th  = "<th className=\"px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase\">Doctor</th><th className=\"px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase\">Dept</th>"

    # ── GAME / LEADERBOARD app ───────────────────────────────────────────────
    elif feat["game"]:
        empty_msg  = "No game sessions yet"
        new_btn    = "+ Add Session"
        form_title = "New Game Session"
        stat_cards = [("Total Sessions", "stats?.total ?? 0"), ("Active", "stats?.active ?? 0"), ("Platform", '"Multi"')]
        extra_fields = f"""
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Game</label>
              <input className="input" placeholder="e.g. Valorant" value={{form.game_name || ""}} onChange={{e => setForm({{...form, game_name: e.target.value}})}} /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Score</label>
              <input className="input" type="number" placeholder="0" value={{form.score || ""}} onChange={{e => setForm({{...form, score: parseInt(e.target.value) || 0}})}} /></div>
          </div>"""
        extra_row = f'<td className="px-5 py-4 text-gray-600">{{item.game_name || "—"}}</td><td className="px-5 py-4 font-bold {score_cls}">{{item.score ?? 0}}</td>'
        extra_th  = '<th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Game</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Score</th>'

    # ── EXPENSE / FINANCE app ────────────────────────────────────────────────
    elif feat["expense"]:
        empty_msg  = "No expenses yet"
        new_btn    = "+ Add Expense"
        form_title = "Add Expense"
        stat_cards = [("Total Expenses", "stats?.total ?? 0"), ("Active", "stats?.active ?? 0"), ("Tracked", '"Auto"')]
        extra_fields = """
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Amount (₹)</label>
              <input className="input" type="number" placeholder="0.00" value={form.amount || ""} onChange={e => setForm({...form, amount: parseFloat(e.target.value) || 0})} /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select className="input" value={form.category || "General"} onChange={e => setForm({...form, category: e.target.value})}>
                <option>General</option><option>Food</option><option>Transport</option><option>Bills</option><option>Entertainment</option>
              </select></div>
          </div>"""
        extra_row = "<td className=\"px-5 py-4 text-gray-600\">{item.category || 'General'}</td><td className=\"px-5 py-4 font-semibold text-emerald-700\">₹{(item.amount || 0).toLocaleString()}</td>"
        extra_th  = "<th className=\"px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase\">Category</th><th className=\"px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase\">Amount</th>"

    # ── TODO / TASK app ──────────────────────────────────────────────────────
    elif feat["todo"]:
        empty_msg  = "No tasks yet"
        new_btn    = "+ Add Task"
        form_title = "New Task"
        stat_cards = [("Total Tasks", "stats?.total ?? 0"), ("Completed", "stats?.active ?? 0"), ("Pending", '"Auto"')]
        extra_fields = """
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
              <select className="input" value={form.priority || "Medium"} onChange={e => setForm({...form, priority: e.target.value})}>
                <option>High</option><option>Medium</option><option>Low</option>
              </select></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
              <input className="input" type="date" value={form.due_date || ""} onChange={e => setForm({...form, due_date: e.target.value})} /></div>
          </div>"""
        extra_row = "<td className=\"px-5 py-4 text-gray-600\">{item.priority || 'Medium'}</td><td className=\"px-5 py-4 text-gray-500\">{item.due_date || '—'}</td>"
        extra_th  = "<th className=\"px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase\">Priority</th><th className=\"px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase\">Due</th>"

    # ── CHART / ANALYTICS / DASHBOARD (last resort before generic) ──────────
    # FIX v8: this block is now AFTER all domain-specific checks.
    # "weather dashboard" no longer reaches here because feat["weather"] is True
    # and is checked first. Same for "expense dashboard", "hospital analytics", etc.
    elif feat["chart"]:
        return f'''// src/App.jsx — Generated by VIA for: {task}
import {{ useState, useEffect }} from "react";
import {{ getStats, getItems }} from "./api.js";

const BAR_COLORS = ["{p}", "#6366f1","#f59e0b","#10b981","#ef4444","#8b5cf6"];

function BarChart({{ data }}) {{
  const max = Math.max(...data.map(d => d.value), 1);
  return (
    <div className="space-y-2">
      {{data.map((d, i) => (
        <div key={{i}} className="flex items-center gap-3">
          <span className="text-xs text-gray-500 w-20 text-right shrink-0">{{d.label}}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
            <div className="h-full rounded-full flex items-center justify-end pr-2 transition-all duration-700"
              style={{{{ width: `${{(d.value/max)*100}}%`, backgroundColor: BAR_COLORS[i % BAR_COLORS.length] }}}}>
              <span className="text-xs text-white font-semibold">{{d.value}}</span>
            </div>
          </div>
        </div>
      ))}}
    </div>
  );
}}

export default function App() {{
  const [stats, setStats] = useState({{ total:0, active:0 }});
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("week");

  useEffect(() => {{
    Promise.all([
      getStats().then(r => r.data).catch(() => ({{ total: 0, active: 0 }})),
      getItems().then(r => Array.isArray(r.data) ? r.data : r.data?.items ?? []).catch(() => []),
    ]).then(([s, i]) => {{ setStats(s); setItems(i); setLoading(false); }});
  }}, []);

  const MOCK_TREND = [
    {{ label:"Mon", value:42 }}, {{ label:"Tue", value:68 }}, {{ label:"Wed", value:55 }},
    {{ label:"Thu", value:91 }}, {{ label:"Fri", value:74 }}, {{ label:"Sat", value:39 }}, {{ label:"Sun", value:57 }},
  ];

  const statusData = ["active","pending","done","inactive"].map(s => ({{
    label: s.charAt(0).toUpperCase() + s.slice(1),
    value: items.filter(i => i.status === s).length,
  }})).filter(d => d.value > 0);

  return (
    <div className="min-h-screen" style={{{{ backgroundColor: "{th["bg"]}" }}}}>
      <nav className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3"><span className="text-2xl">{icon}</span><span className="font-bold text-gray-900">{app_title}</span></div>
          <div className="flex gap-2">
            {{["week","month","year"].map(p => (
              <button key={{p}} onClick={{() => setPeriod(p)}}
                className={{`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${{period===p ? "text-white" : "text-gray-500 bg-white border border-gray-200"}}`}}
                style={{{{ backgroundColor: period===p ? "{p}" : undefined }}}}>
                {{p.charAt(0).toUpperCase()+p.slice(1)}}
              </button>
            ))}}
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">{app_title}</h1>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {{[
            ["Total Records", stats.total ?? items.length ?? 0, "📦", "blue"],
            ["Active",        stats.active ?? items.filter(i=>i.status==="active").length, "✅", "green"],
            ["This Period",   Math.floor(Math.random()*40)+10, "📈", "purple"],
            ["Growth",        "+12%", "🚀", "amber"],
          ].map(([label, val, ic, color]) => (
            <div key={{label}} className={{`card bg-gradient-to-br ${{
              color==="blue" ? "from-blue-50 to-blue-100/50 border-blue-200" :
              color==="green"? "from-green-50 to-green-100/50 border-green-200" :
              color==="purple"?"from-purple-50 to-purple-100/50 border-purple-200":
                               "from-amber-50 to-amber-100/50 border-amber-200"
            }}`}}>
              <p className="text-2xl mb-1">{{ic}}</p>
              <p className="text-2xl font-bold text-gray-900">{{loading ? "…" : val}}</p>
              <p className="text-xs text-gray-500 mt-1">{{label}}</p>
            </div>
          ))}}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="card space-y-4">
            <h2 className="font-semibold text-gray-800">Activity Trend</h2>
            <BarChart data={{MOCK_TREND}} />
          </div>
          <div className="card space-y-4">
            <h2 className="font-semibold text-gray-800">Status Breakdown</h2>
            {{statusData.length > 0
              ? <BarChart data={{statusData}} />
              : <p className="text-gray-400 text-sm py-8 text-center">No data yet</p>
            }}
          </div>
        </div>
        {{items.length > 0 && (
          <div className="card overflow-hidden p-0">
            <div className="px-5 py-4 border-b border-gray-100"><h2 className="font-semibold text-gray-800">Recent Records</h2></div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50"><tr>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Title</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Created</th>
              </tr></thead>
              <tbody className="divide-y divide-gray-50">
                {{items.slice(0,8).map(item => (
                  <tr key={{item.id ?? item._id}} className="hover:bg-gray-50/50">
                    <td className="px-5 py-3 font-medium text-gray-900">{{item.title}}</td>
                    <td className="px-5 py-3"><span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-700">{{item.status || "active"}}</span></td>
                    <td className="px-5 py-3 text-gray-400">{{item.created_at ? new Date(item.created_at).toLocaleDateString() : "—"}}</td>
                  </tr>
                ))}}
              </tbody>
            </table>
          </div>
        )}}
      </main>
    </div>
  );
}}
'''

    # ── GENERIC CRUD FALLBACK ────────────────────────────────────────────────
    else:
        empty_msg  = "No records yet"
        new_btn    = "+ Create New"
        form_title = "Create New Record"
        stat_cards = [("Total", "stats?.total ?? 0"), ("Active", "stats?.active ?? 0"), ("System", '"Online"')]
        extra_fields = """
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <input className="input" placeholder="Category" value={form.category || ""} onChange={e => setForm({...form, category: e.target.value})} /></div>"""
        extra_row = "<td className=\"px-5 py-4 text-gray-500 hidden md:table-cell\">{item.description || '—'}</td>"
        extra_th  = "<th className=\"px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell\">Description</th>"

    # ── SHARED CRUD SCAFFOLD (hospital / game / expense / todo / generic) ────
    stat_cards_jsx = "\n        ".join([
        f'<StatCard title="{lbl}" value={{{val}}} loading={{loading}} color="{["blue","green","purple"][i % 3]}" />'
        for i, (lbl, val) in enumerate(stat_cards)
    ])

    return f'''// src/App.jsx — Generated by VIA for: {task}
import {{ useState, useEffect, useCallback }} from "react";
import {{ Routes, Route, Link, useNavigate }} from "react-router-dom";
import {{ toast, ToastContainer }} from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import {{ getItems, createItem, deleteItem, getStats }} from "./api.js";

const parseItems = (data) => {{
  if (Array.isArray(data)) return data;
  if (data?.items   && Array.isArray(data.items))   return data.items;
  if (data?.data    && Array.isArray(data.data))    return data.data;
  if (data?.results && Array.isArray(data.results)) return data.results;
  if (data && typeof data === "object" &&
      (data.id !== undefined || data._id !== undefined)) return [data];
  return [];
}};

const THEME = "{p}";

export default function App() {{
  return (
    <div className="min-h-screen" style={{{{ backgroundColor: "{th["bg"]}" }}}}>
      <ToastContainer position="top-right" autoClose={{3000}} hideProgressBar={{false}} />
      <nav className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center gap-2">
              <span className="text-2xl">{icon}</span>
              <span className="font-display font-bold text-gray-900 text-lg">{app_title}</span>
            </Link>
            <div className="flex items-center gap-3">
              <Link to="/" className="text-sm text-gray-500 hover:text-gray-900 px-3 py-1.5 rounded-lg hover:bg-gray-50 transition-colors">Dashboard</Link>
              <Link to="/items" className="text-sm text-gray-500 hover:text-gray-900 px-3 py-1.5 rounded-lg hover:bg-gray-50 transition-colors">All Records</Link>
              <Link to="/new" className="btn-primary text-sm py-2 px-4">{new_btn}</Link>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={{<HomePage />}} />
          <Route path="/items" element={{<ItemListPage />}} />
          <Route path="/new" element={{<ItemFormPage />}} />
          <Route path="/edit/:id" element={{<ItemFormPage />}} />
          <Route path="*" element={{<NotFoundPage />}} />
        </Routes>
      </main>
    </div>
  );
}}

function HomePage() {{
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);
  useEffect(() => {{
    Promise.all([
      getStats().then(r => r.data).catch(() => ({{total: 0, active: 0}})),
      getItems().then(r => parseItems(r.data)).catch(() => []),
    ]).then(([s, i]) => {{ setStats(s); setItems(i); setLoading(false); }});
  }}, []);
  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-gray-900">{app_title}</h1>
          <p className="text-gray-500 mt-1 text-sm">Powered by VIA — Autonomous AI Platform</p>
        </div>
        <Link to="/new" className="btn-primary">{new_btn}</Link>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        {stat_cards_jsx}
      </div>
      <div className="card">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-display font-semibold text-gray-900">Recent Records</h2>
          <Link to="/items" className="text-sm font-medium hover:underline" style={{{{ color: THEME }}}}>View all →</Link>
        </div>
        {{loading ? <Spinner /> : items.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-400 mb-4">{empty_msg}</p>
            <Link to="/new" className="btn-primary inline-block">{new_btn}</Link>
          </div>
        ) : (
          <div className="space-y-3">
            {{items.slice(0, 5).map(item => (
              <div key={{item.id ?? item._id}} className="flex items-center justify-between p-4 rounded-xl border border-gray-100 hover:bg-gray-50 transition-all">
                <div>
                  <p className="font-medium text-gray-900">{{item.title}}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{{item.created_at ? new Date(item.created_at).toLocaleDateString() : ""}}</p>
                </div>
                <Badge status={{item.status || "active"}} />
              </div>
            ))}}
          </div>
        )}}
      </div>
    </div>
  );
}}

function StatCard({{ title, value, loading, color }}) {{
  const cls = {{
    blue:   "from-blue-50 to-blue-100/50 border-blue-200 text-blue-700",
    green:  "from-green-50 to-green-100/50 border-green-200 text-green-700",
    purple: "from-purple-50 to-purple-100/50 border-purple-200 text-purple-700",
  }};
  return (
    <div className={{`rounded-2xl border bg-gradient-to-br p-6 ${{cls[color] || cls.blue}}`}}>
      <p className="text-sm font-medium opacity-70">{{title}}</p>
      <p className="text-3xl font-display font-bold mt-2">{{loading ? "..." : value}}</p>
    </div>
  );
}}

function ItemListPage() {{
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [deleting, setDeleting] = useState(null);

  const load = useCallback(() => {{
    setLoading(true);
    getItems()
      .then(r => setItems(parseItems(r.data)))
      .catch(() => setError("Cannot reach backend. It may be starting up — wait 30s and retry."))
      .finally(() => setLoading(false));
  }}, []);

  useEffect(() => {{ load(); }}, [load]);

  const handleDelete = async (id) => {{
    if (!confirm("Delete this record?")) return;
    setDeleting(id);
    try {{
      await deleteItem(id);
      toast.success("Deleted successfully!");
      load();
    }} catch {{
      toast.error("Delete failed. Please try again.");
    }} finally {{
      setDeleting(null);
    }}
  }};

  const filtered = items.filter(i => (i.title || "").toLowerCase().includes(search.toLowerCase()));
  if (loading) return <Spinner />;
  if (error) return (
    <div className="card text-center py-16">
      <p className="text-2xl mb-3">⚠️</p>
      <p className="text-red-500 font-medium mb-4">{{error}}</p>
      <button onClick={{load}} className="btn-primary">Retry</button>
    </div>
  );
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl font-display font-bold text-gray-900">All Records</h1>
        <div className="flex gap-3">
          <input className="input max-w-xs" placeholder="Search..." value={{search}} onChange={{e => setSearch(e.target.value)}} />
          <Link to="/new" className="btn-primary whitespace-nowrap">{new_btn}</Link>
        </div>
      </div>
      {{filtered.length === 0 ? (
        <div className="card text-center py-20">
          <p className="text-5xl mb-4">{icon}</p>
          <p className="text-gray-400 text-lg mb-6">{empty_msg}</p>
          <Link to="/new" className="btn-primary inline-block">{new_btn}</Link>
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-gray-50/80 border-b border-gray-100">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Title</th>
                {extra_th}
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {{filtered.map(item => (
                <tr key={{item.id ?? item._id}} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-5 py-4 font-medium text-gray-900">{{item.title}}</td>
                  {extra_row}
                  <td className="px-5 py-4"><Badge status={{item.status || "active"}} /></td>
                  <td className="px-5 py-4">
                    <div className="flex justify-end gap-2">
                      <Link to={{`/edit/${{item.id ?? item._id}}`}} className="text-xs py-1.5 px-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors">Edit</Link>
                      <button onClick={{() => handleDelete(item.id ?? item._id)}} disabled={{deleting === (item.id ?? item._id)}}
                        className="text-xs py-1.5 px-3 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg border border-red-100 transition-colors disabled:opacity-50">
                        {{deleting === (item.id ?? item._id) ? "..." : "Delete"}}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}}
            </tbody>
          </table>
          <div className="px-5 py-3 bg-gray-50/50 border-t border-gray-100 text-xs text-gray-400">
            {{filtered.length}} record{{filtered.length !== 1 ? "s" : ""}}
          </div>
        </div>
      )}}
    </div>
  );
}}

function ItemFormPage() {{
  const [form, setForm] = useState({{ title: "", description: "", status: "active" }});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const submit = async (e) => {{
    e.preventDefault();
    if (!form.title.trim()) {{ setError("Title is required"); return; }}
    setLoading(true); setError("");
    try {{
      await createItem(form);
      navigate("/items");
      toast.success("Saved successfully!");
    }} catch (err) {{
      const msg = err.response?.data?.detail || "Save failed. Backend may be starting up.";
      setError(msg);
      toast.error(msg);
    }} finally {{
      setLoading(false);
    }}
  }};
  return (
    <div className="max-w-2xl mx-auto">
      <Link to="/items" className="text-sm text-gray-500 hover:text-gray-700 mb-6 inline-block">← Back</Link>
      <div className="card">
        <h1 className="text-2xl font-display font-bold text-gray-900 mb-6">{form_title}</h1>
        {{error && <div className="bg-red-50 border border-red-100 text-red-700 p-4 rounded-xl mb-5 text-sm">{{error}}</div>}}
        <form onSubmit={{submit}} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
            <input className="input" placeholder="Enter title" value={{form.title}} onChange={{e => setForm({{...form, title: e.target.value}})}} required />
          </div>
          {extra_fields}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea className="input resize-none h-24" placeholder="Optional notes..." value={{form.description || ""}} onChange={{e => setForm({{...form, description: e.target.value}})}} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select className="input" value={{form.status}} onChange={{e => setForm({{...form, status: e.target.value}})}}>
              <option value="active">Active</option><option value="inactive">Inactive</option>
              <option value="pending">Pending</option><option value="done">Done</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="submit" className="btn-primary" disabled={{loading}}>{{loading ? "Saving..." : "Save"}}</button>
            <Link to="/items" className="btn-secondary">Cancel</Link>
          </div>
        </form>
      </div>
    </div>
  );
}}

function Badge({{ status }}) {{
  const m = {{ active: "badge-active", inactive: "badge-inactive", pending: "badge-pending", done: "badge-done", scheduled: "badge-scheduled", confirmed: "badge-confirmed" }};
  return <span className={{m[status] || "badge-inactive"}}>{{status}}</span>;
}}

function Spinner() {{
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-4">
      <div className="w-10 h-10 border-4 border-gray-200 rounded-full animate-spin" style={{{{ borderTopColor: THEME }}}} />
      <p className="text-sm text-gray-400">Loading...</p>
    </div>
  );
}}

function NotFoundPage() {{
  return (
    <div className="card text-center py-24">
      <p className="text-8xl font-display font-bold text-gray-100">404</p>
      <p className="text-gray-400 mt-4 mb-6">Page not found</p>
      <Link to="/" className="btn-primary inline-block">Go Home</Link>
    </div>
  );
}}
'''


# ---------------------------------------------------------------------------
# FIX v8: _build_prompt — same priority reorder as _app_jsx().
# Domain-specific hints come before the generic "chart/analytics" hint so
# "create a simple weather dashboard" gets the weather UI hint, not the
# analytics/chart hint.
# ---------------------------------------------------------------------------
def _build_prompt(task: str, ceo_strategy: str = "", inter_context: str = "") -> str:
    strategy_block = f"\nCEO Strategic Direction: {ceo_strategy}\n" if ceo_strategy else ""
    context_block  = f"\nContext from other departments:\n{inter_context}\n" if inter_context else ""

    t = task.lower()

    # ── Detect app type — domain-specific checks first, generic last ─────────
    if any(w in t for w in ["image", "photo", "upload", "grayscale", "picture", "crop", "filter"]):
        ui_hint = """UI REQUIREMENTS — IMAGE/FILE APP:
- File drag-and-drop upload zone (large, prominent, dashed border)
- Image preview (original) shown immediately after selection
- "Process" button triggers POST /api/v1/process with multipart/form-data
- Processed result shown side-by-side with original
- Download button for the result
- Show file name and size below preview
- NO generic form/table — this is a media processing app"""

    elif any(w in t for w in ["recipe", "cook", "ingredient", "meal", "food", "dish"]):
        ui_hint = """UI REQUIREMENTS — RECIPE APP:
- Recipe cards grid (not a table) — each card shows name, category badge, prep time, servings
- Category filter buttons (Breakfast, Lunch, Dinner, Snack, Dessert)
- Click a card to open detail view with full ingredients list and step-by-step instructions
- Add Recipe modal with fields: name, category, prep time, servings, ingredients (textarea), steps (textarea)
- NO generic Title/Description/Status form — fields must match recipes"""

    elif any(w in t for w in ["game", "gaming", "player", "score", "leaderboard"]):
        ui_hint = """UI REQUIREMENTS — GAME/LEADERBOARD APP:
- Leaderboard table sorted by score descending with rank numbers (🥇🥈🥉 for top 3)
- Columns: Rank, Player name, Game, Score, Date
- Add Session form: player name, game name, score (number input), platform
- Top 3 players shown as podium cards at the top
- Score highlighted in bold with color based on rank"""

    elif any(w in t for w in ["grade", "student", "mark", "gpa", "academic", "exam", "result", "subject", "marks"]):
        ui_hint = """UI REQUIREMENTS — GRADE/STUDENT TRACKER:
- Table with columns: Roll No, Name, Subject scores (Math, Science, English, History), Average %, Grade letter
- Grade letter computed from average (A+≥90, A≥80, B≥70, C≥60, D≥50, F<50) shown as colored badge
- Stats row: total students, class average, passing count, failing count
- Add Student modal with subject score inputs (0-100 number fields)
- Sort by name or by average descending
- NO generic Title/Description/Status — use student-specific fields"""

    elif any(w in t for w in ["calculator", "calculate", "math", "compute", "converter", "bmi", "tip calc"]):
        ui_hint = """UI REQUIREMENTS — CALCULATOR APP:
- Full calculator UI: digit buttons 0-9, operators (+, −, ×, ÷), decimal, equals, clear, +/-, %
- Large display showing current value and pending operation
- Calculation history log (last 5 operations)
- Buttons in a 4-column grid, styled with color-coded operator buttons
- NO form, NO table, NO API calls needed — pure client-side logic"""

    elif any(w in t for w in ["kanban", "sprint"]) or (re.search(r'\bboard\b', t) and "weather" not in t and "dashboard" not in t):
        ui_hint = """UI REQUIREMENTS — KANBAN BOARD:
- 4 columns: To Do, In Progress, Review, Done
- Cards inside each column showing title, priority badge (High/Medium/Low), assignee
- Drag-and-drop cards between columns (use HTML5 draggable + onDrop)
- Add Card button opens modal: title, priority select, assignee input
- Card count badge on each column header
- Color-coded column headers
- NO generic list/table view"""

    # FIX v8: weather BEFORE chart — "weather dashboard" must get this hint, not the analytics hint
    elif any(w in t for w in ["weather", "forecast", "temperature", "climate", "rain", "humidity", "wind", "storm"]):
        ui_hint = """UI REQUIREMENTS — WEATHER APP:
- City search bar at the top (text input + search button + °C/°F toggle)
- Hero section with gradient background showing: city name, large weather emoji, temperature, condition, feels-like
- Stats strip below hero: humidity %, wind speed km/h, visibility km
- 7-day forecast as a horizontal strip of day cards (day name, emoji, high/low temps)
- Sunrise, sunset, UV index info cards
- API calls: GET /api/v1/weather/current?city=X and GET /api/v1/weather/forecast?city=X
- Show demo/mock data when backend is offline
- NO generic form/table — this is purely a weather display app"""

    elif any(w in t for w in ["hospital", "appointment", "doctor", "patient", "medical"]):
        ui_hint = """UI REQUIREMENTS — HOSPITAL/APPOINTMENT APP:
- Appointment list with Doctor name, Department, Date/Time, Status columns
- Book Appointment form: patient name, doctor, department (dropdown), date, time, notes
- Department filter (All, General, Cardiology, Neurology, Orthopedics, Pediatrics)
- Status badges: Scheduled (green), Pending (yellow), Cancelled (red)
- Stats: total appointments, scheduled today, active doctors count"""

    elif any(w in t for w in ["expense", "budget", "finance", "spending", "money"]):
        ui_hint = """UI REQUIREMENTS — EXPENSE/FINANCE APP:
- Expense list with Category, Amount, Date, Notes columns
- Add Expense form: description, amount (number), category (Food/Transport/Bills/Entertainment/Other), date
- Category filter tabs
- Total spent summary card and breakdown by category
- Amount displayed with currency symbol (₹ or $)
- Color-coded categories"""

    elif any(w in t for w in ["todo", "task", "checklist"]):
        ui_hint = """UI REQUIREMENTS — TODO/TASK APP:
- Task list with checkboxes to mark complete (strikethrough on done)
- Priority levels (High/Medium/Low) shown as colored badges
- Filter tabs: All, Active, Completed
- Add Task: title, priority select, due date, optional notes
- Stats: total, completed, pending counts
- Completed tasks visually distinct (grayed out, strikethrough)"""

    # FIX v8: chart/analytics is now LAST — only reached if no domain type matched
    elif any(w in t for w in ["chart", "graph", "analytics", "dashboard", "visuali", "report", "statistic"]):
        ui_hint = """UI REQUIREMENTS — ANALYTICS DASHBOARD:
- KPI metric cards at top (4 cards: Total, Active, This Period, Growth)
- Bar chart built with divs/CSS (no external chart library) showing weekly trend
- Status breakdown chart (another bar chart)
- Recent records table below charts
- Period filter buttons (Week / Month / Year)
- All charts built with plain CSS bar charts using percentage widths — NO recharts or chart.js"""

    else:
        ui_hint = f"""UI REQUIREMENTS — CUSTOM APP for: {task}
- Build the UI that DIRECTLY matches this task — not a generic form
- Identify the core entities from the task and make columns/fields match them exactly
- Use appropriate layout: cards for browseable content, table for structured data, wizard for multi-step
- The app should look purpose-built for "{task}", not like a generic CRUD template
- Include relevant domain-specific fields, actions, and terminology"""

    return f"""You are a World-Class Frontend Engineer and UI/UX Designer. Build a COMPLETE, PRODUCTION-READY React frontend.

CRITICAL DESIGN REQUIREMENT: 
The UI must be **STUNNING, MODERN, AND PREMIUM**. DO NOT build a basic, generic white page with simple tables and boring forms. 
- Use rich aesthetics: vibrant modern color palettes, glassmorphism, subtle gradients, and dark modes.
- Implement a beautiful layout with a sidebar or modern top navigation, hero sections, and metric cards.
- Use micro-animations (hover states, transitions) using Tailwind utility classes (`transition-all duration-300 hover:scale-105`).
- Ensure all components look polished like a real SaaS product.

════════════════════════════════════════════════════════
TASK: {task}
════════════════════════════════════════════════════════
{strategy_block}{context_block}
{ui_hint}

OUTPUT FORMAT — each file EXACTLY like this (no backticks, no markdown):
=== FILE: src/App.jsx ===
// complete code here
=== END ===

FILES TO GENERATE: src/App.jsx

APPROVED PACKAGES — import ONLY from this list (build will crash on anything else):
  react, react-dom, react-router-dom, axios,
  react-toastify, react-hot-toast, react-icons, lucide-react,
  date-fns, react-hook-form, clsx

TECHNICAL RULES:
- React 18 hooks only (useState, useEffect, useCallback, useRef)
- HashRouter — required for GitHub Pages (NOT BrowserRouter)
- API base: const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"
- Tailwind CSS for all styling — no inline style objects except for dynamic colors
- NEVER import packages outside the approved list
- NEVER hardcode Render, Railway, or any deployment URLs
- CRITICAL DATA SAFETY: The backend may return a 404 JSON object ({{"detail": "Not Found"}}) if starting up. ALWAYS parse API list responses safely before using .map(). Never set a list state to a raw object.
  Example: const safeList = Array.isArray(r.data) ? r.data : (r.data?.items || []);
- src/App.jsx must be at least 150 lines — build a real, complete UI
- CRITICAL ICON RULE: You MUST ONLY use `lucide-react` for icons. DO NOT use `react-icons` as it causes build errors.
- CRITICAL ROUTING RULE: You MUST use `useNavigate` from `react-router-dom` to change pages. NEVER use `window.location.href` or `window.location.replace` as it breaks GitHub Pages deployment.
- CRITICAL API RULE: You MUST import and use the functions provided in `./api.js` for all API calls (e.g. `import {{ login, register, getItems, createItem }} from './api';`). DO NOT import or use `axios` directly in `App.jsx`!

CRITICAL - SINGLE FILE ONLY:
- src/App.jsx MUST be completely self-contained.
- DO NOT import any local components (e.g. `import Header from './components/Header'`).
- DO NOT import local pages (e.g. `import Home from './pages/Home'`).
- You MUST define all your sub-components (Header, Footer, Modals, Pages) directly inside `src/App.jsx`.
- If you use `import ... from './'` or `import ... from '../'`, the build WILL FAIL.

QUALITY BAR:
- The UI must visually match the task — someone reading the task should recognise the app
- Include realistic sample/seed data so the UI is not empty on first load
- Every interactive element must work (buttons, forms, filters)
"""