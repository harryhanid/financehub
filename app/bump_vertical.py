import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

# Increase base vertical distance from 320 to 450
content = re.sub(r"\(maxDepth \+ 1\) \* 320", "(maxDepth + 1) * 450", content)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Increased vertical scale factor!")
