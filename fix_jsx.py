f = '/app/backend/agents/frontend_agent.py'
c = open(f).read()

# Find the _is_valid_jsx function and replace it entirely
import re

new_func = '''def _is_valid_jsx(code: str) -> bool:
    """Always use LLM output — no template fallback."""
    if not code or len(code.strip()) < 100:
        return False
    crash_imports = [
        "from './components/", "from './views/",
        "from './screens/", "from './pages/", "from '../components/",
    ]
    if any(b in code for b in crash_imports):
        return False
    return True'''

# Replace the entire _is_valid_jsx function
c = re.sub(
    r'def _is_valid_jsx\(code: str\) -> bool:.*?return "return" in code and "useState" in code',
    new_func,
    c,
    flags=re.DOTALL
)

open(f, 'w').write(c)
print('DONE')