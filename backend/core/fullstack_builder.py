# backend/core/fullstack_builder.py — VIA Phase 3
# Generates a complete deployable FastAPI backend based on task complexity
#
# FIXES:
#   1. render.yaml fromDatabase.name matches what render_deployer.py creates
#   2. requirements.txt includes aiosqlite for SQLite fallback
#   3. database.py handles both postgresql:// and sqlite:// correctly
#   4. models.py amount/category fields for expense apps
#   5. Root / endpoint always present in generated main.py
#   6. Base.metadata.create_all() inside startup event — never crashes at import
#   7. No duplicate 'from fastapi import' statements
#   8. TABLE PREFIX per app — each app gets unique table names derived from its slug
#      e.g. expense tracker → expense_tracker_items (not "items")
#      This allows ALL apps to safely share ONE PostgreSQL database with zero conflicts.
#   9. RESOURCE NAME detection — routes use domain name (books, expenses, etc.)
#      so backend always matches what the LLM generates in api.js
#  10. ALIAS ROUTES — both /resource and /api/v1/resource always work

import re
import logging

logger = logging.getLogger("AI-Digital-Company")


# ── Complexity Detection ──────────────────────────────────────────────────────

def detect_app_type(task: str) -> str:
    t = task.lower()

    db_signals = [
        "database", "store", "save", "persist", "crud", "users", "login",
        "register", "auth", "profile", "history", "records", "data",
        "postgresql", "mysql", "sqlite", "mongodb", "supabase",
        "transaction", "transactions", "tracker", "tracking", "management",
        "system", "dashboard", "analytics", "portfolio",
    ]
    backend_signals = [
        "api", "backend", "server", "fastapi", "endpoint", "rest",
        "quiz", "score", "leaderboard", "submit", "fetch", "real-time",
        "test", "iq", "exam", "assessment", "game", "track"
    ]
    # Only pure static/brochure sites with NO interactivity should be frontend-only
    frontend_signals = [
        "landing page", "static page", "brochure", "one page website",
        "simple page", "showcase website"
    ]

    # DB signals always win — check these FIRST before frontend classification
    has_db = any(w in t for w in db_signals)
    if has_db:
        return "fullstack_db"

    # Then check if it's a pure static frontend
    if any(w in t for w in frontend_signals):
        return "frontend"

    has_backend = any(w in t for w in backend_signals)
    if has_backend:
        return "fullstack"
    return "frontend"


# ── Resource Name Detection ───────────────────────────────────────────────────

def _detect_resource_name(task: str) -> str:
    """
    Detects the domain resource name from the task description.
    Used as the API route path so the backend matches what the LLM generates in api.js.

    e.g. "library book management" → "books"
         "expense tracker"         → "expenses"
         "hospital appointment"    → "appointments"
    """
    t = task.lower()

    if any(w in t for w in ["book", "library", "isbn"]):
        return "books"
    if any(w in t for w in ["expense", "budget", "finance", "money", "transaction"]):
        return "expenses"
    if any(w in t for w in ["appointment", "doctor", "hospital", "patient"]):
        return "appointments"
    if any(w in t for w in ["donor", "blood", "donation"]):
        return "donors"
    if any(w in t for w in ["workout", "exercise", "fitness"]):
        return "workouts"
    if any(w in t for w in ["student", "course", "class", "school", "grade"]):
        return "students"
    if any(w in t for w in ["product", "inventory", "stock", "shop", "store"]):
        return "products"
    if any(w in t for w in ["employee", "staff", "hr", "payroll"]):
        return "employees"
    if any(w in t for w in ["task", "todo", "checklist"]):
        return "tasks"
    if any(w in t for w in ["player", "team", "cricket", "football", "sport", "tournament"]):
        return "players"
    if any(w in t for w in ["recipe", "food", "meal", "diet"]):
        return "recipes"
    if any(w in t for w in ["event", "ticket", "conference"]):
        return "events"
    if any(w in t for w in ["note", "journal", "diary"]):
        return "notes"
    if any(w in t for w in ["contact", "address", "phone"]):
        return "contacts"
    if any(w in t for w in ["order", "cart", "purchase", "checkout"]):
        return "orders"
    if any(w in t for w in ["user", "member", "profile"]):
        return "users"
    return "items"  # safe fallback


# ── Alias Route Generator ─────────────────────────────────────────────────────

