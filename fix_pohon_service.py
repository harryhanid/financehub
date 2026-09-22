import re

file_path = "C:/Financehub/app/modules/sahabat_etf/service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'def build_pohon_data\(company_id: int, report_year: int, report_month: int = 12, pillars: list = None\) -> dict:'

new_funcs = """def _build_diagram_buckets(company_id: int, years: list = None, pillars: list = None) -> dict:
    budget_rows, payment_rows = _fetch_report_rows(company_id)
    buckets = {}

    def bucket(section, subgroup, nama, group_setf):
        key = (section, subgroup, nama)
        if key not in buckets:
            buckets[key] = {"val": {"plafon": 0.0, "pta": 0.0, "dibayar": 0.0}, "pillars": set(), "group_setf": group_setf}
        return buckets[key]

    for r in budget_rows:
        if pillars and r["pillar"] and r["pillar"] not in pillars:
            continue
        if years and r["tahun"] not in years:
            continue
            
        section  = _row_section(r["cat1"])
        subgroup = _row_subgroup(section, r)
        amount   = float(r["amount"] or 0)
        is_pta   = (r["cat2"] == "Tambahan Anggaran")
        plafon_amt = 0.0 if is_pta else amount
        pta_amt    = amount if is_pta else 0.0
        
        b = bucket(section, subgroup, r["nama"], r["group_setf"])
        b["pillars"].add(r["pillar"] or "")
        b["val"]["plafon"] += plafon_amt
        b["val"]["pta"] += pta_amt

    for r in payment_rows:
        if pillars and r["pillar"] and r["pillar"] not in pillars:
            continue
        if years and r["tahun"] not in years:
            continue
            
        section  = _row_section(r["cat1"])
        subgroup = _row_subgroup(section, r)
        amount   = float(r["amount"] or 0)

        is_complete = (r["status"] == "complete")
        dibayar  = amount if is_complete else 0.0

        b = bucket(section, subgroup, r["nama"], r["group_setf"])
        b["pillars"].add(r["pillar"] or "")
        b["val"]["dibayar"] += dibayar

    return buckets

def build_pohon_data(company_id: int, years: list = None, pillars: list = None) -> dict:"""

content = re.sub(target, new_funcs, content)

# Now fix `build_pohon_data` body
content = content.replace('buckets = _build_buckets(company_id, report_year, report_month, pillars)', 'buckets = _build_diagram_buckets(company_id, years, pillars)')
content = content.replace('cum = b["cum"]', 'cum = b["val"]')

# Now fix `build_pohon_group_data` definition
content = content.replace('def build_pohon_group_data(company_id: int, report_year: int, report_month: int = 12, pillars: list = None) -> dict:', 'def build_pohon_group_data(company_id: int, years: list = None, pillars: list = None) -> dict:')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated service.py")
