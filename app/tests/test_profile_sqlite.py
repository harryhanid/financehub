import importlib.util
import sqlite3
from pathlib import Path


def _load_profile_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "pg_migrate" / "profile_sqlite.py"
    spec = importlib.util.spec_from_file_location("profile_sqlite", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_profile_counts_kinds_and_date_formats(tmp_path):
    db = tmp_path / "p.db"
    c = sqlite3.connect(db)
    c.execute("create table t (a TEXT, b REAL, c)")
    c.executemany("insert into t values (?,?,?)",
                  [("2025-03-15", 1.5, 1), ("15/03/2025", None, "x"), ("", 2, None)])
    c.commit(); c.close()
    prof = _load_profile_module().profile(str(db))
    assert prof["t"]["a"]["date_formats"] == {"YYYY-MM-DD": 1, "DD/MM/YYYY": 1, "empty": 1}
    assert prof["t"]["b"]["kinds"] == {"real": 2, "null": 1}  # REAL affinity stores 2 as 2.0
    assert prof["t"]["c"]["kinds"] == {"integer": 1, "text": 1, "null": 1}
