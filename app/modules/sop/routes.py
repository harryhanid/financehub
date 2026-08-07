from flask import Blueprint, render_template, request, redirect, url_for, send_file
from flask_jwt_extended import get_jwt
from werkzeug.utils import secure_filename
from auth.middleware import jwt_html_required
from modules.sop.service import list_documents, get_document, record_upload, count_perlu_verifikasi_in_file
from modules.sop.renderer import parse_docx
import os
import tempfile
import docx
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


def _safe_storage_path(rel_path):
    """Resolve rel_path under SOP_STORAGE_DIR, returning None if it would escape."""
    full_path = os.path.abspath(os.path.join(config.SOP_STORAGE_DIR, rel_path))
    storage_root = os.path.abspath(config.SOP_STORAGE_DIR)
    if os.path.commonpath([full_path, storage_root]) != storage_root:
        return None
    return full_path


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
    full_path = _safe_storage_path(document["file_path"])
    if full_path is None or not os.path.exists(full_path):
        missing = dict(document)
        missing["catatan"] = f"File tidak ditemukan di storage: {document['file_path']}"
        return render_template("sop/not_available.html", document=missing, **_ctx())
    try:
        parsed = parse_docx(full_path)
    except Exception:
        corrupt = dict(document)
        corrupt["catatan"] = f"File tidak dapat dibaca (kemungkinan rusak): {document['file_path']}"
        return render_template("sop/not_available.html", document=corrupt, **_ctx())
    return render_template("sop/read.html", document=document, parsed=parsed, **_ctx())


@bp.route("/<int:doc_id>/download")
@jwt_html_required
def download(doc_id):
    document = get_document(doc_id)
    if document is None or not document["file_path"]:
        return redirect(url_for("sop.index"))
    full_path = _safe_storage_path(document["file_path"])
    if full_path is None or not os.path.exists(full_path):
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

    # Save to a temp file in the same directory first and validate it's a real, parseable
    # docx BEFORE touching dest_path. This avoids overwriting a real, already-uploaded
    # document with a corrupt/unparseable one that would then be unrecoverable.
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".upload_tmp", dir=modul_dir)
    os.close(tmp_fd)
    try:
        uploaded_file.save(tmp_path)
        try:
            docx.Document(tmp_path)
        except Exception:
            return redirect(url_for("sop.read_page", doc_id=doc_id))

        verif_count = count_perlu_verifikasi_in_file(tmp_path)
        os.replace(tmp_path, dest_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    rel_path = f"{document['modul']}/{filename}"
    claims = get_jwt()
    record_upload(doc_id, rel_path, verif_count, claims.get("username", ""))

    return redirect(url_for("sop.read_page", doc_id=doc_id))
