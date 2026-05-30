# modules/dashboard/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from database import get_conn
import config

bp = Blueprint("dashboard", __name__)


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

    stats["total_memo"] = conn.execute(
        "SELECT COUNT(*) FROM payment_memo WHERE company_id = ?", (company_id,)
    ).fetchone()[0]
    stats["memo_draft"] = conn.execute(
        "SELECT COUNT(*) FROM payment_memo WHERE company_id = ? AND status = 'draft'", (company_id,)
    ).fetchone()[0]
    conn.close()

    return render_template("dashboard/index.html", stats=stats, active_page="dashboard", **get_ctx())
