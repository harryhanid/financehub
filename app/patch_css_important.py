import re

with open('C:/Financehub/app/static/css/beasiswa_dashboard.css', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('display: flex !important;', 'display: flex;')

with open('C:/Financehub/app/static/css/beasiswa_dashboard.css', 'w', encoding='utf-8') as f:
    f.write(content)
