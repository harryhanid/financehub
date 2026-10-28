with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re

# 1. Add column to loadInputBudget map
text = text.replace(
    '<td>${r.pillar||""}</td>\n      <td class="num-right">${fmtRupiah(a)}</td>\n      <td style="white-space:nowrap">\n        <button',
    '<td>${r.pillar||""}</td>\n      <td style="white-space:nowrap">${r.tgl_expired||"-"}</td>\n      <td class="num-right">${fmtRupiah(a)}</td>\n      <td style="white-space:nowrap">\n        <button'
)

# 2. Fix emptyHtml 6 -> 7
text = text.replace("_emptyHtml(6, 'Belum ada data budget'", "_emptyHtml(7, 'Belum ada data budget'")

with open("app/templates/beasiswa/index.html", "w", encoding="utf-8") as f:
    f.write(text)
