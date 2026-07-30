import os
import datetime
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
