"""Backup harian database (tasks/db_backup.py) dan pemulihan (scripts/pg_migrate/restore_backup.py)
ke Postgres test lokal schema financehub_test. Folder backup selalu di tmp_path, bukan Y:."""
import datetime
import gzip
import importlib.util
import json
import logging
from pathlib import Path

import pytest

import config
import fhdb
from tasks import db_backup
from tasks.db_backup import run_db_backup

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "financehub_test"

_spec = importlib.util.spec_from_file_location("restore_backup", ROOT / "scripts" / "pg_migrate" / "restore_backup.py")
restore_backup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(restore_backup)
restore = restore_backup.restore
verify_against_manifest = restore_backup.verify_against_manifest

REAL_DB_BACKUP_ROOT = config.DB_BACKUP_ROOT


@pytest.fixture(autouse=True)
def _never_real_backup_root(tmp_path, monkeypatch):
    """Pengaman: test di modul ini tidak pernah menulis ke Y: walau memanggil tanpa dest_root."""
    monkeypatch.setattr(config, "DB_BACKUP_ROOT", str(tmp_path / "_default_root"))


EXTRA_TABLES = [
    "create table bk_nopk (a text, b double precision)",
    "create table bk_comp (k1 text not null, k2 bigint not null, v double precision, primary key (k1, k2))",
]


@pytest.fixture
def extra_tables(pg_backend):
    pg_backend.execute_batch(["drop table if exists bk_nopk", "drop table if exists bk_comp"] + EXTRA_TABLES, SCHEMA)
    try:
        yield
    finally:
        pg_backend.execute_batch(["drop table if exists bk_nopk", "drop table if exists bk_comp"], SCHEMA)


def _rows(backend, sql):
    return backend.execute_batch([sql], SCHEMA)[0]["rows"]


def _seed(backend):
    backend.execute_batch([
        "insert into payment_memo (company_id, memo_number, total_amount, notes) values "
        "(1, 'PM-1', 1000.25, 'a''b'), (1, 'PM-2', 0.1, null), (2, 'PM-3', 2500000.75, 'x\\y \u00e9')",
        "insert into bk_nopk values ('z', 1.5), ('a', null), ('a', null), (null, 2.25), ('m', 3)",
        "insert into bk_comp values ('b', 2, 0.5), ('a', 9, 1.25), ('b', 1, 2), ('a', 1, 3)",
    ], SCHEMA)


