import re

service_path = r"C:\Financehub\app\modules\budget\service.py"
with open(service_path, "r", encoding="utf-8") as f:
    service = f.read()

# Add import
import_marker = "from database import get_conn"
if "from format_utils import format_rupiah" not in service:
    service = service.replace(import_marker, import_marker + "\nfrom format_utils import format_rupiah")

# Replace format_currency
old_func = '''def format_currency(num) -> str:
    if num is None:
        return "Rp 0"
    try:
        n = round(float(num))
    except (TypeError, ValueError):
        return "Rp 0"
    return "Rp " + f"{n:,}".replace(",", ".")'''

new_func = '''def format_currency(num) -> str:
    return format_rupiah(num)'''

if old_func in service:
    service = service.replace(old_func, new_func)
else:
    print("Could not find exact old function, using regex")
    service = re.sub(r'def format_currency\(num\) -> str:.*?return "Rp " \+ f"\{n:,\}"\.replace\(",", "\."\)', new_func, service, flags=re.DOTALL)

with open(service_path, "w", encoding="utf-8") as f:
    f.write(service)

print("Task 4 complete")
