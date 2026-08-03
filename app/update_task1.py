path_routes = r"C:\Financehub\app\modules\sponsorship\routes.py"
with open(path_routes, "r", encoding="utf-8") as f:
    routes = f.read()

import re

new_parse = """def _parse_filters():
    filters = {}
    for key in ("cat1", "cat2", "cat4", "description", "status"):
        val = request.args.get(key)
        if val:
            filters[key] = val

    for key in ("cat", "cat3"):
        vals = [v for v in request.args.getlist(key) if v.strip()]
        if vals:
            filters[key] = vals

    tahun_vals = [y for y in request.args.getlist("tahun") if y.strip()]
    if tahun_vals:
        filters["tahun"] = tahun_vals

    return filters"""

routes = re.sub(r'def _parse_filters\(\):.*?return filters', new_parse, routes, flags=re.DOTALL)
with open(path_routes, "w", encoding="utf-8") as f:
    f.write(routes)


path_service = r"C:\Financehub\app\modules\sponsorship\service.py"
with open(path_service, "r", encoding="utf-8") as f:
    service = f.read()

old_apply = """    if filters.get("cat"):
        query += " AND cat = ?"
        params.append(filters["cat"])
    if filters.get("cat3"):
        query += " AND cat3 = ?"
        params.append(filters["cat3"])"""
        
new_apply = """    if filters.get("cat"):
        cats = filters["cat"]
        if isinstance(cats, list) and cats:
            placeholders = ",".join(["?"] * len(cats))
            query += f" AND cat IN ({placeholders})"
            params.extend(cats)
        else:
            query += " AND cat = ?"
            params.append(cats)
    if filters.get("cat3"):
        pillars = filters["cat3"]
        if isinstance(pillars, list) and pillars:
            placeholders = ",".join(["?"] * len(pillars))
            query += f" AND cat3 IN ({placeholders})"
            params.extend(pillars)
        else:
            query += " AND cat3 = ?"
            params.append(pillars)"""

service = service.replace(old_apply, new_apply)
with open(path_service, "w", encoding="utf-8") as f:
    f.write(service)

print("done")
