from flask import Blueprint, render_template, request, session
from auth.middleware import jwt_html_required

coming_soon_bp = Blueprint("coming_soon", __name__)

MODULES = {
    "bank":            {"label": "Bank",            "icon": "🏦", "desc": "Manajemen rekening bank perusahaan."},
    "account-payable": {"label": "Account Payable", "icon": "📋", "desc": "Hutang dan pembayaran ke vendor."},
    "advance":         {"label": "Advance",          "icon": "💳", "desc": "Uang muka karyawan dan proyek."},
    "petty-cash":      {"label": "Petty Cash",       "icon": "💰", "desc": "Kas kecil operasional."},
    "sponsorship":     {"label": "Sponsorship",      "icon": "🤝", "desc": "Pengelolaan sponsorship dan donasi."},
}


@coming_soon_bp.route("/bank")
@coming_soon_bp.route("/account-payable")
@coming_soon_bp.route("/advance")
@coming_soon_bp.route("/petty-cash")
@coming_soon_bp.route("/sponsorship")
@jwt_html_required
def coming_soon_page():
    slug = request.path.lstrip("/")
    module = MODULES.get(slug, {"label": slug.title(), "icon": "🔜", "desc": "Segera hadir."})
    return render_template("coming_soon.html",
                           module=module,
                           company_name=session.get("company_name", ""))
