from flask import Blueprint, render_template, request
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.sop.service import list_documents, get_document, record_upload, count_perlu_verifikasi_in_file

bp = Blueprint("sop", __name__, url_prefix="/sop")

MODULES = [
    "planning-budgeting", "procurement", "finance-payment", "asset-management",
    "hr-personnel", "hr-remuneration", "it-operations", "general-admin-tax",
    "corporate-compliance", "revenue-cycle",
]


def _ctx():
    claims = get_jwt()
    return {"current_user": claims.get("username", ""), "current_role": claims.get("role", "")}


@bp.route("/")
@jwt_html_required
def index():
    search = request.args.get("q", "").strip()
    modul = request.args.get("modul", "").strip()
    status = request.args.get("status", "").strip()
    documents = list_documents(search=search or None, modul=modul or None, status=status or None)
    return render_template(
        "sop/index.html",
        documents=documents, modules=MODULES,
        search=search, modul=modul, status=status,
        **_ctx(),
    )
