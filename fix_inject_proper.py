import re

f = '/app/backend/agents/frontend_agent.py'
c = open(f).read()

# Fix _build_prompt to accept and use project_brief properly
# Find the exact function signature
c = c.replace(
    'def _build_prompt(task: str, ceo_strategy: str = "", inter_context: str = "", project_brief: dict = None) -> str:',
    'def _build_prompt(task: str, ceo_strategy: str = "", inter_context: str = "", project_brief: dict = None) -> str:\n    _pb = project_brief or {}\n    _feat = ", ".join(_pb.get("core_features", [])) or "Not specified"\n    _proj = ("PROJECT BRIEF:\\n  App: " + _pb.get("app_name","") + "\\n  Type: " + _pb.get("app_type","") + "\\n  Features: " + _feat + "\\n  Stack: " + _pb.get("tech_stack","Not specified") + "\\n  Users: " + _pb.get("target_users","Not specified") + "\\n") if _pb.get("app_name") else ""'
)

# Inject _proj into the return f-string after TASK line
c = c.replace(
    'TASK: {task}\n════',
    'TASK: {task}\n{_proj}\n════'
)

open(f, 'w').write(c)

# Verify
c2 = open(f).read()
print('_proj injected:', '_proj' in c2)
print('project_brief param:', 'project_brief: dict = None) -> str:' in c2)