path = r"C:\Financehub\app\templates\users\index.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace('{% extends "base.html" %}\n', '{% extends "base.html" %}\n{% set full_bleed = true %}\n')

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("task 8 done")
