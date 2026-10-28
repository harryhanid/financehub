import re
with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()
matches = re.findall(r'\bhidEtfLineId\b', text)
print("Matches for exact word 'hidEtfLineId':", len(matches))
