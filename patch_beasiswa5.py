with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

# 1. update_budget_row
text = text.replace(
    '"UPDATE budget_beasiswa SET cat1=?,cat2=?,tanggal=?,pillar=?,amount=? WHERE id=? AND company_id=?",\n        (data.get("cat1",""), data.get("cat2",""), data.get("tanggal",""),\n         data.get("pillar",""), amount, row_id, company_id)',
    '"UPDATE budget_beasiswa SET cat1=?,cat2=?,tanggal=?,pillar=?,amount=?,tgl_expired=? WHERE id=? AND company_id=?",\n        (data.get("cat1",""), data.get("cat2",""), data.get("tanggal",""),\n         data.get("pillar",""), amount, data.get("tgl_expired") or None, row_id, company_id)'
)

# 2. add_budget_batch
text = text.replace(
    '"INSERT INTO budget_beasiswa (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar) "\n            "VALUES (?,?,?,?,?,?,?)",\n            (company_id, siswa_code, item.get("cat1",""), item.get("cat2",""),\n             tanggal, amount, pillar)',
    '"INSERT INTO budget_beasiswa (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,tgl_expired) "\n            "VALUES (?,?,?,?,?,?,?,?)",\n            (company_id, siswa_code, item.get("cat1",""), item.get("cat2",""),\n             tanggal, amount, pillar, item.get("tgl_expired") or None)'
)

# 3. get_sisa_budget
text = text.replace(
    '"SELECT cat1, SUM(amount) as total FROM budget_beasiswa "\n        "WHERE company_id=? AND siswa_code=? GROUP BY cat1",\n        (company_id, siswa_code)',
    '"SELECT cat1, SUM(amount) as total FROM budget_beasiswa "\n        "WHERE company_id=? AND siswa_code=? AND (tgl_expired IS NULL OR tgl_expired >= date(\'now\', \'localtime\')) GROUP BY cat1",\n        (company_id, siswa_code)'
)

with open("app/modules/beasiswa/service.py", "w", encoding="utf-8") as f:
    f.write(text)
