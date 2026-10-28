import re

with open('C:/Financehub/app/templates/beasiswa/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Wrap the template variables in spans to protect them
content = re.sub(r'<label><input type="checkbox" class="(dash-[a-z]+-cb)" value="\{\{ ([a-z_]+) \}\}" checked>\s*\{\{ \2 \}\}</label>', r'<label><input type="checkbox" class="\1" value="{{ \2 }}" checked> <span class="filter-text">{{ \2 }}</span></label>', content)

# And for the status ones which are hardcoded
content = content.replace('<label><input type="checkbox" class="dash-status-cb" value="open" checked> Open</label>', '<label><input type="checkbox" class="dash-status-cb" value="open" checked> <span class="filter-text">Open</span></label>')
content = content.replace('<label><input type="checkbox" class="dash-status-cb" value="complete" checked> Complete</label>', '<label><input type="checkbox" class="dash-status-cb" value="complete" checked> <span class="filter-text">Complete</span></label>')

with open('C:/Financehub/app/templates/beasiswa/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
