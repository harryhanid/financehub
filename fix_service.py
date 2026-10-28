with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

# 1. Update INSERT into payment_beasiswa to include etf_pa_line_id
new_insert = """        etf_pa_line_id = row.get("etf_pa_line_id") or None
        cur = conn.execute(
            \"\"\"INSERT INTO payment_beasiswa
               (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,pam,status,etf_pa_line_id)
               VALUES (?,?,?,?,?,?,?,?,?,'open',?)\"\"\",
            (company_id, siswa_code, "By Medical", perawatan,
             tanggal, amount, pillar, perusahaan, pam, etf_pa_line_id)
        )"""

text = re.sub(
    r'cur = conn\.execute\(\s*\"\"\"INSERT INTO payment_beasiswa\s*\(company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,pam,status\)\s*VALUES \(\?,\?,\?,\?,\?,\?,\?,\?,\?,\'open\'\)\"\"\",\s*\(company_id, siswa_code, "By Medical", perawatan,\s*tanggal, amount, pillar, perusahaan, pam\)\s*\)',
    new_insert, text
)

# 2. Add PA status update to on_process at the end of add_klaim_multi
new_end = """
    # Update PA status to on_process
    pa_line_ids = [row.get("etf_pa_line_id") for row in rows if row.get("etf_pa_line_id")]
    if pa_line_ids:
        from modules.etf_payment_application.service import _PILLAR_PA_TBL
        pair = _PILLAR_PA_TBL.get((pillar or "").upper())
        if pair:
            lines_tbl, pa_tbl = pair
            ph = ",".join("?" * len(pa_line_ids))
            from utils.dates import _ts
            ts_op = _ts()
            conn.execute(
                f\"\"\"UPDATE {pa_tbl} SET status = 'on_process', updated_at = ?
                    WHERE id IN (
                        SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                    ) AND company_id = ? AND status = 'open'\"\"\",
                [ts_op] + pa_line_ids + [company_id]
            )

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"{saved} data klaim berhasil ditambahkan."}"""

text = re.sub(r'conn\.commit\(\)\s*conn\.close\(\)\s*return \{"ok": True, "pesan": f"\{saved\} data klaim berhasil ditambahkan\."\}', new_end, text)

with open("app/modules/beasiswa/service.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated add_klaim_multi")
