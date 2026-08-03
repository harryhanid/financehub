path = r"C:\Financehub\app\templates\etf_payment_application\index.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

import re

# Find setupCreateSiswaSearch()
pattern = re.compile(r"function setupCreateSiswaSearch\(\) \{[\s\S]*?sugg\.addEventListener\('mouseleave', \(\) => \{ sugg\.style\.display = 'none'; \}\);\n\}")

match = pattern.search(c)
if not match:
    # try another ending if mouseleave is not there
    pattern = re.compile(r"function setupCreateSiswaSearch\(\) \{[\s\S]*?\}\);\n  \}\);\n\}")
    match = pattern.search(c)
    
if not match:
    # simpler pattern
    pattern = re.compile(r"function setupCreateSiswaSearch\(\) \{.*?(?=\n\nfunction)", re.DOTALL)
    match = pattern.search(c)

print("Match found:", match is not None)
