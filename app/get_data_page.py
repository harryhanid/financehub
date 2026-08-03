path = r"C:\Financehub\app\modules\sponsorship\routes.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
import re
match = re.search(r'def data_page\(\):.*?return render_template', c, flags=re.DOTALL)
if match:
    print(match.group(0))
