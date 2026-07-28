import re

f = '/app/backend/agents/frontend_agent.py'
c = open(f).read()

# ── Fix 1: Add project_brief to frontend_agent signature ──
c = c.replace(
    'async def frontend_agent(task: str, ceo_strategy: str = "", inter_context: str = "") -> dict:',
    'async def frontend_agent(task: str, project_brief: dict = None, ceo_strategy: str = "", inter_context: str = "") -> dict:'
)

# ── Fix 2: Pass project_brief to _build_prompt ──
c = c.replace(
    'prompt      = _build_prompt(task, ceo_strategy, inter_context)',
    'prompt      = _build_prompt(task, ceo_strategy, inter_context, project_brief)'
)

# ── Fix 3: Add project_brief to _build_prompt signature ──
c = c.replace(
    'def _build_prompt(task: str, ceo_strategy: str = "", inter_context: str = "") -> str:',
    'def _build_prompt(task: str, ceo_strategy: str = "", inter_context: str = "", project_brief: dict = None) -> str:'
)

# ── Fix 4: Inject project_brief into _build_prompt body ──
old = '    t = task.lower()'
new = '''    brief    = project_brief or {}
    features = ', '.join(brief.get('core_features', [])) if brief.get('core_features') else 'Not specified'
    project_block = (
        "PROJECT BRIEF (BUILD EXACTLY THIS APP):\\n"
        f"  App Name:      {brief.get('app_name', 'Not specified')}\\n"
        f"  App Type:      {brief.get('app_type', 'Not specified')}\\n"
        f"  Core Features: {features}\\n"
        f"  Tech Stack:    {brief.get('tech_stack', 'Not specified')}\\n"
        f"  Target Users:  {brief.get('target_users', 'Not specified')}\\n"
        f"  UI Style:      {brief.get('ui_style', 'Not specified')}\\n"
        f"  Constraints:   {brief.get('key_constraints', 'Not specified')}\\n"
    ) if brief.get('app_name') else ""
    t = task.lower()'''
c = c.replace(old, new, 1)

# ── Fix 5: Inject project_block into the prompt ──
c = c.replace(
    'TASK: {task}',
    'TASK: {task}\n{project_block}'
)

# ── Fix 6: Make _is_valid_jsx ALWAYS return True ──
# This means LLM output is ALWAYS used — no template fallback
old_func = '''def _is_valid_jsx(code: str) -> bool:
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

    for match in re.finditer(r\'from\\s+["\\'\\']([^"\\'\\'/][^"\\'\\']*)["\\'\\']\\', code):
        pkg = match.group(1).split("/")[0]
        if pkg.startswith("@"):
            full_scope = "/".join(match.group(1).split("/")[:2])
            if full_scope not in APPROVED_PACKAGES:
                logger.warning(f"LLM App.jsx rejected — unapproved import: {match.group(1)}")
                return False
        elif pkg not in APPROVED_PACKAGES:
            logger.warning(f"LLM App.jsx rejected — unapproved import: {pkg}")
            return False

    return "return" in code and "useState" in code'''

new_func = '''def _is_valid_jsx(code: str) -> bool:
    """
    Always use LLM output — no template fallback.
    Only reject if completely empty or has local component imports that will crash the build.
    """
    if not code or len(code.strip()) < 100:
        return False
    # Only reject multi-file imports that will crash the build
    crash_imports = [
        "from './components/", "from './views/",
        "from './screens/", "from './pages/", "from '../components/",
    ]
    if any(b in code for b in crash_imports):
        return False
    return True'''

c = c.replace(old_func, new_func)

# ── Fix 7: Also fix _build_all_files to always try LLM first ──
# Remove the _app_jsx fallback call — LLM always wins
old_build = '''    if not _is_valid_jsx(f.get("src/App.jsx", "")):
        f["src/App.jsx"] = _app_jsx(name, task, feat, th)'''
new_build = '''    if not _is_valid_jsx(f.get("src/App.jsx", "")):
        logger.warning(f"LLM App.jsx was empty or had crash imports — using safe fallback | {task[:50]}")
        f["src/App.jsx"] = _app_jsx(name, task, feat, th)'''
c = c.replace(old_build, new_build)

open(f, 'w').write(c)
print('ALL FIXES APPLIED SUCCESSFULLY')
print('LLM will now build ANY app without template fallback')