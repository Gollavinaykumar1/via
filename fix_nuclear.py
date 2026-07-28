import re

f = '/app/backend/agents/frontend_agent.py'
c = open(f).read()

# Remove ALL project_block injections using regex
# This removes any block that starts with project_block assignment
c = re.sub(
    r"\n    brief\s*=\s*project_brief or \{\}.*?t = task\.lower\(\)",
    "\n    t = task.lower()",
    c,
    flags=re.DOTALL
)

# Remove any remaining {project_block} references in f-strings
c = c.replace('\n{project_block}\n', '\n')
c = c.replace('{project_block}', '')
c = c.replace('\n{project_section}\n', '\n')
c = c.replace('{project_section}', '')

# Remove project_block standalone assignments if any remain
c = re.sub(
    r'\n\s+project_block\s*=.*?(?=\n\s+[a-zA-Z])',
    '\n',
    c,
    flags=re.DOTALL
)

open(f, 'w').write(c)

# Verify
c2 = open(f).read()
count = c2.count('project_block')
print(f'project_block occurrences remaining: {count}')
if count == 0:
    print('CLEAN - all removed')
else:
    idx = c2.find('project_block')
    print('Still found at:')
    print(c2[idx-50:idx+200])