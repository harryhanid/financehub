# modules/etf_payment_application/routes.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.etf_payment_application.service import (
    get_pa_list, create_pa, update_pa, get_pa_lines, get_siswa_autocomplete,
)
import config

bp = Blueprint("etf_payment_application", __name__, url_prefix="/etf-payment-application")


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


@bp.route("/")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))
    company_id = session["company_id"]
    pa_list = get_pa_list(company_id)
    return render_template(
        "etf_payment_application/index.html",
        pa_list=pa_list,
        cat1=config.CAT1_BGT,
        cat2_sem=config.CAT2_SEM,
        active_page="etf_payment_app",
        **_ctx(),
    )


@bp.route("/siswa-search")
@jwt_html_required
def siswa_search():
    q          = request.args.get("q", "")
    company_id = session.get("company_id")
    return jsonify(get_siswa_autocomplete(company_id, q))


@bp.route("/create", methods=["POST"])
@jwt_html_required
def create():
    company_id = session.get("company_id")
    data       = request.get_json(force=True)
    header = {
        "tgl_payment_application": data.get("tgl_payment_application", ""),
        "tgl_surat_pengajuan":     data.get("tgl_surat_pengajuan", ""),
        "keterangan":              data.get("keterangan", ""),
    }
    lines = data.get("lines", [])
    return jsonify(create_pa(company_id, header, lines))


@bp.route("/<int:pa_id>/update", methods=["POST"])
@jwt_html_required
def update(pa_id):
    company_id = session.get("company_id")
    data       = request.get_json(force=True)
    return jsonify(update_pa(pa_id, company_id, data))


@bp.route("/<int:pa_id>/lines")
@jwt_html_required
def lines(pa_id):
    company_id = session.get("company_id")
    return jsonify(get_pa_lines(pa_id, company_id))
