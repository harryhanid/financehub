"""Seed data referensi FinanceHub (companies, coa, coa_pam, vendors, admin default).

Idempoten: semua insert `ON CONFLICT DO NOTHING`; admin default hanya dibuat kalau belum ada user
`admin` (bcrypt cost 12, sama seperti sebelumnya). Skema TIDAK dibuat di sini: lihat app/db_migrations.
Pindahan dari database.init_db() versi SQLite; nilai seed tidak diubah.
"""
import bcrypt

import config

VENDOR_SEED = [
    ("PT. Aditunggal Mahajaya",                        "AGRI",           "5101C1POFF"),
    ("PT. Agrokarya Primalestari",                     "AGRI",           "4401C1POFF"),
    ("PT. Agrolestari Sentosa",                        "AGRI",           "4201C1POFF"),
    ("PT. Binasawit Abadi Pratama",                    "AGRI",           "3201C1POFF"),
    ("PT. Buana Artha Sejahtera",                      "AGRI",           "4501C1POFF"),
    ("PT. Buana Wiralestari Mas",                      "AGRI",           "2001C1POFF"),
    ("PT. Bumi Permai Lestari",                        "AGRI",           "2601C1POFF"),
    ("PT. Djuandasawit Lestari",                       "AGRI",           "2801C1POFF"),
    ("PT. Forestalestari Dwikarya",                    "AGRI",           "2901C1POFF"),
    ("PT. Ivo Mas Tunggal",                            "AGRI",           "1901C1POFF"),
    ("PT. Kresna Duta Agroindo",                       "AGRI",           "1101C1POFF"),
    ("PT. Maskapai Perkebunan Leidong West Indonesia", "AGRI",           "1201C1POFF"),
    ("PT. Mitrakarya Agroindo",                        "AGRI",           "3801C1POFF"),
    ("PT. Paramitra Internusa Pratama",                "AGRI",           "4701C1POFF"),
    ("PT. Ramajaya Pramukti",                          "AGRI",           "2101C1POFF"),
    ("PT. SMART Tbk",                                  "AGRI",           "1008C1POFF"),
    ("PT. Sawitakarya Manunggul",                      "AGRI",           "3401C1POFF"),
    ("PT. Sumber Indah Perkasa",                       "AGRI",           "2501C1CMOF"),
    ("PT. Tapian Nadenggan",                           "AGRI",           "1401C1POFF"),
    ("NON PILLAR",                                     "NON PILLAR",     "NON PILLAR"),
    ("NON ALLOCATED",                                  "NON ALLOCATED",  "NON ALLOCATED"),
    ("SAHABAT ETF",                                    "SETF",           "SAHABAT ETF"),
]


def seed_reference_data(conn) -> None:
    """Tulis seed lewat `conn` (fhdb.Connection): 1 panggilan cek admin + 1 batch atomik."""
    has_admin = conn.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone() is not None

    items = []
    for c in config.COMPANIES:
        items.append((
            "INSERT INTO companies (id, code, name) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
            (c["id"], c["code"], c["name"]),
        ))
    # id companies diisi eksplisit: majukan sequence identity supaya insert tanpa id tidak bentrok.
    items.append((
        "SELECT setval(pg_get_serial_sequence('companies', 'id'), "
        "(SELECT coalesce(max(id), 1) FROM companies))",
        (),
    ))
    for entry in config.COA_LIST:
        items.append((
            "INSERT INTO coa (gl_code, gl_name) VALUES (?, ?) ON CONFLICT DO NOTHING",
            (entry["gl_code"], entry["gl_name"]),
        ))
    for sr, mr, adv, exp in config.COA_PAM_SEED:
        items.append((
            "INSERT INTO coa_pam (klasifikasi_sr, klasifikasi_mr, coa_advance, coa_expense) "
            "VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING",
            (sr, mr, adv, exp),
        ))
    for name, pillar, cc in VENDOR_SEED:
        items.append((
            "INSERT INTO vendors (name, pillar, cost_center) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
            (name, pillar, cc),
        ))
    if not has_admin:
        pw_hash = bcrypt.hashpw(config.ADMIN_DEFAULT_PASSWORD.encode(), bcrypt.gensalt(12)).decode()
        items.append((
            "INSERT INTO users (username, password_hash, role, must_change_pw) "
            "VALUES ('admin', ?, 'releaser', 1) ON CONFLICT DO NOTHING",
            (pw_hash,),
        ))
    conn.batch(items)
    conn.commit()
