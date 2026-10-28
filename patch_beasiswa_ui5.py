with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re

# Add expired to lpr-bgt-tbody header
text = text.replace(
    '<thead><tr><th>Kategori 1</th><th>Kategori 2</th><th>Tanggal</th><th>Pillar</th><th class="num-right">Amount</th></tr></thead>',
    '<thead><tr><th>Kategori 1</th><th>Kategori 2</th><th>Tanggal</th><th>Pillar</th><th>Expired</th><th class="num-right">Amount</th></tr></thead>'
)
text = text.replace(
    '<th colspan="4" style="text-align:right">Subtotal</th>',
    '<th colspan="5" style="text-align:right">Subtotal</th>'
)

# Add expired to lpr-bgt-tbody map
text = text.replace(
    '<td>${r.pillar || ""}</td>\n    <td class="num-right">${fmtRupiah(r.amount || 0)}</td>\n  </tr>`',
    '<td>${r.pillar || ""}</td>\n    <td style="white-space:nowrap">${r.tgl_expired || "-"}</td>\n    <td class="num-right">${fmtRupiah(r.amount || 0)}</td>\n  </tr>`'
)

with open("app/templates/beasiswa/index.html", "w", encoding="utf-8") as f:
    f.write(text)