def _read_jsonl(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_backup_restore_roundtrip(tmp_path, pg_backend, extra_tables):
    _seed(pg_backend)
    before_pm = _rows(pg_backend, "select * from payment_memo order by id")
    before_co = _rows(pg_backend, "select * from companies order by id")
    folder = run_db_backup(str(tmp_path), keep_days=30)

    assert Path(folder).name == datetime.date.today().isoformat()
    manifest = json.loads((Path(folder) / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["payment_memo"]["rows"] == 3 and manifest["companies"]["rows"] == len(before_co)
    assert manifest["payment_memo"]["columns"][:3] == ["id", "company_id", "memo_number"]
    assert "refresh_tokens" not in manifest
    assert not (Path(folder) / "refresh_tokens.jsonl.gz").exists()
    assert (Path(folder) / "0002_schema.sql").read_bytes() == (
        ROOT / "app" / "db_migrations" / "0002_schema.sql").read_bytes()
    for t in manifest:
        assert (Path(folder) / f"{t}.jsonl.gz").exists()
    assert _read_jsonl(Path(folder) / "payment_memo.jsonl.gz") == before_pm

    pg_backend.execute_batch(["truncate payment_memo, companies, bk_nopk, bk_comp restart identity cascade"], SCHEMA)
    counts = restore(folder, pg_backend, SCHEMA)
    assert counts["payment_memo"] == 3 and counts["bk_nopk"] == 5
    assert verify_against_manifest(folder, pg_backend, SCHEMA) == []
    assert _rows(pg_backend, "select * from payment_memo order by id") == before_pm
    assert _rows(pg_backend, "select * from companies order by id") == before_co
    # identity lanjut dari max(id)+1
    nxt = _rows(pg_backend, "insert into payment_memo (company_id) values (1) returning id")
    assert nxt[0][0] == 4


def test_backup_paging_orders_every_table_kind(tmp_path, pg_backend, extra_tables, monkeypatch):
    _seed(pg_backend)
    monkeypatch.setattr(db_backup, "PAGE_ROWS", 2)
    folder = Path(run_db_backup(str(tmp_path)))
    # pk satu kolom: keyset urut id
    assert [r[0] for r in _read_jsonl(folder / "payment_memo.jsonl.gz")] == [1, 2, 3]
    # pk komposit: urut (k1, k2)
    assert _read_jsonl(folder / "bk_comp.jsonl.gz") == [["a", 1, 3], ["a", 9, 1.25], ["b", 1, 2], ["b", 2, 0.5]]
    # tanpa pk: urut semua kolom, NULL terakhir (urutan default Postgres)
    assert _read_jsonl(folder / "bk_nopk.jsonl.gz") == [
        ["a", None], ["a", None], ["m", 3], ["z", 1.5], [None, 2.25]]


def test_verify_against_manifest_detects_differences(tmp_path, pg_backend, extra_tables):
    _seed(pg_backend)
    folder = run_db_backup(str(tmp_path))
    pg_backend.execute_batch(["update payment_memo set total_amount = total_amount + 0.01 where id = 1",
                              "delete from bk_nopk where a = 'z'"], SCHEMA)
    mm = verify_against_manifest(folder, pg_backend, SCHEMA)
    assert sorted((m.table, m.column or "") for m in mm) == [("bk_nopk", ""), ("bk_nopk", "b"),
                                                             ("payment_memo", "total_amount")]


def test_backup_prunes_older_than_30_days(tmp_path):
    today = datetime.date.today()
    old = tmp_path / "2026-01-01"
    old.mkdir()
    (old / "manifest.json").write_text("{}")
    recent = tmp_path / (today - datetime.timedelta(days=5)).isoformat()
    edge = tmp_path / (today - datetime.timedelta(days=30)).isoformat()
    recent.mkdir()
    edge.mkdir()
    keep = [tmp_path / "notes", tmp_path / "2026-13-45", tmp_path / "2026-01-01-extra"]
    for k in keep:
        k.mkdir()
    (tmp_path / "2026-01-02").write_text("bukan folder")

    run_db_backup(str(tmp_path), keep_days=30)

    assert not old.exists()
    assert recent.exists() and edge.exists()
    assert all(k.exists() for k in keep)
    assert (tmp_path / "2026-01-02").is_file()
    assert (tmp_path / today.isoformat() / "manifest.json").exists()


def test_backup_same_day_replaces_folder_without_partials(tmp_path, pg_backend):
    first = Path(run_db_backup(str(tmp_path)))
    (first / "stale.txt").write_text("x")
    second = Path(run_db_backup(str(tmp_path)))
    assert second == first and not (second / "stale.txt").exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == [first.name]


def test_backup_failure_keeps_previous_backups(tmp_path, monkeypatch):
    old = tmp_path / "2026-01-01"
    old.mkdir()

    def boom(*a, **k):
        raise fhdb.OperationalError("putus")

    monkeypatch.setattr(db_backup, "_dump", boom)
    with pytest.raises(fhdb.OperationalError):
        run_db_backup(str(tmp_path))
    assert old.exists()  # retensi hanya setelah backup berhasil
    assert sorted(p.name for p in tmp_path.iterdir()) == ["2026-01-01"]  # tidak ada sisa .partial


def test_default_root_from_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_BACKUP_ROOT", str(tmp_path / "root"))
    folder = run_db_backup()
    assert Path(folder).parent == tmp_path / "root"


def test_config_backup_root_value():
    assert REAL_DB_BACKUP_ROOT == r"Y:\Seagate\Flow\db-backup"


def test_scheduled_job_logs_unreachable_as_warning(monkeypatch, caplog):
    def boom(*a, **k):
        raise fhdb.OperationalError("fh_exec HTTP koneksi gagal")

    monkeypatch.setattr(db_backup, "run_db_backup", boom)
    with caplog.at_level(logging.WARNING):
        assert db_backup.scheduled_db_backup() is None
    rec = [r for r in caplog.records if "db_backup" in r.getMessage()]
    assert rec and rec[0].levelno == logging.WARNING


def test_scheduled_job_never_raises(monkeypatch, caplog):
    def boom(*a, **k):
        raise OSError("Y: tidak ada")

    monkeypatch.setattr(db_backup, "run_db_backup", boom)
    with caplog.at_level(logging.ERROR):
        assert db_backup.scheduled_db_backup() is None
    assert any(r.levelno == logging.ERROR for r in caplog.records)


def test_scheduled_job_success(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_BACKUP_ROOT", str(tmp_path))
    path = db_backup.scheduled_db_backup()
    assert path and Path(path).parent == tmp_path


class _NoTouchBackend:
    def execute_batch(self, stmts, schema):
        raise AssertionError("backend tidak boleh dipanggil")

    def close(self):
        pass


def test_restore_refuses_production_without_confirm(tmp_path):
    with pytest.raises(PermissionError) as ei:
        restore(str(tmp_path), _NoTouchBackend(), "financehub")
    assert "--confirm-production" in str(ei.value)


def test_restore_refuses_unlisted_schema(tmp_path):
    with pytest.raises(ValueError):
        restore(str(tmp_path), _NoTouchBackend(), "public")


def test_restore_cli_refuses_production(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(restore_backup.load_data, "make_backend", lambda kind, dsn: _NoTouchBackend())
    with pytest.raises(SystemExit) as ei:
        restore_backup.main(["--folder", str(tmp_path), "--schema", "financehub", "--backend", "http"])
    assert ei.value.code == 2
    assert "--confirm-production" in capsys.readouterr().err


def test_restore_rejects_corrupt_row_count(tmp_path, pg_backend):
    folder = Path(run_db_backup(str(tmp_path)))
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    m["companies"]["rows"] += 1
    (folder / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    before = _rows(pg_backend, "select count(*) from companies")
    with pytest.raises(ValueError):
        restore(str(folder), pg_backend, SCHEMA)
    assert _rows(pg_backend, "select count(*) from companies") == before  # belum ada yang ditulis
