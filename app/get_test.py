path = r"C:\Financehub\app\tests\test_sponsorship_routes.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
import re
match = re.search(r'def test_data_page_pagination_preserves_filters\(client\):.*?(?=\ndef )', c, flags=re.DOTALL)
if match:
    print(match.group(0))
