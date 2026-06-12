def export_application_excel(company_id: int, month: int = None, year: int = None) -> bytes:
    from modules.payment_application.service import get_applications
    from modules.payment_memo.exports import _make_xlsx
    rows    = get_applications(company_id, month, year)
    headers = ["No. Application", "Memo", "Tgl Pengajuan", "Target Bayar",
               "Aktual Bayar", "Total (Rp)", "TAT (hari kerja)", "Status"]
    fields  = ["application_number", "memo_number", "submitted_at",
               "target_payment_date", "actual_payment_date", "total_amount",
               "tat_days", "status"]
    widths  = [22, 22, 14, 14, 14, 16, 16, 12]
    return _make_xlsx("Payment Application", headers, fields, rows, widths)
