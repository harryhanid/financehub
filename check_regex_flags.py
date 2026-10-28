import re
with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

matches = re.finditer(r'/(.*?)/([a-zA-Z]*)', text)
for match in matches:
    flags = match.group(2)
    # Check if flags contain any invalid characters (valid flags: g, i, m, s, u, y, d)
    if flags and not re.match(r'^[gimsuy]+$', flags):
        print(f"Suspicious regex: {match.group(0)}")
