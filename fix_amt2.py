with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("const firstAmt = parseFloat(siswaRow._amt?.value) || 0;", "const firstAmt = parseFloat(siswaRow._amt?.value.replace(/,/g,'')) || 0;")

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed firstAmt parsing again")
