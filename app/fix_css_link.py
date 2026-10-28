import re

with open('C:/Financehub/app/templates/beasiswa/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    r"href="{{ url_for(\'static\', filename=\'css/beasiswa_dashboard.css\') }}?v=2"",
    r'href="{{ url_for(''static'', filename=''css/beasiswa_dashboard.css'') }}?v=3"'
)
# Wait, replacing literal backslashes in Python string:
content = content.replace(
    r"href="{{ url_for(\'static\', filename=\'css/beasiswa_dashboard.css\') }}?v=2"",
    ""
)

# Let's just use re.sub very safely
content = re.sub(r'href="\{\{\s*url_for\([^}]*beasiswa_dashboard\.css[^}]*\}\}[^"]*"', 'href="{{ url_for(\'static\', filename=\'css/beasiswa_dashboard.css\') }}?v=4"', content)

with open('C:/Financehub/app/templates/beasiswa/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
