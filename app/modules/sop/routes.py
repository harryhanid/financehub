from flask import Blueprint, render_template, request, redirect, url_for, send_file
from flask_jwt_extended import get_jwt
from werkzeug.utils import secure_filename
from auth.middleware import jwt_html_required
from modules.sop.service import list_documents, get_document, record_upload, count_perlu_verifikasi_in_file
from modules.sop.renderer import parse_docx
import os
import config

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


@bp.route("/<int:doc_id>")
@jwt_html_required
def read_page(doc_id):
    document = get_document(doc_id)
    if document is None:
        return redirect(url_for("sop.index"))
    if document["status"] == "belum_dibuat" or not document["file_path"]:
        return render_template("sop/not_available.html", document=document, **_ctx())
    full_path = os.path.join(config.SOP_STORAGE_DIR, document["file_path"])
    if not os.path.exists(full_path):
        missing = dict(document)
        missing["catatan"] = f"File tidak ditemukan di storage: {document['file_path']}"
        return render_template("sop/not_available.html", document=missing, **_ctx())
    parsed = parse_docx(full_path)
    return render_template("sop/read.html", document=document, parsed=parsed, **_ctx())


@bp.route("/<int:doc_id>/download")
@jwt_html_required
def download(doc_id):
    document = get_document(doc_id)
    if document is None or not document["file_path"]:
        return redirect(url_for("sop.index"))
    full_path = os.path.join(config.SOP_STORAGE_DIR, document["file_path"])
    if not os.path.exists(full_path):
        return redirect(url_for("sop.index"))
    return send_file(full_path, as_attachment=True, download_name=os.path.basename(full_path))


@bp.route("/<int:doc_id>/upload", methods=["POST"])
@jwt_html_required
def upload(doc_id):
    document = get_document(doc_id)
    if document is None:
        return redirect(url_for("sop.index"))

    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename.lower().endswith(".docx"):
        return redirect(url_for("sop.read_page", doc_id=doc_id))

    modul_dir = os.path.join(config.SOP_STORAGE_DIR, document["modul"])
    os.makedirs(modul_dir, exist_ok=True)

    if document["file_path"]:
        # Existing on-disk filename came from the DB, not from this request — already safe.
        filename = os.path.basename(document["file_path"])
    else:
        # First-time upload: filename is fully attacker-controlled multipart data. Sanitize it.
        filename = secure_filename(uploaded_file.filename)
        if not filename:
            # secure_filename() can return "" for adversarial input (e.g. all-unsafe chars).
            return redirect(url_for("sop.read_page", doc_id=doc_id))

    dest_path = os.path.join(modul_dir, filename)

    # Defense-in-depth: verify dest_path still resolves inside modul_dir, regardless of how
    # filename was derived above. Guards against future filename-generation changes too.
    abs_modul_dir = os.path.abspath(modul_dir)
    abs_dest_path = os.path.abspath(dest_path)
    if os.path.commonpath([abs_dest_path, abs_modul_dir]) != abs_modul_dir:
        return redirect(url_for("sop.read_page", doc_id=doc_id))

    uploaded_file.save(dest_path)

    rel_path = f"{document['modul']}/{filename}"
    verif_count = count_perlu_verifikasi_in_file(dest_path)
    claims = get_jwt()
    record_upload(doc_id, rel_path, verif_count, claims.get("username", ""))

    return redirect(url_for("sop.read_page", doc_id=doc_id))
