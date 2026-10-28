with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
m = re.search(r'function lprSelectSiswa.*?lpr-bgt-tbody.*?<\/tr>`', text, re.DOTALL)
if m: print(m.group(0))
