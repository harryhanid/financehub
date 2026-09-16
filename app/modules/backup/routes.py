import os
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, session
from auth.middleware import jwt_html_required
from flask_jwt_extended import get_jwt
from werkzeug.utils import secure_filename
from modules.backup.service import list_directory, create_directory, delete_item, secure_path

bp = Blueprint("backup", __name__, url_prefix="/backup")

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

@bp.route("/", methods=["GET", "POST"])
@jwt_html_required
def index():
    current_path = request.args.get("path", "")
    try:
        items = list_directory(current_path)
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("backup.index"))

    return render_template(
        "backup/index.html",
        active_page="backup",
        use_unified_header=True,
        items=items,
        current_path=current_path,
        **_ctx()
    )

@bp.route("/create_folder", methods=["POST"])
@jwt_html_required
def create_folder():
    current_path = request.form.get("path", "")
    folder_name = request.form.get("folder_name", "").strip()
    
    if folder_name:
        new_path = os.path.join(current_path, folder_name).replace("\\", "/")
        try:
            create_directory(new_path)
            flash("Folder created successfully.", "success")
        except Exception as e:
            flash(f"Error creating folder: {e}", "danger")
            
    return redirect(url_for("backup.index", path=current_path))

@bp.route("/upload", methods=["POST"])
@jwt_html_required
def upload():
    current_path = request.form.get("path", "")
    if "file" not in request.files:
        flash("No file part", "danger")
        return redirect(url_for("backup.index", path=current_path))
        
    file = request.files["file"]
    if file.filename == "":
        flash("No selected file", "danger")
        return redirect(url_for("backup.index", path=current_path))
        
    if file:
        filename = secure_filename(file.filename)
        rel_path = os.path.join(current_path, filename).replace("\\", "/")
        try:
            target_path = secure_path(rel_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            file.save(str(target_path))
            flash("File uploaded successfully.", "success")
        except Exception as e:
            flash(f"Error uploading file: {e}", "danger")
            
    return redirect(url_for("backup.index", path=current_path))

@bp.route("/download")
@jwt_html_required
def download():
    file_path = request.args.get("path", "")
    if not file_path:
        flash("No file specified", "danger")
        return redirect(url_for("backup.index"))
        
    try:
        target = secure_path(file_path)
        if target.is_dir():
            flash("Cannot download a directory directly", "danger")
            return redirect(url_for("backup.index", path=os.path.dirname(file_path)))
            
        return send_file(target, as_attachment=True)
    except Exception as e:
        flash(f"Error downloading file: {e}", "danger")
        return redirect(url_for("backup.index"))

@bp.route("/delete", methods=["POST"])
@jwt_html_required
def delete():
    file_path = request.form.get("path", "")
    parent_path = os.path.dirname(file_path).replace("\\", "/") if file_path else ""
    
    if not file_path:
        flash("No file specified for deletion", "danger")
        return redirect(url_for("backup.index", path=parent_path))
        
    try:
        delete_item(file_path)
        flash("Item deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting item: {e}", "danger")
        
    return redirect(url_for("backup.index", path=parent_path))
