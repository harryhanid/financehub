import subprocess
try:
    pristine = subprocess.check_output(["git", "show", "HEAD:app/static/js/sahabat_etf.js"], cwd="C:/Financehub").decode("utf-8")
    with open("C:/Financehub/pristine_temp.js", "w", encoding="utf-8") as f:
        f.write(pristine)
    print("Saved pristine_temp.js")
except Exception as e:
    print(e)
