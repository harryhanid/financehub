path_service = r"C:\Financehub\app\modules\sponsorship\service.py"
with open(path_service, "r", encoding="utf-8") as f:
    c = f.read()

import re
match = re.search(r'def get_dashboard_data.*?def ', c, flags=re.DOTALL)
if match:
    print(match.group(0)[-1000:])
else:
    print("Could not find get_dashboard_data")
