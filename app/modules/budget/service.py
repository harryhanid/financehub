# modules/budget/service.py
import re
import time
import uuid
from datetime import datetime, date
from database import get_conn

VALID_COMPANIES = ("PO", "TF")


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _base36(n: int) -> str:
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if n == 0:
        return "0"
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(digits[r])
    return "".join(reversed(out))


def generate_budget_id(company: str, dept: str, mm: int, yy: int) -> str:
    dept_upper = (dept or "").upper()
    dept_code = re.sub(r"[^A-Z0-9]", "", dept_upper)[:4] or "XXX"
    ts = _base36(int(time.time() * 1000))[-5:]
    return f"{company}-{dept_code}-{str(yy)[-2:]}-{mm:02d}-{ts}"


def compute_deadline(mm: int, yy: int, expiry_months: int = 3) -> str:
    total_months = yy * 12 + (mm - 1) + expiry_months
    target_year = total_months // 12
    target_month0 = total_months % 12
    first_of_target = date(target_year, target_month0 + 1, 1)
    from datetime import timedelta
    return (first_of_target - timedelta(days=1)).isoformat()


def _apply_common_filters(query: str, params: list, filters: dict, id_col: str = "budget_id") -> tuple:
    if filters.get("company") and filters["company"] != "ALL":
        query += " AND company = ?"
        params.append(filters["company"])
    if filters.get("dept") and filters["dept"] != "ALL":
        query += " AND dept = ?"
        params.append(filters["dept"])
    if filters.get("year") and str(filters["year"]) != "ALL":
        query += " AND yy = ?"
        params.append(int(filters["year"]))
    if filters.get("category") and filters["category"] != "ALL":
        query += " AND budget_category = ?"
        params.append(filters["category"])
    if filters.get("activity") and filters["activity"] != "ALL":
        query += " AND activity = ?"
        params.append(filters["activity"])
    return query, params


def list_budgets(filters: dict = None) -> list:
    filters = filters or {}
    conn = get_conn()
    query = "SELECT * FROM budget_master WHERE 1=1"
    query, params = _apply_common_filters(query, [], filters)
    query += " ORDER BY yy DESC, mm DESC"
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return rows


