with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('sugg.style.display = data.rows?.length ? "block" : "none";', 'sugg.style.display = data?.length ? "block" : "none";')

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed display logic")
