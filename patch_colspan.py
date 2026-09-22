with open('app/static/js/sahabat_etf.js', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('<td colspan="2" style="text-align:center;color:var(--text-muted)">Belum ada data.</td>', '<td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data.</td>')

with open('app/static/js/sahabat_etf.js', 'w', encoding='utf-8') as f:
    f.write(c)

print("Colspan patched")
