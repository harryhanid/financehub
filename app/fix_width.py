file_path = r"C:\Financehub\app\templates\etf_payment_application\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace(
    '<th data-sort="13">Tgl PA</th>',
    '<th data-sort="13" style="white-space: nowrap; min-width: 110px;">Tgl PA</th>'
)

html = html.replace(
    '<th>Tgl Surat</th>',
    '<th style="white-space: nowrap; min-width: 110px;">Tgl Surat</th>'
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(html)
print("Updated successfully")
