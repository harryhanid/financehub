# C:\Financehub\app\config.py
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "finance_hub.db")

JWT_SECRET       = os.environ.get("FH_JWT_SECRET", secrets.token_hex(32))
JWT_ACCESS_HOURS = 1
JWT_REFRESH_DAYS = 7

FLASK_SECRET = os.environ.get("FH_SECRET", secrets.token_hex(32))

ADMIN_DEFAULT_PASSWORD = "Admin@123"

COMPANIES = [
    {"id": 1, "code": "SMT", "name": "Sinar Mas Tjipta"},
    {"id": 2, "code": "ETF", "name": "Eka Tjipta Foundation"},
]

JENJANG = ["SD/SMP/SMA", "S1", "S2", "S3", "SETF"]

PROGRAM = [
    "Kejaksaan", "Kejaksaan LN", "Polri", "Special Case",
    "Special Cases LN", "Tjipta Siswa Mandiri", "Bank Sinarmas",
    "IKPP", "SMART", "Tjipta Bangun Desa", "IKPP - Tjipta Bangun Desa",
    "Soci Mas", "SMMA", "Sahabat ETF", "Tjipta Sarjana Mandiri",
]

STATUS_SISWA = ["Aktif", "lulus", "gugur", "undur diri"]

PILLAR = ["AGRI", "APP", "Finance", "Mining", "Property", "ENERGY & FINANCE"]

CAT1_BGT = [
    "By Pendidikan", "By Tunjangan", "By Penelitian", "By Pendaftaran",
    "By Ujian", "By Matrikulasi", "By Daftar Ulang", "By Gedung",
    "By Wisuda", "By Orientasi", "By Registrasi", "Kelas Afirmasi",
    "Test TOEFL", "Test Kemampuan Akademik (TKA)", "By Uang Pangkal",
    "By Tugas Akhir", "By Seragam", "By Kegiatan", "By Akomodasi",
    "By Kemahasiswaan", "By Sumbangan Pembangunan", "Rawat Inap",
    "Rawat Jalan", "Tahap 1", "Tahap 2", "Tahap 3",
    "Test TPDA", "Uang Pengembangan Institusi (IPI)",
    "By Ujian Kualifikasi", "Test Kemampuan Bahasa Inggris",
    "By Medical", "By Claim Medical",
]

CAT2_SEM = [
    "Semester 1", "Semester 2", "Semester 3", "Semester 4", "Semester 5",
    "Semester 6", "Semester 7", "Semester 8", "Semester 9", "Semester 10",
    "Tahap 1", "Tahap 2", "Tahap 3",
]

KODE_JENJANG = {
    "S1": "1", "S2": "2", "S3": "3",
    "SD/SMP/SMA": "4", "SD/SMA/SMA": "4", "SETF": "5",
}

PERUSAHAAN = [
    "PT. Aditunggal Mahajaya", "PT. Agrokarya Primalestari", "AGROLESTARI MANDIRI",
    "PT. Agrolestari Sentosa", "BAHANA KARYA SEMESTA", "BANGUN NUSA MANDIRI",
    "Bank", "PT. Binasawit Abadi Pratama", "BORNEO INDOBARA", "BUANA ADHITAMA",
    "PT. Buana Artha Sejahtera", "PT. Buana Wiralestari Mas", "PT. Bumi Permai Lestari",
    "BUMI SAWIT PERMAI", "BUMIPALMA LESTARIPERSADA", "CAHAYANUSA GEMILANG",
    "Cipta Kridatama", "PT. Djuandasawit Lestari", "DSS", "PT. Forestalestari Dwikarya",
    "Gems", "IKPP", "In Progress Allocation (AGRI)", "PT. Ivo Mas Tunggal",
    "KARTIKA PRIMA CIPTA", "KENCANA GRAHA PERMAI", "PT. Kresna Duta Agroindo",
    "KRUING LESTARI JAYA", "LONTAR PAPYRUS", "MANTAP ANDALAN UNGGUL",
    "PT. Maskapai Perkebunan Leidong West Indonesia", "MEGANUSA INTISAWIT",
    "PT. Mitrakarya Agroindo", "PT. Paramitra Internusa Pratama", "PERSADA GRAHA MANDIRI",
    "PRIMASENTOSA PRATAMAPUTRA", "PRISMA CIPTA MANDIRI", "PT. Berau Coal",
    "PT. Ramajaya Pramukti", "SATYA KISMA USAHA", "SAWIT MAS SEJAHTERA",
    "PT. Sawitakarya Manunggul", "Sekuritas", "SINAR KENCANA INTI PERKASA",
    "SINAR MAS MULTIARTHA", "PT. SMART Tbk", "SML", "PT. Sumber Indah Perkasa",
    "PT. Tapian Nadenggan",
]

COST_CENTER_MAP = {
    "PT. Forestalestari Dwikarya":                    "2901C1POFF",
    "PT. Ivo Mas Tunggal":                            "1901C1POFF",
    "PT. Maskapai Perkebunan Leidong West Indonesia": "1201C1POFF",
    "PT. Mitrakarya Agroindo":                        "3801C1POFF",
    "PT. Agrokarya Primalestari":                     "4401C1POFF",
    "PT. Agrolestari Sentosa":                        "4201C1POFF",
    "PT. Binasawit Abadi Pratama":                    "3201C1POFF",
    "PT. Buana Artha Sejahtera":                      "4501C1POFF",
    "PT. Buana Wiralestari Mas":                      "2001C1POFF",
    "PT. Bumi Permai Lestari":                        "2601C1POFF",
    "PT. Djuandasawit Lestari":                       "2801C1POFF",
    "PT. Paramitra Internusa Pratama":                "4701C1POFF",
    "PT. Ramajaya Pramukti":                          "2101C1POFF",
    "PT. Sawitakarya Manunggul":                      "3401C1POFF",
    "PT. SMART Tbk":                                  "1008C1POFF",
    "PT. Aditunggal Mahajaya":                        "5101C1POFF",
    "PT. Kresna Duta Agroindo":                       "1101C1POFF",
    "PT. Tapian Nadenggan":                           "1401C1POFF",
    "PT. Sumber Indah Perkasa":                       "2501C1CMOF",
}
