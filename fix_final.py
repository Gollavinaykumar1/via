import re

f = '/app/backend/agents/frontend_agent.py'
c = open(f).read()

# Find the return statement in _build_prompt and fix the project_block reference
# The issue is {project_block} is in the f-string but not always defined
# Simple fix: replace the problematic f-string with a safe version

# Fix the return f-string to not use {project_block} directly
# Instead build the full string before returning

old_return = '''    return f"""You are a senior React engineer. Build a COMPLETE, PRODUCTION-READY React frontend.

════════════════════════════════════════════════════════
TASK: {task}
{project_block}
════════════════════════════════════════════════════════'''

new_return = '''    project_section = project_block if project_block else ""
    return f"""You are a senior React engineer. Build a COMPLETE, PRODUCTION-READY React frontend.

════════════════════════════════════════════════════════
TASK: {task}
{project_section}
════════════════════════════════════════════════════════'''

c = c.replace(old_return, new_return)

# If that didn't work, try the version without project_block in TASK line
if 'project_section' not in c:
    print('First replacement failed, trying alternative...')
    # Just remove {project_block} from the f-string entirely
    # and add project context to strategy_block instead
    old2 = 'TASK: {task}\n{project_block}\n════'
    new2 = 'TASK: {task}\n════'
    c = c.replace(old2, new2)
    
    old3 = 'TASK: {task}\n════'
    new3 = 'TASK: {task}\n{strategy_block}\n════'
    
    # Make project_block part of strategy_block
    old4 = '    strategy_block = f"\\nCEO Strategic Direction: {ceo_strategy}\\n" if ceo_strategy else ""'
    new4 = '''    strategy_block = f"\\nCEO Strategic Direction: {ceo_strategy}\\n" if ceo_strategy else ""
    if project_block:
        strategy_block = project_block + strategy_block'''
    c = c.replace(old4, new4)

open(f, 'w').write(c)
print('DONE')