def _alias_routes(resource: str, use_db: bool) -> str:
    """
    Generates alias routes so BOTH formats work regardless of what the LLM picks in api.js:
      /api/v1/{resource}   — most common LLM output
      /{resource}          — short form LLM sometimes generates

    If resource == "items", aliases are skipped (original routes already cover it).
    """
    if resource == "items":
        return ""

    if use_db:
        return f'''
# ── Route aliases: /api/v1/{resource} and /{resource} mirror /api/v1/items ────
@app.get("/api/v1/{resource}")
def alias_get_{resource}(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_items(skip=skip, limit=limit, db=db)

@app.post("/api/v1/{resource}")
def alias_create_{resource}(payload: dict, db: Session = Depends(get_db)):
    return create_item(payload=payload, db=db)

@app.get("/api/v1/{resource}/{{item_id}}")
def alias_get_{resource}_one(item_id: int, db: Session = Depends(get_db)):
    return get_item(item_id=item_id, db=db)

@app.put("/api/v1/{resource}/{{item_id}}")
def alias_update_{resource}(item_id: int, payload: dict, db: Session = Depends(get_db)):
    return update_item(item_id=item_id, payload=payload, db=db)

@app.delete("/api/v1/{resource}/{{item_id}}")
def alias_delete_{resource}(item_id: int, db: Session = Depends(get_db)):
    return delete_item(item_id=item_id, db=db)

@app.get("/{resource}")
def alias_get_{resource}_short(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_items(skip=skip, limit=limit, db=db)

@app.post("/{resource}")
def alias_create_{resource}_short(payload: dict, db: Session = Depends(get_db)):
    return create_item(payload=payload, db=db)

@app.get("/{resource}/{{item_id}}")
def alias_get_{resource}_short_one(item_id: int, db: Session = Depends(get_db)):
    return get_item(item_id=item_id, db=db)

@app.put("/{resource}/{{item_id}}")
def alias_update_{resource}_short(item_id: int, payload: dict, db: Session = Depends(get_db)):
    return update_item(item_id=item_id, payload=payload, db=db)

@app.delete("/{resource}/{{item_id}}")
def alias_delete_{resource}_short(item_id: int, db: Session = Depends(get_db)):
    return delete_item(item_id=item_id, db=db)
'''
    else:
        return f'''
# ── Route aliases: /api/v1/{resource} and /{resource} mirror /api/v1/items ────
@app.get("/api/v1/{resource}")
def alias_get_{resource}():
    return get_items()

@app.post("/api/v1/{resource}")
def alias_create_{resource}(item: dict):
    return create_item(item=item)

@app.get("/api/v1/{resource}/{{item_id}}")
def alias_get_{resource}_one(item_id: int):
    return get_item(item_id=item_id)

@app.put("/api/v1/{resource}/{{item_id}}")
def alias_update_{resource}(item_id: int, update: dict):
    return update_item(item_id=item_id, update=update)

@app.delete("/api/v1/{resource}/{{item_id}}")
def alias_delete_{resource}(item_id: int):
    return delete_item(item_id=item_id)

@app.get("/{resource}")
def alias_get_{resource}_short():
    return get_items()

@app.post("/{resource}")
def alias_create_{resource}_short(item: dict):
    return create_item(item=item)

@app.get("/{resource}/{{item_id}}")
def alias_get_{resource}_short_one(item_id: int):
    return get_item(item_id=item_id)

@app.put("/{resource}/{{item_id}}")
def alias_update_{resource}_short(item_id: int, update: dict):
    return update_item(item_id=item_id, update=update)

@app.delete("/{resource}/{{item_id}}")
def alias_delete_{resource}_short(item_id: int):
    return delete_item(item_id=item_id)
'''


# ── FastAPI Backend Generator ─────────────────────────────────────────────────

from backend.core.llm_provider import llm
import json

async def _generate_schema_via_llm(task: str) -> list:
    prompt = (
        "You are a database architect. Based on this app idea: '" + task + "'\n"
        "Return ONLY a JSON array of database fields needed for the main item. "
        "Each field MUST be a dictionary with 'name' (snake_case) and "
        "'type' (one of String, Integer, Float, DateTime). "
        "DO NOT include 'id' or 'created_at' (they are automatically added).\n"
        "Keep it simple (maximum 4-6 fields). Return ONLY valid JSON, no markdown.\n"
        "Example output: [{\"name\": \"title\", \"type\": \"String\"}, {\"name\": \"status\", \"type\": \"String\"}]"
    )
    raw = await llm.agenerate(prompt)
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if m:
        try:
            schema = json.loads(m.group())
            if isinstance(schema, list) and all(isinstance(x, dict) for x in schema):
                return schema
        except: pass
    raise ValueError("LLM returned invalid schema format")

