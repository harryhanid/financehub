import re

with open("C:/Financehub/app/modules/sahabat_etf/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add new decorators
new_decorators = """
def sahabat_public_or_jwt(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("public_sahabat_access"):
            return f(*args, **kwargs)
        try:
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request()
        except Exception:
            return jsonify({"ok": False, "pesan": "Token tidak valid atau expired."}), 401
        return f(*args, **kwargs)
    return decorated

def etf_company_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("public_sahabat_access"):
            return f(*args, **kwargs)
        if session.get("company_code") != "ETF":
            return jsonify({"ok": False, "pesan": "Akses ditolak. Modul ini khusus company ETF."}), 403
        return f(*args, **kwargs)
    return decorated
"""

# Replace existing etf_company_required
content = re.sub(r'def etf_company_required\(f\):.*?return decorated\n', new_decorators, content, flags=re.DOTALL)

# 2. Replace @jwt_html_required with @sahabat_public_or_jwt
content = content.replace("@jwt_html_required", "@sahabat_public_or_jwt")

# 3. Add public_login route
public_routes = """
@bp.route("/login", methods=["GET", "POST"])
def public_login():
    if request.method == "POST":
        pwd = request.form.get("password")
        if pwd == "Sahabat88":
            session["public_sahabat_access"] = True
            return redirect(url_for("beasiswa.index", tab="sahabat"))
        else:
            return render_template("sahabat_etf/public_login.html", error="Password salah!")
    return render_template("sahabat_etf/public_login.html")
"""
content = content + "\n" + public_routes

with open("C:/Financehub/app/modules/sahabat_etf/routes.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated sahabat_etf/routes.py")
