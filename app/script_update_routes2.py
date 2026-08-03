path = r"C:\Financehub\app\modules\sponsorship\routes.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

new_routes = """
@bp.route("/data/export")
@jwt_html_required
@smt_company_required
def export_data_route():
    from modules.sponsorship.exports import export_data_excel
    filters = _parse_filters()
    xls_bytes = export_data_excel(_cid(), filters)
    import io
    from flask import send_file
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Sponsorship_Data.xlsx"
    )

@bp.route("/outstanding/export")
@jwt_html_required
@smt_company_required
def export_outstanding_route():
    from modules.sponsorship.exports import export_outstanding_excel
    filters = _parse_filters()
    xls_bytes = export_outstanding_excel(_cid(), filters)
    import io
    from flask import send_file
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Sponsorship_Outstanding.xlsx"
    )
"""

c += new_routes
with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done")
