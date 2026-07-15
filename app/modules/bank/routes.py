import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, send_file
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.bank.service import (
    get_setf_rows, split_by_status,
    get_bank_setf_rows, compute_running_balance,
    get_available_years, resolve_period, filter_period,
    add_transaksi, update_transaksi, delete_transaksi,
)
from modules.bank.reports import build_laporan_mutasi_excel

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
    pam_rows = get_setf_rows(cid)
    open_rows, _ = split_by_status(pam_rows)
    bank_rows = get_bank_setf_rows(cid)
    balance = compute_running_balance(bank_rows)
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


@bp.route("/transaksi", methods=["POST"])
@jwt_html_required
def create_transaksi():
    cid = _cid()
    if not cid:
        return jsonify({"ok": False, "pesan": "Company belum dipilih."}), 400
    data = request.get_json(force=True) or {}
    result = add_transaksi(
        cid, data.get("tanggal"), data.get("jenis"), data.get("jumlah"), data.get("keterangan")
    )
    return jsonify(result)


@bp.route("/transaksi/<int:row_id>/update", methods=["POST"])
@jwt_html_required
def update_transaksi_route(row_id):
    cid = _cid()
    if not cid:
        return jsonify({"ok": False, "pesan": "Company belum dipilih."}), 400
    data = request.get_json(force=True) or {}
    result = update_transaksi(
        row_id, cid, data.get("tanggal"), data.get("jenis"), data.get("jumlah"), data.get("keterangan")
    )
    return jsonify(result)


@bp.route("/transaksi/<int:row_id>/delete", methods=["POST"])
@jwt_html_required
def delete_transaksi_route(row_id):
    cid = _cid()
    if not cid:
        return jsonify({"ok": False, "pesan": "Company belum dipilih."}), 400
    result = delete_transaksi(row_id, cid)
    return jsonify(result)


@bp.route("/export-laporan-mutasi")
@jwt_html_required
def export_laporan_mutasi_route():
    cid = _cid()
    if not cid:
        return redirect(url_for("dashboard.select_company"))
    xls_bytes = build_laporan_mutasi_excel(cid)
    filename = f"Laporan Mutasi Bank Sahabat ETF - {datetime.now():%Y-%m-%d}.xlsx"
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )
