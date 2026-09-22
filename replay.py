import os
import glob

scripts = glob.glob("C:/Financehub/*.py")
js_scripts = []
for script in scripts:
    with open(script, "r", encoding="utf-8") as f:
        try:
            content = f.read()
            if "sahabat_etf.js" in content and ("re.sub" in content or ".replace" in content):
                mtime = os.path.getmtime(script)
                js_scripts.append((mtime, script, content))
        except Exception:
            pass

js_scripts.sort(key=lambda x: x[0])

# Start with the pristine git version
os.system("git checkout C:/Financehub/app/static/js/sahabat_etf.js")

for t, s, code in js_scripts:
    if s.endswith("fix_dual_axis.py"):
        break # Stop right before the syntax error script!
        
    print(f"Running {os.path.basename(s)}")
    
    # We will execute the code, but we need to patch `open` so it only writes to sahabat_etf.js
    # We can just extract the re.sub parts!
    # But it's easier to just run the code with a mocked open.
    
    mock_code = f"""
import builtins
import os

original_open = builtins.open

def mocked_open(file, mode='r', *args, **kwargs):
    if 'w' in mode:
        if 'sahabat_etf.js' not in str(file):
            # Return a dummy file object that does nothing
            class DummyFile:
                def write(self, *a, **k): pass
                def __enter__(self): return self
                def __exit__(self, *a, **k): pass
            return DummyFile()
    return original_open(file, mode, *args, **kwargs)

builtins.open = mocked_open

try:
{chr(10).join('    ' + line for line in code.split(chr(10)))}
except Exception as e:
    print("Error:", e)
"""
    with open("runner.py", "w", encoding="utf-8") as out:
        out.write(mock_code)
    
    os.system("python runner.py")

print("Done replaying history.")