async def generate_backend_files(task: str, app_type: str) -> dict:
    if app_type == "frontend":
        return {}

    schema = []
    if app_type == "fullstack_db":
        schema = await _generate_schema_via_llm(task)

    files = {}
    slug         = _slugify(task)
    title        = _title(task)
    table_prefix = slug.replace("-", "_")[:40]
    resource     = _detect_resource_name(task)

    files["main.py"]          = _generate_main_py(task, title, app_type, table_prefix, resource, schema)
    files["requirements.txt"] = _generate_requirements(app_type)
    files["render.yaml"]      = _generate_render_yaml(slug, app_type)
    files[".gitignore"]       = _generate_gitignore()
    files[".python-version"]  = "3.11.0\n"

    if app_type == "fullstack_db":
        files["database.py"] = _generate_database_py()
        files["models.py"]   = _generate_models_py(task, table_prefix, schema)

    logger.info(
        f"Fullstack builder | app_type={app_type} | table_prefix={table_prefix} "
        f"| resource={resource} | {len(files)} backend files generated"
    )
    return files


# ── File Generators ───────────────────────────────────────────────────────────

def _generate_main_py(task: str, title: str, app_type: str, table_prefix: str, resource: str = "items", schema: list = None) -> str:
    use_db = app_type == "fullstack_db"

    if use_db:
        db_import = """from database import engine, get_db
from models import Base, Item
from sqlalchemy.orm import Session"""
        startup_event = """
@app.on_event("startup")
def on_startup():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        import logging as _log
        _log.getLogger("via").warning(f"DB init warning: {e}")
"""
        items_data_var = ""
        extra_endpoints = '''
def _item_to_dict(item):
    """Serialize any SQLAlchemy Item to a plain dict, preserving types."""
    result = {}
    for col in Item.__table__.columns:
        val = getattr(item, col.name)
        result[col.name] = str(val) if hasattr(val, "isoformat") else val
    return result

@app.get("/api/v1/items")
def get_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = db.query(Item).offset(skip).limit(limit).all()
    return {"items": [_item_to_dict(i) for i in items], "total": db.query(Item).count()}

@app.get("/api/v1/items/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return _item_to_dict(item)

@app.post("/api/v1/items")
def create_item(payload: dict, db: Session = Depends(get_db)):
    writable = {c.name for c in Item.__table__.columns if c.name not in ("id", "created_at")}
    item = Item()
    for key, val in payload.items():
        if key in writable:
            setattr(item, key, val)
    # Ensure title always has a value if it exists in writable
    if not getattr(item, "title", None) and "title" in writable:
        item.title = payload.get("title", "Untitled")
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_to_dict(item)

@app.put("/api/v1/items/{item_id}")
def update_item(item_id: int, payload: dict, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    writable = {c.name for c in Item.__table__.columns if c.name not in ("id", "created_at")}
    for key, val in payload.items():
        if key in writable:
            setattr(item, key, val)
    db.commit()
    db.refresh(item)
    return _item_to_dict(item)

@app.delete("/api/v1/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"deleted": item_id}

@app.get("/api/v1/stats")
def get_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func as sqlfunc
    total = db.query(sqlfunc.count(Item.id)).scalar()
    cols = [c.name for c in Item.__table__.columns]
    active = 0
    if "status" in cols:
        active = db.query(sqlfunc.count(Item.id)).filter(Item.status == "active").scalar()
    return {"total": total, "active": active}
'''
        extra_endpoints += _alias_routes(resource, use_db)
    else:
        db_import = ""
        startup_event = ""
        items_data_var = 'items_data = []'
        extra_endpoints = '''
@app.get("/api/v1/items")
def get_items():
    return {"items": items_data, "total": len(items_data)}

@app.post("/api/v1/items")
def create_item(item: dict):
    item["id"] = len(items_data) + 1
    items_data.append(item)
    return item

@app.get("/api/v1/items/{item_id}")
def get_item(item_id: int):
    item = next((i for i in items_data if i["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.put("/api/v1/items/{item_id}")
def update_item(item_id: int, update: dict):
    for i, item in enumerate(items_data):
        if item["id"] == item_id:
            items_data[i].update(update)
            return items_data[i]
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/api/v1/items/{item_id}")
def delete_item(item_id: int):
    global items_data
    items_data = [i for i in items_data if i["id"] != item_id]
    return {"deleted": item_id}

@app.get("/api/v1/stats")
def get_stats():
    return {"total": len(items_data), "active": sum(1 for i in items_data if i.get("status", "") == "active")}
'''
        extra_endpoints += _alias_routes(resource, use_db)

    fastapi_import = (
        "from fastapi import FastAPI, HTTPException, Depends"
        if use_db
        else "from fastapi import FastAPI, HTTPException"
    )

    return f'''# main.py — Generated by VIA for: {task}
{fastapi_import}
from fastapi.middleware.cors import CORSMiddleware
{db_import}
import os

app = FastAPI(
    title="{title}",
    description="Generated by VIA — Autonomous AI Digital Team",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
{startup_event}
{items_data_var}

@app.get("/")
def root():
    return {{"app": "{title}", "status": "running", "docs": "/docs", "api": "/api/v1/items"}}

@app.get("/health")
def health():
    return {{"status": "healthy"}}

{extra_endpoints}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
'''


