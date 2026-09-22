import sys
import re

def patch_backend():
    # 1. Patch routes.py
    with open(r'C:\Financehub\app\modules\sponsorship\routes.py', 'r', encoding='utf-8') as f:
        routes_content = f.read()

    new_route = """@bp.route("/input/create-bulk", methods=["POST"])
@jwt_html_required
@smt_company_required
def input_create_bulk():
    payload = request.get_json(force=True)
    result = create_transaksi_bulk(_cid(), payload)
    return jsonify(result)

@bp.route("/data")"""

    if "create_transaksi_bulk" not in routes_content:
        routes_content = routes_content.replace('@bp.route("/data")', new_route)

        # We also need to import create_transaksi_bulk
        import_stmt = "from .service import (\n    create_transaksi,\n    create_transaksi_bulk,"
        routes_content = re.sub(r'from \.service import \(\s*create_transaksi,', import_stmt, routes_content)

        with open(r'C:\Financehub\app\modules\sponsorship\routes.py', 'w', encoding='utf-8') as f:
            f.write(routes_content)
        print("Patched routes.py successfully!")

    # 2. Patch service.py
    with open(r'C:\Financehub\app\modules\sponsorship\service.py', 'r', encoding='utf-8') as f:
        service_content = f.read()

    new_service = """def create_transaksi_bulk(company_id: int, payload: dict) -> dict:
    lines = payload.get("lines", [])
    if not lines:
        return {"ok": False, "pesan": "Tidak ada baris transaksi."}
    
    # Common validation
    if not payload.get("tanggal_form_sponsor"):
        return {"ok": False, "pesan": "Tanggal Form Sponsor wajib diisi."}
    if not payload.get("lembaga_perorangan"):
        return {"ok": False, "pesan": "Lembaga/Perorangan wajib diisi."}

    # Extract header data
    cat = payload.get("cat")
    desc = payload.get("description")
    tgl_form = payload.get("tanggal_form_sponsor")
    tgl_pay = payload.get("tanggal_payment") or None
    lembaga = payload.get("lembaga_perorangan")
    perihal = payload.get("perihal")
    reff = payload.get("reff")
    status = payload.get("status")
    coa = payload.get("coa")
    cc_total = payload.get("cc_total")
    cc = payload.get("cc")
    source = payload.get("source")

    conn = get_conn()
    try:
        for idx, line in enumerate(lines):
            cat1 = line.get("cat1")
            perusahaan = get_perusahaan(cat1)
            if not perusahaan:
                conn.rollback()
                return {"ok": False, "pesan": f"Baris {idx+1}: Cat1 '{cat1}' tidak ditemukan."}
            
            try:
                amt = float(line.get("amount_request", 0) or 0)
            except (TypeError, ValueError):
                conn.rollback()
                return {"ok": False, "pesan": f"Baris {idx+1}: Amount Request harus berupa angka."}
            
            conn.execute(
                \"\"\"
                INSERT INTO sponsorship_transaksi
                    (company_id, cat, description, tanggal_form_sponsor, tanggal_payment,
                     cat1, cat2, cat3, lembaga_perorangan, perihal, amount_request, reff,
                     status, cat4, coa, cc_total, cc, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        COALESCE(?, '701078002'), COALESCE(?, 'SMT - Corporate Communication'),
                        COALESCE(?, 'POSPON'), COALESCE(?, 'Sponsor'))
                \"\"\",
                (
                    company_id, cat, desc, tgl_form, tgl_pay,
                    perusahaan["cat1"], perusahaan["cat2"], perusahaan["cat3"],
                    lembaga, perihal, amt, reff, status, line.get("cat4"),
                    coa, cc_total, cc, source
                )
            )
        conn.commit()
        return {"ok": True, "pesan": f"Berhasil menyimpan {len(lines)} transaksi Sponsorship."}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "pesan": f"Gagal menyimpan transaksi: {str(e)}"}
"""
    if "create_transaksi_bulk" not in service_content:
        service_content += "\n" + new_service
        with open(r'C:\Financehub\app\modules\sponsorship\service.py', 'w', encoding='utf-8') as f:
            f.write(service_content)
        print("Patched service.py successfully!")

if __name__ == '__main__':
    patch_backend()
