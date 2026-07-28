import ast

f = '/app/backend/core/fullstack_builder.py'
c = open(f).read()

# Add ast import
if 'import ast' not in c:
    c = c.replace('import re\nimport logging', 'import re\nimport logging\nimport ast')

# Add validator function after logger
old_logger = 'logger = logging.getLogger("AI-Digital-Company")'
new_logger = '''logger = logging.getLogger("AI-Digital-Company")

def _validate_python(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError as e:
        logger.warning(f"Syntax error in generated code: {e}")
        return False

def _safe_main(title: str) -> str:
    return """# main.py — VIA Safe Fallback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title=\"""" + title + """\", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

db = []

@app.get("/")
def root():
    return {"app": \"""" + title + """\", "status": "running", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/v1/items")
def get_items():
    return {"items": db, "total": len(db)}

@app.post("/api/v1/items")
def create_item(item: dict):
    item["id"] = len(db) + 1
    db.append(item)
    return item

@app.get("/api/v1/items/{item_id}")
def get_item(item_id: int):
    item = next((i for i in db if i.get("id") == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item

@app.put("/api/v1/items/{item_id}")
def update_item(item_id: int, data: dict):
    for i, item in enumerate(db):
        if item.get("id") == item_id:
            db[i].update(data)
            return db[i]
    raise HTTPException(status_code=404, detail="Not found")

@app.delete("/api/v1/items/{item_id}")
def delete_item(item_id: int):
    global db
    db = [i for i in db if i.get("id") != item_id]
    return {"deleted": item_id}

@app.get("/api/v1/stats")
def get_stats():
    return {"total": len(db), "active": len(db)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
"""'''

if old_logger in c and '_validate_python' not in c:
    c = c.replace(old_logger, new_logger)
    print('Added validator functions')
else:
    print('Validator already exists or logger not found')

# Fix generate_backend_files to use validator
old_line = '    files["main.py"]          = _generate_main_py(task, title, app_type, table_prefix, resource)'
new_line = '''    _raw_main = _generate_main_py(task, title, app_type, table_prefix, resource)
    if _validate_python(_raw_main):
        files["main.py"] = _raw_main
        logger.info("main.py syntax OK")
    else:
        files["main.py"] = _safe_main(title)
        logger.warning("main.py had syntax errors — using safe fallback")'''

if old_line in c:
    c = c.replace(old_line, new_line)
    print('Fixed generate_backend_files')
else:
    print('generate_backend_files line not found — may already be fixed')

open(f, 'w').write(c)
print('DONE')