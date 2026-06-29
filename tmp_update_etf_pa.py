import sqlite3
import pandas as pd

df = pd.read_excel(
    r'C:\Users\25010160\Downloads\AGRI_PA_20260617_1007 - SEMUA STATUS (Reviewed).xlsx',
    sheet_name='AGRI Payment Application'
)

conn = sqlite3.connect('app/finance_hub.db')
cur = conn.cursor()

def safe(val):
    if pd.isna(val) or val == '':
        return None
    return str(val).strip()

# ── 1. UPDATE etf_pa (one row per unique PA, take first occurrence) ──
pa_header = df.drop_duplicates('No. PA', keep='first')

pa_updated = 0
pa_not_found = []

sql_pa = (
    "UPDATE etf_pa "
    "SET tgl_payment_application=?, tgl_surat_pengajuan=?, "
    "doc_received_by_educ=?, received_pa_from_educ=?, "
    "checked_by_fincon=?, approved_by_htj_1=?, "
    "send_pa_back_to_educ=?, pa_received_by_po_fin=?, "
    "approval_by_htj_2=?, nomor_pam=?, tanggal_bayar=?, "
    "keterangan=?, status=?, updated_at=datetime('now') "
    "WHERE pa_number=? AND company_id=2"
)

for _, row in pa_header.iterrows():
    pa_num = row['No. PA']
    cur.execute(sql_pa, (
        safe(row['Tgl PA']),
        safe(row['Tgl Surat Pengajuan']),
        safe(row['Doc Recv Educ']),
        safe(row['Recv PA Educ']),
        safe(row['Checked Fincon']),
        safe(row['Approved HTj']),
        safe(row['Send Back Educ']),
        safe(row['PA Recv PO Fin']),
        safe(row['Approval HTj']),
        safe(row['Nomor PAM']),
        safe(row['Tgl Bayar']),
        safe(row['Keterangan']),
        safe(row['Status']),
        pa_num,
    ))
    if cur.rowcount == 0:
        pa_not_found.append(pa_num)
    else:
        pa_updated += 1

print(f'etf_pa: {pa_updated} updated, {len(pa_not_found)} not found')
if pa_not_found[:5]:
    print('  Not found:', pa_not_found[:5])

# ── 2. UPDATE etf_pa_lines ──
cur.execute('SELECT id, code FROM siswa')
code_to_id = {r[1]: r[0] for r in cur.fetchall()}

cur.execute('SELECT id, pa_number FROM etf_pa WHERE company_id=2')
pa_num_to_id = {r[1]: r[0] for r in cur.fetchall()}

lines_updated = 0
lines_not_found = []

sql_line_exact = (
    "UPDATE etf_pa_lines "
    "SET jenis_pembayaran=?, semester=?, tahun_ajaran=?, "
    "ipk_sem_sebelumnya=?, jumlah_pembayaran=? "
    "WHERE pa_id=? AND student_id=? AND jenis_pembayaran=? AND jumlah_pembayaran=?"
)

sql_line_fallback = (
    "UPDATE etf_pa_lines "
    "SET jenis_pembayaran=?, semester=?, tahun_ajaran=?, "
    "ipk_sem_sebelumnya=?, jumlah_pembayaran=? "
    "WHERE pa_id=? AND student_id=? AND jenis_pembayaran=?"
)

for _, row in df.iterrows():
    pa_num = row['No. PA']
    pa_id  = pa_num_to_id.get(pa_num)
    if pa_id is None:
        lines_not_found.append(('no_pa', pa_num))
        continue

    s_code = str(int(row['ID Siswa'])) if not pd.isna(row['ID Siswa']) else None
    s_id   = code_to_id.get(s_code)
    if s_id is None:
        lines_not_found.append(('no_siswa', s_code, pa_num))
        continue

    jenis  = safe(row['Jenis Bayar'])
    sem    = safe(row['Semester'])
    tahun  = safe(row['Tahun Ajaran'])
    ipk    = None if pd.isna(row['IPK Sblmnya']) else float(row['IPK Sblmnya'])
    jumlah = None if pd.isna(row['Jumlah (Rp)']) else int(row['Jumlah (Rp)'])

    cur.execute(sql_line_exact, (jenis, sem, tahun, ipk, jumlah, pa_id, s_id, jenis, jumlah))
    if cur.rowcount == 0:
        cur.execute(sql_line_fallback, (jenis, sem, tahun, ipk, jumlah, pa_id, s_id, jenis))
        if cur.rowcount == 0:
            lines_not_found.append(('no_line', pa_num, s_code, jenis))
        else:
            lines_updated += 1
    else:
        lines_updated += 1

print(f'etf_pa_lines: {lines_updated} updated, {len(lines_not_found)} not found')
if lines_not_found:
    print('  Sample not found:', lines_not_found[:10])

conn.commit()
conn.close()
print('\nDone. Committed.')
