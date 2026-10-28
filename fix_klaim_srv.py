with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

# 1. Update save_klaim_payment insert
new_insert = """            cur = conn.execute(
                \"\"\"INSERT INTO payment_beasiswa
                   (company_id, siswa_code, cat1, cat2, tanggal, amount,
                    pillar, perusahaan, pam, status, klasifikasi_pam, etf_pa_line_id)
                   VALUES (?, ?,?,?,?,?,?,?,?,?,'open',?,?)\"\"\",
                (company_id, siswa_code, "By Medical", cat2, row_tanggal,
                 amount, pillar, perusahaan, pam_no, klasifikasi, row.get("etf_pa_line_id") or None)
            )"""

text = re.sub(
    r'cur = conn\.execute\(\s*\"\"\"INSERT INTO payment_beasiswa.*?VALUES \(\?, \?,\?,\?,\?,\?,\?,\?,\?,\?,\'open\',\?\)\"\"\",.*?klasifikasi\)\s*\)',
    new_insert, text, flags=re.DOTALL
)

# 2. Update PA lines
new_end = """        conn.execute(
            \"\"\"INSERT INTO pam_records
               (klasifikasi, company_id, pam_no, pam_date, requestors_name, keterangan,
                total_amount, dpp, pt, due_date, pillar, source, status, attachment_file_id, created_at)
               VALUES (?, ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)\"\"\",
            (klasifikasi, company_id, pam_no, tanggal,
             config.PAM_DEFAULT_REQUESTOR, keterangan,
             grand_total, grand_total, perusahaan, due_date, pillar, "klaim_medis", "open",
             data.get("attachment_file_id", ""), _ts())
        )

        # Update PA status to on_process and set nomor_pam
        tab = data.get("tab") or "agri"
        from modules.etf_payment_application.service import _TAB_CFG
        pa_tbl, lines_tbl, _, _ = _TAB_CFG.get(tab, _TAB_CFG["agri"])
        pa_line_ids = [row.get("etf_pa_line_id") for row in rows if row.get("etf_pa_line_id")]
        if pa_line_ids:
            ph = ",".join("?" * len(pa_line_ids))
            ts_op = _ts()
            conn.execute(
                f\"\"\"UPDATE {pa_tbl} SET status = 'on_process', updated_at = ?, nomor_pam = ?
                    WHERE id IN (
                        SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                    ) AND company_id = ? AND status = 'open'\"\"\",
                [ts_op, pam_no] + pa_line_ids + [company_id]
            )

        conn.commit()"""

text = re.sub(r'conn\.execute\(\s*\"\"\"INSERT INTO pam_records.*?conn\.commit\(\)', new_end, text, flags=re.DOTALL)

with open("app/modules/payment_memo/service.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated save_klaim_payment")