def _generate_requirements(app_type: str) -> str:
    base = """fastapi==0.115.0
uvicorn[standard]==0.29.0
pydantic==2.10.6
email-validator==2.1.1
python-dotenv==1.0.1
httpx==0.27.0
requests==2.31.0
"""
    if app_type == "fullstack_db":
        base += """sqlalchemy==2.0.29
psycopg2-binary==2.9.9
alembic==1.13.1
aiosqlite==0.20.0
python-multipart==0.0.9
passlib[bcrypt]==1.7.4
PyJWT==2.8.0
python-jose[cryptography]==3.3.0
"""
    return base


def _generate_render_yaml(slug: str, app_type: str) -> str:
    db_env = """
      - key: DATABASE_URL
        sync: false""" if app_type == "fullstack_db" else ""

    return f"""services:
  - type: web
    name: {slug[:50]}
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: APP_ENV
        value: production{db_env}
"""


def _generate_gitignore() -> str:
    return '''
# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class
'''

_LLM_BACKEND_PROMPT = """You are a Principal Backend Engineer.
Task: {task}
App Type: {app_type}

Generate the full backend code for this app using FastAPI and SQLAlchemy (if app_type is fullstack_db).
Required files:
- main.py (FastAPI application with all necessary endpoints)

CRITICAL RULES:
- DO NOT generate `database.py`. Assume it already exists and provides `Base`, `engine`, and `get_db`. Import them like: `from database import Base, engine, get_db`.
- CRITICAL DATABASE URL RULE: NEVER hardcode any database URL in main.py. NEVER write lines like `DATABASE_URL = "postgresql://..."` or `SQLALCHEMY_DATABASE_URL = "postgresql://..."` in main.py. The database connection is handled entirely in database.py which reads DATABASE_URL from environment variables automatically.
- When defining SQLAlchemy models in Python, DO NOT use Pydantic types (like EmailStr) inside Column(). You MUST use SQLAlchemy types (like String, Integer). Example: `email = Column(String, unique=True)`.
- Use `from sqlalchemy import Column, String, Integer` etc.
- CRITICAL AUTH RULE: The frontend will send LOGIN and REGISTER requests as standard JSON (`application/json`) to `/api/v1/auth/login` and `/api/v1/auth/register`. DO NOT use `OAuth2PasswordRequestForm` (which requires form-data). Accept JSON via standard Pydantic models (e.g. `class LoginRequest(BaseModel): email: str, password: str`).
- CRITICAL ROOT ROUTE RULE: main.py MUST always include a root GET "/" route that returns JSON status. Example:
  @app.get("/")
  def root():
      return {{"status": "running", "docs": "/docs"}}
- CRITICAL HEALTH ROUTE RULE: main.py MUST always include a GET "/health" route:
  @app.get("/health")
  def health():
      return {{"status": "healthy"}}
- CRITICAL CORS RULE: Always add CORSMiddleware with allow_origins=["*"] so the React frontend can connect.

Use standard markdown code blocks, e.g.,
```python
# main.py
...
```
"""

