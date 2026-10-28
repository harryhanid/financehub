with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
m = re.search(r'function loadBudgetList.*?tbody\.innerHTML = d\.rows\.map\(.*?<\/tr>`', text, re.DOTALL)
if m: print(m.group(0))
