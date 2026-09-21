route_code = """
@bp.route("/tree-data")
@jwt_html_required
def tree_data():
    from database import get_conn
    conn = get_conn()
    rows = conn.execute("SELECT code, nama, group_setf FROM siswa WHERE program='Sahabat ETF' AND group_setf != ''").fetchall()
    conn.close()

    bloodlines = {}
    partners = {}

    for code, nama, g in rows:
        g = g.strip()
        if g in ['A', 'B']:
            bloodlines[g] = {'id': g, 'code': code, 'name': nama, 'partners': [], 'children': []}
        elif '.' not in g:
            base = 'A' if (g.isdigit() and int(g) < 10) else 'B'
            partners[g] = {'id': g, 'name': nama, 'code': code, 'base': base}
        else:
            parts = g.split('.')
            last = parts[-1]
            if last == '0' * len(last):
                base = '.'.join(parts[:-1])
                partners[g] = {'id': g, 'name': nama, 'code': code, 'base': base}
            else:
                bloodlines[g] = {'id': g, 'code': code, 'name': nama, 'partners': [], 'children': []}

    for pid, p in partners.items():
        base = p['base']
        if base in bloodlines:
            bloodlines[base]['partners'].append(p)

    roots = []
    for g, b in bloodlines.items():
        if g in ['A', 'B']:
            roots.append(b)
            continue

        parts = g.split('.')
        if len(parts) == 2:
            parent_partner_id = parts[0]
        else:
            last = parts[-1]
            prefix = '.'.join(parts[:-1])
            parent_partner_id = prefix + '.' + '0'*len(last)

        parent_bloodline_id = None
        if parent_partner_id in partners:
            parent_bloodline_id = partners[parent_partner_id]['base']

        if parent_bloodline_id and parent_bloodline_id in bloodlines:
            bloodlines[parent_bloodline_id]['children'].append(b)
        else:
            roots.append(b)

    return jsonify({"ok": True, "data": roots})
"""

with open("C:/Financehub/app/modules/sahabat_etf/routes.py", "a", encoding="utf-8") as f:
    f.write(route_code)
