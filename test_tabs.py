import re
with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

for m in re.finditer(r'<button[^>]*class="[^"]*tab-btn[^"]*"[^>]*data-tab="([^"]+)"[^>]*>(.*?)</button>', text):
    print(f"{m.group(1)}: {m.group(2)}")
