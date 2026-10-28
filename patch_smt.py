import re
with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

text = re.sub(
    r'(INSERT INTO pam_transaction_lines\s*\([^)]+keterangan,)\s*created_at\)',
    r'\1 klasifikasi_pam, created_at)',
    text
)
text = re.sub(
    r'(VALUES\s*\(\?\s*,\s*\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?)',
    r'\1,?',
    text
)
text = re.sub(
    r'(\(pam_id,\s*coa_id,\s*sr,\s*mr,\s*gl,\s*tipe_dokumen,\s*no_invoice,\s*ldpp,\s*lppn,\s*lothers,\s*ltotal,\s*cc,\s*ba,\s*vendor,\s*ket,\s*_ts\(\)\))',
    r'(pam_id, coa_id, sr, mr, gl, tipe_dokumen, no_invoice, ldpp, lppn, lothers, ltotal, cc, ba, vendor, ket, klasifikasi, _ts())',
    text
)

with open("app/modules/payment_memo/service.py", "w", encoding="utf-8") as f:
    f.write(text)
