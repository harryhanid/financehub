path = r"C:\Financehub\app\templates\sponsorship\data.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
import re
match = re.search(r'<div class="pagination">.*?</div>', c, flags=re.DOTALL)
if match:
    print(match.group(0))
