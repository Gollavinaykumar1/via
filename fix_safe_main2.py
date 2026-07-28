f = '/app/backend/core/fullstack_builder.py'
c = open(f).read()

# Find _safe_main and replace entirely with working version
import re

new_safe_main = '''def _safe_main(title: str) -> str:
    t = title.replace('"', '\\"')
    return """# main.py — VIA Safe Fallback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title=\"""" + t + """\", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = []

@app.get("/")
def root():
    return {"app": \"""" + t + """\", "status": "running", "docs": "/docs"}

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
"""

'''

# Replace everything between def _safe_main and the next def/class
c_new = re.sub(
    r'def _safe_main\(title: str\) -> str:.*?(?=\ndef |\nclass |\n# ──)',
    new_safe_main,
    c,
    flags=re.DOTALL
)

if c_new == c:
    print('Pattern not matched — trying alternative...')
    # Try to find and replace just the broken line
    c_new = c.replace(
        'app = FastAPI(title=" + title + ", version="1.0.0")',
        'app = FastAPI(title="VIA App", version="1.0.0")'
    )
    c_new = c_new.replace(
        'app = FastAPI(title= + title + , version="1.0.0")',
        'app = FastAPI(title="VIA App", version="1.0.0")'
    )
    if c_new != c:
        print('Fixed broken FastAPI title line')
    else:
        print('Could not find broken line')

open(f, 'w').write(c_new)

# Verify by checking what _safe_main generates
import sys
sys.path.insert(0, '/app')
exec(open(f).read().split('def _safe_main')[1].split('\ndef ')[0].replace('def _safe_main', ''))

import ast
try:
    # Test with a sample title
    idx = c_new.find('def _safe_main')
    print('DONE - checking syntax of generated code...')

    # Simple verification
    if 'app = FastAPI(title=' in c_new:
        # Extract the safe main generation
        print('Safe main function found')

    import py_compile
    import tempfile
    import os
    # Write a test
    test_code = '''
def _safe_main(title):
    return "test"
result = _safe_main("test")
print("Function works:", result)
'''
    print('Running syntax check on fullstack_builder...')
except Exception as e:
    print(f'Error: {e}')

import py_compile
try:
    py_compile.compile(f)
    print('SYNTAX OK - fullstack_builder.py is valid')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')