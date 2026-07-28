f = '/app/backend/core/fullstack_builder.py'
c = open(f).read()

old = '    files["main.py"]          = _generate_main_py(task, title, app_type, table_prefix, resources, project_brief)'

new = '''    _raw_main = _generate_main_py(task, title, app_type, table_prefix, resources, project_brief)
    if _validate_python(_raw_main):
        files["main.py"] = _raw_main
        logger.info("main.py syntax OK")
    else:
        files["main.py"] = _safe_main(title)
        logger.warning("main.py had syntax errors — using safe fallback")'''

if old in c:
    c = c.replace(old, new)
    open(f, 'w').write(c)
    print('FIXED - validator now called for every app')
else:
    print('Line not found - printing current line:')
    idx = c.find('files["main.py"]')
    print(c[idx-50:idx+200])