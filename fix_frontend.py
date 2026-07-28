c = open('/app/backend/agents/frontend_agent.py').read()

# Fix 1: lower threshold
c = c.replace(
    'if not code or len(code.strip()) < 800:',
    'if not code or len(code.strip()) < 200:'
)

# Fix 2: add project_brief to frontend_agent signature
c = c.replace(
    'async def frontend_agent(task: str, ceo_strategy: str = "", inter_context: str = "") -> dict:',
    'async def frontend_agent(task: str, project_brief: dict = None, ceo_strategy: str = "", inter_context: str = "") -> dict:'
)

# Fix 3: pass project_brief to _build_prompt
c = c.replace(
    'prompt      = _build_prompt(task, ceo_strategy, inter_context)',
    'prompt      = _build_prompt(task, ceo_strategy, inter_context, project_brief)'
)

# Fix 4: add project_brief param to _build_prompt
c = c.replace(
    'def _build_prompt(task: str, ceo_strategy: str = "", inter_context: str = "") -> str:',
    'def _build_prompt(task: str, ceo_strategy: str = "", inter_context: str = "", project_brief: dict = None) -> str:'
)

# Fix 5: inject project_brief context inside _build_prompt
old = '    t = task.lower()'
new = '''    brief = project_brief or {}
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

# Fix 6: inject project_block into prompt
c = c.replace(
    'TASK: {task}',
    'TASK: {task}\n{project_block}'
)

open('/app/backend/agents/frontend_agent.py', 'w').write(c)
print('ALL FIXES APPLIED SUCCESSFULLY')