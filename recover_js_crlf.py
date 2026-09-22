import os
import glob
import re

scripts = glob.glob("C:/Financehub/*.py")
js_scripts = []
for script in scripts:
    with open(script, "r", encoding="utf-8") as f:
        content = f.read()
        if "sahabat_etf.js" in content and ("re.sub" in content or "replace" in content):
            mtime = os.path.getmtime(script)
            js_scripts.append((mtime, script, content))

js_scripts.sort(key=lambda x: x[0])

import subprocess
pristine = subprocess.check_output(["git", "show", "HEAD:app/static/js/sahabat_etf.js"], cwd="C:/Financehub").decode("utf-8")

# NORMALIZE NEWLINES
current_content = pristine.replace("\r\n", "\n")

class MockFile:
    def __init__(self, content):
        self.content = content.replace("\r\n", "\n")
    def read(self): return self.content
    def write(self, s):
        global current_content
        current_content = s.replace("\r\n", "\n")
    def __enter__(self): return self
    def __exit__(self, *a): pass

import builtins
original_open = builtins.open

def mocked_open(file, mode='r', *args, **kwargs):
    if 'sahabat_etf.js' in str(file):
        return MockFile(current_content)
    if 'w' in mode:
        class DummyFile:
            def write(self, *a, **k): pass
            def __enter__(self): return self
            def __exit__(self, *a, **k): pass
        return DummyFile()
    return original_open(file, mode, *args, **kwargs)

builtins.open = mocked_open

for t, s, code in js_scripts:
    if s.endswith("fix_dual_axis.py"):
        break
    
    # NORMALIZE script code too just in case!
    code = code.replace("\r\n", "\n")
    
    namespace = {'__builtins__': builtins}
    try:
        exec(code, namespace)
    except Exception as e:
        pass

builtins.open = original_open

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(current_content)

print("Recovered with newline normalization!")
