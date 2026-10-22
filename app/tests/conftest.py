# tests/conftest.py
import os
import shutil
import sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

# Real production SOP storage lives at config.SOP_STORAGE_DIR (app/storage/sop),
# which as of this fix contains real, migrated corporate SOP documents. Tests must
# never write into it. Point tests at an isolated directory nested under tests/,
# mirroring the DB_PATH override above.
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

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    shutil.rmtree(config.SOP_STORAGE_DIR, ignore_errors=True)
    from database import init_db
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    shutil.rmtree(config.SOP_STORAGE_DIR, ignore_errors=True)
