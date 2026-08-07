"""One-time migration: import existing SOP .docx files from the SOP
consolidation project into FinanceHub's sop_documents table + storage.

Usage: python modules/sop/migrate.py <path-to-sop-smt-etf-folder>

Run manually once. Not wired into app.py or any scheduler. Safe to re-run
against an empty sop_documents table only — re-running against an already
migrated table creates duplicate rows (no dedup key on nama+modul).
"""
import os
import shutil
import sys
import re

import docx
import config
from modules.sop.service import create_document, count_perlu_verifikasi_in_file

MODULE_FOLDERS = [
    "planning-budgeting", "procurement", "finance-payment", "asset-management",
    "hr-personnel", "hr-remuneration", "it-operations", "general-admin-tax",
    "corporate-compliance",
]

# Out-of-scope rows from INDEX.md Lampiran A — no source document found,
# so no .docx exists for these. Hardcoded here since the list is small,
# static, and specific to this one-time migration.
OUT_OF_SCOPE = [
    ("hr-personnel", "Pengajuan & Penambahan Karyawan",
     "Tidak ada dokumen sumber ditemukan"),
    ("hr-personnel", "Penerimaan Karyawan",
     "Tidak ada dokumen sumber ditemukan"),
    ("hr-personnel", "Kehadiran Kerja (attendance)",
     "Tidak ada dokumen sumber ditemukan"),
    ("hr-personnel", "Jamuan Bisnis & Konsumsi Meeting (versi HR)",
     "Tidak ada dokumen sumber ditemukan"),
    ("hr-personnel", "Pengaturan Jam Kerja untuk Lanjut Pendidikan",
     "Tidak ada dokumen sumber ditemukan"),
    ("hr-remuneration", "Payroll",
     "Hanya ditemukan PKS vendor payroll 2018 & jadwal cutoff, bukan dokumen prosedur"),
    ("hr-remuneration", "Melahirkan (maternity)",
     "Tidak ada dokumen sumber ditemukan"),
    ("revenue-cycle", "Penagihan Diplomacy & Advisory Fee",
     "Tidak ada dokumen sumber ditemukan"),
]

_KODE_RE = re.compile(r"^(\d+)-")


def migrate_sop_documents(source_root):
    imported = 0
    for modul in MODULE_FOLDERS:
        modul_source_dir = os.path.join(source_root, modul)
        if not os.path.isdir(modul_source_dir):
            continue
        dest_dir = os.path.join(config.SOP_STORAGE_DIR, modul)
        os.makedirs(dest_dir, exist_ok=True)
        for filename in sorted(os.listdir(modul_source_dir)):
            if not filename.lower().endswith(".docx"):
                continue
            src_path = os.path.join(modul_source_dir, filename)
            dest_path = os.path.join(dest_dir, filename)
            shutil.copyfile(src_path, dest_path)

            nama = docx.Document(dest_path).paragraphs[0].text.strip()
            kode_match = _KODE_RE.match(filename)
            kode = kode_match.group(1) if kode_match else None
            verif_count = count_perlu_verifikasi_in_file(dest_path)

            create_document(
                modul=modul, nama=nama, kode=kode,
                file_path=f"{modul}/{filename}",
                perlu_verifikasi_count=verif_count,
            )
            imported += 1

    out_of_scope = 0
    for modul, nama, catatan in OUT_OF_SCOPE:
        create_document(modul=modul, nama=nama, status="belum_dibuat", catatan=catatan)
        out_of_scope += 1

    return {"imported": imported, "out_of_scope": out_of_scope}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python modules/sop/migrate.py <path-to-sop-smt-etf-folder>")
        sys.exit(1)
    result = migrate_sop_documents(sys.argv[1])
    print(f"Imported {result['imported']} SOP documents, "
          f"seeded {result['out_of_scope']} out-of-scope rows.")
