f = '/app/backend/agents/frontend_agent.py'
c = open(f).read()

# Remove the project_block code that got injected into _features() by mistake
bad_code = '''def _features(task: str) -> dict:
    brief = project_brief or {}
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

good_code = '''def _features(task: str) -> dict:
    t = task.lower()'''

c = c.replace(bad_code, good_code)

# Now also remove {project_block} from the prompt f-string since it's not defined there
c = c.replace('TASK: {task}\n{project_block}\n════', 'TASK: {task}\n════')
c = c.replace('\n{project_block}\n', '\n')

open(f, 'w').write(c)
print('STEP 1 DONE - removed bad injection')

# Verify _features is clean now
c2 = open(f).read()
if 'project_block' in c2:
    print('WARNING: project_block still exists somewhere')
    idx = c2.find('project_block')
    print(c2[idx-100:idx+200])
else:
    print('CLEAN - project_block fully removed')