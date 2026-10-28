import os

# 1. Patch service.py
service_path = r'C:\Financehub\app\modules\sponsorship\service.py'
with open(service_path, 'r', encoding='utf-8') as f:
    service_content = f.read()

if 'def sync_transaksi_excel' not in service_content:
    sync_func = '''
def sync_transaksi_excel(company_id: int, file_bytes: bytes) -> dict:
    import openpyxl
    import io
    
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.active
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal membaca file Excel: {str(e)}"}
        
    conn = get_conn()
    try:
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            return {"ok": False, "pesan": "File Excel kosong atau tidak memiliki data."}
            
        header = rows[0]
        # Pastikan kolom sesuai dengan format export
        
        updated_count = 0
        inserted_count = 0
        
        for idx, row in enumerate(rows[1:], start=2):
            # Row structure: 0:ID, 1:Cat, 2:Desc, 3:Tgl Form, 4:Tgl Pay, 5:Cat1, 6:Cat2, 7:Cat3, 8:Lembaga, 9:Perihal, 10:Amount, 11:APP, 12:ENERGY, 13:PROPERTY, 14:AGRI, 15:Reff, 16:Status, 17:Cat4, 18:COA, 19:CC Total, 20:CC, 21:Source
            
            tx_id = row[0]
            cat = row[1]
            desc = row[2]
            tgl_form = row[3]
            tgl_pay = row[4] if row[4] else None
            cat1 = row[5]
            lembaga = row[8]
            perihal = row[9]
            amt = row[10]
            reff = row[15]
            status = row[16]
            cat4 = row[17]
            coa = row[18]
            cc_total = row[19]
            cc = row[20]
            source = row[21]
            
            # Abaikan baris yang kosong atau tidak valid
            if not cat1 or not tgl_form or not lembaga:
                continue
                
            perusahaan = get_perusahaan(cat1)
            if not perusahaan:
                conn.rollback()
                return {"ok": False, "pesan": f"Baris {idx}: Cat1 '{cat1}' tidak ditemukan di database."}
                
            cat2 = perusahaan["cat2"]
            cat3 = perusahaan["cat3"]
            
            try:
                amt = float(amt) if amt else 0
            except ValueError:
                amt = 0
                
            if tx_id:
                # Update
                conn.execute(
                    """
                    UPDATE sponsorship_transaksi 
                    SET cat=?, description=?, tanggal_form_sponsor=?, tanggal_payment=?,
                        cat1=?, cat2=?, cat3=?, lembaga_perorangan=?, perihal=?, amount_request=?, reff=?,
                        status=?, cat4=?, coa=?, cc_total=?, cc=?, source=?
                    WHERE id=? AND company_id=?
                    """,
                    (cat, desc, tgl_form, tgl_pay, cat1, cat2, cat3, lembaga, perihal, amt, reff, status, cat4, coa, cc_total, cc, source, tx_id, company_id)
                )
                updated_count += 1
            else:
                # Insert
                conn.execute(
                    """
                    INSERT INTO sponsorship_transaksi
                        (company_id, cat, description, tanggal_form_sponsor, tanggal_payment,
                         cat1, cat2, cat3, lembaga_perorangan, perihal, amount_request, reff,
                         status, cat4, coa, cc_total, cc, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, '701078002'), COALESCE(?, 'SMT - Corporate Communication'), COALESCE(?, 'POSPON'), COALESCE(?, 'Sponsor'))
                    """,
                    (company_id, cat, desc, tgl_form, tgl_pay, cat1, cat2, cat3, lembaga, perihal, amt, reff, status, cat4, coa, cc_total, cc, source)
                )
                inserted_count += 1
                
        conn.commit()
        return {"ok": True, "pesan": f"Sync sukses: {updated_count} di-update, {inserted_count} ditambah."}
        
    except Exception as e:
        conn.rollback()
        return {"ok": False, "pesan": f"Gagal sync transaksi: {str(e)}"}
'''
    with open(service_path, 'a', encoding='utf-8') as f:
        f.write(sync_func)
    print("service.py patched.")

# 2. Patch routes.py (add sync_transaksi_excel to import and add /data/sync route)
routes_path = r'C:\Financehub\app\modules\sponsorship\routes.py'
with open(routes_path, 'r', encoding='utf-8') as f:
    routes_content = f.read()

if 'sync_transaksi_excel' not in routes_content:
    routes_content = routes_content.replace(
        'delete_perusahaan,',
        'delete_perusahaan, sync_transaksi_excel,'
    )
    
    # modify download_name
    routes_content = routes_content.replace(
        'download_name="Sponsorship_Data.xlsx"',
        'download_name="Sponsorship - MASTER.xlsx"'
    )
    
    route_func = '''
@bp.route("/data/sync", methods=["POST"])
@jwt_html_required
@smt_company_required
def data_sync_route():
    if "file" not in request.files:
        return jsonify({"ok": False, "pesan": "File tidak ditemukan."})
    file = request.files["file"]
    if not file.filename.endswith(".xlsx"):
        return jsonify({"ok": False, "pesan": "Format file harus .xlsx"})
        
    file_bytes = file.read()
    result = sync_transaksi_excel(_cid(), file_bytes)
    return jsonify(result)
'''
    routes_content += route_func
    with open(routes_path, 'w', encoding='utf-8') as f:
        f.write(routes_content)
    print("routes.py patched.")

# 3. Patch data.html (add sync button and file input)
data_html_path = r'C:\Financehub\app\templates\sponsorship\data.html'
with open(data_html_path, 'r', encoding='utf-8') as f:
    data_html = f.read()

if 'id="sp-sync-file"' not in data_html:
    search_str = '''<button type="button" class="budget-btn" style="background-color:#10b981;margin-left:auto" onclick="exportDataExcel()">Export to Excel</button>'''
    replace_str = search_str + '''\n    <button type="button" class="budget-btn" style="background-color:#3b82f6;margin-left:8px" onclick="document.getElementById('sp-sync-file').click()">Sync Data</button>\n    <input type="file" id="sp-sync-file" style="display:none" accept=".xlsx" onchange="sponsorshipDataSync()" />'''
    
    new_html = data_html.replace(search_str, replace_str)
    with open(data_html_path, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print("data.html patched.")

# 4. Patch sponsorship.js (add sponsorshipDataSync)
js_path = r'C:\Financehub\app\static\js\sponsorship.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

if 'function sponsorshipDataSync' not in js_content:
    js_func = '''
function sponsorshipDataSync() {
  const fileInput = document.getElementById("sp-sync-file");
  if (!fileInput.files.length) return;
  const file = fileInput.files[0];
  
  if (!confirm("Apakah Anda yakin ingin mensinkronisasi data menggunakan file: " + file.name + "?")) {
    fileInput.value = "";
    return;
  }
  
  const formData = new FormData();
  formData.append("file", file);
  
  showLoading("Memproses Sinkronisasi...");
  
  fetch("/sponsorship/data/sync", {
    method: "POST",
    body: formData
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) { setTimeout(function () { window.location.reload(); }, 1000); }
  })
  .catch(function() { showToast("Terjadi kesalahan saat sync data.", "error"); })
  .finally(function() {
    hideLoading();
    fileInput.value = "";
  });
}
'''
    js_content += js_func
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)
    print("sponsorship.js patched.")
