# tasks/flow_backup.py
import os
import datetime
import traceback

import config


def _cleanup_old_files(folder: str, keep_days: int, prefix: str = "", suffix: str = "") -> None:
    """Delete dated files in `folder` older than `keep_days`.

    Files are expected to be named `<prefix><YYYY-MM-DD><suffix>`. Anything that
    doesn't parse as a date after stripping prefix/suffix is left alone.
    """
    if not os.path.exists(folder):
        return
    now = datetime.datetime.now()
    for fname in os.listdir(folder):
        full_path = os.path.join(folder, fname)
        if not os.path.isfile(full_path):
            continue
        stem = fname
        if suffix and stem.endswith(suffix):
            stem = stem[: -len(suffix)]
        elif suffix:
            continue
        else:
            stem, _ = os.path.splitext(stem)
        
        if prefix and stem.startswith(prefix):
            stem = stem[len(prefix):]
        elif prefix:
            continue
        try:
            file_date = datetime.datetime.strptime(stem, "%Y-%m-%d")
        except ValueError:
            continue
        if (now - file_date).days > keep_days:
            os.remove(full_path)


def _pam_pillar_export(pillar: str):
    def _fn(company_id: int) -> bytes:
        from modules.payment_memo.exports import export_pam_tab_excel
        return export_pam_tab_excel(company_id, pillar=pillar)
    return _fn


def _pa_tab_export(tab: str):
    def _fn(company_id: int) -> bytes:
        from modules.etf_payment_application.service import export_pa_excel
        return export_pa_excel(company_id, tab=tab)
    return _fn


def _open_pam_export(company_id: int) -> bytes:
    from modules.payment_memo.exports import export_open_pam_excel
    return export_open_pam_excel(company_id)


def _bank_mutasi_export(company_id: int) -> bytes:
    from modules.bank.reports import build_laporan_mutasi_excel
    return build_laporan_mutasi_excel(company_id)


def _sahabat_etf_report_export(company_id: int) -> bytes:
    from modules.sahabat_etf.service import get_available_years, build_report_data
    from modules.sahabat_etf.report_xlsx import build_report_workbook
    years = get_available_years(company_id)
    year = int(years[0]) if years else datetime.datetime.now().year
    data = build_report_data(company_id, year)
    return build_report_workbook(data)


def _sponsorship_report_export(company_id: int) -> bytes:
    from modules.sponsorship.service import get_available_years
    from modules.sponsorship.exports import export_report_excel
    years = get_available_years(company_id)
    tahun = years[0] if years else str(datetime.datetime.now().year)
    return export_report_excel(company_id, tahun, "all")


BACKUP_REGISTRY = [
    {"company": "ETF", "module": "Bank", "submodule": "Mutasi & Saldo", "export_fn": _bank_mutasi_export},
    {"company": "ETF", "module": "Payment Approval Memo", "submodule": "Open PAM", "export_fn": _open_pam_export},
    {"company": "ETF", "module": "Payment Approval Memo", "submodule": "Advance", "export_fn": _pam_pillar_export("ADVANCE")},
    {"company": "ETF", "module": "Payment Approval Memo", "submodule": "AGRI", "export_fn": _pam_pillar_export("AGRI")},
    {"company": "ETF", "module": "Payment Approval Memo", "submodule": "APP", "export_fn": _pam_pillar_export("APP")},
    {"company": "ETF", "module": "Payment Approval Memo", "submodule": "LAND", "export_fn": _pam_pillar_export("LAND")},
    {"company": "ETF", "module": "Payment Approval Memo", "submodule": "SETF", "export_fn": _pam_pillar_export("SETF")},
    {"company": "ETF", "module": "Payment Application", "submodule": "AGRI", "export_fn": _pa_tab_export("agri")},
    {"company": "ETF", "module": "Payment Application", "submodule": "APP", "export_fn": _pa_tab_export("app")},
    {"company": "ETF", "module": "Payment Application", "submodule": "LAND", "export_fn": _pa_tab_export("sml")},
    {"company": "ETF", "module": "Payment Application", "submodule": "SETF", "export_fn": _pa_tab_export("setf")},
    {"company": "ETF", "module": "Beasiswa", "submodule": "Sahabat ETF", "export_fn": _sahabat_etf_report_export},
    {"company": "SMT", "module": "Payment Approval Memo", "submodule": "Open PAM", "export_fn": _open_pam_export},
    {"company": "SMT", "module": "Payment Approval Memo", "submodule": "Advance", "export_fn": _pam_pillar_export("ADVANCE")},
    {"company": "SMT", "module": "Payment Approval Memo", "submodule": "PAM List", "export_fn": _pam_pillar_export("SMT")},
    {"company": "SMT", "module": "Sponsorship", "submodule": "Report", "export_fn": _sponsorship_report_export},
]


def run_excel_backups() -> None:
    companies = {c["code"]: c for c in config.COMPANIES}
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    for entry in BACKUP_REGISTRY:
        label = f"{entry['company']}/{entry['module']}/{entry['submodule']}"
        try:
            company = companies[entry["company"]]
            target_dir = os.path.join(config.BACKUP_ROOT, company["name"], entry["module"], entry["submodule"])
            os.makedirs(target_dir, exist_ok=True)

            xlsx_bytes = entry["export_fn"](company["id"])

            filepath = os.path.join(target_dir, f"{today_str}.xlsx")
            with open(filepath, "wb") as f:
                f.write(xlsx_bytes)

            print(f"[FLOW Backup] OK: {label}")
            _cleanup_old_files(target_dir, keep_days=5)
        except Exception as e:
            print(f"[FLOW Backup] ERROR {label}: {e}")
            traceback.print_exc()


# run_sqlite_backup (salinan file SQLite ke "Dsqlite Backup") dihapus: database utama sekarang
# Postgres (Supabase), tidak ada lagi file SQLite yang perlu disalin. Backup database punya job
# sendiri (tasks/db_backup.py, plan Supabase primary DB). Job ini hanya backup Excel lewat export
# modul.
def run_flow_backups() -> None:
    run_excel_backups()
