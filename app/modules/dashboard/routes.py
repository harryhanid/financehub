# modules/dashboard/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from database import get_conn
from modules.dashboard.service import get_etf_dashboard_data
import config

bp = Blueprint("dashboard", __name__)

DASHBOARD_TABS = [
    ("Dashboard",             "dashboard.index",               "dashboard"),
    ("Beasiswa",              "beasiswa.index",                "beasiswa"),
    ("Payment Approval Memo", "payment_memo.index",            "payment_memo"),
    ("Payment Application",   "etf_payment_application.index", "etf_payment_app"),
    ("Budget",                "budget.index",                  "budget"),
    ("Bank",                  "bank.index",                    "bank"),
    ("Sponsorship",           "sponsorship.index",             "sponsorship"),
    ("Users",                 "users.index",                   "users"),
]

# Sub-tab previews for the Alt+Down module-switcher carousel. Mirrors each
# module's own {% block module_tabs %} header markup exactly — entries use
# "tab" for the existing ?tab= deep-link (initTabs() in app.js), or "url"
# for modules whose "tabs" are actually separate routes (Budget, Sponsorship).
MODULE_SUBTABS = {
    "dashboard": [],
    "beasiswa": [
        {"label": "Dashboard",     "tab": "dashboard"},
        {"label": "Data Siswa",    "tab": "siswa"},
        {"label": "Data Budget",   "tab": "budget"},
        {"label": "Data Payment",  "tab": "payment"},
        {"label": "Report Siswa",  "tab": "laporan"},
        {"label": "Rekam Medis",   "tab": "rekam"},
        {"label": "Sahabat ETF",   "tab": "sahabat"},
    ],
    "etf_payment_app": [
        {"label": "Open PA", "tab": "summary"},
        {"label": "Advance", "tab": "advance"},
        {"label": "Input",   "tab": "input"},
        {"label": "AGRI",    "tab": "agri"},
        {"label": "APP",     "tab": "app"},
        {"label": "LAND",    "tab": "sml"},
        {"label": "SETF",    "tab": "setf"},
    ],
    "budget": [
        {"label": "Kelola Budget",         "url": "/budget/master"},
        {"label": "Kelola Realisasi",      "url": "/budget/realisasi"},
        {"label": "Carryover / Tambahan",  "url": "/budget/carryover"},
    ],
    "bank": [
        {"label": "Mutasi & Saldo", "tab": "mutasi"},
        {"label": "Open",           "tab": "open"},
    ],
    "sponsorship": [
        {"label": "Dashboard", "url": "/sponsorship/"},
        {"label": "Input",     "url": "/sponsorship/input"},
        {"label": "Data",      "url": "/sponsorship/data"},
        {"label": "Report",    "url": "/sponsorship/report"},
    ],
    "users": [],
}

PAYMENT_MEMO_SUBTABS_SMT = [
    {"label": "Open PAM",   "tab": "draft-pay"},
    {"label": "Input",      "tab": "input-payment"},
    {"label": "PAM List",   "tab": "smt"},
    {"label": "Advance",    "tab": "advance"},
    {"label": "Print Memo", "tab": "draft-memo"},
]
PAYMENT_MEMO_SUBTABS_DEFAULT = [
    {"label": "Open PAM",   "tab": "draft-pay"},
    {"label": "Input",      "tab": "input-payment"},
    {"label": "AGRI",       "tab": "pam"},
    {"label": "APP",        "tab": "fiori"},
    {"label": "LAND",       "tab": "sml"},
    {"label": "SETF",       "tab": "setf"},
    {"label": "Advance",    "tab": "pa-advance"},
    {"label": "Vendors",    "tab": "vendors"},
    {"label": "Print Memo", "tab": "draft-memo"},
]


def get_ctx():
    try:
        claims = get_jwt()
        return {
            "current_user": claims.get("username", ""),
            "current_role": claims.get("role", ""),
            "company_id":   session.get("company_id"),
            "company_code": session.get("company_code"),
            "company_name": session.get("company_name"),
        }
    except Exception:
        return {}


@bp.route("/select-company")
@jwt_html_required
def select_company():
    return render_template("company_select.html", companies=config.COMPANIES, **get_ctx())


@bp.route("/select-company", methods=["POST"])
@jwt_html_required
def select_company_post():
    company_id = request.form.get("company_id")
    chosen = next((c for c in config.COMPANIES if str(c["id"]) == str(company_id)), None)
    if not chosen:
        return redirect(url_for("dashboard.select_company"))
    session["company_id"]   = chosen["id"]
    session["company_code"] = chosen["code"]
    session["company_name"] = chosen["name"]
    return redirect(url_for("dashboard.index"))


@bp.route("/dashboard")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))

    conn       = get_conn()
    company_id = session["company_id"]
    stats      = {}
    dash       = None

    if session.get("company_code") == "ETF":
        stats["total_siswa"]   = conn.execute(
            "SELECT COUNT(*) FROM siswa WHERE company_id = ?", (company_id,)
        ).fetchone()[0]
        stats["siswa_aktif"]   = conn.execute(
            "SELECT COUNT(*) FROM siswa WHERE company_id = ? AND status = 'Aktif'", (company_id,)
        ).fetchone()[0]
        stats["total_budget"]  = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM budget_beasiswa WHERE company_id = ?", (company_id,)
        ).fetchone()[0]
        stats["total_payment"] = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM payment_beasiswa WHERE company_id = ?", (company_id,)
        ).fetchone()[0]
        conn.close()
        dash = get_etf_dashboard_data(company_id)
    else:
        stats["total_memo"] = conn.execute(
            "SELECT COUNT(*) FROM payment_memo WHERE company_id = ?", (company_id,)
        ).fetchone()[0]
        stats["memo_draft"] = conn.execute(
            "SELECT COUNT(*) FROM payment_memo WHERE company_id = ? AND status = 'open'", (company_id,)
        ).fetchone()[0]
        conn.close()

    return render_template("dashboard/index.html", stats=stats, dash=dash,
                           active_page="dashboard", use_unified_header=True, **get_ctx())