def get_budget(budget_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM budget_master WHERE id = ?", (budget_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_budget(payload: dict) -> dict:
    company = payload.get("company")
    if company not in VALID_COMPANIES:
        return {"ok": False, "pesan": "Company harus PO atau TF."}
    try:
        mm = int(payload.get("mm"))
        yy = int(payload.get("yy"))
    except (TypeError, ValueError):
        return {"ok": False, "pesan": "Bulan/tahun tidak valid."}
    if not (1 <= mm <= 12):
        return {"ok": False, "pesan": "Bulan harus 1-12."}
    if yy < 2000:
        return {"ok": False, "pesan": "Tahun tidak valid."}

    dept = payload.get("dept", "")
    budget_id = generate_budget_id(company, dept, mm, yy)
    deadline = compute_deadline(mm, yy)
    try:
        amount = float(payload.get("amount") or 0)
    except (TypeError, ValueError):
        return {"ok": False, "pesan": "Jumlah tidak valid."}

    conn = get_conn()
    existing = conn.execute("SELECT id FROM budget_master WHERE id = ?", (budget_id,)).fetchone()
    if existing:
        conn.close()
        return {"ok": False, "pesan": f"Budget ID sudah ada: {budget_id}"}
    conn.execute(
        """INSERT INTO budget_master
           (id, mm, yy, company, dept, gl_account, gl_description, budget_category,
            activity, description, amount, deadline, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (budget_id, mm, yy, company, dept,
         payload.get("gl_account", ""), payload.get("gl_description", ""),
         payload.get("budget_category", ""), payload.get("activity", ""),
         payload.get("description", ""), amount, deadline, _ts())
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Budget berhasil dibuat.", "id": budget_id}


def update_budget(budget_id: str, payload: dict) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT * FROM budget_master WHERE id = ?", (budget_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Budget tidak ditemukan."}
    try:
        mm = int(payload.get("mm", row["mm"]))
        yy = int(payload.get("yy", row["yy"]))
        amount = float(payload.get("amount", row["amount"]) or 0)
    except (TypeError, ValueError):
        conn.close()
        return {"ok": False, "pesan": "Bulan/tahun/jumlah tidak valid."}
    deadline = compute_deadline(mm, yy)
    conn.execute(
        """UPDATE budget_master SET mm=?, yy=?, company=?, dept=?, gl_account=?,
           gl_description=?, budget_category=?, activity=?, description=?, amount=?,
           deadline=?, updated_at=? WHERE id=?""",
        (mm, yy, payload.get("company", row["company"]), payload.get("dept", row["dept"]),
         payload.get("gl_account", row["gl_account"]), payload.get("gl_description", row["gl_description"]),
         payload.get("budget_category", row["budget_category"]), payload.get("activity", row["activity"]),
         payload.get("description", row["description"]), amount, deadline, _ts(), budget_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Budget berhasil diupdate.", "id": budget_id}


def delete_budget(budget_id: str) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT id FROM budget_master WHERE id = ?", (budget_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Budget tidak ditemukan."}
    conn.execute("DELETE FROM budget_master WHERE id = ?", (budget_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Budget {budget_id} dihapus."}


def list_realisasi(filters: dict = None) -> list:
    filters = filters or {}
    conn = get_conn()
    query = "SELECT * FROM budget_realisasi WHERE 1=1"
    query, params = _apply_common_filters(query, [], filters)
    query += " ORDER BY tanggal_realisasi DESC"
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return rows


def create_realisasi(payload: dict) -> dict:
    budget_id = payload.get("budget_id")
    budget = get_budget(budget_id)
    if not budget:
        return {"ok": False, "pesan": f"Budget ID tidak ditemukan: {budget_id}"}
    try:
        amount = float(payload.get("amount") or 0)
    except (TypeError, ValueError):
        return {"ok": False, "pesan": "Jumlah tidak valid."}
    if amount <= 0:
        return {"ok": False, "pesan": "Jumlah harus lebih dari 0."}

    trx_id = f"TRX-{uuid.uuid4().hex[:8].upper()}"
    tanggal = payload.get("tanggal_realisasi") or datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    conn.execute(
        """INSERT INTO budget_realisasi
           (trx_id, budget_id, mm, yy, company, dept, gl_account, gl_description,
            budget_category, activity, description, amount, tanggal_realisasi, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (trx_id, budget_id, budget["mm"], budget["yy"], budget["company"], budget["dept"],
         budget["gl_account"], budget["gl_description"], budget["budget_category"],
         budget["activity"], payload.get("description") or budget["description"],
         amount, tanggal, _ts())
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Realisasi berhasil dicatat.", "trx_id": trx_id}


def update_realisasi(trx_id: str, payload: dict) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT * FROM budget_realisasi WHERE trx_id = ?", (trx_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Transaksi tidak ditemukan."}
    try:
        amount = float(payload.get("amount", row["amount"]) or 0)
    except (TypeError, ValueError):
        conn.close()
        return {"ok": False, "pesan": "Jumlah tidak valid."}
    if amount <= 0:
        conn.close()
        return {"ok": False, "pesan": "Jumlah harus lebih dari 0."}
    description = payload.get("description", row["description"])
    tanggal = payload.get("tanggal_realisasi", row["tanggal_realisasi"])
    conn.execute(
        "UPDATE budget_realisasi SET description=?, amount=?, tanggal_realisasi=? WHERE trx_id=?",
        (description, amount, tanggal, trx_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Realisasi berhasil diupdate."}


def delete_realisasi(trx_id: str) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT trx_id FROM budget_realisasi WHERE trx_id = ?", (trx_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Transaksi tidak ditemukan."}
    conn.execute("DELETE FROM budget_realisasi WHERE trx_id = ?", (trx_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Transaksi dihapus."}
