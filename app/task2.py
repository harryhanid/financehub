import re

# 1. Update payment_memo/exports.py
exports_path = r"C:\Financehub\app\modules\payment_memo\exports.py"
with open(exports_path, "r", encoding="utf-8") as f:
    exports = f.read()

# Add import
import_marker = "from modules.payment_memo.service import"
if "from format_utils import format_rupiah" not in exports:
    exports = exports.replace(import_marker, "from format_utils import format_rupiah\n" + import_marker)

# Remove _fmt_rp
exports = re.sub(r'def _fmt_rp\(v\) -> str:.*?return str\(v\)\n*', '', exports, flags=re.DOTALL)

# Replace call sites in exports.py
exports = exports.replace("invoice_amt = _fmt_rp(pam.get(\"total_amount\", 0))", 'invoice_amt = format_rupiah(pam.get("total_amount", 0))')
exports = exports.replace("invoice_amt = _fmt_rp(data.get(\"total_amount\", 0))", 'invoice_amt = format_rupiah(data.get("total_amount", 0))')
exports = exports.replace('fmt_amt = f"Rp {amt:,.0f}".replace(",", ".")', 'fmt_amt = format_rupiah(amt)')
exports = exports.replace('fmt_tot = f"Rp {total:,.0f}".replace(",", ".")', 'fmt_tot = format_rupiah(total)')

# Fix raw f-strings in beasiswa PA
exports = exports.replace('_p(f"{pr[\'pendidikan\']:,.0f}" if pr.get("pendidikan") else "", _s7r),', '_p(format_rupiah(pr[\'pendidikan\'], prefix="") if pr.get("pendidikan") else "", _s7r),')
exports = exports.replace('_p(f"{pr[\'tunjangan\']:,.0f}"  if pr.get("tunjangan")  else "", _s7r),', '_p(format_rupiah(pr[\'tunjangan\'], prefix="") if pr.get("tunjangan")  else "", _s7r),')
exports = exports.replace('_p(f"{pr[\'penelitian\']:,.0f}" if pr.get("penelitian") else "", _s7r),', '_p(format_rupiah(pr[\'penelitian\'], prefix="") if pr.get("penelitian") else "", _s7r),')
exports = exports.replace('_p(f"{siswa[\'total_pembayaran\']:,.0f}" if first else "", _s7r),', '_p(format_rupiah(siswa[\'total_pembayaran\'], prefix="") if first else "", _s7r),')
exports = exports.replace('_p(f"{siswa[\'sisa_pendidikan\']:,.0f}" if first else "", _s7r),', '_p(format_rupiah(siswa[\'sisa_pendidikan\'], prefix="") if first else "", _s7r),')
exports = exports.replace('_p(f"{siswa[\'sisa_tunjangan\']:,.0f}"  if first else "", _s7r),', '_p(format_rupiah(siswa[\'sisa_tunjangan\'], prefix="") if first else "", _s7r),')
exports = exports.replace('_p(f"{siswa[\'sisa_penelitian\']:,.0f}" if first else "", _s7r),', '_p(format_rupiah(siswa[\'sisa_penelitian\'], prefix="") if first else "", _s7r),')
exports = exports.replace('_p(f"{grand_total:,.0f}",', '_p(format_rupiah(grand_total, prefix=""),')

# Fix attachment table blocks
exports = exports.replace('_p(f"{pb[\'amount\']:,.0f}", _S_TD_R),', '_p(format_rupiah(pb[\'amount\'], prefix=""), _S_TD_R),')
exports = exports.replace('_p(f"{total:,.0f}", _style("totv", fontName="Helvetica-Bold", fontSize=8, alignment=2)),', '_p(format_rupiah(total, prefix=""), _style("totv", fontName="Helvetica-Bold", fontSize=8, alignment=2)),')

with open(exports_path, "w", encoding="utf-8") as f:
    f.write(exports)

# 2. Update payment_memo/service.py
service_path = r"C:\Financehub\app\modules\payment_memo\service.py"
with open(service_path, "r", encoding="utf-8") as f:
    service = f.read()

import_marker_service = "from modules.bank.service import sync_pam_to_bank_setf"
if "from format_utils import format_rupiah" not in service:
    service = service.replace(import_marker_service, import_marker_service + "\nfrom format_utils import format_rupiah")

service = service.replace('f"{item[\'amount\']:,.0f}",', 'format_rupiah(item[\'amount\'], prefix=""),')
service = service.replace('rows.append(["", "", "", "TOTAL", f"{total:,.0f}"])', 'rows.append(["", "", "", "TOTAL", format_rupiah(total, prefix="")])')

with open(service_path, "w", encoding="utf-8") as f:
    f.write(service)

print("Task 2 complete")
