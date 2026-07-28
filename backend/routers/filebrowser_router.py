# backend/routers/filebrowser_router.py — VIA Phase 3: Project File Browser

import os
import json
import zipfile
import io
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, JSONResponse
from backend.auth.auth import get_current_active_user

router = APIRouter(prefix="/files", tags=["File Browser"])

# Projects are saved here by agents
PROJECTS_BASE = Path("projects")

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json",
    ".md", ".txt", ".yaml", ".yml", ".toml", ".env", ".sh", ".sql",
    ".Dockerfile", ".gitignore", ".env.example", ""
}

SYNTAX_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sh": "bash",
    ".sql": "sql",
    ".toml": "toml",
}


def _is_safe_path(base: Path, target: Path) -> bool:
    """Prevent path traversal attacks."""
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _build_tree(path: Path, base: Path) -> dict:
    """Recursively build a file tree dict."""
    if not path.exists():
        return {}

    node = {
        "name": path.name,
        "path": str(path.relative_to(base)),
        "type": "directory" if path.is_dir() else "file",
    }

    if path.is_dir():
        children = []
        try:
            for child in sorted(path.iterdir()):
                if child.name.startswith(".") and child.name not in (".env.example", ".gitignore"):
                    continue
                if child.name in ("__pycache__", "node_modules", ".git", ".venv", "venv"):
                    continue
                children.append(_build_tree(child, base))
        except PermissionError:
            pass
        node["children"] = children
        node["child_count"] = len(children)
    else:
        node["size_bytes"] = path.stat().st_size
        node["extension"] = path.suffix.lower()
        node["language"] = SYNTAX_MAP.get(path.suffix.lower(), "text")

    return node


@router.get("/projects/")
async def list_projects(current_user: dict = Depends(get_current_active_user)):
    """List all generated projects."""
    if not PROJECTS_BASE.exists():
        return {"projects": [], "total": 0}

    projects = []
    for d in sorted(PROJECTS_BASE.iterdir(), reverse=True):
        if d.is_dir():
            # Count files recursively
            file_count = sum(1 for _ in d.rglob("*") if _.is_file())
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            projects.append({
                "name": d.name,
                "path": str(d.relative_to(PROJECTS_BASE)),
                "file_count": file_count,
                "size_bytes": size,
                "modified": d.stat().st_mtime,
            })

    return {"projects": projects, "total": len(projects)}


@router.get("/projects/{project_name}/tree/")
async def get_project_tree(
    project_name: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get file tree for a project."""
    project_path = PROJECTS_BASE / project_name
    if not project_path.exists():
        raise HTTPException(404, f"Project '{project_name}' not found")
    if not _is_safe_path(PROJECTS_BASE, project_path):
        raise HTTPException(403, "Access denied")

    tree = _build_tree(project_path, PROJECTS_BASE)
    return {"project": project_name, "tree": tree}


@router.get("/projects/{project_name}/read/")
async def read_file(
    project_name: str,
    file_path: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Read a specific file from a project."""
    project_base = PROJECTS_BASE / project_name
    full_path = (project_base / file_path).resolve()

    if not _is_safe_path(PROJECTS_BASE, full_path):
        raise HTTPException(403, "Access denied")

    if not full_path.exists():
        raise HTTPException(404, "File not found")

    if full_path.suffix.lower() not in ALLOWED_EXTENSIONS and full_path.suffix != "":
        raise HTTPException(400, "File type not viewable")

    try:
        size = full_path.stat().st_size
        if size > 500_000:  # 500KB max
            raise HTTPException(413, "File too large to display")

        content = full_path.read_text(encoding="utf-8", errors="replace")
        return {
            "file": file_path,
            "content": content,
            "language": SYNTAX_MAP.get(full_path.suffix.lower(), "text"),
            "size_bytes": size,
            "lines": content.count("\n") + 1,
        }
    except UnicodeDecodeError:
        raise HTTPException(400, "Binary file cannot be displayed")


@router.get("/projects/{project_name}/download/")
async def download_project(
    project_name: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Download an entire project as a ZIP file."""
    project_path = PROJECTS_BASE / project_name
    if not project_path.exists():
        raise HTTPException(404, "Project not found")
    if not _is_safe_path(PROJECTS_BASE, project_path):
        raise HTTPException(403, "Access denied")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in project_path.rglob("*"):
            if file.is_file():
                if any(p in file.parts for p in ("__pycache__", "node_modules", ".git")):
                    continue
                arcname = file.relative_to(project_path)
                zf.write(file, arcname)

    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={project_name}.zip"}
    )


@router.delete("/projects/{project_name}/")
async def delete_project(
    project_name: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a generated project."""
    import shutil
    project_path = PROJECTS_BASE / project_name
    if not project_path.exists():
        raise HTTPException(404, "Project not found")
    if not _is_safe_path(PROJECTS_BASE, project_path):
        raise HTTPException(403, "Access denied")

    shutil.rmtree(project_path)
    return {"deleted": True, "project": project_name}
