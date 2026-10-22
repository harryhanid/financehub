# tests/conftest.py
import os
import shutil
import sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config

# Database test: Postgres lokal (tests/_pg, port 54330, lihat tests/fhdb_fixtures.py) schema
# financehub_test lewat fhdb PgBackend. Skema dibangun sekali per sesi dari app/db_migrations
# (0001+0002+0002b+0003); clean_db mengosongkan semua tabel + reset identity tiap test lalu init_db().
config.DB_BACKEND = "pg"
config.DB_SCHEMA = "financehub_test"
config.FH_PG_DSN = "postgresql://postgres@127.0.0.1:54330/postgres"  # ditimpa fhdb_schema dengan DSN aktual

# Real production SOP storage lives at config.SOP_STORAGE_DIR (app/storage/sop),
# which as of this fix contains real, migrated corporate SOP documents. Tests must
# never write into it. Point tests at an isolated directory nested under tests/,
# mirroring the test-database override above.
_REAL_SOP_STORAGE_DIR = os.path.abspath(config.SOP_STORAGE_DIR)
_TEST_SOP_STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_storage_sop")
)

# Safety check: the test storage dir must never equal or contain/be-contained-by
# the real storage dir. If this ever trips, something is misconfigured and we must
# not proceed to any rmtree() call below.
assert _TEST_SOP_STORAGE_DIR != _REAL_SOP_STORAGE_DIR, (
    "Test SOP storage dir must not equal the real SOP storage dir: "
    f"{_TEST_SOP_STORAGE_DIR!r}"
)
assert not _REAL_SOP_STORAGE_DIR.startswith(_TEST_SOP_STORAGE_DIR + os.sep), (
    "Real SOP storage dir must not be nested inside the test SOP storage dir: "
    f"real={_REAL_SOP_STORAGE_DIR!r} test={_TEST_SOP_STORAGE_DIR!r}"
)
assert not _TEST_SOP_STORAGE_DIR.startswith(_REAL_SOP_STORAGE_DIR + os.sep), (
    "Test SOP storage dir must not be nested inside the real SOP storage dir: "
    f"real={_REAL_SOP_STORAGE_DIR!r} test={_TEST_SOP_STORAGE_DIR!r}"
)
print(f"[conftest] real SOP storage dir: {_REAL_SOP_STORAGE_DIR}")
print(f"[conftest] test SOP storage dir: {_TEST_SOP_STORAGE_DIR}")

config.SOP_STORAGE_DIR = _TEST_SOP_STORAGE_DIR

from app import create_app

# Fixture Postgres bersama (pg_dsn, pg_backend) untuk test fhdb.
pytest_plugins = ["tests.fhdb_fixtures"]


def pytest_configure(config):  # noqa: F811 -- `config` di sini objek pytest, bukan modul config app
    config.addinivalue_line(
        "markers",
        "contract_http: test kontrak HttpBackend ke Supabase sungguhan; hanya jalan kalau FH_CONTRACT_HTTP=1",
    )

@pytest.fixture
def app():
    application = create_app(testing=True)
    yield application

@pytest.fixture
def client(app):
    return app.test_client()

MIGRATION_FILES = ("0001_fh_exec.sql", "0002_schema.sql", "0002b_compat.sql", "0003_privileges.sql")

# Satu statement (= satu panggilan backend, satu transaksi): kosongkan semua tabel schema test dan
# reset semua sequence identity -- efek sama dengan TRUNCATE ... RESTART IDENTITY CASCADE.
# Bukan TRUNCATE karena TRUNCATE 62 tabel (+cascade) ~1,1 detik per test di Windows, DELETE ~0,01 detik.
# session_replication_role=replica (hanya transaksi ini; butuh superuser, ada di Postgres test lokal)
# mematikan trigger FK sehingga urutan delete tidak penting. Tabel diambil dinamis supaya tabel yang
# dibuat saat test (mis. tabel GL per entitas/tahun) ikut kosong.
_RESET_ALL = (
    "do 'declare r record; begin "
    "perform set_config(''session_replication_role'', ''replica'', true); "
    "for r in select tablename from pg_tables where schemaname = ''financehub_test'' loop "
    "execute format(''delete from financehub_test.%I'', r.tablename); end loop; "
    "for r in select sequencename from pg_sequences "
    "where schemaname = ''financehub_test'' and last_value is not null loop "
    "perform setval(format(''financehub_test.%I'', r.sequencename), 1, false); end loop; "
    "end'"
)


@pytest.fixture(scope="session")
def fhdb_schema(pg_dsn):
    """Schema financehub_test berisi skema FinanceHub lengkap (sekali per sesi); yield PgBackend."""
    import fhdb
    from fhdb.backends import PgBackend
    from tests.fhdb_fixtures import MIGRATIONS_DIR

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "apply_migrations",
        os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "pg_migrate", "apply_migrations.py"))
    apply_migrations = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(apply_migrations)

    config.FH_PG_DSN = pg_dsn
    fhdb._backends.clear()
    backend = PgBackend(pg_dsn)
    try:
        apply_migrations.apply(backend, config.DB_SCHEMA,
                               [os.path.join(MIGRATIONS_DIR, f) for f in MIGRATION_FILES])
        yield backend
    finally:
        backend.close()


@pytest.fixture(autouse=True)
def clean_db(fhdb_schema):
    # Pengaman: reset menghapus SEMUA baris; hanya boleh ke schema test di Postgres lokal.
    from urllib.parse import urlparse
    assert config.DB_BACKEND == "pg", f"clean_db: DB_BACKEND harus 'pg', bukan {config.DB_BACKEND!r}"
    assert config.DB_SCHEMA == "financehub_test", f"clean_db: DB_SCHEMA harus financehub_test, bukan {config.DB_SCHEMA!r}"
    assert urlparse(config.FH_PG_DSN).hostname in ("127.0.0.1", "localhost"), (
        "clean_db: FH_PG_DSN harus ke Postgres lokal (127.0.0.1/localhost)")
    fhdb_schema.execute_batch([_RESET_ALL], config.DB_SCHEMA)
    shutil.rmtree(config.SOP_STORAGE_DIR, ignore_errors=True)
    from database import init_db
    init_db()
    yield
    shutil.rmtree(config.SOP_STORAGE_DIR, ignore_errors=True)


@pytest.fixture
def auth_headers(client):
    """Login sebagai admin default (seed init_db) lewat /auth/login; header Bearer JWT akses."""
    resp = client.post("/auth/login", json={"username": "admin", "password": config.ADMIN_DEFAULT_PASSWORD})
    data = resp.get_json()
    assert data and data.get("ok"), f"login admin gagal: {data!r}"
    return {"Authorization": f"Bearer {data['access_token']}"}
