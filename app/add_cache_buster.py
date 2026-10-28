import re

with open('C:/Financehub/app/templates/beasiswa/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add cache buster to beasiswa_dashboard.css
content = re.sub(
    r'href="\{\{ url_for\(\'static\', filename=\'css/beasiswa_dashboard\.css\'\) \}\}"',
    r'href="{{ url_for(\'static\', filename=\'css/beasiswa_dashboard.css\') }}?v=2"',
    content
)

with open('C:/Financehub/app/templates/beasiswa/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
