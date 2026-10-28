with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re

# 1. bgt-list header
text = text.replace(
    '<th>Tanggal</th><th>Pillar</th><th class="num-right">Amount</th><th>Aksi</th>',
    '<th>Tanggal</th><th>Pillar</th><th>Expired</th><th class="num-right">Amount</th><th>Aksi</th>'
)
text = text.replace('id="bgt-list-tbody">\n          <tr><td colspan="9"', 'id="bgt-list-tbody">\n          <tr><td colspan="10"')
text = text.replace("tbody.innerHTML = `<tr><td colspan=\"9\"", "tbody.innerHTML = `<tr><td colspan=\"10\"")
text = text.replace("_emptyHtml(9, 'Tidak ada data')", "_emptyHtml(10, 'Tidak ada data')")

# 2. bgt-list JS map
text = text.replace(
    '<td>${row.pillar||""}</td>\n        <td class="num-right">${fmtRupiah(a)}</td>',
    '<td>${row.pillar||""}</td>\n        <td style="white-space:nowrap">${row.tgl_expired||"-"}</td>\n        <td class="num-right">${fmtRupiah(a)}</td>'
)
text = text.replace(
    'onclick="bgtEditRow(${row.id},\'${(row.cat1||"").replace(/\'/g,"\\\\\'")}\',\'${(row.cat2||"").replace(/\'/g,"\\\\\'")}\',\'${row.tanggal||""}\',\'${row.pillar||""}\',${a})"',
    'onclick="bgtEditRow(${row.id},\'${(row.cat1||"").replace(/\'/g,"\\\\\'")}\',\'${(row.cat2||"").replace(/\'/g,"\\\\\'")}\',\'${row.tanggal||""}\',\'${row.pillar||""}\',${a},\'${row.tgl_expired||""}\')"'
)

# 3. ibgt-tbody header (modal)
text = text.replace(
    '<tr><th>Kategori 1</th><th>Kategori 2</th><th>Tanggal</th><th>Pillar</th><th class="num-right">Amount</th><th>Aksi</th></tr>',
    '<tr><th>Kategori 1</th><th>Kategori 2</th><th>Tanggal</th><th>Pillar</th><th>Expired</th><th class="num-right">Amount</th><th>Aksi</th></tr>'
)
text = text.replace('colspan="6"', 'colspan="7"')
text = text.replace('id="ibgt-total">—</th><th></th></tr>', 'id="ibgt-total">—</th><th></th></tr>')
text = text.replace('<th colspan="4">Total</th><th class="num-right" id="ibgt-total">', '<th colspan="5">Total</th><th class="num-right" id="ibgt-total">')

# 4. _bgtAfterSave JS map (which renders ibgt-tbody)
text = text.replace(
    '<td>${r.pillar||""}</td>\n        <td class="num-right">${fmtRupiah(a)}</td>\n        <td>',
    '<td>${r.pillar||""}</td>\n        <td style="white-space:nowrap">${r.tgl_expired||"-"}</td>\n        <td class="num-right">${fmtRupiah(a)}</td>\n        <td>'
)
text = text.replace(
    'onclick="ibgtEditRow(${r.id},\'${(r.cat1||"").replace(/\'/g,"\\\\\'")}\',\'${(r.cat2||"").replace(/\'/g,"\\\\\'")}\',\'${r.tanggal||""}\',\'${r.pillar||""}\',${a})"',
    'onclick="ibgtEditRow(${r.id},\'${(r.cat1||"").replace(/\'/g,"\\\\\'")}\',\'${(r.cat2||"").replace(/\'/g,"\\\\\'")}\',\'${r.tanggal||""}\',\'${r.pillar||""}\',${a},\'${r.tgl_expired||""}\')"'
)

with open("app/templates/beasiswa/index.html", "w", encoding="utf-8") as f:
    f.write(text)
