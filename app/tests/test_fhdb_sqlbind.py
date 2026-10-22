from fhdb.sqlbind import bind, split_script
from fhdb.errors import ProgrammingError
import pytest, datetime

def test_bind_literals():
    assert bind("select ?, ?, ?, ?", (None, 3, 1.5, "O'Neil; --")) == \
        "select NULL, 3, 1.5, 'O''Neil; --'"

def test_bind_bool_as_int_like_sqlite():
    assert bind("select ?", (True,)) == "select 1"

def test_bind_dates_as_iso_text():
    assert bind("select ?", (datetime.date(2026, 10, 22),)) == "select '2026-10-22'"
    assert bind("select ?", (datetime.datetime(2026, 10, 22, 9, 5, 1),)) == "select '2026-10-22 09:05:01'"

def test_question_mark_inside_quotes_untouched():
    assert bind("select '?' as q, ?", (1,)) == "select '?' as q, 1"

def test_param_count_mismatch():
    with pytest.raises(ProgrammingError):
        bind("select ?, ?", (1,))

def test_split_script_ignores_semicolons_in_quotes():
    assert split_script("create table a(x text default ';'); insert into a values ('a;b');") == \
        ["create table a(x text default ';')", "insert into a values ('a;b')"]


# --- tambahan di luar brief: kasus tepi ---

def test_bind_question_mark_in_identifier_and_comment_untouched():
    assert bind('select "a?" , ? -- tanya?\n', (2,)) == 'select "a?" , 2 -- tanya?\n'

def test_bind_unicode_text_utf8():
    assert bind("select ?", ("Rp é 中文",)) == "select 'Rp é 中文'"

def test_bind_backslash_not_doubled_standard_conforming_strings():
    bs = chr(92)
    assert bind("select ?", ("a" + bs + "b",)) == "select 'a" + bs + "b'"

def test_bind_none_params_and_too_many_params():
    assert bind("select 1", None) == "select 1"
    with pytest.raises(ProgrammingError):
        bind("select ?", (1, 2))

def test_bind_bytes_rejected():
    with pytest.raises(ProgrammingError):
        bind("select ?", (b"x",))

def test_programming_error_is_sqlite_subclass():
    import sqlite3
    with pytest.raises(sqlite3.ProgrammingError):
        bind("select ?", ())

def test_split_script_drops_empty_and_comment_only_parts():
    assert split_script("-- header;\nselect 1;;\n  ;select 2 -- x;y\n") == ["select 1", "select 2"]
