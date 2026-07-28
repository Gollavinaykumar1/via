# backend/core/code_writer.py — Phase 3
# Handles LLM code block extraction and project file saving

import os
import re
import logging
from datetime import datetime

logger = logging.getLogger("AI-Digital-Company")

# Base directory where all generated projects are saved
PROJECTS_BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "projects")


def _strip_fences(content: str) -> str:
    """
    Strip markdown code fences from content before saving to disk.
    Fixes SyntaxError on line 1 when LLM wraps output in ```python ... ```
    """
    content = content.strip()
    # Full fence block: ```python\n...\n```
    match = re.match(r"^```[a-zA-Z]*\n(.*?)```\s*$", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Partial — starts with ``` but no closing fence
    if content.startswith("```"):
        lines = content.splitlines()
        lines = lines[1:]  # remove opening ```python line
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # remove closing ``` line
        return "\n".join(lines).strip()
    return content


def extract_code_blocks(llm_output: str) -> dict:
    """
    Parse LLM output that follows this format:

        === FILE: main.py ===
        # code here
        === END ===

    Returns a dict of { "filename": "file content" }
    Falls back to markdown ``` blocks if === format not found.
    """
    files = {}

    # ── Primary parser: === FILE: name === ... === END === ───────────────────
    pattern = r"=== FILE:\s*(.+?)\s*===\s*\n(.*?)=== END ==="
    matches = re.findall(pattern, llm_output, re.DOTALL)

    if matches:
        for filename, content in matches:
            filename = filename.strip()
            content  = content.strip()
            if filename and content:
                # Strip fences in case LLM nested them inside === FILE === blocks
                if filename.endswith(".py"):
                    content = _strip_fences(content)
                files[filename] = content
                logger.info(f"Extracted file | {filename} | {len(content)} chars")
        return files

    # ── Fallback parser: ```python / ```bash / ``` blocks ───────────────────
    fallback_pattern = r"```(?:python|bash|sql|yaml|json|txt|md|)?\n(.*?)```"
    fallback_matches = re.findall(fallback_pattern, llm_output, re.DOTALL)

    if fallback_matches:
        logger.warning("Primary file format not found — using markdown code block fallback")
        for i, content in enumerate(fallback_matches):
            content = content.strip()
            if content:
                # Try to detect filename from first line comment
                first_line = content.split("\n")[0]
                if first_line.startswith("#") and "." in first_line:
                    detected = first_line.lstrip("# ").split("—")[0].strip()
                    if detected.endswith(".py") or detected.endswith(".txt") or detected.endswith(".md"):
                        files[detected] = content
                        continue
                files[f"file_{i+1}.py"] = content

    return files


def save_project_files(task: str, department: str, files: dict) -> dict:
    """
    Save all generated files to:
        projects/<task_slug>/<department>/

    Strips markdown fences from .py files before writing to disk.
    """
    task_slug      = _slugify(task)
    timestamp      = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_folder = f"{task_slug}_{timestamp}"

    project_path    = os.path.abspath(os.path.join(PROJECTS_BASE_DIR, project_folder))
    department_path = os.path.join(project_path, department)

    os.makedirs(department_path, exist_ok=True)
    logger.info(f"Saving files | {department_path}")

    files_written = []
    errors        = []

    for filename, content in files.items():
        try:
            # Strip fences from Python files before saving
            if filename.endswith(".py"):
                content = _strip_fences(content)

            file_path = os.path.join(department_path, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            files_written.append(filename)
            logger.info(f"Saved | {filename}")

        except Exception as e:
            logger.error(f"Failed to save {filename} | {str(e)}")
            errors.append({"file": filename, "error": str(e)})

    logger.info(
        f"Save complete | {department} | "
        f"{len(files_written)} saved | {len(errors)} errors"
    )

    return {
        "project_path":    project_path,
        "department_path": department_path,
        "files_written":   files_written,
        "file_count":      len(files_written),
        "errors":          errors,
    }


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    text = re.sub(r"^[-_]+|[-_]+$", "", text)
    return text[:60]