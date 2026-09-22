import os
import glob
import subprocess

scripts = glob.glob("C:/Financehub/*.py")
js_scripts = []
for script in scripts:
    with open(script, "r", encoding="utf-8") as f:
        try:
            content = f.read()
            if "sahabat_etf.js" in content and ("re.sub" in content or ".replace" in content):
                mtime = os.path.getmtime(script)
                js_scripts.append((mtime, script))
        except Exception:
            pass

js_scripts.sort(key=lambda x: x[0])

# We want to run scripts up to fix_pohon_pta.py
to_run = []
for t, s in js_scripts:
    to_run.append(s)
    if s.endswith("fix_pohon_pta.py"):
        break

print(f"Found {len(to_run)} scripts to execute to restore state.")
