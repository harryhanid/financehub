# modules/budget/exports.py
from datetime import datetime
from modules.budget.service import get_dashboard_data


def _csv_cell(v) -> str:
    if v is None:
        return '""'
    return '"' + str(v).replace('"', '""') + '"'


def export_transactions_csv(filters: dict) -> bytes:
    data = get_dashboard_data(filters)
    lines = ["Budget ID,Company,Dept,Category,Activity,GL Account,Description,Allocated,Used,Balance,Utilization %,Status,Deadline"]
    for t in data["transactions"]:
        util = f"{(t['realized'] / t['amount'] * 100):.2f}" if t["amount"] > 0 else "0.00"
        lines.append(",".join([
            _csv_cell(t["id"]), _csv_cell(t["company"]), _csv_cell(t["dept"]),
            _csv_cell(t["category"]), _csv_cell(t["activity"]), _csv_cell(t["gl_acc"]),
            _csv_cell(t["desc"]), str(t["amount"]), str(t["realized"]), str(t["balance"]),
            util, _csv_cell(t["status"]), _csv_cell(t["deadline"]),
        ]))
    return ("\n".join(lines) + "\n").encode("utf-8-sig")


def export_realization_csv(filters: dict) -> bytes:
    data = get_dashboard_data(filters)
    lines = ["Trx ID,Budget ID,Date,Company,Dept,Category,Activity,Description,Amount"]
    for r in data["realizations"]:
        lines.append(",".join([
            _csv_cell(r["trx_id"]), _csv_cell(r["budget_id"]), _csv_cell(r["tanggal_realisasi"]),
            _csv_cell(r["company"]), _csv_cell(r["dept"]), _csv_cell(r["budget_category"]),
            _csv_cell(r["activity"]), _csv_cell(r["description"]), str(r["amount"]),
        ]))
    return ("\n".join(lines) + "\n").encode("utf-8-sig")


def export_department_report_csv(filters: dict) -> bytes:
    data = get_dashboard_data(filters)
    by_dept = {}
    for t in data["transactions"]:
        dept = t["dept"] or "(unset)"
        if dept not in by_dept:
            by_dept[dept] = {"budget": 0, "realized": 0, "count": 0, "expired": 0}
        by_dept[dept]["budget"] += t["amount"]
        by_dept[dept]["realized"] += t["realized"]
        by_dept[dept]["count"] += 1
        if t["status"] == "Expired":
            by_dept[dept]["expired"] += 1
    lines = ["Department,Total Budget,Total Realized,Remaining,Budget Count,Expired Count,Utilization %"]
    for dept, v in by_dept.items():
        util = f"{(v['realized'] / v['budget'] * 100):.2f}" if v["budget"] > 0 else "0.00"
        lines.append(",".join([
            _csv_cell(dept), str(v["budget"]), str(v["realized"]), str(v["budget"] - v["realized"]),
            str(v["count"]), str(v["expired"]), util,
        ]))
    return ("\n".join(lines) + "\n").encode("utf-8-sig")


def export_expired_report_csv(filters: dict) -> bytes:
    data = get_dashboard_data(filters)
    expired = [t for t in data["transactions"] if t["status"] == "Expired"]
    lines = ["Budget ID,Company,Dept,Category,Activity,Amount,Realized,Balance,Deadline,Days Expired"]
    now = datetime.now().date()
    for t in expired:
        days = (now - datetime.fromisoformat(t["deadline"]).date()).days if t["deadline"] else 0
        lines.append(",".join([
            _csv_cell(t["id"]), _csv_cell(t["company"]), _csv_cell(t["dept"]), _csv_cell(t["category"]),
            _csv_cell(t["activity"]), str(t["amount"]), str(t["realized"]), str(t["amount"] - t["realized"]),
            _csv_cell(t["deadline"]), str(days),
        ]))
    return ("\n".join(lines) + "\n").encode("utf-8-sig")


def export_compliance_report_csv(filters: dict) -> bytes:
    data = get_dashboard_data(filters)
    lines = ["Budget ID,Type,Requested By,Request Date,Status,Approval Date,Extension Months,Additional Amount,Reason,Approved By"]
    for c in data["carryovers"]:
        lines.append(",".join([
            _csv_cell(c["budget_id"]), _csv_cell(c["type"]), _csv_cell(c["requested_by"]),
            _csv_cell(c["request_date"]), _csv_cell(c["status"]), _csv_cell(c["approval_date"]),
            str(c["extension_months"]), str(c["additional_amount"] or 0), _csv_cell(c["reason"]),
            _csv_cell(c["approved_by"]),
        ]))
    return ("\n".join(lines) + "\n").encode("utf-8-sig")
