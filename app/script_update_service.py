import re

path = r"C:\Financehub\app\modules\beasiswa\service.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

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

# get_dashboard_summary
c = c.replace('def get_dashboard_summary(company_id: int, years: list = None, pillars: list = None) -> list:',
              'def get_dashboard_summary(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None) -> list:')
c = c.replace('pillar_sql, pillar_params = _pillar_filter_sql(pillars, "pillar")',
              'pillar_sql, pillar_params = _pillar_filter_sql(pillars, "pillar")\n    program_sql, program_params = _program_filter_sql(programs, "s.program")\n    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")')
c = c.replace('WHERE s.company_id = ?\n        ORDER BY s.nama\n        """,\n        [company_id, *budget_year_params, company_id, *payment_year_params, *pillar_params, company_id],',
              'WHERE s.company_id = ?{program_sql}{jenjang_sql}\n        ORDER BY s.nama\n        """,\n        [company_id, *budget_year_params, company_id, *payment_year_params, *pillar_params, company_id, *program_params, *jenjang_params],')

# get_dashboard_breakdown
c = c.replace('def get_dashboard_breakdown(company_id: int, years: list = None, pillars: list = None) -> dict:',
              'def get_dashboard_breakdown(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None) -> dict:')
c = c.replace('pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")',
              'pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")\n    program_sql, program_params = _program_filter_sql(programs, "s.program")\n    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")')

# Inject in budget_rows
c = c.replace('WHERE b.company_id = ?{budget_year_sql}\n        GROUP BY b.cat1\n        """,\n        [company_id, *budget_year_params],',
              'WHERE b.company_id = ?{budget_year_sql}{program_sql}{jenjang_sql}\n        GROUP BY b.cat1\n        """,\n        [company_id, *budget_year_params, *program_params, *jenjang_params],')
# Inject in payment_rows
c = c.replace('WHERE p.company_id = ?{payment_year_sql}{pillar_sql}\n        GROUP BY p.cat1\n        """,\n        [company_id, *payment_year_params, *pillar_params],',
              'WHERE p.company_id = ?{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}\n        GROUP BY p.cat1\n        """,\n        [company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params],')
# Inject in budget_jenjang_rows
c = c.replace('WHERE b.company_id = ?{budget_year_sql}\n        GROUP BY s.jenjang\n        """,\n        [company_id, *budget_year_params],',
              'WHERE b.company_id = ?{budget_year_sql}{program_sql}{jenjang_sql}\n        GROUP BY s.jenjang\n        """,\n        [company_id, *budget_year_params, *program_params, *jenjang_params],')
# Inject in payment_jenjang_rows
c = c.replace('WHERE p.company_id = ?{payment_year_sql}{pillar_sql}\n        GROUP BY s.jenjang\n        """,\n        [company_id, *payment_year_params, *pillar_params],',
              'WHERE p.company_id = ?{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}\n        GROUP BY s.jenjang\n        """,\n        [company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params],')

c = c.replace('for s in get_dashboard_summary(company_id, years, pillars)',
              'for s in get_dashboard_summary(company_id, years, pillars, programs, jenjangs)')

# get_dashboard_monthly
c = c.replace('def get_dashboard_monthly(company_id: int, years: list = None, pillars: list = None) -> dict:',
              'def get_dashboard_monthly(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None) -> dict:')
c = c.replace('pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")',
              'pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")\n    program_sql, program_params = _program_filter_sql(programs, "s.program")\n    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")')

# Budget
c = c.replace('WHERE b.company_id = ? AND strftime(\'%Y\', b.tanggal) = ?\n        GROUP BY bulan\n        """,\n        (company_id, str(chart_year)),',
              'WHERE b.company_id = ? AND strftime(\'%Y\', b.tanggal) = ?{program_sql}{jenjang_sql}\n        GROUP BY bulan\n        """,\n        [company_id, str(chart_year), *program_params, *jenjang_params],')
# Realisasi
c = c.replace('AND strftime(\'%Y\', p.tanggal) IN ({year_placeholders}){pillar_sql}\n        GROUP BY tahun, bulan\n        """,\n        [company_id, *[str(y) for y in years_to_fetch], *pillar_params],',
              'AND strftime(\'%Y\', p.tanggal) IN ({year_placeholders}){pillar_sql}{program_sql}{jenjang_sql}\n        GROUP BY tahun, bulan\n        """,\n        [company_id, *[str(y) for y in years_to_fetch], *pillar_params, *program_params, *jenjang_params],')


# get_dashboard_latest_payments
c = c.replace('def get_dashboard_latest_payments(company_id: int, years: list = None, pillars: list = None, limit: int = 20) -> list:',
              'def get_dashboard_latest_payments(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, limit: int = 20) -> list:')
c = c.replace('pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")',
              'pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")\n    program_sql, program_params = _program_filter_sql(programs, "s.program")\n    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")')
c = c.replace('WHERE p.company_id = ? AND p.status = \'complete\'{payment_year_sql}{pillar_sql}\n        ORDER BY p.id DESC\n        LIMIT ?\n        """,\n        [company_id, *payment_year_params, *pillar_params, limit],',
              'WHERE p.company_id = ? AND p.status = \'complete\'{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}\n        ORDER BY p.id DESC\n        LIMIT ?\n        """,\n        [company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params, limit],')

# get_dashboard_program_summary
c = c.replace('def get_dashboard_program_summary(company_id: int, years: list = None, pillars: list = None) -> list:',
              'def get_dashboard_program_summary(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None) -> list:')
c = c.replace('summary = get_dashboard_summary(company_id, years, pillars)',
              'summary = get_dashboard_summary(company_id, years, pillars, programs, jenjangs)')

# get_dashboard_pillar_yearly
c = c.replace('def get_dashboard_pillar_yearly(company_id: int, pillars: list = None) -> list:',
              'def get_dashboard_pillar_yearly(company_id: int, pillars: list = None, programs: list = None, jenjangs: list = None) -> list:')
c = c.replace('pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")',
              'pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")\n    program_sql, program_params = _program_filter_sql(programs, "s.program")\n    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")')
c = c.replace('AND p.tanggal IS NOT NULL AND p.tanggal != \'\'{pillar_sql}\n        GROUP BY tahun, p.pillar\n        ORDER BY tahun DESC, p.pillar ASC\n        """,\n        [company_id, *pillar_params],',
              'AND p.tanggal IS NOT NULL AND p.tanggal != \'\'{pillar_sql}{program_sql}{jenjang_sql}\n        GROUP BY tahun, p.pillar\n        ORDER BY tahun DESC, p.pillar ASC\n        """,\n        [company_id, *pillar_params, *program_params, *jenjang_params],')


with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done")
