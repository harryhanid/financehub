"""SPIKE (throwaway): uji baca/tulis/transaksi FinanceHub ke Supabase lewat HTTPS (RPC fh_spike_exec).

Jalankan setelah 01_setup.sql dijalankan di Supabase:
    python scripts/spike_https/probe.py
Tulis hanya ke fh_spike.t; financehub hanya dibaca.
"""
import http.client
import json
import statistics
import time
from urllib.parse import urlparse

from dotenv import dotenv_values
from psycopg2.extensions import adapt

ENV = dotenv_values(r"C:\FinanceHub\app\.env")
HOST = urlparse(ENV["SUPABASE_URL"]).hostname
KEY = ENV["SUPABASE_SERVICE_KEY"]
conn = http.client.HTTPSConnection(HOST, timeout=30)
# Key lama (JWT "eyJ...") juga dikirim sebagai Bearer; key baru "sb_secret_..." cukup di header apikey.
AUTH = {"apikey": KEY, **({"Authorization": f"Bearer {KEY}"} if KEY.startswith("eyJ") else {})}
print(f"project: {HOST} | jenis key: {'legacy JWT' if KEY.startswith('eyJ') else KEY.split('_')[0] + '_' + KEY.split('_')[1] if '_' in KEY else '?'}")


def bind(sql, params=()):
    """Ganti ? dengan literal SQL yang di-quote aman (pola placeholder FinanceHub)."""
    parts = sql.split("?")
    assert len(parts) == len(params) + 1, "jumlah ? tidak sama dengan params"
    out = parts[0]
    for p, rest in zip(params, parts[1:]):
        out += adapt(p).getquoted().decode() + rest
    return out


def run(stmts):
    body = json.dumps({"stmts": stmts})
    t = time.perf_counter()
    conn.request("POST", "/rest/v1/rpc/fh_spike_exec", body=body,
                 headers={**AUTH, "Content-Type": "application/json"})
    r = conn.getresponse()
    data = r.read()
    ms = (time.perf_counter() - t) * 1000
    return r.status, ms, json.loads(data) if data else None


def show(label, status, ms, data):
    print(f"{label}: HTTP {status}, {ms:.0f} ms -> {json.dumps(data, ensure_ascii=False)[:220]}")


# 0. Fungsi tersedia?
st, ms, d = run(["select 1 as ok"])
show("0. panggilan pertama (TLS)", st, ms, d)
if st != 200:
    raise SystemExit("Fungsi fh_spike_exec belum ada di project ini: cek .env menunjuk project yang benar dan 01_setup.sql sudah dijalankan.")

# 1. Latensi
lat = [run(["select 1 as ok"])[1] for _ in range(20)]
print(f"1. latensi x20: median {statistics.median(lat):.0f} ms, max {max(lat):.0f} ms")

# 2. READ data asli financehub (hanya baca)
st, ms, d = run(["select to_regclass('financehub.siswa') is not null as ada"])
if st == 200 and d[0]["rows"][0]["ada"]:
    show("2. read financehub", *run([
        "select count(*) as n_siswa from financehub.siswa",
        "select id, code, name from financehub.companies order by id",
    ]))
else:
    print("2. read financehub: schema financehub belum ada di project ini (dilewati, wajar untuk project baru)")

# 3. WRITE: insert ... returning id (pengganti lastrowid), update, select
st, ms, d = run([bind("insert into fh_spike.t (nama, jumlah, tgl) values (?, ?, ?) returning id",
                      ("O'Neil; drop table x --", 1234567.89, "2026-10-22"))])
if st != 200:
    raise SystemExit(f"insert gagal: HTTP {st} {d}")
new_id = d[0]["rows"][0]["id"]
show("3a. insert returning", st, ms, d)
show("3b. update + select", *run([
    bind("update fh_spike.t set jumlah = jumlah + 1 where id = ?", (new_id,)),
    bind("select * from fh_spike.t where id = ?", (new_id,)),
]))

# 4. TRANSAKSI: batch dengan statement gagal di tengah -> semua harus batal
before = run(["select count(*) as n from fh_spike.t"])[2][0]["rows"][0]["n"]
st, ms, d = run([
    bind("insert into fh_spike.t (nama) values (?)", ("harus-batal",)),
    "insert into fh_spike.t (nama) values (null)",  # melanggar NOT NULL
])
after = run(["select count(*) as n from fh_spike.t"])[2][0]["rows"][0]["n"]
print(f"4. batch gagal: HTTP {st}; baris sebelum={before}, sesudah={after} -> "
      f"{'ATOMIC OK' if before == after else 'TIDAK ATOMIC'}")

# 5. Batch besar: 500 insert dalam 1 panggilan
stmts = [bind("insert into fh_spike.t (nama, jumlah, tgl) values (?, ?, ?)", (f"r{i}", i * 1.5, "2026-10-22"))
         for i in range(500)]
st, ms, d = run(stmts)
print(f"5. 500 insert satu panggilan: HTTP {st}, {ms:.0f} ms")

# 6. Pola N+1: 50 query kecil, masing-masing 1 panggilan
t = time.perf_counter()
for i in range(1, 51):
    run([bind("select nama from fh_spike.t where id = ?", (i,))])
print(f"6. 50 query kecil berurutan: {(time.perf_counter() - t) * 1000:.0f} ms")

# 7. Tipe nilai yang diterima Python
row = run([bind("select id, jumlah, tgl from fh_spike.t where id = ?", (new_id,))])[2][0]["rows"][0]
print("7. tipe Python:", {k: type(v).__name__ for k, v in row.items()}, row)

# 8. Anon key tidak boleh memanggil fungsi (cek tanpa service key)
conn.request("POST", "/rest/v1/rpc/fh_spike_exec", body=json.dumps({"stmts": ["select 1"]}),
             headers={"Content-Type": "application/json"})
r = conn.getresponse(); r.read()
print(f"8. tanpa key: HTTP {r.status} (harus 401/403)")
