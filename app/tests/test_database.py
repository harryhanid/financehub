# tests/test_database.py -- database.py di atas fhdb (Postgres test schema financehub_test).
# Skema dibuat sekali per sesi oleh conftest (0001+0002+0002b+0003); clean_db mengosongkan tabel lalu init_db().
import config


def test_get_conn_is_fhdb():
    import database
    import fhdb
    assert database.get_conn is fhdb.get_conn
    c = database.get_conn()
    assert isinstance(c, fhdb.Connection)
    assert c.execute("select current_schema()").fetchone()[0] == "financehub_test"


def test_init_db_seeds_companies_and_admin():
    from database import get_conn
    c = get_conn()
    assert [tuple(r) for r in c.execute("select id, code from companies order by id")] == [(1, "SMT"), (2, "ETF")]
    assert c.execute("select role from users where username='admin'").fetchone()[0] == "releaser"


def test_init_db_admin_must_change_pw_and_bcrypt_hash():
    import bcrypt
    from database import get_conn
    row = get_conn().execute(
        "select password_hash, must_change_pw from users where username='admin'").fetchone()
    assert row["must_change_pw"] == 1
    assert bcrypt.checkpw(config.ADMIN_DEFAULT_PASSWORD.encode(), row["password_hash"].encode())


def test_init_db_seeds_reference_tables():
    from database import get_conn
    from fhdb.seed import VENDOR_SEED
    c = get_conn()
    assert c.execute("select count(*) from coa").fetchone()[0] == len({e["gl_code"] for e in config.COA_LIST})
    assert c.execute("select count(*) from coa_pam").fetchone()[0] > 0
    assert c.execute("select count(*) from vendors").fetchone()[0] == len(VENDOR_SEED)


def test_init_db_is_idempotent():
    from database import init_db, get_conn
    from fhdb.seed import VENDOR_SEED
    init_db()
    init_db()
    c = get_conn()
    assert c.execute("select count(*) from companies").fetchone()[0] == 2
    assert c.execute("select count(*) from users where username='admin'").fetchone()[0] == 1
    assert c.execute("select count(*) from vendors").fetchone()[0] == len(VENDOR_SEED)


def test_init_db_keeps_existing_admin_password():
    from database import init_db, get_conn
    c = get_conn()
    c.execute("update users set password_hash='x', must_change_pw=0 where username='admin'")
    c.commit()
    init_db()
    row = get_conn().execute("select password_hash, must_change_pw from users where username='admin'").fetchone()
    assert (row[0], row[1]) == ("x", 0)


def test_init_db_runs_no_ddl(monkeypatch):
    import database
    from fhdb.connection import Connection
    seen = []
    for name in ("execute", "executemany", "executescript", "batch"):
        orig = getattr(Connection, name)

        def spy(self, *a, _orig=orig, _name=name, **k):
            seen.append((_name, a[0]))
            return _orig(self, *a, **k)

        monkeypatch.setattr(Connection, name, spy)
    database.init_db()
    assert seen, "init_db harus menulis seed lewat fhdb"
    assert all(n != "executescript" for n, _ in seen)
    sqls = [s for n, s in seen if isinstance(s, str)]
    assert not any(s.lstrip().lower().startswith(("create", "alter", "drop")) for s in sqls)
    assert not hasattr(database, "DDL")
    assert not hasattr(database, "migrate_db")


def test_bank_setf_table_exists():
    from database import get_conn
    cols = {r[1] for r in get_conn().execute("PRAGMA table_info(bank_setf)")}
    assert cols == {
        "id", "company_id", "tanggal", "jenis", "jumlah",
        "keterangan", "source", "pam_record_id", "created_at", "updated_at",
    }


def test_rls_enabled_on_all_tables(pg_raw):
    n_off = pg_raw.scalar(
        "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace "
        "where n.nspname='financehub_test' and c.relkind='r' and not c.relrowsecurity "
        "and c.relname <> 't'")
    assert n_off == 0


def test_db_unreachable_returns_503(client, auth_headers, monkeypatch):
    import fhdb.connection, fhdb.errors
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise fhdb.errors.OperationalError("timeout")

    monkeypatch.setattr(fhdb.connection.Connection, "execute", boom)
    resp = client.get("/api/v1/payment-memo?company=SMT", headers=auth_headers)
    assert resp.status_code == 503
    assert "Database tidak terjangkau" in resp.get_json()["error"]
    assert len(calls) == 1  # handler tidak mengulang request


def test_db_unreachable_html_page_returns_503(client, auth_headers, monkeypatch):
    import fhdb.connection, fhdb.errors

    with client.session_transaction() as s:
        s["company_id"], s["company_code"], s["company_name"] = 1, "SMT", "SMT"

    def boom(*a, **k):
        raise fhdb.errors.OperationalError("timeout")

    monkeypatch.setattr(fhdb.connection.Connection, "execute", boom)
    resp = client.get("/payment-memo/", headers=auth_headers)
    assert resp.status_code == 503
    assert "text/html" in resp.content_type
    assert "Database tidak terjangkau" in resp.get_data(as_text=True)
