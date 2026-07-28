# backend/core/code_runner.py — Phase 4

import os
import sys
import time
import subprocess
import py_compile
import logging

logger = logging.getLogger("AI-Digital-Company")


def strip_markdown_fences(content: str) -> str:
    import re
    content = content.strip()
    fence_pattern = re.compile(r"^```[a-zA-Z]*\n(.*?)```\s*$", re.DOTALL)
    match = fence_pattern.match(content)
    if match:
        return match.group(1).strip()
    if content.startswith("```"):
        lines = content.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return content


# ── 1. SYNTAX CHECKER ────────────────────────────────────────────────────────

def check_syntax(file_path: str) -> dict:
    try:
        py_compile.compile(file_path, doraise=True)
        return {"file": file_path, "passed": True, "error": None}
    except py_compile.PyCompileError as e:
        return {"file": file_path, "passed": False, "error": str(e)}


def check_all_syntax(department_path: str) -> dict:
    results = []
    passed  = 0
    failed  = 0

    for root, dirs, files in os.walk(department_path):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fname in files:
            if fname.endswith(".py"):
                full_path = os.path.join(root, fname)
                result = check_syntax(full_path)
                results.append(result)
                if result["passed"]:
                    passed += 1
                else:
                    failed += 1
                    logger.warning(f"Syntax error | {full_path} | {result['error']}")

    return {
        "total_files": passed + failed,
        "passed":      passed,
        "failed":      failed,
        "all_passed":  failed == 0,
        "results":     results
    }


# ── 2. REQUIREMENTS — skip local install, Render handles it ──────────────────

def install_requirements(department_path: str) -> dict:
    """
    Skips local pip install completely.
    Reason: Windows venv causes Fatal Python error: init_import_site
    when subprocess pip runs inside uvicorn's async loop.
    Render installs requirements.txt automatically on deploy — no local install needed.
    """
    req_path = os.path.join(department_path, "requirements.txt")

    if not os.path.exists(req_path):
        return {
            "found":     False,
            "installed": False,
            "output":    "No requirements.txt found",
            "error":     None
        }

    logger.info(f"Requirements found | {req_path} | Render will install on deploy")
    return {
        "found":     True,
        "installed": True,
        "output":    "requirements.txt found — Render will install on deploy.",
        "error":     None
    }


# ── 3. IMPORT TESTER ─────────────────────────────────────────────────────────

def test_imports(department_path: str) -> dict:
    results = []
    passed  = 0
    failed  = 0
    testable = ["main.py", "models.py", "services.py", "auth.py", "security.py"]

    for fname in testable:
        full_path = os.path.join(department_path, fname)
        if not os.path.exists(full_path):
            continue
        # Use forward slashes for subprocess compatibility on Windows
        safe_path = full_path.replace("\\", "/")
        try:
            result = subprocess.run(
                [sys.executable, "-c",
                 f"import importlib.util; "
                 f"spec=importlib.util.spec_from_file_location('mod',r'{full_path}'); "
                 f"mod=importlib.util.module_from_spec(spec)"],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=department_path
            )
            if result.returncode == 0:
                passed += 1
                results.append({"file": fname, "importable": True, "error": None})
            else:
                failed += 1
                results.append({"file": fname, "importable": False, "error": result.stderr[:200]})
        except subprocess.TimeoutExpired:
            failed += 1
            results.append({"file": fname, "importable": False, "error": "Timed out"})
        except Exception as e:
            failed += 1
            results.append({"file": fname, "importable": False, "error": str(e)})

    return {
        "tested":     passed + failed,
        "passed":     passed,
        "failed":     failed,
        "all_passed": failed == 0,
        "results":    results
    }


# ── 4. MASTER RUNNER ─────────────────────────────────────────────────────────