def _extract_llm_files(raw: str) -> dict:
    import re
    files = {}
    # Find all code blocks
    pattern = re.compile(r'```[a-zA-Z]*\n(.*?)```', re.DOTALL)
    for i, match in enumerate(pattern.finditer(raw)):
        content = match.group(1).strip()
        # Try to find the filename in the first line
        first_line = content.split('\n')[0].strip()
        filename = None
        if first_line.startswith('#') and '.' in first_line:
            filename = first_line.strip('# ').split()[0]
        elif "FastAPI(" in content or "from fastapi" in content:
            filename = "main.py"
        elif "sqlalchemy" in content and "declarative_base" in content:
            filename = "database.py"
        elif "sqlalchemy" in content and "Column" in content:
            filename = "models.py"
        elif "uvicorn" in content and "fastapi" in content:
            filename = "requirements.txt"
        else:
            filename = f"file_{i}.txt"
            
        if filename:
            files[filename] = content
            
    # Also look outside codeblocks for explicit markers like "**main.py**"
    return files

def _validate_llm_backend(files: dict) -> bool:
    if "main.py" not in files:
        logger.warning("Validation failed: main.py not in files. Files found: " + str(list(files.keys())))
        return False
    if "FastAPI" not in files["main.py"]:
        logger.warning("Validation failed: FastAPI not in main.py")
        return False
    return True

async def generate_backend_files_llm(task: str, app_type: str) -> dict:
    from backend.core.llm_provider import llm
    
    if app_type == "frontend":
        return {}
        
    logger.info(f"LLM Backend Generator | task={task[:60]} | app_type={app_type}")
    
    prompt = _LLM_BACKEND_PROMPT.format(task=task, app_type=app_type)
    raw = await llm.agenerate(prompt)
    files = _extract_llm_files(raw)
    
    if not _validate_llm_backend(files):
        raise ValueError("LLM Backend Generator failed validation. Prompt should be updated to ensure valid FastAPI output.")
        
    if "main.py" in files:
        files["main.py"] = files["main.py"].replace("sqlite+aiosqlite:///", "sqlite:///")
        files["main.py"] = files["main.py"].replace("create_async_engine", "create_engine")
        files["main.py"] = files["main.py"].replace("from sqlalchemy.ext.asyncio import", "# from sqlalchemy.ext.asyncio import")
        files["main.py"] = files["main.py"].replace("@app.on_startup()", '@app.on_event("startup")')
        files["main.py"] = files["main.py"].replace("async def on_startup():", "def on_startup():")

        # CRITICAL FIX: Remove any hardcoded DATABASE_URL / SQLALCHEMY_DATABASE_URL lines
        # that the LLM may have generated (e.g. "postgresql://user:password@host:port/db")
        # These cause ValueError: invalid literal for int() with base 10: 'port'
        import re as _re
        # Remove lines that set DATABASE_URL or SQLALCHEMY_DATABASE_URL to a hardcoded value
        files["main.py"] = _re.sub(
            r'^\s*(SQLALCHEMY_DATABASE_URL|DATABASE_URL)\s*=\s*["\']postgresql://[^\'"]+["\'].*$',
            '# DATABASE_URL is set in database.py from environment variables',
            files["main.py"],
            flags=_re.MULTILINE
        )
        # Also remove any create_engine() calls in main.py that use hardcoded URLs
        files["main.py"] = _re.sub(
            r'^\s*engine\s*=\s*create_engine\(.*$',
            '# engine is created in database.py',
            files["main.py"],
            flags=_re.MULTILINE
        )
        # Remove any SessionLocal definitions in main.py
        files["main.py"] = _re.sub(
            r'^\s*SessionLocal\s*=\s*sessionmaker\(.*$',
            '# SessionLocal is defined in database.py',
            files["main.py"],
            flags=_re.MULTILINE
        )
        # Ensure CORS is present
        if "CORSMiddleware" not in files["main.py"]:
            cors_inject = (
                "\nfrom fastapi.middleware.cors import CORSMiddleware\n"
                "app.add_middleware(CORSMiddleware, allow_origins=['*'], "
                "allow_credentials=True, allow_methods=['*'], allow_headers=['*'])\n"
            )
            files["main.py"] = files["main.py"].replace(
                "app = FastAPI(", cors_inject + "\napp = FastAPI(", 1
            ) if "app = FastAPI(" in files["main.py"] else files["main.py"] + cors_inject
            logger.info("Auto-injected CORSMiddleware into generated main.py")

        # Inject root route if LLM forgot to include it
        if '@app.get("/")' not in files["main.py"] and "@app.get('/')" not in files["main.py"]:
            inject = (
                '\n\n@app.get("/")\n'
                'def root():\n'
                '    return {"status": "running", "docs": "/docs", "health": "/health"}\n'
                '\n@app.get("/health")\n'
                'def health():\n'
                '    return {"status": "healthy"}\n'
            )
            import_end = files["main.py"].find('\napp.add_middleware')
            if import_end == -1:
                import_end = files["main.py"].find('\n@app.')
            if import_end > 0:
                files["main.py"] = files["main.py"][:import_end] + inject + files["main.py"][import_end:]
            else:
                files["main.py"] = files["main.py"] + inject
            logger.info("Auto-injected root / and /health routes into generated main.py")
        
    slug = _slugify(task)
    files["requirements.txt"] = _generate_requirements(app_type)
    files.setdefault("render.yaml", _generate_render_yaml(slug, app_type))
    files.setdefault(".gitignore", _generate_gitignore())
    files.setdefault(".python-version", "3.11.0\n")
    
    if app_type == "fullstack_db":
        files["database.py"] = _generate_database_py()
        
    if "requirements.txt" in files and app_type == "fullstack_db":
        if "psycopg2" not in files["requirements.txt"]:
            files["requirements.txt"] += "\npsycopg2-binary\n"
        
    logger.info(f"LLM Backend Generator | SUCCESS | {len(files)} files generated")
    return files


