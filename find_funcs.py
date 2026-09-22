file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = list(re.finditer(r'function setfRender', content))
for m in matches:
    print(content[m.start():m.end()+30])
