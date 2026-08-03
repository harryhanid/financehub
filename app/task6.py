import re

# 1. app/static/js/app.js
app_js_path = r"C:\Financehub\app\static\js\app.js"
with open(app_js_path, "r", encoding="utf-8") as f:
    app_js = f.read()

new_fmtJutaan = """
function fmtJutaan(amount) {
  const jt = (amount || 0) / 1000000;
  return jt.toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}
"""
if "function fmtJutaan" not in app_js:
    # insert after fmtRupiah
    app_js = app_js.replace('function fmtRupiah(n) {\n  return new Intl.NumberFormat("id-ID").format(n || 0);\n}', 'function fmtRupiah(n) {\n  return new Intl.NumberFormat("id-ID").format(n || 0);\n}\n' + new_fmtJutaan)
    with open(app_js_path, "w", encoding="utf-8") as f:
        f.write(app_js)

# 2. app/static/js/dashboard_beasiswa.js
db_path = r"C:\Financehub\app\static\js\dashboard_beasiswa.js"
with open(db_path, "r", encoding="utf-8") as f:
    db_js = f.read()
old_db = """function dashFmtJutaan(amount) {
  const jt = (amount || 0) / 1000000;
  return jt.toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}"""
new_db = """function dashFmtJutaan(amount) {
  return fmtJutaan(amount);
}"""
if old_db in db_js:
    db_js = db_js.replace(old_db, new_db)
    with open(db_path, "w", encoding="utf-8") as f:
        f.write(db_js)

# 3. app/static/js/sahabat_etf.js
etf_path = r"C:\Financehub\app\static\js\sahabat_etf.js"
with open(etf_path, "r", encoding="utf-8") as f:
    etf_js = f.read()
old_etf = """function setfFmtJutaan(amount) {
  const jt = (amount || 0) / 1000000;
  return jt.toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}"""
new_etf = """function setfFmtJutaan(amount) {
  return fmtJutaan(amount);
}"""
if old_etf in etf_js:
    etf_js = etf_js.replace(old_etf, new_etf)
    with open(etf_path, "w", encoding="utf-8") as f:
        f.write(etf_js)

# 4. app/static/js/sponsorship.js
sp_path = r"C:\Financehub\app\static\js\sponsorship.js"
with open(sp_path, "r", encoding="utf-8") as f:
    sp_js = f.read()

# Note: sponsorship.js was recently updated in the previous plan. Let's see if _sponsorshipFormatRupiah exists.
old_sp = """function _sponsorshipFormatRupiah(n) {
  return "Rp " + Number(n || 0).toLocaleString("id-ID");
}"""
new_sp = """function _sponsorshipFormatRupiah(n) {
  return "Rp " + fmtRupiah(n);
}"""

if old_sp in sp_js:
    sp_js = sp_js.replace(old_sp, new_sp)
    with open(sp_path, "w", encoding="utf-8") as f:
        f.write(sp_js)
else:
    print("_sponsorshipFormatRupiah not found in sponsorship.js, might have been removed already")

print("Task 6 complete")
