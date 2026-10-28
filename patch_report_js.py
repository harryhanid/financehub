import os

js_path = r'C:\Financehub\app\static\js\sponsorship.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

search1 = '''    html += '<thead><tr><th>NO</th><th>LEMBAGA / PERORANGAN</th><th>PERIHAL</th>' +'''
replace1 = '''    html += '<thead><tr><th>NO</th><th>TANGGAL PAYMENT</th><th>REFF</th><th>LEMBAGA / PERORANGAN</th><th>PERIHAL</th>' +'''

search2 = '''    html += '<tr class="sp-report-section-band"><td colspan="' + (4 + _SP_REPORT_PILLAR_LABELS.length) + '">' +'''
replace2 = '''    html += '<tr class="sp-report-section-band"><td colspan="' + (6 + _SP_REPORT_PILLAR_LABELS.length) + '">' +'''

search3 = '''      html += '<tr><td>' + row.no + '</td><td>' + _sponsorshipEsc(row.lembaga_perorangan) +
        '</td><td>' + _sponsorshipEsc(row.perihal || "") + '</td>' +'''
replace3 = '''      html += '<tr><td>' + row.no + '</td><td>' + _sponsorshipEsc(row.tanggal_payment || "") + '</td><td>' + _sponsorshipEsc(row.reff || "") + '</td><td>' + _sponsorshipEsc(row.lembaga_perorangan) +
        '</td><td>' + _sponsorshipEsc(row.perihal || "") + '</td>' +'''

search4 = '''  html += '<tr class="sp-report-subtotal-row"><td colspan="3">Grand Total Sponsorship</td>' +'''
replace4 = '''  html += '<tr class="sp-report-subtotal-row"><td colspan="5">Grand Total Sponsorship</td>' +'''

search5 = '''  html += '<tr class="sp-report-pct-row"><td colspan="3">% Allocation</td>' +'''
replace5 = '''  html += '<tr class="sp-report-pct-row"><td colspan="5">% Allocation</td>' +'''

search6 = '''      html += '<tr class="sp-report-subtotal-row"><td colspan="3">Sub Total ' + _sponsorshipEsc(section.description.toUpperCase()) + '</td>' +'''
replace6 = '''      html += '<tr class="sp-report-subtotal-row"><td colspan="5">Sub Total ' + _sponsorshipEsc(section.description.toUpperCase()) + '</td>' +'''

js_content = js_content.replace(search1, replace1)
js_content = js_content.replace(search2, replace2)
js_content = js_content.replace(search3, replace3)
js_content = js_content.replace(search4, replace4)
js_content = js_content.replace(search5, replace5)
js_content = js_content.replace(search6, replace6)

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)
print("sponsorship.js patched")
