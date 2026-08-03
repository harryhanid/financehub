path = r"C:\Financehub\app\modules\sponsorship\routes.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
"""def api_dashboard_data():
    data = get_dashboard_data(_cid(), _parse_filters())""",
"""def api_dashboard_data():
    filters = _parse_filters()
    cat4_mode = (request.args.get("cat4") or "all").lower()
    # Remove raw cat4 from filters to handle it via cat4_mode logic
    if "cat4" in filters: del filters["cat4"]
    data = get_dashboard_data(_cid(), filters, cat4_mode)"""
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done routes.py")
