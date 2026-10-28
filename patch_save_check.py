with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

# 1. save_pa_payment
text = text.replace(
    'if not rows:\n        return {"ok": False, "pesan": "Minimal 1 baris siswa."}',
    'if not rows:\n        return {"ok": False, "pesan": "Minimal 1 baris siswa."}\n\n    from modules.beasiswa.service import check_budget_sufficient\n    chk = check_budget_sufficient(company_id, rows)\n    if not chk["ok"]:\n        return chk'
)

# 2. save_klaim_payment
text = text.replace(
    'for row in rows:\n        if float(row.get("amount", 0)) <= 0:\n            return {"ok": False,\n                    "pesan": f"Siswa {row.get(\'siswa_code\', \'?\')} harus memiliki amount > 0."}',
    'for row in rows:\n        if float(row.get("amount", 0)) <= 0:\n            return {"ok": False,\n                    "pesan": f"Siswa {row.get(\'siswa_code\', \'?\')} harus memiliki amount > 0."}\n\n    from modules.beasiswa.service import check_budget_sufficient\n    chk = check_budget_sufficient(company_id, rows, default_cat1="By Medical")\n    if not chk["ok"]:\n        return chk'
)

with open("app/modules/payment_memo/service.py", "w", encoding="utf-8") as f:
    f.write(text)