def _generate_database_py() -> str:
    return '''# database.py — SQLAlchemy setup (auto-generated by VIA)
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Reads DATABASE_URL set by Render's PostgreSQL service
# Falls back to local SQLite for development
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("RENDER_DATABASE_URL")
    or "sqlite:///./app.db"
)

# Render injects postgres:// but SQLAlchemy 1.4+ requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Validate the URL has no placeholder values
if ":port" in DATABASE_URL or "@host:" in DATABASE_URL or "user:password" in DATABASE_URL:
    # Fallback to SQLite if URL looks like a template placeholder
    import logging as _dblog
    _dblog.getLogger("via").warning("DATABASE_URL appears to be a placeholder — falling back to SQLite")
    DATABASE_URL = "sqlite:///./app.db"

# SQLite needs check_same_thread=False; PostgreSQL does not
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''


def _generate_models_py(task: str, table_prefix: str, schema: list = None) -> str:
    if schema is None:
        schema = [{"name": "title", "type": "String"}, {"name": "description", "type": "String"}, {"name": "status", "type": "String"}]
        
    columns_code = ""
    for f in schema:
        name = f.get("name", "field").replace(" ", "_").lower()
        typ = f.get("type", "String")
        if typ not in ["String", "Integer", "Float", "DateTime"]:
            typ = "String"
        
        nullable = ", nullable=True" if typ in ["String", "DateTime"] else ", default=0.0" if typ == "Float" else ", default=0"
        if name in ["title", "status"]:
            nullable = ', index=True' if name == 'title' else ', default="active"'
            
        columns_code += f"    {name} = Column({typ}{nullable})\n"
        
    return f'''# models.py — table prefix: {table_prefix}
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from database import Base

class Item(Base):
    __tablename__ = "{table_prefix}_items"
    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String, index=True)
    description = Column(String, nullable=True)
    status      = Column(String, default="active")
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
'''


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:50].strip("-") or "via-app"


def _title(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(w.capitalize() for w in text.split()[:6])


# ── Self-Correction (Phase 2) ─────────────────────────────────────────────────

async def self_correct_backend(
    task: str,
    files: dict,
    error_summary: str,
    attempt: int = 1,
) -> dict:
    """
    Phase 2 self-correction: send the syntax/import error back to the LLM so
    it can fix the generated code. Returns a corrected files dict.
    Only patches main.py — the file most likely to have LLM-generated bugs.
    """
    from backend.core.llm_provider import llm
    logger.info(f"Self-correction attempt {attempt}/3 | error: {error_summary[:100]}")

    broken_code = files.get("main.py", "")
    prompt = (
        "You are Dev, Staff Backend Engineer at VIA fixing a bug in generated code.\n\n"
        f"Original task: {task}\n\n"
        "This Python file has a syntax/import error:\n"
        f"{broken_code[:3000]}\n\n"
        f"Error detected:\n{error_summary}\n\n"
        "Fix ONLY the specific error. Return the complete corrected main.py with no markdown "
        "fences, no explanations — just the raw Python code."
    )
    corrected = await llm.agenerate(prompt)
    if corrected:
        corrected = corrected.strip()
        if corrected.startswith("```"):
            lines = corrected.splitlines()
            corrected = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        files["main.py"] = corrected
        logger.info(f"Self-correction applied | attempt={attempt}")
    return files