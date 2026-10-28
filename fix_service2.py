with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

new_end = """
    # Update PA status to on_process and set nomor_pam
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
                f\"\"\"UPDATE {pa_tbl} SET status = 'on_process', updated_at = ?, nomor_pam = ?
                    WHERE id IN (
                        SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                    ) AND company_id = ? AND status = 'open'\"\"\",
                [ts_op, pam] + pa_line_ids + [company_id]
            )

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"{saved} data klaim berhasil ditambahkan."}"""

text = re.sub(r'# Update PA status to on_process.*return \{"ok": True, "pesan": f"\{saved\} data klaim berhasil ditambahkan\."\}', new_end, text, flags=re.DOTALL)

with open("app/modules/beasiswa/service.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Added nomor_pam update")
