with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(r'        etf_pa_line_id = row\.get\("etf_pa_line_id"\) or None', r'        etf_pa_line_id = row.get("etf_pa_line_id") or None', text)

# I used 16 spaces in the replacement string: '                etf_pa_line_id'
text = text.replace("                etf_pa_line_id = row.get(\"etf_pa_line_id\") or None", "        etf_pa_line_id = row.get(\"etf_pa_line_id\") or None")

with open("app/modules/beasiswa/service.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed indent")
