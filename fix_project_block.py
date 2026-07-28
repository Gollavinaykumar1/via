import re

f = '/app/backend/agents/frontend_agent.py'
c = open(f).read()

# The problem: project_block is defined inside _build_prompt
# but the f-string in the return uses {project_block}
# which fails when _build_prompt is called without project_brief
# Fix: make project_block default to empty string at the top of _build_prompt

old = '''    brief    = project_brief or {}
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

new = '''    brief    = project_brief or {}
    features = ', '.join(brief.get('core_features', [])) if brief.get('core_features') else 'Not specified'
    app_name  = brief.get('app_name', '')
    app_type  = brief.get('app_type', '')
    tech_stack = brief.get('tech_stack', 'Not specified')
    target_users = brief.get('target_users', 'Not specified')
    ui_style  = brief.get('ui_style', 'Not specified')
    constraints = brief.get('key_constraints', 'Not specified')
    if app_name:
        project_block = (
            f"PROJECT BRIEF (BUILD EXACTLY THIS APP):\\n"
            f"  App Name:      {app_name}\\n"
            f"  App Type:      {app_type}\\n"
            f"  Core Features: {features}\\n"
            f"  Tech Stack:    {tech_stack}\\n"
            f"  Target Users:  {target_users}\\n"
            f"  UI Style:      {ui_style}\\n"
            f"  Constraints:   {constraints}\\n"
        )
    else:
        project_block = ""
    t = task.lower()'''

c = c.replace(old, new)

# Also fix the TASK line to use project_block safely
c = c.replace(
    'TASK: {task}\n{project_block}',
    'TASK: {task}'
)

# Find the return f-string and inject project_block after the task line
c = c.replace(
    'TASK: {task}\n════',
    'TASK: {task}\n{project_block}\n════'
)

open(f, 'w').write(c)
print('DONE - project_block fix applied')