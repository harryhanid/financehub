path = r"C:\Financehub\app\modules\sponsorship\exports.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    '"Amount Request", "AGRI", "APP", "ENERGY & FINANCE", "PROPERTY",',
    '"Amount Request", "APP", "ENERGY", "PROPERTY", "AGRI",'
).replace(
    'r.get("amount_request"), r.get("agri"), r.get("app"), r.get("energy_finance"), r.get("property"),',
    'r.get("amount_request"), r.get("app"), r.get("energy_finance"), r.get("property"), r.get("agri"),'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done exports.py")
