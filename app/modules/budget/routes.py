# modules/budget/routes.py
from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required, role_required
from modules.budget.service import (
    list_budgets, get_budget, create_budget, update_budget, delete_budget,
    list_realisasi, create_realisasi, update_realisasi, delete_realisasi,
)

bp = Blueprint("budget", __name__, url_prefix="/budget")


def _current_username() -> str:
    try:
        return get_jwt().get("username", "")
    except Exception:
        return ""


@bp.route("/master")
@jwt_html_required
def master_list():
    company = request.args.get("company")
    budgets = list_budgets({"company": company} if company else None)
    return render_template("budget/master_list.html", budgets=budgets, active_page="budget",
                            filter_company=company)


@bp.route("/master/<budget_id>")
@jwt_html_required
def master_get(budget_id):
    budget = get_budget(budget_id)
    if not budget:
        return jsonify({"ok": False, "pesan": "Budget tidak ditemukan."}), 404
    return jsonify({"ok": True, "budget": budget})


@bp.route("/master/create", methods=["POST"])
@jwt_html_required
def master_create():
    payload = request.get_json(force=True)
    result = create_budget(payload)
    return jsonify(result)


@bp.route("/master/<budget_id>/update", methods=["POST"])
@jwt_html_required
def master_update(budget_id):
    payload = request.get_json(force=True)
    result = update_budget(budget_id, payload)
    return jsonify(result)


@bp.route("/master/<budget_id>/delete", methods=["POST"])
@role_required("releaser")
def master_delete(budget_id):
    result = delete_budget(budget_id)
    return jsonify(result)


@bp.route("/realisasi")
@jwt_html_required
def realisasi_list():
    company = request.args.get("company")
    realisasi = list_realisasi({"company": company} if company else None)
    return render_template("budget/realisasi_list.html", realisasi=realisasi, active_page="budget",
                            filter_company=company)


@bp.route("/realisasi/create", methods=["POST"])
@jwt_html_required
def realisasi_create():
    payload = request.get_json(force=True)
    result = create_realisasi(payload)
    return jsonify(result)


@bp.route("/realisasi/<trx_id>/update", methods=["POST"])
@jwt_html_required
def realisasi_update(trx_id):
    payload = request.get_json(force=True)
    result = update_realisasi(trx_id, payload)
    return jsonify(result)


@bp.route("/realisasi/<trx_id>/delete", methods=["POST"])
@jwt_html_required
def realisasi_delete(trx_id):
    result = delete_realisasi(trx_id)
    return jsonify(result)
