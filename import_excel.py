import pandas as pd
import sqlite3
import numpy as np

DB = r'C:\Financehub\app\finance_hub.db'
DL = r'C:\Users\25010160\Downloads'


def is_null(v):
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    return False


def to_str(v):
    if is_null(v):
        return None
    return str(v)


def to_int(v):
    if is_null(v):
        return None
    return int(v)


def to_float(v):
    if is_null(v):
        return None
    return float(v)


def clean_date(v):
    if is_null(v):
        return None
    if hasattr(v, 'strftime'):
        return v.strftime('%Y-%m-%d')
    s = str(v).strip()
    return s if s and s != 'nan' else None


conn = sqlite3.connect(DB)
cur = conn.cursor()
results = {}

# --- 1. payment_beasiswa ---
print('--- payment_beasiswa ---')
df = pd.read_excel(f'{DL}/payment_beasiswa query upload 240626.xlsx', dtype_backend='numpy_nullable')
before = cur.execute('SELECT COUNT(*) FROM payment_beasiswa').fetchone()[0]

rows = []
for _, r in df.iterrows():
    rows.append((
        to_int(r['id']), to_int(r['company_id']), to_str(r['siswa_code']),
        to_str(r['cat1']), to_str(r['cat2']), to_str(r['tanggal']),
        to_float(r['amount']), to_str(r['pillar']), to_str(r['pam']),
        to_str(r['perusahaan']), to_str(r['cat3']), to_str(r['cat4']),
        to_int(r['memo_id']), to_str(r['status']), to_str(r['created_at']),
        to_str(r['tgl_pengajuan']), to_str(r['tgl_receive']), to_str(r['tgl_pa']),
        to_str(r['tgl_final']), to_str(r['tgl_retur']), to_str(r['tgl_final6']),
        to_str(r['tgl_proses']),
        clean_date(r['tgl_HT_AGRI']), clean_date(r['tgl_Yurike_AGRI']),
        clean_date(r['tgl_Aditya_AGRI']), clean_date(r['tgl_Pedy_AGRI']),
        clean_date(r['tgl_C2_AGRI']), clean_date(r['tgl_MSIG_AGRI']),
        clean_date(r['tgl_Paid_AGRI']), clean_date(r['tgl_A-GS_APP']),
        clean_date(r['tgl_A-HJK_APP']), clean_date(r['tgl_ASPIRO_APP']),
        clean_date(r['tgl_Paid_APP']), to_int(r['etf_pa_line_id']),
        clean_date(r['tgl_Paid_LAND']), clean_date(r['tgl_Paid_ENERGY']),
        clean_date(r['tgl_Paid_SETF']),
    ))

cur.executemany(
    'INSERT OR REPLACE INTO payment_beasiswa '
    '(id,company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,pam,perusahaan,cat3,cat4,'
    'memo_id,status,created_at,tgl_pengajuan,tgl_receive,tgl_pa,tgl_final,tgl_retur,'
    'tgl_final6,tgl_proses,tgl_HT_AGRI,tgl_Yurike_AGRI,tgl_Aditya_AGRI,tgl_Pedy_AGRI,'
    'tgl_C2_AGRI,tgl_MSIG_AGRI,tgl_Paid_AGRI,"tgl_A-GS_APP","tgl_A-HJK_APP",'
    'tgl_ASPIRO_APP,tgl_Paid_APP,etf_pa_line_id,tgl_Paid_LAND,tgl_Paid_ENERGY,tgl_Paid_SETF)'
    ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
    rows
)
conn.commit()
after = cur.execute('SELECT COUNT(*) FROM payment_beasiswa').fetchone()[0]
print(f'  {before} -> {after} (+{after - before})')
results['payment_beasiswa'] = (before, after)

# --- 2. etf_pa ---
print('--- etf_pa ---')
df = pd.read_excel(f'{DL}/etf_pa query upload 240626.xlsx', dtype_backend='numpy_nullable')
df = df.dropna(subset=['id'])
before = cur.execute('SELECT COUNT(*) FROM etf_pa').fetchone()[0]

