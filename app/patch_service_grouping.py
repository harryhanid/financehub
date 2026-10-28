import re

with open('C:/Financehub/app/modules/beasiswa/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_get_requests = '''def get_budget_requests(company_id: int) -> list:
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT req.*, s.nama as siswa_nama "
        "FROM budget_beasiswa_requests req "
        "LEFT JOIN siswa s ON s.company_id=req.company_id AND s.code=req.siswa_code "
        "WHERE req.company_id=? ORDER BY req.id DESC",
        (company_id,)
    ).fetchall()]
    conn.close()
    
    # Group by batch_id
    batches = {}
    for r in rows:
        bid = r.get("batch_id")
        if not bid:
            bid = str(r["id"]) # fallback
        if bid not in batches:
            batches[bid] = {
                "batch_id": bid,
                "created_at": r["created_at"],
                "siswa_code": r["siswa_code"],
                "siswa_nama": r["siswa_nama"],
                "action_type": r["action_type"],
                "created_by": r["created_by"],
                "total_amount": 0,
                "lines": [],
                "status": "PENDING", # compute aggregate status later
            }
        batches[bid]["lines"].append(r)
        batches[bid]["total_amount"] += r["amount"]
    
    result = []
    for bid, data in batches.items():
        statuses = set([l["status"] for l in data["lines"]])
        if "PENDING" in statuses and ("APPROVED" in statuses or "REJECTED" in statuses):
            data["status"] = "PARTIAL"
        elif len(statuses) == 1:
            data["status"] = statuses.pop()
        else:
            data["status"] = "PROCESSED"
        result.append(data)
        
    return sorted(result, key=lambda x: x["created_at"], reverse=True)

def approve_budget_request_batch(company_id: int, request_ids: list, processed_by: str) -> dict:
    conn = get_conn()
    approved = 0
    for req_id in request_ids:
        req = conn.execute("SELECT * FROM budget_beasiswa_requests WHERE id=? AND company_id=?", (req_id, company_id)).fetchone()
        if not req or req["status"] != 'PENDING':
            continue
        
        action = req["action_type"]
        if action == 'ADD':
            conn.execute(
                "INSERT INTO budget_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, tgl_expired) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (company_id, req["siswa_code"], req["cat1"], req["cat2"], req["tanggal"], req["amount"], req["pillar"], req["tgl_expired"])
            )
        elif action == 'EDIT':
            conn.execute(
                "UPDATE budget_beasiswa SET cat1=?, cat2=?, tanggal=?, amount=?, pillar=?, tgl_expired=? WHERE id=? AND company_id=?",
                (req["cat1"], req["cat2"], req["tanggal"], req["amount"], req["pillar"], req["tgl_expired"], req["budget_id"], company_id)
            )
        elif action == 'DELETE':
            conn.execute("DELETE FROM budget_beasiswa WHERE id=? AND company_id=?", (req["budget_id"], company_id))
            
        conn.execute("UPDATE budget_beasiswa_requests SET status='APPROVED', processed_by=?, processed_at=CURRENT_TIMESTAMP WHERE id=?", (processed_by, req_id))
        approved += 1
        
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"{approved} baris pengajuan disetujui."}

def reject_budget_request_batch(company_id: int, request_ids: list, processed_by: str, reason: str) -> dict:
    conn = get_conn()
    rejected = 0
    for req_id in request_ids:
        req = conn.execute("SELECT * FROM budget_beasiswa_requests WHERE id=? AND company_id=?", (req_id, company_id)).fetchone()
        if not req or req["status"] != 'PENDING':
            continue
            
        conn.execute(
            "UPDATE budget_beasiswa_requests SET status='REJECTED', processed_by=?, processed_at=CURRENT_TIMESTAMP, reject_reason=? WHERE id=?",
            (processed_by, reason, req_id)
        )
        rejected += 1
        
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"{rejected} baris pengajuan ditolak."}'''

content = re.sub(r'(?sm)def get_budget_requests\(company_id: int\) -> list:.*?return \{"ok": True, "pesan": "Pengajuan berhasil ditolak\."\}', new_get_requests, content)

with open('C:/Financehub/app/modules/beasiswa/service.py', 'w', encoding='utf-8') as f:
    f.write(content)
