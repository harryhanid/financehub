for filename in ["data.html", "outstanding.html", "report.html"]:
    path = rf"C:\Financehub\app\templates\sponsorship\{filename}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()
    
    # We just insert {% set full_bleed = true %} after the extends line
    c = c.replace('{% extends "base.html" %}\n', '{% extends "base.html" %}\n{% set full_bleed = true %}\n')
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)

print("task 5 done")
