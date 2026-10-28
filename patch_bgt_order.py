with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re

# 1. bgt-list header
text = text.replace(
    '<th>Tanggal</th><th>Pillar</th><th>Expired</th><th class="num-right">Amount</th>',
    '<th>Tanggal</th><th>Expired</th><th>Pillar</th><th class="num-right">Amount</th>'
)

# 2. bgt-list map
text = text.replace(
    '<td>${row.pillar||""}</td>\n        <td style="white-space:nowrap">${row.tgl_expired||"-"}</td>\n        <td class="num-right">${fmtRupiah(a)}</td>',
    '<td style="white-space:nowrap">${row.tgl_expired||"-"}</td>\n        <td>${row.pillar||""}</td>\n        <td class="num-right">${fmtRupiah(a)}</td>'
)

# 3. ibgt-tbody header (modal)
text = text.replace(
    '<th>Tanggal</th><th>Pillar</th><th>Expired</th><th class="num-right">Amount</th>',
    '<th>Tanggal</th><th>Expired</th><th>Pillar</th><th class="num-right">Amount</th>'
)

# 4. _bgtAfterSave map (ibgt-tbody)
text = text.replace(
    '<td>${r.pillar||""}</td>\n        <td style="white-space:nowrap">${r.tgl_expired||"-"}</td>\n        <td class="num-right">${fmtRupiah(a)}</td>',
    '<td style="white-space:nowrap">${r.tgl_expired||"-"}</td>\n        <td>${r.pillar||""}</td>\n        <td class="num-right">${fmtRupiah(a)}</td>'
)

# 5. lpr-bgt-tbody header (laporan)
text = text.replace(
    '<th>Tanggal</th><th>Pillar</th><th>Expired</th><th class="num-right">Amount</th>',
    '<th>Tanggal</th><th>Expired</th><th>Pillar</th><th class="num-right">Amount</th>'
)

# 6. lpr-bgt-tbody map (laporan)
text = text.replace(
    '<td>${r.pillar || ""}</td>\n    <td style="white-space:nowrap">${r.tgl_expired || "-"}</td>\n    <td class="num-right">${fmtRupiah(r.amount || 0)}</td>',
    '<td style="white-space:nowrap">${r.tgl_expired || "-"}</td>\n    <td>${r.pillar || ""}</td>\n    <td class="num-right">${fmtRupiah(r.amount || 0)}</td>'
)

# 7. loadInputBudget map (modal map fallback?)
# I patched loadInputBudget earlier with this exact string:
text = text.replace(
    '<td>${r.pillar||""}</td>\n      <td style="white-space:nowrap">${r.tgl_expired||"-"}</td>\n      <td class="num-right">${fmtRupiah(a)}</td>',
    '<td style="white-space:nowrap">${r.tgl_expired||"-"}</td>\n      <td>${r.pillar||""}</td>\n      <td class="num-right">${fmtRupiah(a)}</td>'
)


with open("app/templates/beasiswa/index.html", "w", encoding="utf-8") as f:
    f.write(text)
