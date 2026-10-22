import os

def test_local_pg_starts_and_answers(tmp_path):
    import psycopg2
    from tests.pgtest import local_pg
    dsn = local_pg.start(str(tmp_path / "data"), port=int(os.environ.get("FH_TEST_PG_PORT_LOCAL", "54331")))
    try:
        with psycopg2.connect(dsn) as c, c.cursor() as cur:
            cur.execute("select current_setting('server_version_num')::int >= 160000")
            assert cur.fetchone()[0] is True
    finally:
        local_pg.stop(str(tmp_path / "data"))
