with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
m = re.search(r'<tbody id="bgt-list-tbody".*?<thead>.*?</thead>', text, re.DOTALL)
if m: print(m.group(0))
else:
    m = re.search(r'<thead>.*?</thead>\s*<tbody id="bgt-list-tbody"', text, re.DOTALL)
    if m: print(m.group(0))
