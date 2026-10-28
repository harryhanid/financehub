with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
m = re.search(f'<table id="smt-table".*?<thead.*?</thead>', text, re.DOTALL)
if m:
    lines = m.group(0).split('\n')
    for i, l in enumerate(lines):
        if '>Status</th>' in l:
            print(f"smt-table: {lines[i-1].strip()} -> {l.strip()}")
