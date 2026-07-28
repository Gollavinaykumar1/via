import re

f = '/app/backend/core/fullstack_builder.py'
c = open(f).read()

# Find and replace the broken _safe_main function entirely
old = re.search(r'def _safe_main\(title: str\) -> str:.*?(?=\ndef |\nclass |\n# )', c, re.DOTALL)

if old:
    print(f"Found _safe_main at position {old.start()}")
    print("Current broken version:")
    print(old.group()[:200])
else:
    print("_safe_main not found by regex, searching manually...")
    idx = c.find('def _safe_main')
    if idx >= 0:
        print(c[idx:idx+300])
    else:
        print("_safe_main NOT FOUND in file")