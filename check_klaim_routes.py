with open("app/modules/klaim_medical/routes.py", "r", encoding="utf-8") as f:
    text = f.read()
import re
match = re.search(r'def create.*', text)
if match:
    print(match.group(0))
