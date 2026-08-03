path_service = r"C:\Financehub\app\modules\sponsorship\service.py"
with open(path_service, "r", encoding="utf-8") as f:
    service = f.read()

import re
match = re.search(r'status_chart = \[.*?return {.*?"statusChart": status_chart,.*?}', service, flags=re.DOTALL)
if match:
    print(match.group(0))
else:
    print("Not found")
