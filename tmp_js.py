import re

with open(r'app\static\js\sahabat_etf.js', 'r', encoding='utf-8') as f:
    content = f.read()

# setfLaporanHeaderRow
content = re.sub(
    r'<th colspan="4">Tahun \' \+ reportYear \+ \'</th>\' \+\s*\'<th colspan="4">S/D Tahun \' \+ reportYear \+ \'</th></tr>\' \+\s*\'<tr class="setf-laporan-header">\' \+\s*\'<th>Plafon</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th>\' \+\s*\'<th>Plafon</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th></tr>\';',
    r'<th colspan="5">Tahun \' + reportYear + \'</th>\' +\n    \'<th colspan="5">S/D Tahun \' + reportYear + \'</th></tr>\' +\n    \'<tr class="setf-laporan-header">\' +\n    \'<th>Plafon</th><th>PTA</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th>\' +\n    \'<th>Plafon</th><th>PTA</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th></tr>\';',
    content
)

# setfLaporanMetricsCells
content = re.sub(
    r'return \'<td class="num-right">\' \+ setfFmtJutaan\(m\.cur\.plafon\) \+ \'</td>\' \+\s*\'<td class="num-right">\' \+ setfFmtJutaan\(m\.cur\.klaim\) \+ \'</td>\' \+\s*\'<td class="num-right">\' \+ setfFmtJutaan\(m\.cur\.dibayar\) \+ \'</td>\' \+\s*\'<td class="num-right">\' \+ setfFmtJutaan\(m\.cur\.saldo\) \+ \'</td>\' \+\s*\'<td class="num-right">\' \+ setfFmtJutaan\(m\.cum\.plafon\) \+ \'</td>\' \+\s*\'<td class="num-right">\' \+ setfFmtJutaan\(m\.cum\.klaim\) \+ \'</td>\' \+\s*\'<td class="num-right">\' \+ setfFmtJutaan\(m\.cum\.dibayar\) \+ \'</td>\' \+\s*\'<td class="num-right">\' \+ setfFmtJutaan\(m\.cum\.saldo\) \+ \'</td>\';',
    r'return \'<td class="num-right">\' + setfFmtJutaan(m.cur.plafon) + \'</td>\' +\n         \'<td class="num-right">\' + setfFmtJutaan(m.cur.pta) + \'</td>\' +\n         \'<td class="num-right">\' + setfFmtJutaan(m.cur.klaim) + \'</td>\' +\n         \'<td class="num-right">\' + setfFmtJutaan(m.cur.dibayar) + \'</td>\' +\n         \'<td class="num-right">\' + setfFmtJutaan(m.cur.saldo) + \'</td>\' +\n         \'<td class="num-right">\' + setfFmtJutaan(m.cum.plafon) + \'</td>\' +\n         \'<td class="num-right">\' + setfFmtJutaan(m.cum.pta) + \'</td>\' +\n         \'<td class="num-right">\' + setfFmtJutaan(m.cum.klaim) + \'</td>\' +\n         \'<td class="num-right">\' + setfFmtJutaan(m.cum.dibayar) + \'</td>\' +\n         \'<td class="num-right">\' + setfFmtJutaan(m.cum.saldo) + \'</td>\';',
    content
)

# setfRenderLaporanPillarBreakdown pct row
content = re.sub(
    r'\'<td class="num-right">\' \+ \(p\.pct_cur\.plafon \* 100\)\.toFixed\(1\) \+ \'%</td>\' \+\s*\'<td class="num-right">\' \+ \(p\.pct_cur\.klaim \* 100\)\.toFixed\(1\) \+ \'%</td>\' \+\s*\'<td class="num-right">\' \+ \(p\.pct_cur\.dibayar \* 100\)\.toFixed\(1\) \+ \'%</td>\' \+\s*\'<td class="num-right">\' \+ \(p\.pct_cur\.saldo \* 100\)\.toFixed\(1\) \+ \'%</td>\' \+\s*\'<td class="num-right">\' \+ \(p\.pct_cum\.plafon \* 100\)\.toFixed\(1\) \+ \'%</td>\' \+\s*\'<td class="num-right">\' \+ \(p\.pct_cum\.klaim \* 100\)\.toFixed\(1\) \+ \'%</td>\' \+\s*\'<td class="num-right">\' \+ \(p\.pct_cum\.dibayar \* 100\)\.toFixed\(1\) \+ \'%</td>\' \+\s*\'<td class="num-right">\' \+ \(p\.pct_cum\.saldo \* 100\)\.toFixed\(1\) \+ \'%</td></tr>\';',
    r'\'<td class="num-right">\' + (p.pct_cur.plafon * 100).toFixed(1) + \'%</td>\' +\n      \'<td class="num-right">\' + (p.pct_cur.pta * 100).toFixed(1) + \'%</td>\' +\n      \'<td class="num-right">\' + (p.pct_cur.klaim * 100).toFixed(1) + \'%</td>\' +\n      \'<td class="num-right">\' + (p.pct_cur.dibayar * 100).toFixed(1) + \'%</td>\' +\n      \'<td class="num-right">\' + (p.pct_cur.saldo * 100).toFixed(1) + \'%</td>\' +\n      \'<td class="num-right">\' + (p.pct_cum.plafon * 100).toFixed(1) + \'%</td>\' +\n      \'<td class="num-right">\' + (p.pct_cum.pta * 100).toFixed(1) + \'%</td>\' +\n      \'<td class="num-right">\' + (p.pct_cum.klaim * 100).toFixed(1) + \'%</td>\' +\n      \'<td class="num-right">\' + (p.pct_cum.dibayar * 100).toFixed(1) + \'%</td>\' +\n      \'<td class="num-right">\' + (p.pct_cum.saldo * 100).toFixed(1) + \'%</td></tr>\';',
    content
)


with open(r'app\static\js\sahabat_etf.js', 'w', encoding='utf-8') as f:
    f.write(content)
