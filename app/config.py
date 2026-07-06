# C:\Financehub\app\config.py
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "finance_hub.db")

def _load_or_create_secret(env_var: str, filename: str) -> str:
    val = os.environ.get(env_var)
    if val:
        return val
    path = os.path.join(BASE_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    new = secrets.token_hex(32)
    with open(path, "w") as f:
        f.write(new)
    return new

JWT_SECRET       = _load_or_create_secret("FH_JWT_SECRET", ".jwt_secret")
JWT_ACCESS_HOURS = 1
JWT_REFRESH_DAYS = 7

FLASK_SECRET = _load_or_create_secret("FH_SECRET", ".flask_secret")

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

PILLAR = ["AGRI", "APP", "ENERGY & FINANCE", "PROPERTY", "SETF", "NON PILLAR", "NON ALLOCATED"]

CAT1_BGT = ["By Pendidikan", "By Tunjangan", "By Penelitian", "By Medical"]

CAT2_SEM = [
    "Semester 1", "Semester 2", "Semester 3", "Semester 4", "Semester 5",
    "Semester 6", "Semester 7", "Semester 8", "Semester 9", "Semester 10",
    "By Pendaftaran", "By Ujian", "By Matrikulasi", "By Daftar Ulang",
    "By Gedung", "By Penelitian", "By Wisuda",
    "Rawat Inap", "Rawat Jalan",
    "Tahap 1", "Tahap 2", "Tahap 3",
    "By Orientasi", "By Registrasi", "Kelas Afirmasi",
    "Test TOEFL", "Test Kemampuan Akademik (TKA)",
    "By Uang Pangkal", "By Tugas Akhir", "By Seragam",
    "By Kegiatan", "By Akomodasi", "By Kemahasiswaan",
    "By Sumbangan Pembangunan", "Test TPDA",
    "Uang Pengembangan Institusi (IPI)",
    "By Ujian Kualifikasi", "Test Kemampuan Bahasa Inggris",
    "By Surat Keterangan Sehat & Bebas Narkoba",
    "By Buku dan Seragam", "By Kursus Bahasa Mandarin",
    "By Kursus Matematika",
]

CAT3_MEDICAL = [
    "Alkes", "Kamar", "Konsultasi dan Visit", "Laboratorium",
    "Obat", "Radiologi", "Sewa Alat Rumah Sakit", "Tindakan Dokter",
]

KELAS_MEDICAL = ["Basic", "Deluxe", "Emergency", "Rawat Jalan", "Standard", "VIP", "VVIP", "SVIP"]

SPESIALISASI_MEDICAL = [
    "Internal Medicine", "Cardiology", "Orthopaedy", "Obstetric & Gynaecology",
    "Pediatrics", "Pulmonology", "Neurology", "Neurosurgeon", "General Surgery",
    "ENT", "Dermatovenerology", "Psychiatry", "Opthalmology", "Plastic Surgery",
    "General Practitioner", "Dentistry",
]

TRANSAKSI_TYPES = ["Beasiswa", "Klaim Medis", "Tagihan", "ETF", "Sponsor", "Others"]

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

# Chart of Accounts — seed data for coa table + GL Account dropdown
COA_LIST = [
    {"gl_code": "70107800", "gl_name": "Sponsorship Expense"},
    {"gl_code": "70107500", "gl_name": "Social Donation Expense"},
    {"gl_code": "70110220", "gl_name": "CSR Expense"},
    {"gl_code": "70110230", "gl_name": "Scholarship Expense"},
    {"gl_code": "70109100", "gl_name": "Communication Expense - 3rd Party"},
    {"gl_code": "70110100", "gl_name": "Professional International Organization Expense"},
    {"gl_code": "70110110", "gl_name": "Professional National Organization Expense"},
    {"gl_code": "70111130", "gl_name": "Consultant Fee"},
    {"gl_code": "70108100", "gl_name": "Office Equipment Expense"},
    {"gl_code": "70111132", "gl_name": "Biaya Jasa Konsultan – Affiliasi"},
    {"gl_code": "70107200", "gl_name": "Entertainment Expense"},
    {"gl_code": "70119310", "gl_name": "Gift Expense"},
    {"gl_code": "70106300", "gl_name": "Overseas Travel Expense"},
    {"gl_code": "70107600", "gl_name": "Office Consumption"},
]

PAM_DEFAULT_GL        = "70110230"
PAM_DEFAULT_REQUESTOR = "Jany Turkanda"
PAM_APPROVED_BY_1 = "Hong Tjhin"
PAM_APPROVED_BY_2 = "Tenti Kidjo"

# COA-PAM lookup — SMT GL/Advance "Jenis Biaya" classification (Statutory Report /
# Management Report labels) + the GL code to use depending on Transaksi type.
# Seed data from C:\Users\25010160\Downloads\COA.xlsx (44 rows).
# Tuple shape: (klasifikasi_sr, klasifikasi_mr, coa_advance, coa_expense)
# coa_advance is None where the row only applies to GL (Expense) transactions.
COA_PAM_SEED = [
    ("Beasiswa", "Scholarship Expense", None, "70110230"),
    ("Biaya Listrik", "Electrical Expense", None, "70103200"),
    ("Biaya Organisasi Profesional", "Biaya Organisasi Profesional", None, "70110110"),
    ("Consumption", "Office Consumption", None, "70107600"),
    ("CSR", "CSR Expense", None, "70110220"),
    ("Entertainment", "Entertainment Expense", None, "70107200"),
    ("Equipment", "Office Equipment Expense", None, "70108100"),
    ("Fotocopy", "Biaya Fotocopy", None, "70108110"),
    ("Gift", "Gift Expense", None, "70119310"),
    ("Iklan Media Cetak / Digital", "Biaya Iklan Media Cetak", None, "70004113"),
    ("Iklan Media Digital", "Biaya Iklan Media Digital", None, "70004113"),
    ("Iklan Metro TV", "Biaya Spot Iklan TV & Radio", None, "70004111"),
    ("Jasa Advokasi", "Biaya Jasa Konsultan – Affiliasi", None, "70111132"),
    ("Jasa Konsultan", "Consultant Fee", None, "70111130"),
    ("Link Net", "Communication Expense - 3rd Party", None, "70109100"),
    ("Local Transport", "Local Transportation Expense", None, "70106100"),
    ("Majalah", "Biaya Langganan Majalah", None, "70110400"),
    ("Memberhip International", "Professional International Organization Expense", None, "70110100"),
    ("Membership National", "Professional National Organization Expense", None, "70110110"),
    ("Office Supplies", "Office Supplies", None, "70108100"),
    ("Perbaikan Perabot", "Repair And Maintenance Expense (Material)", None, "70101114"),
    ("Perdin Dalam Negeri", "Local Travel Expense", None, "70106200"),
    ("Perdin Luar Negeri", "Overseas Travel Expense", None, "70106300"),
    ("Piutang Lainnya", "Other Receivable", None, "13001710"),
    ("Rapimnas Kadin daftar acara", "Local Conference Expense", None, "70110500"),
    ("Saham", "Pernyertaan Saham dengan Metode Biaya", None, "25001100"),
    ("Sewa Kendaraan dan Perlengkapan", "Equipment Rent Expense - 3rd Party", None, "70105120"),
    ("Sewa Peralatan", "Equipment Rent Expense - 3rd P", None, "70105120"),
    ("Sponsor", "Sponsorship Expense", None, "70107800"),
    ("Sumbangan", "Social Donation Expense", None, "70107500"),
    ("Advance Others - Sponsor", "Advance Others", "15000900", "70107800"),
    ("Advance Perdin - Perdin Lokal", "Advance Perdin", "16001100", "70106200"),
    ("Advance for Training", "Advance Training", "16001300", "70110200"),
    ("Advance Others - CSR", "Advance Others", "15000900", "70110220"),
    ("Advance Others - Office Equipment", "Advance Others", "15000900", "70108100"),
    ("Advance Uang Muka Lainnya", "Advance Uang Muka Lainnya", "16001810", "70108100"),
    ("Advance Uang Muka Lainnya - Vendor", "Advance Uang Muka Lainnya - Vendor", "16001800", "70108100"),
    ("Advance Uang Muka Lainnya - Karyawan", "Advance Uang Muka Lainnya - Karyawan", "16001810", "70108100"),
    ("Advance Others - Jasa Konsultan", "Advance Others - Jasa Konsultan", "16001810", "70111130"),
    ("Advance Others - Sewa Kendaraan dan Perlengkapan", "Advance Others - Equipment Rent Expense - 3rd Party", "16001810", "70105120"),
    ("Advance - CSR", "Advance Uang Muka CSR", "16001810", "70110220"),
    ("Advance Others - Ceremonial exp", "Advance Others - Ceremonial exp", "16001810", "70101700"),
    ("Advance Membership Organisasi Nasional", "Advance Membership Organisasi Nasional", "15000900", "70110110"),
    ("Advance Others - Biaya Promosi Iklan", "Advance Others", "15000900", "70004110"),
]
