import re
with open('app/templates/payment_memo/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace <th style="...">Aksi</th> with <th style="...">Lampiran</th><th style="...">Aksi</th>
content = re.sub(
    r'(<th style="[^"]*">\s*Aksi\s*</th>)',
    r'<th style="padding:7px 8px;text-align:center">Lampiran</th>\n            \1',
    content
)

# Fix double injection for the first one if we already injected it
# The first one might be <th style="padding:8px 10px;text-align:left;">Lampiran</th> ... Lampiran ... Aksi
content = content.replace('<th style="padding:7px 8px;text-align:center">Lampiran</th>\n            <th style="padding:8px 10px;text-align:left;">Aksi</th>', '<th style="padding:8px 10px;text-align:left;">Aksi</th>') # revert the accidental duplicate on the first one

# Wait, the first one was already replaced perfectly because the python script replaced it explicitly.
# So I'll just remove ANY Lampiran column before Aksi first, then inject it everywhere.
content = re.sub(r'<th[^>]*>Lampiran</th>\s*<th([^>]*)>\s*Aksi\s*</th>', r'<th\1>Aksi</th>', content)
# Now inject cleanly everywhere
content = re.sub(
    r'(<th[^>]*>\s*Aksi\s*</th>)',
    r'<th style="padding:7px 8px;text-align:center">Lampiran</th>\n            \1',
    content
)

with open('app/templates/payment_memo/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
