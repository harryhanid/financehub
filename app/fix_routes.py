routes_path = r"C:\Financehub\app\modules\beasiswa\routes.py"
with open(routes_path, "r", encoding="utf-8") as f:
    routes = f.read()

bad_block = "from modules.beasiswa.service import\nfrom format_utils import format_rupiah"
if bad_block in routes:
    routes = routes.replace(bad_block, "from modules.beasiswa.service import")
    
if "from format_utils import format_rupiah" not in routes:
    routes = "from format_utils import format_rupiah\n" + routes

with open(routes_path, "w", encoding="utf-8") as f:
    f.write(routes)

print("Fixed beasiswa/routes.py")
