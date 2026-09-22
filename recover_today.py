import os
import glob
import re
import builtins
import sys

# Get all scripts from today
scripts = glob.glob("C:/Financehub/*.py")
js_scripts = []
for script in scripts:
    with open(script, "r", encoding="utf-8") as f:
        content = f.read()
        if "sahabat_etf.js" in content and ("re.sub" in content or "replace" in content):
            mtime = os.path.getmtime(script)
            # Only scripts after pristine_sahabat.js
            if mtime > os.path.getmtime("C:/Financehub/pristine_sahabat.js"):
                js_scripts.append((mtime, script, content))

js_scripts.sort(key=lambda x: x[0])

# Start with pristine
with open("C:/Financehub/pristine_sahabat.js", "r", encoding="utf-8") as f:
    current_content = f.read()

class MockFile:
    def __init__(self, content): self.content = content.replace("\r\n", "\n")
    def read(self): return self.content
    def write(self, s):
        global current_content
        current_content = s.replace("\r\n", "\n")
    def __enter__(self): return self
    def __exit__(self, *a): pass

original_open = builtins.open

def mocked_open(file, mode='r', *args, **kwargs):
    if 'sahabat_etf.js' in str(file): return MockFile(current_content)
    if 'w' in mode:
        class DummyFile:
            def write(self, *a, **k): pass
            def __enter__(self): return self
            def __exit__(self, *a, **k): pass
        return DummyFile()
    return original_open(file, mode, *args, **kwargs)

builtins.open = mocked_open

# Filter out the destructive ones
skip_scripts = [
    "fix_family_table_single.py",
    "fix_syntax.py",
    "rewrite_func.py",
    "fix_pdf_scaling.py",
    "check_scripts.py"
]

for t, s, code in js_scripts:
    name = os.path.basename(s)
    if name in skip_scripts:
        print(f"Skipping {name}")
        continue
    
    # We also skip replace_file_content calls because they are not scripts.
    # Wait, my table fix was a replace_file_content! I'll have to re-apply it manually!
    
    print(f"Running {name}")
    try:
        exec(code, globals())
    except Exception as e:
        print(f"Error in {name}: {e}")

builtins.open = original_open

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(current_content)

print("Recovered file to C:/Financehub/app/static/js/sahabat_etf.js")
