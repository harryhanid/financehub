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


def format_currency(num) -> str:
    if num is None:
        return "Rp 0"
    try:
        n = round(float(num))
    except (TypeError, ValueError):
        return "Rp 0"
    return "Rp " + f"{n:,}".replace(",", ".")


def _date_in_period(d: str, period_mode: str, period_month: int, period_year) -> bool:
    if period_mode == "FULL":
        return True
    if not d:
        return False
    try:
        dt = datetime.fromisoformat(d[:10])
    except ValueError:
        return False
    if period_year is not None and dt.year != period_year:
        return False
    if period_mode == "YTD":
        return dt.month <= period_month
    if period_mode == "MTD":
        return dt.month == period_month
    return True


def _month_in_period(mm, period_mode: str, period_month: int) -> bool:
    if period_mode == "FULL":
        return True
    m = int(mm or 0)
    if not m:
        return True
    if period_mode == "YTD":
        return m <= period_month
    if period_mode == "MTD":
        return m == period_month
    return True


def _build_budget_data(filters: dict) -> list:
    filters = filters or {}
    conn = get_conn()
    budget_rows = conn.execute("SELECT * FROM budget_master").fetchall()
    realisasi_rows = conn.execute(
        "SELECT budget_id, amount, tanggal_realisasi FROM budget_realisasi"
    ).fetchall()
    conn.close()

    period_mode = str(filters.get("periodMode") or "FULL").upper()
    period_month = int(filters.get("periodMonth") or datetime.now().month)
    year_filter = filters.get("year")
    period_year = int(year_filter) if year_filter and str(year_filter) != "ALL" else None

    realized_map = {}
    last_trx_map = {}
    for r in realisasi_rows:
        if not _date_in_period(r["tanggal_realisasi"], period_mode, period_month, period_year):
            continue
        realized_map[r["budget_id"]] = realized_map.get(r["budget_id"], 0) + (r["amount"] or 0)
        if r["tanggal_realisasi"]:
            last_trx_map.setdefault(r["budget_id"], []).append(r["tanggal_realisasi"])

    company = filters.get("company")
    dept = filters.get("dept")
    category = filters.get("category")
    activity = filters.get("activity")
    now = datetime.now().date()

    out = []
    for row in budget_rows:
        if company and company != "ALL" and row["company"] != company:
            continue
        if dept and dept != "ALL" and row["dept"] != dept:
            continue
        if year_filter and str(year_filter) != "ALL" and str(row["yy"]) != str(year_filter):
            continue
        if category and category != "ALL" and row["budget_category"] != category:
            continue
        if activity and activity != "ALL" and row["activity"] != activity:
            continue
        if not _month_in_period(row["mm"], period_mode, period_month):
            continue

        realized = realized_map.get(row["id"], 0)
        amount = row["amount"] or 0
        status = "Active"
        days_to_deadline = 999
        deadline_iso = row["deadline"] or ""
        if row["deadline"]:
            try:
                deadline_date = datetime.fromisoformat(row["deadline"]).date()
                days_to_deadline = (deadline_date - now).days
                if now > deadline_date and amount > realized:
                    status = "Expired"
                elif now > deadline_date and realized >= amount:
                    status = "Completed"
                elif amount > 0 and (realized / amount) >= 0.9:
                    status = "Near Limit"
            except ValueError:
                pass

        out.append({
            "id": row["id"], "mm": row["mm"], "yy": row["yy"],
            "company": row["company"], "dept": row["dept"] or "",
            "gl_acc": row["gl_account"] or "", "gl_desc": row["gl_description"] or "",
            "category": row["budget_category"] or "", "activity": row["activity"] or "",
            "desc": row["description"] or "", "amount": amount, "deadline": deadline_iso,
            "realized": realized, "balance": amount - realized, "status": status,
            "daysToDeadline": days_to_deadline,
            "utilizationRate": (realized / amount * 100) if amount > 0 else 0,
            "lastTransaction": max(last_trx_map[row["id"]]) if last_trx_map.get(row["id"]) else "",
        })
    return out


def calculate_summary(data: list) -> dict:
    total_budget = sum(d["amount"] for d in data)
    total_realized = sum(d["realized"] for d in data)
    total_expired = sum(1 for d in data if d["status"] == "Expired")
    total_near_limit = sum(1 for d in data if d["status"] == "Near Limit")
    total_completed = sum(1 for d in data if d["status"] == "Completed")
    total_active = len(data) - total_expired - total_near_limit - total_completed
    avg_util = (total_realized / total_budget * 100) if total_budget > 0 else 0
    return {
        "totalBudget": total_budget, "totalRealized": total_realized,
        "remaining": total_budget - total_realized,
        "totalExpired": total_expired, "totalNearLimit": total_near_limit,
        "totalActive": total_active, "totalCompleted": total_completed,
        "totalItems": len(data), "avgUtilization": avg_util,
        "formatted": {
            "totalBudget": format_currency(total_budget),
            "totalRealized": format_currency(total_realized),
            "remaining": format_currency(total_budget - total_realized),
            "avgUtilization": f"{avg_util:.1f}%",
        },
    }


def group_budget_vs_realized(data: list, key: str) -> dict:
    agg = {}
    for d in data:
        k = d.get(key) or "(unset)"
        if k not in agg:
            agg[k] = {"budget": 0, "realized": 0, "count": 0}
        agg[k]["budget"] += d["amount"]
        agg[k]["realized"] += d["realized"]
        agg[k]["count"] += 1
    sorted_items = sorted(agg.items(), key=lambda x: x[1]["budget"], reverse=True)
    return {
        "labels": [k for k, _ in sorted_items],
        "budget": [v["budget"] for _, v in sorted_items],
        "realized": [v["realized"] for _, v in sorted_items],
        "count": [v["count"] for _, v in sorted_items],
    }


def group_by_month(data: list) -> dict:
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    budget = [0] * 12
    realized = [0] * 12
    for d in data:
        idx = int(d["mm"] or 0) - 1
        if 0 <= idx < 12:
            budget[idx] += d["amount"]
            realized[idx] += d["realized"]
    return {"labels": months, "budget": budget, "realized": realized}


def group_by_company(data: list) -> dict:
    companies = {"PO": {"budget": 0, "realized": 0}, "TF": {"budget": 0, "realized": 0}}
    for d in data:
        if d["company"] in companies:
            companies[d["company"]]["budget"] += d["amount"]
            companies[d["company"]]["realized"] += d["realized"]
    return {
        "labels": ["PO", "TF"],
        "budget": [companies["PO"]["budget"], companies["TF"]["budget"]],
        "realized": [companies["PO"]["realized"], companies["TF"]["realized"]],
    }


def group_by_status(data: list) -> dict:
    statuses = {"Active": 0, "Near Limit": 0, "Expired": 0, "Completed": 0}
    for d in data:
        if d["status"] in statuses:
            statuses[d["status"]] += 1
    return {"labels": list(statuses.keys()), "values": list(statuses.values())}
