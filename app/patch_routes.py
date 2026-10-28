import re

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix existing routes
content = re.sub(
    r'return jsonify\(delete_budget_row\(_cid\(\), row_id\)\)',
    r'return jsonify(delete_budget_row(_cid(), row_id, _ctx()["current_user"]))',
    content
)

content = re.sub(
    r'return jsonify\(update_budget_row\(_cid\(\), row_id, request.get_json\(force=True\) or \{\}\)\)',
    r'return jsonify(update_budget_row(_cid(), row_id, request.get_json(force=True) or {}, _ctx()["current_user"]))',
    content
)

content = re.sub(
    r'return jsonify\(add_budget_batch\(_cid\(\), code,\s*data\.get\("tanggal", ""\), data\.get\("pillar", ""\), data\.get\("items", \[\]\)\)\)',
    r'return jsonify(add_budget_batch(_cid(), code, data.get("tanggal", ""), data.get("pillar", ""), data.get("items", []), _ctx()["current_user"]))',
    content
)

# Add new approval routes
new_routes = """
from modules.beasiswa.service import get_budget_requests, approve_budget_request, reject_budget_request

@bp.route("/approval-budget")
@role_required("BC", "Admin")
@etf_company_required
def approval_budget_page():
    return render_template("beasiswa/approval.html", ctx=_ctx(), requests=get_budget_requests(_cid()))

@bp.route("/approval-budget/<int:req_id>/approve", methods=["POST"])
@role_required("BC", "Admin")
@etf_company_required
def approval_budget_approve(req_id):
    return jsonify(approve_budget_request(_cid(), req_id, _ctx()["current_user"]))

@bp.route("/approval-budget/<int:req_id>/reject", methods=["POST"])
@role_required("BC", "Admin")
@etf_company_required
def approval_budget_reject(req_id):
    data = request.get_json(force=True) or {}
    reason = data.get("reason", "").strip()
    if not reason:
        return jsonify({"ok": False, "pesan": "Alasan penolakan wajib diisi."})
    return jsonify(reject_budget_request(_cid(), req_id, _ctx()["current_user"], reason))
"""
content = content.replace('from modules.beasiswa.service import (', 'from modules.beasiswa.service import get_budget_requests, approve_budget_request, reject_budget_request,\n    ')

if "@bp.route(\"/approval-budget\")" not in content:
    content += new_routes

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
