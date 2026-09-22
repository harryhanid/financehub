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
            js_scripts.append((mtime, script))

js_scripts.sort(key=lambda x: x[0])
for t, s in js_scripts:
    print(os.path.basename(s))
