with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()
import re
for match in re.finditer(r"def .*klaim.*", text):
    print(match.group(0))
