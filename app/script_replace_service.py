import re

path = r"C:\Financehub\app\modules\beasiswa\service.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Add _program_filter_sql and _jenjang_filter_sql
helpers = """def _pillar_filter_sql(pillars, column):
    if not pillars:
        return "", []
    placeholders = ",".join("?" for _ in pillars)
    return f" AND {column} IN ({placeholders})", list(pillars)

def _program_filter_sql(programs, column):
    if not programs:
        return "", []
    placeholders = ",".join("?" for _ in programs)
    return f" AND {column} IN ({placeholders})", list(programs)

def _jenjang_filter_sql(jenjangs, column):
    if not jenjangs:
        return "", []
    placeholders = ",".join("?" for _ in jenjangs)
    return f" AND {column} IN ({placeholders})", list(jenjangs)"""

c = re.sub(r'def _pillar_filter_sql.*?\n\s*return.*?list\(pillars\)', helpers, c, flags=re.DOTALL)


# 1. get_dashboard_summary
def replace_summary(m):
    sig = m.group(1).replace(")", ", programs: list = None, jenjangs: list = None)")
    body = m.group(2)
    body = body.replace('pillar_sql, pillar_params = _pillar_filter_sql(pillars, "pillar")', 
                        'pillar_sql, pillar_params = _pillar_filter_sql(pillars, "pillar")\n    program_sql, program_params = _program_filter_sql(programs, "s.program")\n    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")')
    body = body.replace('WHERE company_id = ?{budget_year_sql}', 'WHERE company_id = ?{budget_year_sql}') # Doesn't have s.program, need to join siswa? Wait, budget_total subquery doesn't join siswa! 
    return sig + body

# Let's write custom replacements for each function to be careful.
