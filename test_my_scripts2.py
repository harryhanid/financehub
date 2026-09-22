import os, subprocess, builtins

subprocess.call(["python", "recover_js_clean.py"], cwd="C:/Financehub")
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()
if "function setfRenderDrilldownChip" not in content: print("Missing after recover")

scripts = ["fix_clean_functions2.py", "fix_hanging.py", "fix_kat_hanging.py", "fix_sg_hanging.py", "fix_tahunan_hanging.py", "fix_quotes.py", "fix_pohon.py", "fix_pohon_js.py"]
for s in scripts:
    subprocess.call(["python", s], cwd="C:/Financehub")
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
        c = f.read()
    if "function setfRenderDrilldownChip" not in c:
        print("DELETED BY:", s)
        break
