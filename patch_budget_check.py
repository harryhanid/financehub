with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()

text += """
def check_budget_sufficient(company_id: int, rows: list, default_cat1: str = None) -> dict:
    req = {}
    for r in rows:
        sc = r.get("siswa_code")
        c1 = r.get("cat1") or default_cat1
        try:
            amt = float(str(r.get("amount", 0)).replace(",", ""))
        except:
            amt = 0
        if not sc or not c1 or amt <= 0:
            continue
        req[(sc, c1)] = req.get((sc, c1), 0) + amt

    if not req:
        return {"ok": True}

    for (sc, c1), total_req in req.items():
        sisa_info = get_sisa_budget(company_id, sc)
        sisa = sisa_info["sisa"].get(c1, 0)
        if total_req > sisa:
            return {"ok": False, "pesan": f"Budget tidak cukup untuk {sc} (Kategori {c1}). Diminta: Rp {total_req:,.0f}, Sisa: Rp {sisa:,.0f}."}
    return {"ok": True}
"""
with open("app/modules/beasiswa/service.py", "w", encoding="utf-8") as f:
    f.write(text)
