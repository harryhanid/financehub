import os, glob, re, sys, subprocess, builtins

scripts = glob.glob("C:/Financehub/*.py")
js_scripts = []
for script in scripts:
    with open(script, "r", encoding="utf-8") as f:
        content = f.read()
        if "sahabat_etf.js" in content and ("re.sub" in content or "replace" in content):
            js_scripts.append((os.path.getmtime(script), script, content))

js_scripts.sort(key=lambda x: x[0])

pristine = subprocess.check_output(["git", "show", "HEAD:app/static/js/sahabat_etf.js"], cwd="C:/Financehub").decode("utf-8")
current_content = pristine.replace("\r\n", "\n")

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

for t, s, code in js_scripts:
    if s.endswith("fix_dual_axis.py"): break
    try:
        exec(code, {'__builtins__': builtins, '__name__': '__main__'})
    except: pass
    if "setfRenderDrilldownChip" not in current_content:
        print("DELETED BY:", s)
        break

builtins.open = original_open
