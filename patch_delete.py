import os

# 1. Patch service.py
service_path = r'C:\Financehub\app\modules\sponsorship\service.py'
with open(service_path, 'r', encoding='utf-8') as f:
    service_content = f.read()

if 'def delete_transaksi' not in service_content:
    delete_func = '''

def delete_transaksi(transaksi_id: int, company_id: int = None) -> dict:
    conn = get_conn()
    select_query = "SELECT * FROM sponsorship_transaksi WHERE id = ?"
    params = [transaksi_id]
    if company_id:
        select_query += " AND company_id = ?"
        params.append(company_id)
        
    t = conn.execute(select_query, params).fetchone()
    if not t:
        conn.close()
        return {"ok": False, "pesan": "Transaksi tidak ditemukan."}
        
    try:
        conn.execute("DELETE FROM sponsorship_transaksi WHERE id = ?", (transaksi_id,))
        conn.commit()
        return {"ok": True, "pesan": "Transaksi berhasil dihapus."}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "pesan": f"Gagal menghapus transaksi: {str(e)}"}
'''
    # Append to the end
    with open(service_path, 'a', encoding='utf-8') as f:
        f.write(delete_func)
    print("service.py patched.")

# 2. Patch routes.py
routes_path = r'C:\Financehub\app\modules\sponsorship\routes.py'
with open(routes_path, 'r', encoding='utf-8') as f:
    routes_content = f.read()

if 'delete_transaksi' not in routes_content:
    routes_content = routes_content.replace(
        'create_transaksi, create_transaksi_bulk, get_transaksi,',
        'create_transaksi, create_transaksi_bulk, get_transaksi, delete_transaksi,'
    )
    routes_content = routes_content.replace(
        'create_transaksi, get_transaksi,',
        'create_transaksi, get_transaksi, delete_transaksi,'
    )
    
    route_func = '''
@bp.route("/data/<int:id>/delete", methods=["POST"])
@jwt_html_required
def data_delete(id):
    result = delete_transaksi(id, _cid() if not _wrong_company() else None)
    return jsonify(result)
'''
    # Find @bp.route("/data/<int:id>/update", methods=["POST"])
    import re
    if re.search(r'@bp\.route\("/data/<int:id>/update"', routes_content):
        # Insert before it
        routes_content = re.sub(r'(@bp\.route\("/data/<int:id>/update")', route_func.strip() + r'\n\n\1', routes_content)
    else:
        # Just append
        routes_content += route_func
        
    with open(routes_path, 'w', encoding='utf-8') as f:
        f.write(routes_content)
    print("routes.py patched.")

# 3. Patch data.html
data_html_path = r'C:\Financehub\app\templates\sponsorship\data.html'
with open(data_html_path, 'r', encoding='utf-8') as f:
    data_html = f.read()

if 'Hapus Transaksi' not in data_html:
    search_str = '''<button type="button" style="background:transparent; border:1px solid var(--sl-300); color:var(--text-muted); padding:0.6rem 1.5rem; border-radius:8px; font-weight:600; cursor:pointer;" onclick="closeModal('sp-edit-modal')"'''
    replace_str = '''<button type="button" style="background:var(--red-500, #ef4444); border:none; color:white; padding:0.6rem 1.5rem; border-radius:8px; font-weight:600; cursor:pointer; margin-right:auto;" onclick="sponsorshipDataDelete()" onmouseover="this.style.background='var(--red-600, #dc2626)'" onmouseout="this.style.background='var(--red-500, #ef4444)'">Hapus Transaksi</button>\n        ''' + search_str
    
    new_html = data_html.replace(search_str, replace_str)
    with open(data_html_path, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print("data.html patched.")

# 4. Patch sponsorship.js
js_path = r'C:\Financehub\app\static\js\sponsorship.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

if 'function sponsorshipDataDelete' not in js_content:
    js_func = '''
function sponsorshipDataDelete() {
  const id = document.getElementById("sp-ed-id").value;
  if (!id) return;
  if (!confirm("Apakah Anda yakin ingin menghapus transaksi ini?")) return;
  
  showLoading("Menghapus transaksi...");
  apiFetch("/sponsorship/data/" + id + "/delete", { method: "POST" })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      showToast(data.pesan, data.ok ? "success" : "error");
      if (data.ok) { closeModal("sp-edit-modal"); setTimeout(function () { window.location.reload(); }, 1000); }
    })
    .catch(function () { showToast("Gagal menghapus transaksi.", "error"); })
    .finally(function () { hideLoading(); });
}
'''
    # insert before sponsorshipDataSave
    js_content = js_content.replace('function sponsorshipDataSave()', js_func.strip() + '\n\nfunction sponsorshipDataSave()')
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)
    print("sponsorship.js patched.")
