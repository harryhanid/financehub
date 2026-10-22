"""modules/payment_application/service.py di Postgres (Task 9): penomoran application_number lewat
fungsi plpgsql fn_create_payment_application (db_migrations/0004_fn_payment_application.sql)."""
import threading

import pytest

from database import get_conn
from modules.payment_application.service import create_application, get_applications

COMPANY_ID = 2


def _memo(memo_number="M-1", status="on_process", company_id=COMPANY_ID):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?, ?, ?)",
        (company_id, memo_number, status),
    )
    memo_id = cur.lastrowid
    conn.close()
    return memo_id


def _count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM payment_application").fetchone()[0]
    conn.close()
    return n


def test_create_application_numbers_sequentially_per_company():
    memo_id = _memo()
    r1 = create_application(COMPANY_ID, memo_id, "2026-07-01", "2026-07-10", "a")
    r2 = create_application(COMPANY_ID, memo_id, "2026-07-02", "2026-07-11", "b")
    assert r1["ok"] and r2["ok"]
    assert r1["application_number"] == "APP/2/2026/0001"
    assert r2["application_number"] == "APP/2/2026/0002"
    assert isinstance(r1["application_id"], int)
    assert r2["application_id"] != r1["application_id"]

    conn = get_conn()
    row = dict(conn.execute(
        "SELECT * FROM payment_application WHERE id=?", (r1["application_id"],)).fetchone())
    conn.close()
    assert row["status"] == "open"
    assert row["memo_id"] == memo_id
    assert row["submitted_at"] == "2026-07-01"
    assert row["notes"] == "a"


def test_create_application_rejects_memo_not_ready():
    memo_id = _memo(status="draft")
    r = create_application(COMPANY_ID, memo_id, "2026-07-01", "2026-07-10", "")
    assert r["ok"] is False
    assert _count() == 0


def test_create_application_atomic_on_failure():
    """Task 9 (atomic-flows.md): COUNT+1 dan INSERT satu fungsi plpgsql. Paksa INSERT gagal
    (nomor hasil COUNT+1 sudah dipakai -> UNIQUE): tidak ada baris yang tertulis."""
    memo_id = _memo()
    conn = get_conn()
    # Satu baris yang sudah memakai nomor 0002: COUNT = 1, jadi nomor berikutnya 0002 -> bentrok.
    conn.execute(
        "INSERT INTO payment_application (company_id, memo_id, application_number, status) "
        "VALUES (?, ?, 'APP/2/2026/0002', 'open')", (COMPANY_ID, memo_id))
    conn.close()
    before = _count()

    with pytest.raises(Exception):
        create_application(COMPANY_ID, memo_id, "2026-07-01", "2026-07-10", "x")

    assert _count() == before


def test_create_application_concurrent_requests_get_distinct_numbers():
    """Advisory lock per company_id: request bersamaan tidak mendapat nomor yang sama."""
    memo_id = _memo()
    n_threads = 6
    barrier = threading.Barrier(n_threads)
    results, errors = [], []

    def _worker(i):
        try:
            barrier.wait()
            results.append(create_application(COMPANY_ID, memo_id, "2026-07-01", "2026-07-10", str(i)))
        except Exception as e:  # pragma: no cover - dilaporkan lewat assert di bawah
            errors.append(e)

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    numbers = sorted(r["application_number"] for r in results)
    assert numbers == [f"APP/2/2026/{i:04d}" for i in range(1, n_threads + 1)]


def test_get_applications_filters_by_month_and_year():
    memo_id = _memo()
    create_application(COMPANY_ID, memo_id, "2026-07-01", "2026-07-10", "jul")
    create_application(COMPANY_ID, memo_id, "2026-08-03", "2026-08-10", "aug")
    create_application(COMPANY_ID, memo_id, "03/08/2026", "2026-08-10", "non-iso")

    assert [r["notes"] for r in get_applications(COMPANY_ID, month=7, year=2026)] == ["jul"]
    assert [r["notes"] for r in get_applications(COMPANY_ID, month=8)] == ["aug"]
    assert len(get_applications(COMPANY_ID)) == 3
