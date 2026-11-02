# tests/test_prportal_key.py -- scripts/pg_migrate/prportal_key.py: buat/cabut kunci PR Portal.
# Backend palsu menangkap statement; tidak ada koneksi ke DB sungguhan selain Postgres test lokal.
import hashlib
import importlib.util
import json
import os
import re

import pytest

_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "pg_migrate", "prportal_key.py")


def _load():
    spec = importlib.util.spec_from_file_location("prportal_key", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeBackend:
    def __init__(self, rowcount=1):
        self.calls = []
        self.closed = False
        self._rowcount = rowcount

    def execute_batch(self, stmts, schema):
        self.calls.append((list(stmts), schema))
        return [{"rowcount": self._rowcount} for _ in stmts]

    def close(self):
        self.closed = True


def _printed_key(out):
    m = re.search(r"^FLOW_PRP_KEY=(\S+)$", out, re.M)
    assert m, out
    return m.group(1)


def test_prportal_key_inserts_hash_not_plain(capsys):
    mod = _load()
    fb = FakeBackend()
    mod.main(["--schema", "financehub_staging", "--label", "PR Portal staging"], backend=fb)
    out = capsys.readouterr().out
    key = _printed_key(out)
    assert len(key) >= 40
    assert out.count(key) == 1  # dicetak sekali
    assert len(fb.calls) == 1
    stmts, schema = fb.calls[0]
    text = json.dumps(stmts)
    assert key not in text
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", h)
    assert h in text
    assert "public.prp_keys" in text and "financehub_staging" in text and "PR Portal staging" in text
    assert schema == "financehub_staging"
    assert "Script Property" in out
    assert fb.closed


def test_prportal_key_new_key_each_run(capsys):
    mod = _load()
    mod.main(["--schema", "financehub", "--label", "a"], backend=FakeBackend())
    k1 = _printed_key(capsys.readouterr().out)
    mod.main(["--schema", "financehub", "--label", "a"], backend=FakeBackend())
    k2 = _printed_key(capsys.readouterr().out)
    assert k1 != k2


def test_prportal_key_label_quoted(capsys):
    mod = _load()
    fb = FakeBackend()
    mod.main(["--schema", "financehub", "--label", "o'brien"], backend=fb)
    assert "'o''brien'" in fb.calls[0][0][0]


def test_prportal_key_rejects_test_schema():
    mod = _load()
    with pytest.raises(SystemExit):
        mod.main(["--schema", "financehub_test", "--label", "x"], backend=FakeBackend())


def test_prportal_key_revoke(capsys):
    mod = _load()
    fb = FakeBackend(rowcount=2)
    mod.main(["--schema", "financehub", "--revoke", "PR Portal prod"], backend=fb)
    out = capsys.readouterr().out
    stmts, _ = fb.calls[0]
    assert len(stmts) == 1
    s = stmts[0].lower()
    assert s.startswith("update public.prp_keys set revoked_at = now()")
    assert "'pr portal prod'" in s and "'financehub'" in s and "revoked_at is null" in s
    assert "FLOW_PRP_KEY=" not in out and "2" in out


def test_prportal_key_requires_label_or_revoke():
    mod = _load()
    with pytest.raises(SystemExit):
        mod.main(["--schema", "financehub"], backend=FakeBackend())


def test_prportal_key_created_key_works_with_api(fhdb_schema):
    """Integrasi lokal: hash dari skrip cocok dengan hash SQL di public.prp_* (Postgres test lokal)."""
    from database import get_conn

    mod = _load()
    key = mod.create_key(fhdb_schema, "financehub_test", "uji integrasi skrip")
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    try:
        conn = get_conn()
        try:
            res = conn.execute("SELECT public.prp_search_siswa(?, ?)::text", (key, "zzz")).fetchone()[0]
        finally:
            conn.close()
        assert json.loads(res) == []
        assert mod.revoke_key(fhdb_schema, "financehub_test", "uji integrasi skrip") == 1
        conn = get_conn()
        try:
            with pytest.raises(Exception) as ei:
                conn.execute("SELECT public.prp_search_siswa(?, ?)::text", (key, "zzz")).fetchone()
        finally:
            conn.close()
        assert "42501" in str(ei.value)
    finally:
        fhdb_schema.execute_batch([f"delete from public.prp_keys where key_hash = '{h}'"], "financehub_test")
