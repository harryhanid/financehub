with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    '<th style="padding:8px 10px;text-align:left;">Status</th>',
    '<th style="padding:8px 10px;text-align:left;">Klasifikasi</th>\n            <th style="padding:8px 10px;text-align:left;">Status</th>'
)

text = text.replace(
    '<th style="padding:7px 8px;">Status</th>',
    '<th style="padding:7px 8px;">Klasifikasi</th>\n            <th style="padding:7px 8px;">Status</th>'
)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
