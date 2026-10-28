with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
for tbl in ['pam-table', 'fiori-table', 'sml-table', 'energy-table', 'setf-table']:
    m = re.search(f'<table id="{tbl}".*?<thead.*?</thead>', text, re.DOTALL)
    if m:
        lines = m.group(0).split('\n')
        for i, l in enumerate(lines):
            if '>Status</th>' in l:
                print(f"{tbl}: {lines[i-1].strip()} -> {l.strip()}")
