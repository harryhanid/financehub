import re

with open('C:/Financehub/app/modules/beasiswa/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I will just write a python function to replace the entire block from "def delete_budget_row" to "return get_budget_requests"
new_funcs = '''def delete_budget_row(company_id: int, row_id: int, created_by: str) -> dict:
    conn = get_conn()
    row  = conn.execute("SELECT * FROM budget_beasiswa WHERE id=? AND company_id=?", (row_id, company_id)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Baris budget tidak ditemukan."}
    conn.execute(
        "INSERT INTO budget_beasiswa_requests (company_id, siswa_code, action_type, budget_id, cat1, cat2, tanggal, amount, pillar, tgl_expired, created_by, batch_id) VALUES (?, ?, 'DELETE', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (company_id, row["siswa_code"], row["id"], row["cat1"], row["cat2"], row["tanggal"], row["amount"], row["pillar"], row["tgl_expired"], created_by, str(uuid.uuid4())[:8])
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Pengajuan hapus budget telah dikirim ke BC."}

def update_budget_row(company_id: int, row_id: int, data: dict, created_by: str) -> dict:
    conn = get_conn()
    row  = conn.execute("SELECT * FROM budget_beasiswa WHERE id=? AND company_id=?", (row_id, company_id)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Baris budget tidak ditemukan."}
    try:
        amount = float(str(data.get("amount", 0)).replace(",", ""))
    except (ValueError, TypeError):
        amount = 0
    if amount <= 0:
        conn.close()
        return {"ok": False, "pesan": "Amount harus lebih dari 0."}
    conn.execute(
        "INSERT INTO budget_beasiswa_requests (company_id, siswa_code, action_type, budget_id, cat1, cat2, tanggal, amount, pillar, tgl_expired, created_by, batch_id) VALUES (?, ?, 'EDIT', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (company_id, row["siswa_code"], row["id"], data.get("cat1",""), data.get("cat2",""), data.get("tanggal",""), amount, data.get("pillar",""), data.get("tgl_expired") or None, created_by, str(uuid.uuid4())[:8])
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Pengajuan edit budget telah dikirim ke BC."}

def add_budget_batch(company_id: int, siswa_code: str, tanggal: str, pillar: str, items: list, created_by: str) -> dict:
    conn  = get_conn()
    batch_id = str(uuid.uuid4())[:8]
    saved = 0
    for item in items:
        try:
            amount = float(str(item.get("amount", 0)).replace(",", ""))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            continue
        conn.execute(
            "INSERT INTO budget_beasiswa_requests (company_id, siswa_code, action_type, cat1, cat2, tanggal, amount, pillar, tgl_expired, created_by, batch_id) VALUES (?, ?, 'ADD', ?, ?, ?, ?, ?, ?, ?, ?)",
            (company_id, siswa_code, item.get("cat1",""), item.get("cat2",""), tanggal, amount, pillar, item.get("tgl_expired") or None, created_by, batch_id)
        )
        saved += 1
    conn.commit()
    conn.close()
    if saved == 0:
        return {"ok": False, "pesan": "Tidak ada baris budget valid yang dikirim."}
    return {"ok": True, "pesan": f"{saved} baris pengajuan budget telah dikirim ke BC."}'''

content = re.sub(r'(?sm)def delete_budget_row\(company_id: int, row_id: int, created_by: str\) -> dict:.*?return \{"ok": True, "pesan": f"\{saved\} baris pengajuan budget telah dikirim ke BC\."\}', new_funcs, content)

with open('C:/Financehub/app/modules/beasiswa/service.py', 'w', encoding='utf-8') as f:
    f.write(content)
