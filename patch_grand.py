import os

js_path = r'C:\Financehub\app\static\js\sponsorship.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

search = '''  html += '<tr class="sp-report-grandtotal-row"><td colspan="3">TOTAL SPONSORSHIP (ACTUAL)</td>' +'''
replace = '''  html += '<tr class="sp-report-grandtotal-row"><td colspan="5">TOTAL SPONSORSHIP (ACTUAL)</td>' +'''

if search in js_content:
    js_content = js_content.replace(search, replace)
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)
    print("Patched grandtotal in sponsorship.js")
else:
    print("String not found in js")