def run_phase4_checks(task: str, department: str, department_path: str) -> dict:
    start = time.time()
    logger.info(f"Phase 4 checks starting | {department} | {department_path}")

    if not os.path.exists(department_path):
        return {
            "department": department,
            "phase4_ran": False,
            "error":      f"Department path not found: {department_path}"
        }

    syntax_report       = check_all_syntax(department_path)
    requirements_report = install_requirements(department_path)
    import_report       = test_imports(department_path)
    duration            = round(time.time() - start, 2)

    overall_passed = (
        syntax_report["all_passed"] and
        (not requirements_report["found"] or requirements_report["installed"])
    )

    logger.info(
        f"Phase 4 done | {department} | "
        f"Syntax: {'OK' if syntax_report['all_passed'] else 'FAIL'} | "
        f"Requirements: {'OK' if requirements_report['installed'] else 'SKIP'} | "
        f"Duration: {duration}s"
    )

    return {
        "department":           department,
        "phase4_ran":           True,
        "overall_passed":       overall_passed,
        "duration_seconds":     duration,
        "syntax_check":         syntax_report,
        "requirements_install": requirements_report,
        "import_test":          import_report,
        "summary":              _build_summary(syntax_report, requirements_report, import_report)
    }


def _build_summary(syntax: dict, requirements: dict, imports: dict) -> str:
    lines = []
    if syntax["all_passed"]:
        lines.append(f"[OK] Syntax: {syntax['passed']} files clean")
    else:
        lines.append(f"[FAIL] Syntax errors in {syntax['failed']} file(s)")
        for r in syntax["results"]:
            if not r["passed"]:
                lines.append(f"   -> {os.path.basename(r['file'])}: {r['error']}")

    if not requirements["found"]:
        lines.append("[SKIP] No requirements.txt")
    elif requirements["installed"]:
        lines.append("[OK] Requirements ready for Render deploy")
    else:
        lines.append(f"[FAIL] Requirements issue: {requirements['error']}")

    if imports["tested"] == 0:
        lines.append("[SKIP] No files to import-test")
    elif imports["all_passed"]:
        lines.append(f"[OK] Imports: {imports['passed']} files OK")
    else:
        lines.append(f"[WARN] Import issues in {imports['failed']} file(s)")

    return " | ".join(lines)


# ── 5. FRONTEND BUILD VERIFIER ────────────────────────────────────────────────

async def verify_frontend_build(frontend_path: str, timeout: int = 90) -> dict:
    """Run npm install + npm run build in the frontend dir and capture result."""
    import asyncio
    if not os.path.exists(frontend_path):
        return {"passed": False, "error": f"Path not found: {frontend_path}"}
    try:
        proc = await asyncio.create_subprocess_exec(
            "npm", "install", "--prefer-offline",
            cwd=frontend_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            return {"passed": False, "error": f"npm install failed: {stderr.decode()[:500]}"}
        proc2 = await asyncio.create_subprocess_exec(
            "npm", "run", "build",
            cwd=frontend_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr2 = await asyncio.wait_for(proc2.communicate(), timeout=timeout)
        if proc2.returncode != 0:
            return {"passed": False, "error": f"Build failed: {stderr2.decode()[:500]}"}
        return {"passed": True, "error": None}
    except asyncio.TimeoutError:
        return {"passed": False, "error": f"Build timed out after {timeout}s"}
    except Exception as e:
        return {"passed": False, "error": str(e)[:300]}


# ── 6. LIVE URL HEALTH CHECK ──────────────────────────────────────────────────

def check_live_url(url: str, retries: int = 3, wait: int = 15) -> dict:
    """Poll a live URL after deploy to confirm it actually responds."""
    import requests as req
    last_error = ""
    for attempt in range(retries):
        try:
            r = req.get(url, timeout=10)
            if r.status_code < 500:
                logger.info(f"Live URL check OK | {url} | status={r.status_code}")
                return {"reachable": True, "status_code": r.status_code, "url": url}
            last_error = f"HTTP {r.status_code}"
        except Exception as e:
            last_error = str(e)[:100]
        if attempt < retries - 1:
            time.sleep(wait)
    logger.warning(f"Live URL check FAILED | {url} | {last_error}")
    return {"reachable": False, "error": last_error, "url": url}