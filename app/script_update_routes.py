import re

path = r"C:\Financehub\app\modules\beasiswa\routes.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Replace the extraction logic
def repl_extract(m):
    return m.group(0) + '\n    programs_str = request.args.get("programs", "")\n    jenjangs_str = request.args.get("jenjangs", "")\n    programs = [p for p in programs_str.split(",") if p]\n    jenjangs = [j for j in jenjangs_str.split(",") if j]'

c = re.sub(r'pillars = \[p for p in pillars_str\.split\(\",\"\) if p\]', repl_extract, c)

# Replace the calls
funcs = [
    'get_dashboard_summary',
    'get_dashboard_breakdown',
    'get_dashboard_monthly',
    'get_dashboard_latest_payments',
    'get_dashboard_program_summary'
]

for func in funcs:
    old = f'{func}(_cid(), years, pillars)'
    new = f'{func}(_cid(), years, pillars, programs, jenjangs)'
    c = c.replace(old, new)

# Special case for get_dashboard_pillar_yearly
c = c.replace('get_dashboard_pillar_yearly(_cid(), pillars)',
              'get_dashboard_pillar_yearly(_cid(), pillars, programs, jenjangs)')

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done")
