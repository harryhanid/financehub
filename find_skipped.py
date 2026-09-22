import glob

scripts = glob.glob("C:/Financehub/*.py")
for script in scripts:
    with open(script, "r", encoding="utf-8") as f:
        content = f.read()
        if "sahabat_etf.js" in content and "re.sub" not in content and "replace" not in content:
            print(script)
