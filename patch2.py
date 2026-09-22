with open('app/modules/payment_memo/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

helper = '''
def _handle_pam_attachment_upload(pam_no: str, result: dict):
    from flask import request
    if not result.get("ok"): return
    files = request.files.getlist("files")
    single_file = request.files.get("file")
    if single_file and single_file not in files:
        files.append(single_file)
    valid_files = [f for f in files if f and f.filename]
    if not valid_files: return

    folder_name = pam_no.replace('/', '-')
    from utils.gdrive_service import create_gdrive_folder, upload_file_to_gdrive
    from database import get_conn
    try:
        folder_id = create_gdrive_folder(folder_name)
        uploaded_ids = []
        for f in valid_files:
            import io
            file_stream = io.BytesIO(f.read())
            file_id = upload_file_to_gdrive(f.filename, file_stream, f.mimetype, folder_id)
            if file_id: uploaded_ids.append(file_id)
        if uploaded_ids:
            conn = get_conn()
            row = conn.execute("SELECT id, attachment_file_id FROM pam_records WHERE pam_no=?", (pam_no,)).fetchone()
            if row:
                pam_id = row[0]
                existing = row[1]
                new_val = ",".join(uploaded_ids)
                if existing: new_val = existing + "," + new_val
                conn.execute("UPDATE pam_records SET attachment_file_id=? WHERE id=?", (new_val, pam_id))
                conn.commit()
            conn.close()
    except Exception as e:
        result["pesan"] += f" (Upload GDrive gagal: {str(e)})"
'''

content = content.replace('import config, io', 'import config, io' + helper)

def replace_return(func_name, var_name):
    global content
    old = f"result = {func_name}\n    return jsonify(result)"
    new = f"result = {func_name}\n    if result.get('ok') and result.get('pam_no'):\n        _handle_pam_attachment_upload(result.get('pam_no'), result)\n    return jsonify(result)"
    content = content.replace(old, new)

# For save_pa
old_save_pa = "result = save_pa_payment(company_id, company_code, data)\n    return jsonify(result)"
new_save_pa = "result = save_pa_payment(company_id, company_code, data)\n    if result.get('ok') and result.get('pam_no'):\n        _handle_pam_attachment_upload(result.get('pam_no'), result)\n    return jsonify(result)"
content = content.replace(old_save_pa, new_save_pa)

old_save_klaim = "result = save_klaim_payment(company_id, company_code, data)\n    return jsonify(result)"
new_save_klaim = "result = save_klaim_payment(company_id, company_code, data)\n    if result.get('ok') and result.get('pam_no'):\n        _handle_pam_attachment_upload(result.get('pam_no'), result)\n    return jsonify(result)"
content = content.replace(old_save_klaim, new_save_klaim)

old_save_others = "result = save_others_payment(company_id, company_code, data)\n    return jsonify(result)"
new_save_others = "result = save_others_payment(company_id, company_code, data)\n    if result.get('ok') and result.get('pam_no'):\n        _handle_pam_attachment_upload(result.get('pam_no'), result)\n    return jsonify(result)"
content = content.replace(old_save_others, new_save_others)

old_save_smt = "result = save_smt_pam_transaction(company_id, company_code, data)\n    return jsonify(result)"
new_save_smt = "result = save_smt_pam_transaction(company_id, company_code, data)\n    if result.get('ok') and result.get('pam_no'):\n        _handle_pam_attachment_upload(result.get('pam_no'), result)\n    return jsonify(result)"
content = content.replace(old_save_smt, new_save_smt)

# For update_pam_record_route
old_update = "result   = update_pam_and_application(pam_id, pam_data, app_data, session.get(\"company_id\", 0))\n    return jsonify(result)"
new_update = """result   = update_pam_and_application(pam_id, pam_data, app_data, session.get("company_id", 0))
    if result.get('ok'):
        from database import get_conn
        conn = get_conn()
        row = conn.execute("SELECT pam_no, attachment_file_id FROM pam_records WHERE id=?", (pam_id,)).fetchone()
        if row:
            pam_no = row[0]
            existing_attachment_file_id = row[1]
            # Handle physical deletion of removed attachments
            frontend_attachments = pam_data.get("attachment_file_id", "")
            if existing_attachment_file_id:
                old_ids = [fid.strip() for fid in existing_attachment_file_id.split(",")]
                frontend_ids = [fid.strip() for fid in frontend_attachments.split(",")] if frontend_attachments else []
                deleted_ids = [fid for fid in old_ids if fid and fid not in frontend_ids]
                if deleted_ids:
                    from utils.gdrive_service import delete_gdrive_file
                    for did in deleted_ids:
                        delete_gdrive_file(did)
                        
            _handle_pam_attachment_upload(pam_no, result)
        conn.close()
    return jsonify(result)
"""
content = content.replace(old_update, new_update)

with open('app/modules/payment_memo/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)

