with open("app/modules/sponsorship/service.py", "r", encoding="utf-8") as f:
    text = f.read()
import re
if re.search(r'def get_perusahaan', text):
    print("EXISTS")
else:
    print("MISSING")
