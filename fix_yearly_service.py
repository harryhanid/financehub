import re

file_path = "C:/Financehub/app/modules/sahabat_etf/service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'def get_yearly_breakdown\(company_id: int, pillars: list = None\) -> dict:\n    conn = get_conn\(\)\n    pillar_sql, pillar_params = _pillar_filter_sql\(pillars, "p\.pillar"\)\n    b_pillar_sql, b_pillar_params = _pillar_filter_sql\(pillars, "b\.pillar"\)'

replacement = """def get_yearly_breakdown(company_id: int, years: list = None, pillars: list = None) -> dict:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    b_pillar_sql, b_pillar_params = _pillar_filter_sql(pillars, "b.pillar")"""

content = re.sub(target, replacement, content)

target_b_sql = r'WHERE b\.company_id = \? AND s\.program = \? AND b\.tanggal IS NOT NULL AND b\.tanggal != \'\'\{b_pillar_sql\}'
replacement_b_sql = "WHERE b.company_id = ? AND s.program = ? AND b.tanggal IS NOT NULL AND b.tanggal != ''{budget_year_sql}{b_pillar_sql}"
content = re.sub(target_b_sql, replacement_b_sql, content)

target_b_params = r'\[company_id, PROGRAM_NAME, \*b_pillar_params\]'
replacement_b_params = "[company_id, PROGRAM_NAME, *budget_year_params, *b_pillar_params]"
content = re.sub(target_b_params, replacement_b_params, content)

target_p_sql = r'WHERE p\.company_id = \? AND s\.program = \? AND p\.status = \'complete\'\s*AND p\.tanggal IS NOT NULL AND p\.tanggal != \'\'\{pillar_sql\}'
replacement_p_sql = "WHERE p.company_id = ? AND s.program = ? AND p.status = 'complete'\n              AND p.tanggal IS NOT NULL AND p.tanggal != ''{payment_year_sql}{pillar_sql}"
content = re.sub(target_p_sql, replacement_p_sql, content)

target_p_params = r'\[company_id, PROGRAM_NAME, \*pillar_params\]'
replacement_p_params = "[company_id, PROGRAM_NAME, *payment_year_params, *pillar_params]"
content = re.sub(target_p_params, replacement_p_params, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
