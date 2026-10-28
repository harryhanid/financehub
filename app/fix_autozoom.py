import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Change roam: true to roam: 'move'
content = content.replace("roam: true,", "roam: 'move',\n          zoom: 1,")

# 2. Remove the old stopPropagation wheel listener since roam: 'move' handles it natively
shield_regex = r"document\.addEventListener\(\"DOMContentLoaded\", function\(\) \{[\s\S]*?\}, \{ capture: true \}\);\s*\}\s*\}, 100\);\s*\}\);"
content = re.sub(shield_regex, "", content)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Locked zoom scale and fixed roam behavior!")
