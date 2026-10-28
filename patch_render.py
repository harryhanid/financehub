with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    '<td style="padding:6px 8px">${_statusBadge(r.status)}</td>',
    '<td style="padding:6px 8px">${esc(r.klasifikasi || \'Normal\')}</td>\n      <td style="padding:6px 8px">${_statusBadge(r.status)}</td>'
)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
