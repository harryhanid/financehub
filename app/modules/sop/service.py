import docx
from database import get_conn


def create_document(modul, nama, kode=None, status="aktif", file_path=None,
                     catatan=None, perlu_verifikasi_count=0, uploaded_by=None):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO sop_documents
           (modul, kode, nama, status, file_path, catatan, perlu_verifikasi_count, uploaded_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (modul, kode, nama, status, file_path, catatan, perlu_verifikasi_count, uploaded_by),
    )
    conn.commit()
    doc_id = cur.lastrowid
    conn.close()
    return doc_id


def get_document(doc_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM sop_documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_documents(search=None, modul=None, status=None):
    conn = get_conn()
    query = "SELECT * FROM sop_documents WHERE 1=1"
    params = []
    if search:
        query += " AND LOWER(nama) ILIKE ?"
        params.append(f"%{search.lower()}%")
    if modul:
        query += " AND modul = ?"
        params.append(modul)
    if status:
        query += " AND status = ?"
        params.append(status)
    # SQLite CAST(kode AS INTEGER): NULL tetap NULL (urut paling awal), selain itu awalan angka
    # ('12', '1.7' -> 1, '3a' -> 3) dan teks tanpa awalan angka -> 0. NULLS FIRST meniru urutan
    # NULL SQLite pada ASC. ::numeric (bukan ::bigint): kode > 19 digit tidak membuat query gagal.
    query += (" ORDER BY modul, CASE WHEN kode IS NULL THEN NULL"
              " ELSE COALESCE(substring(ltrim(kode) from '^[-+]?[0-9]+')::numeric, 0) END NULLS FIRST")
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_upload(doc_id, file_path, perlu_verifikasi_count, uploaded_by, catatan=None):
    conn = get_conn()
    # Postgres: UPDATE + INSERT history dalam satu batch (satu transaksi). uploaded_at sama dengan
    # CURRENT_TIMESTAMP SQLite: teks UTC 'YYYY-MM-DD HH:MM:SS'.
    conn.batch([
        ("""UPDATE sop_documents
           SET file_path=?, perlu_verifikasi_count=?, uploaded_by=?,
               uploaded_at=to_char(now() at time zone 'utc', 'YYYY-MM-DD HH24:MI:SS'), status='aktif'
           WHERE id=?""",
         (file_path, perlu_verifikasi_count, uploaded_by, doc_id)),
        ("INSERT INTO sop_upload_history (sop_id, uploaded_by, catatan) VALUES (?, ?, ?)",
         (doc_id, uploaded_by, catatan)),
    ])
    conn.commit()
    conn.close()


def count_perlu_verifikasi_in_file(file_path):
    document = docx.Document(file_path)
    text = "\n".join(p.text for p in document.paragraphs)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text
    return text.count("PERLU VERIFIKASI")