rows = []
for _, r in df.iterrows():
    rows.append((
        to_int(r['id']), to_int(r['company_id']), to_str(r['pa_number']),
        clean_date(r['tgl_payment_application']), clean_date(r['tgl_surat_pengajuan']),
        clean_date(r['doc_received_by_educ']), clean_date(r['received_pa_from_educ']),
        clean_date(r['checked_by_fincon']), clean_date(r['approved_by_htj_1']),
        clean_date(r['send_pa_back_to_educ']), clean_date(r['pa_received_by_po_fin']),
        clean_date(r['approval_by_htj_2']), to_str(r['nomor_pam']),
        to_str(r['tanggal_bayar']), to_str(r['keterangan']), to_str(r['status']),
        to_str(r['created_at']), to_str(r['updated_at']),
    ))

cur.executemany(
    'INSERT OR REPLACE INTO etf_pa '
    '(id,company_id,pa_number,tgl_payment_application,tgl_surat_pengajuan,'
    'doc_received_by_educ,received_pa_from_educ,checked_by_fincon,approved_by_htj_1,'
    'send_pa_back_to_educ,pa_received_by_po_fin,approval_by_htj_2,nomor_pam,'
    'tanggal_bayar,keterangan,status,created_at,updated_at)'
    ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
    rows
)
conn.commit()
after = cur.execute('SELECT COUNT(*) FROM etf_pa').fetchone()[0]
print(f'  {before} -> {after} (+{after - before})')
results['etf_pa'] = (before, after)

# --- 3. etf_pa_lines ---
print('--- etf_pa_lines ---')
df = pd.read_excel(f'{DL}/etf_pa_lines query upload 240626.xlsx', dtype_backend='numpy_nullable')
df = df[[c for c in df.columns if not c.startswith('Unnamed')]]
before = cur.execute('SELECT COUNT(*) FROM etf_pa_lines').fetchone()[0]

rows = []
for _, r in df.iterrows():
    rows.append((
        to_int(r['id']), to_int(r['pa_id']), to_int(r['student_id']),
        to_str(r['jenis_pembayaran']), to_str(r['semester']), to_str(r['tahun_ajaran']),
        to_float(r['ipk_sem_sebelumnya']), to_int(r['jumlah_pembayaran']),
    ))

cur.executemany(
    'INSERT OR REPLACE INTO etf_pa_lines '
    '(id,pa_id,student_id,jenis_pembayaran,semester,tahun_ajaran,ipk_sem_sebelumnya,jumlah_pembayaran)'
    ' VALUES (?,?,?,?,?,?,?,?)',
    rows
)
conn.commit()
after = cur.execute('SELECT COUNT(*) FROM etf_pa_lines').fetchone()[0]
print(f'  {before} -> {after} (+{after - before})')
results['etf_pa_lines'] = (before, after)

# --- 4. pam_records ---
print('--- pam_records ---')
df = pd.read_excel(f'{DL}/pam_records query upload 240626.xlsx', dtype_backend='numpy_nullable')
before = cur.execute('SELECT COUNT(*) FROM pam_records').fetchone()[0]

rows = []
for _, r in df.iterrows():
    rows.append((
        to_int(r['id']), to_int(r['company_id']), to_str(r['pam_no']),
        to_str(r['pam_date']), to_str(r['gl_account']), to_str(r['cost_center']),
        to_str(r['pt']), to_str(r['requestors_name']), to_str(r['keterangan']),
        to_float(r['total_amount']), to_str(r['due_date']), to_str(r['status']),
        to_str(r['created_at']), to_str(r['updated_at']), to_str(r['tanggal_bayar']),
        to_str(r['source']), to_str(r['mata_uang']), to_int(r['dpp']),
        to_float(r['ppn']), to_str(r['pillar']),
    ))

cur.executemany(
    'INSERT OR REPLACE INTO pam_records '
    '(id,company_id,pam_no,pam_date,gl_account,cost_center,pt,requestors_name,keterangan,'
    'total_amount,due_date,status,created_at,updated_at,tanggal_bayar,source,mata_uang,dpp,ppn,pillar)'
    ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
    rows
)
conn.commit()
after = cur.execute('SELECT COUNT(*) FROM pam_records').fetchone()[0]
print(f'  {before} -> {after} (+{after - before})')
results['pam_records'] = (before, after)

conn.close()

print('\n=== SUMMARY ===')
for t, (b, a) in results.items():
    print(f'  {t}: {b} -> {a} (+{a - b} baru)')
