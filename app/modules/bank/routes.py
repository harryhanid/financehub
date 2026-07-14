from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.bank.service import (
    get_setf_rows, split_by_status, compute_running_balance,
    get_available_years, resolve_period, filter_period,
)

bp = Blueprint("bank", __name__, url_prefix="/bank")

MONTH_NAMES = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def _ctx():
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


def _cid():
    return session.get("company_id")


@bp.route("/")
@jwt_html_required
def index():
    cid = _cid()
    if not cid:
        return redirect(url_for("dashboard.select_company"))
    rows = get_setf_rows(cid)
    open_rows, complete_rows = split_by_status(rows)
    balance = compute_running_balance(complete_rows)
    years = get_available_years(cid)
    bulan, tahun = resolve_period(request.args.get("bulan"), request.args.get("tahun"))
    display_rows = filter_period(balance["rows"], bulan, tahun)

    return render_template(
        "bank/index.html",
        active_page="bank",
        open_rows=open_rows,
        display_rows=display_rows,
        saldo_current=balance["saldo_current"],
        total_pemasukan=balance["total_pemasukan"],
        total_pengeluaran=balance["total_pengeluaran"],
        years=years,
        selected_bulan=bulan,
        selected_tahun=tahun,
        month_names=MONTH_NAMES,
        **_ctx(),
    )
