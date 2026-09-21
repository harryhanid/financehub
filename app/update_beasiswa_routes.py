import re

with open("C:/Financehub/app/modules/beasiswa/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace index() route
old_index = """@bp.route("/")
@jwt_html_required
def index():
    if not _cid():
        return redirect(url_for("dashboard.select_company"))
    wrong_company = _wrong_company()"""

new_index = """@bp.route("/")
def index():
    tab = request.args.get("tab")
    
    # Intercept public access for sahabat tab
    if tab == "sahabat":
        if session.get("public_sahabat_access"):
            return render_template("sahabat_etf/public_index.html")
            
        try:
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request()
        except Exception:
            return redirect(url_for("sahabat_etf.public_login"))
    else:
        try:
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request()
        except Exception:
            return redirect(url_for("auth.login_page"))

    if not _cid():
        return redirect(url_for("dashboard.select_company"))
    wrong_company = _wrong_company()"""

content = content.replace(old_index, new_index)

with open("C:/Financehub/app/modules/beasiswa/routes.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated beasiswa/routes.py")
