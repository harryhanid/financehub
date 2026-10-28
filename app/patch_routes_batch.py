import re

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('approve_budget_request, reject_budget_request', 'approve_budget_request_batch, reject_budget_request_batch')

new_funcs = '''
@bp.route("/approval-budget", methods=["GET"])
@etf_company_required
def approval_budget_page():
    return render_template("beasiswa/approval.html", ctx=_ctx(), requests=get_budget_requests(_cid()))

@bp.route("/approval-budget/approve", methods=["POST"])
@role_required("BC", "Admin")
@etf_company_required
def approval_budget_approve():
    data = request.get_json(force=True) or {}
    req_ids = data.get("request_ids", [])
    if not req_ids:
        return jsonify({"ok": False, "pesan": "Tidak ada baris yang dipilih."})
    return jsonify(approve_budget_request_batch(_cid(), req_ids, _ctx()["current_user"]))

@bp.route("/approval-budget/reject", methods=["POST"])
@role_required("BC", "Admin")
@etf_company_required
def approval_budget_reject():
    data = request.get_json(force=True) or {}
    req_ids = data.get("request_ids", [])
    reason = data.get("reason", "").strip()
    if not req_ids:
        return jsonify({"ok": False, "pesan": "Tidak ada baris yang dipilih."})
    if not reason:
        return jsonify({"ok": False, "pesan": "Alasan penolakan wajib diisi."})
    return jsonify(reject_budget_request_batch(_cid(), req_ids, _ctx()["current_user"], reason))
'''

content = re.sub(r'(?sm)@bp\.route\("/approval-budget"\).*?def approval_budget_reject\(req_id\):.*?return jsonify\(reject_budget_request\(_cid\(\), req_id, _ctx\(\)\["current_user"\], reason\)\)', new_funcs, content)

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
