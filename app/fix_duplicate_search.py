import re

with open('C:/Financehub/app/templates/beasiswa/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix duplicate panel-search
content = re.sub(
    r'<div class="panel-search" style="padding:0\.4rem;border-bottom:1px solid var\(--border\);">\s*<input type="text" class="dash-filter-search dm-inp" placeholder="Cari Angkatan\.\.\." style="width:100%;font-size:0\.75rem;" onkeyup="dashFilterSearch\(this\)">\s*</div>\s*<div class="panel-search" style="padding:0\.4rem;border-bottom:1px solid var\(--border\);"><input type="text" class="dash-filter-search dm-inp" placeholder="Cari\.\.\." style="width:100%;font-size:0\.75rem;" onkeyup="dashFilterSearch\(this\)"></div>',
    r'<div class="panel-search" style="padding:0.4rem;border-bottom:1px solid var(--border);"><input type="text" class="dash-filter-search dm-inp" placeholder="Cari Angkatan..." style="width:100%;font-size:0.75rem;" onkeyup="dashFilterSearch(this)"></div>',
    content
)

with open('C:/Financehub/app/templates/beasiswa/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
