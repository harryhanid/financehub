# modules/budget/routes.py
from flask import Blueprint, render_template, request, jsonify, send_file, session
import io
from datetime import datetime as _dt
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required, role_required
from modules.budget.service import (
    list_budgets, get_budget, create_budget, update_budget, delete_budget,
    list_realisasi, create_realisasi, update_realisasi, delete_realisasi,
    get_dashboard_data, get_available_years, get_available_categories,
    get_available_departments, get_available_activities,
    request_carryover, request_additional_budget,
    approve_carryover, approve_additional_budget, reject_request,
)
from modules.budget.exports import (
    export_transactions_csv, export_realization_csv, export_department_report_csv,
    export_expired_report_csv, export_compliance_report_csv,
)

bp = Blueprint("budget", __name__, url_prefix="/budget")


def _current_username() -> str:
    try:
        return get_jwt().get("username", "")
    except Exception:
        return ""


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


@bp.route("/master")
@jwt_html_required
def master_list():
    company = request.args.get("company")
    budgets = list_budgets({"company": company} if company else None)
    return render_template("budget/master_list.html", budgets=budgets, active_page="budget",
                            filter_company=company, **_ctx())


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
                            filter_company=company, **_ctx())


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


EXPORTERS = {
    "transactions": export_transactions_csv,
    "realization": export_realization_csv,
    "department": export_department_report_csv,
    "expired": export_expired_report_csv,
    "compliance": export_compliance_report_csv,
}


def _filters_from_query():
    return {
        "company": request.args.get("company"),
        "dept": request.args.get("dept"),
        "year": request.args.get("year"),
        "category": request.args.get("category"),
        "activity": request.args.get("activity"),
        "periodMode": request.args.get("periodMode", "FULL"),
        "periodMonth": request.args.get("periodMonth", type=int),
    }


@bp.route("/")
@jwt_html_required
def index():
    return render_template("budget/dashboard.html", active_page="budget", **_ctx())


@bp.route("/api/dashboard-data")
@jwt_html_required
def api_dashboard_data():
    return jsonify(get_dashboard_data(_filters_from_query()))


@bp.route("/api/lookups")
@jwt_html_required
def api_lookups():
    return jsonify({
        "years": get_available_years(),
        "categories": get_available_categories(),
        "departments": get_available_departments(),
        "activities": get_available_activities(),
    })


@bp.route("/carryover")
@jwt_html_required
def carryover_page():
    from modules.budget.service import get_carryover_data
    return render_template("budget/carryover.html", logs=get_carryover_data(), active_page="budget", **_ctx())


@bp.route("/carryover/request", methods=["POST"])
@jwt_html_required
def carryover_request():
    payload = request.get_json(force=True)
    result = request_carryover(payload.get("budget_id"), _current_username(), payload.get("reason", ""))
    return jsonify(result)


@bp.route("/additional/request", methods=["POST"])
@jwt_html_required
def additional_request():
    payload = request.get_json(force=True)
    result = request_additional_budget(
        payload.get("budget_id"), _current_username(), payload.get("amount"), payload.get("reason", "")
    )
    return jsonify(result)


@bp.route("/carryover/<budget_id>/approve", methods=["POST"])
@role_required("releaser")
def carryover_approve(budget_id):
    payload = request.get_json(force=True)
    result = approve_carryover(budget_id, _current_username(), payload.get("extension_months"))
    return jsonify(result)


@bp.route("/additional/<budget_id>/approve", methods=["POST"])
@role_required("releaser")
def additional_approve(budget_id):
    payload = request.get_json(force=True)
    result = approve_additional_budget(budget_id, _current_username(), payload.get("extension_months"))
    return jsonify(result)


@bp.route("/carryover/<budget_id>/reject", methods=["POST"])
@role_required("releaser")
def carryover_reject(budget_id):
    payload = request.get_json(force=True)
    result = reject_request(budget_id, _current_username(), payload.get("reason", ""))
    return jsonify(result)


@bp.route("/export/<report_type>")
@jwt_html_required
def export_route(report_type):
    exporter = EXPORTERS.get(report_type)
    if not exporter:
        return jsonify({"ok": False, "pesan": f"Report type tidak dikenal: {report_type}"}), 400
    csv_bytes = exporter(_filters_from_query())
    fname = f"budget_{report_type}_{_dt.now().strftime('%Y%m%d_%H%M')}.csv"
    return send_file(io.BytesIO(csv_bytes), mimetype="text/csv", download_name=fname, as_attachment=True)
