import re
with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

for m in re.finditer(r'on[a-z]+="([^"]+)"', text):
    content = m.group(1)
    if re.search(r'/[^/]+/[^gimsuy\'"\s]+', content):
        print(f"Suspect in inline handler: {content}")
