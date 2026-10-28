import re

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# For any function starting with api_dashboard_
# let's just make sure programs and programs_str are defined.
# If programs = ... is missing but programs_str = ... is present:
content = re.sub(
    r'(programs_str = request\.args\.get\("programs", ""\))\n(\s*jenjangs_str)',
    r'\1\n    programs = [p for p in programs_str.split(",") if p]\n\2',
    content
)

# Wait, maybe programs_str = ... is completely missing in some?
# Let's check api_dashboard_latest_payments:
if "def api_dashboard_latest_payments():" in content:
    # Just print the first 15 lines of each api function to debug
    funcs = re.findall(r'(def api_dashboard_.*?\):.*?(?=def api_dashboard_|$))', content, flags=re.DOTALL)
    for func in funcs:
        print(func.strip()[:300])
        print('-'*40)

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
