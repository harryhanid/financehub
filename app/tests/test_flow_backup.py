import os
import datetime
import pytest
import config
import tasks.flow_backup as flow_backup
from tasks.flow_backup import _cleanup_old_files


def test_cleanup_keeps_recent_and_removes_old_files(tmp_path):
    today = datetime.datetime.now()
    recent = today - datetime.timedelta(days=3)
    old = today - datetime.timedelta(days=8)

    recent_path = tmp_path / f"{recent.strftime('%Y-%m-%d')}.xlsx"
    old_path = tmp_path / f"{old.strftime('%Y-%m-%d')}.xlsx"
    recent_path.write_text("recent")
    old_path.write_text("old")

    _cleanup_old_files(str(tmp_path), keep_days=5)

    assert recent_path.exists()
    assert not old_path.exists()


def test_cleanup_ignores_files_that_dont_match_date_pattern(tmp_path):
    junk_path = tmp_path / "not-a-date.xlsx"
    junk_path.write_text("junk")

    _cleanup_old_files(str(tmp_path), keep_days=5)

    assert junk_path.exists()


def test_cleanup_handles_prefix_and_suffix_for_sqlite_naming(tmp_path):
    today = datetime.datetime.now()
    old = today - datetime.timedelta(days=15)

    recent_path = tmp_path / f"finance_hub_{today.strftime('%Y-%m-%d')}.db"
    old_path = tmp_path / f"finance_hub_{old.strftime('%Y-%m-%d')}.db"
    recent_path.write_text("recent")
    old_path.write_text("old")

    _cleanup_old_files(str(tmp_path), keep_days=10, prefix="finance_hub_", suffix=".db")

    assert recent_path.exists()
    assert not old_path.exists()


def test_run_excel_backups_writes_files_for_every_registry_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_ROOT", str(tmp_path))
    flow_backup.run_excel_backups()

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    for entry in flow_backup.BACKUP_REGISTRY:
        company_name = next(c["name"] for c in config.COMPANIES if c["code"] == entry["company"])
        expected = tmp_path / company_name / entry["module"] / entry["submodule"] / f"{today_str}.xlsx"
        assert expected.exists(), f"missing backup for {entry['company']}/{entry['module']}/{entry['submodule']}"
        assert expected.stat().st_size > 0


def test_one_failing_entry_does_not_block_the_rest(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_ROOT", str(tmp_path))

    def _broken(company_id):
        raise RuntimeError("simulated export failure")

    fake_registry = [
        {"company": "ETF", "module": "Broken", "submodule": "Sub", "export_fn": _broken},
        {"company": "ETF", "module": "Working", "submodule": "Sub", "export_fn": lambda cid: b"ok"},
    ]
    monkeypatch.setattr(flow_backup, "BACKUP_REGISTRY", fake_registry)
    flow_backup.run_excel_backups()

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    working_file = tmp_path / "Eka Tjipta Foundation" / "Working" / "Sub" / f"{today_str}.xlsx"
    broken_dir = tmp_path / "Eka Tjipta Foundation" / "Broken" / "Sub"
    assert working_file.exists()
    assert working_file.read_bytes() == b"ok"
    assert not broken_dir.exists() or not any(broken_dir.iterdir())


def test_run_sqlite_backup_copies_db_to_dsqlite_backup_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_ROOT", str(tmp_path))
    flow_backup.run_sqlite_backup()

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    expected = tmp_path / "Dsqlite Backup" / f"finance_hub_{today_str}.db"
    assert expected.exists()
    assert expected.read_bytes() == open(config.DB_PATH, "rb").read()


def test_run_sqlite_backup_prunes_files_older_than_ten_days(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_ROOT", str(tmp_path))
    backup_dir = tmp_path / "Dsqlite Backup"
    backup_dir.mkdir(parents=True)
    old_date = datetime.datetime.now() - datetime.timedelta(days=11)
    old_file = backup_dir / f"finance_hub_{old_date.strftime('%Y-%m-%d')}.db"
    old_file.write_text("stale backup")

    flow_backup.run_sqlite_backup()

    assert not old_file.exists()


def test_run_flow_backups_runs_both_excel_and_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_ROOT", str(tmp_path))
    flow_backup.run_flow_backups()

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    assert (tmp_path / "Dsqlite Backup" / f"finance_hub_{today_str}.db").exists()
    assert (tmp_path / "Eka Tjipta Foundation" / "Bank" / "Mutasi & Saldo" / f"{today_str}.xlsx").exists()


def test_app_module_no_longer_imports_the_old_excel_backup_task():
    import app as app_module
    source = open(app_module.__file__).read()
    assert "tasks.excel_backup" not in source
    assert "run_flow_backups" in source


def test_old_excel_backup_module_is_removed():
    import importlib
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("tasks.excel_backup")

