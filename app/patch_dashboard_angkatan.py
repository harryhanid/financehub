import re

with open('C:/Financehub/app/modules/beasiswa/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add _angkatan_filter_sql helper
if "def _angkatan_filter_sql" not in content:
    helper = '''def _jenjang_filter_sql(jenjangs, column):
    if not jenjangs:
        return "", []
    placeholders = ",".join("?" for _ in jenjangs)
    return f" AND {column} IN ({placeholders})", list(jenjangs)

def _angkatan_filter_sql(angkatans, column):
    if not angkatans:
        return "", []
    placeholders = ",".join("?" for _ in angkatans)
    return f" AND {column} IN ({placeholders})", list(angkatans)'''
    content = re.sub(r'(?sm)def _jenjang_filter_sql\(jenjangs, column\):.*?return f" AND \{column\} IN \(\{placeholders\}\)", list\(jenjangs\)', helper, content)

# Update signatures
for func in ['get_dashboard_summary', 'get_dashboard_breakdown', 'get_dashboard_monthly', 'get_dashboard_latest_payments', 'get_dashboard_program_summary']:
    content = re.sub(
        fr'def {func}\(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None\)',
        f'def {func}(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None, angkatans: list = None)',
        content
    )

content = re.sub(
    r'def get_dashboard_pillar_yearly\(company_id: int, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None\)',
    r'def get_dashboard_pillar_yearly(company_id: int, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None, angkatans: list = None)',
    content
)

# Update get_dashboard_program_summary inner call
content = re.sub(
    r'summary = get_dashboard_summary\(company_id, years, pillars, programs, jenjangs, statuses\)',
    r'summary = get_dashboard_summary(company_id, years, pillars, programs, jenjangs, statuses, angkatans)',
    content
)

# Inject angkatan_sql into queries
def inject_angkatan(func_name, content, table_alias='s'):
    # Find the function definition
    pattern = fr'(def {func_name}\(.*?\):.*?jenjang_sql, jenjang_params = _jenjang_filter_sql\(jenjangs, "{table_alias}\.jenjang"\))'
    content = re.sub(pattern, rf'\1\n    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "{table_alias}.angkatan")', content, flags=re.DOTALL)
    
    # Add to the execute params
    # We need to find jenjang_params + status_case_params or similar and inject + angkatan_params
    # Let's just do a generic replacement within the function body if possible, or specifically.
    return content

content = inject_angkatan('get_dashboard_summary', content, 's')
content = content.replace('jenjang_params + status_case_params)', 'jenjang_params + angkatan_params + status_case_params)')

content = inject_angkatan('get_dashboard_breakdown', content, 's')
content = content.replace('jenjang_params + status_case_params)', 'jenjang_params + angkatan_params + status_case_params)')

content = inject_angkatan('get_dashboard_monthly', content, 's')
content = content.replace('jenjang_params + status_case_params)', 'jenjang_params + angkatan_params + status_case_params)')

content = inject_angkatan('get_dashboard_latest_payments', content, 's')
content = content.replace('jenjang_params + status_case_params + [limit])', 'jenjang_params + angkatan_params + status_case_params + [limit])')

content = inject_angkatan('get_dashboard_pillar_yearly', content, 's')
content = content.replace('jenjang_params + status_case_params)', 'jenjang_params + angkatan_params + status_case_params)')

# Inject into the SQL queries themselves (the WHERE clause or AND clauses)
# We know the SQLs usually have {jenjang_sql}{status_case_frag}
content = content.replace('{jenjang_sql}{status_case_frag}', '{jenjang_sql}{angkatan_sql}{status_case_frag}')

with open('C:/Financehub/app/modules/beasiswa/service.py', 'w', encoding='utf-8') as f:
    f.write(content)
