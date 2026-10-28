with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()
import re
for func in ['loadPAM', 'loadFIORI', 'loadSML', 'loadENERGY', 'loadSETF', 'loadSMT']:
    m = re.search(fr'function {func}\(.*?\).*?_statusBadge\(r\.status\)', text, re.DOTALL)
    if m:
        lines = m.group(0).split('\n')
        print(f"--- {func} ---")
        print("\n".join(lines[-3:]))
