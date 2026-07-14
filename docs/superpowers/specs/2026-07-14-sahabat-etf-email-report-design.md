# Sahabat ETF — Email Report Trigger Design

## Ringkasan

Tombol "Kirim Laporan" baru di dashboard Sahabat ETF (`/beasiswa/sahabat`) yang mengirim ringkasan + lampiran Excel (Ringkasan & Detail Transaksi) ke daftar email yang diinput manual oleh user setiap kali kirim. Menggunakan Gmail SMTP dengan App Password — server FinanceHub punya akses internet biasa.

## Kenapa

Dashboard Sahabat ETF (11 siswa program) sudah live dengan export Excel manual (download), tapi belum ada cara mengirim laporan langsung ke pihak lain (mis. finance/HR) tanpa harus download lalu forward manual. Automasi email untuk dashboard lain (Beasiswa Dashboard BI, Budget Monitoring) sebelumnya ditunda karena FinanceHub belum punya infra SMTP sama sekali — fitur ini membangun infra dasar tersebut, discope ke Sahabat ETF dulu.

## Keputusan Desain

| Area | Keputusan | Alasan |
|---|---|---|
| Scope | Dashboard Sahabat ETF saja | Modul lain (Beasiswa Dashboard BI) belum dieksekusi; infra dibangun reusable tapi tidak sekaligus dipasang di modul lain |
| Trigger | Manual — tombol "Kirim Laporan" | Bukan terjadwal; user klik kapan butuh, tidak perlu scheduler |
| Penerima | Diinput manual tiap kirim (comma-separated), tidak disimpan | Paling fleksibel, tanpa perlu tabel/halaman pengaturan baru |
| Transport | Gmail SMTP (`smtp.gmail.com:587`) + App Password | Server FinanceHub punya akses internet; user sudah punya akun Gmail/Workspace |
| Library | `smtplib` + `email.mime` (stdlib) | Zero dependency baru — cukup untuk 1 fungsi kirim dengan lampiran |
| Isi email | Ringkasan angka di body (jumlah siswa, total budget/realisasi, daftar over-budget) + 2 lampiran Excel (Ringkasan, Detail Transaksi) | Bisa dibaca cepat tanpa buka lampiran, detail tetap ada di attachment |
| Filter | Ikut filter tahun/pillar yang aktif di dashboard saat tombol diklik | Laporan yang dikirim = yang sedang dilihat user |
| Kredensial | Env var `FH_GMAIL_USER`, `FH_GMAIL_APP_PASSWORD` | Mengikuti pola `os.environ.get` yang sudah dipakai di `config.py` |

## Arsitektur

```
[Dashboard] --klik "Kirim Laporan"--> [modal: input recipients] --submit-->
  POST /beasiswa/sahabat/send-report {recipients, years, pillar}
    -> etf_company_required guard
    -> validasi format email tiap recipient
    -> generate 2 xlsx in-memory (reuse builder dari export_summary/export_detail)
    -> build HTML body (ringkasan angka dari get_siswa_summary)
    -> email_service.send_report_email(to_addrs, subject, body_html, attachments)
        -> smtplib.SMTP(smtp.gmail.com, 587) + starttls + login + send_message
    -> JSON {"ok": true/false, "pesan": "..."}
```

### File baru
- `app/email_service.py` — 1 fungsi reusable: `send_report_email(to_addrs: list[str], subject: str, body_html: str, attachments: list[tuple[str, bytes]]) -> None`. Raise exception on failure (auth error, network error) — dibungkus try/except di route.

### File yang diubah
- `app/config.py` — tambah `SMTP_HOST = "smtp.gmail.com"`, `SMTP_PORT = 587`, `GMAIL_USER = os.environ.get("FH_GMAIL_USER")`, `GMAIL_APP_PASSWORD = os.environ.get("FH_GMAIL_APP_PASSWORD")`.
- `app/modules/sahabat_etf/routes.py` —
  - extract logic pembuatan workbook dari `_xlsx_response()` jadi helper `_build_xlsx_bytes(sheet_title, headers, rows, amount_cols) -> bytes`, dipakai baik oleh `_xlsx_response()` (existing export routes) maupun route baru.
  - route baru `POST /beasiswa/sahabat/send-report`, guard `@etf_company_required`.
- `app/templates/sahabat_etf/index.html` — tombol baru "Kirim Laporan" di `.budget-toolbar`, plus modal/prompt kecil untuk input recipients.
- `app/static/js/sahabat_etf.js` — handler klik tombol: ambil filter aktif, buka prompt input email, fetch POST, tampilkan toast hasil.

## Validasi & Error Handling

- **Recipients kosong** → ditolak di client (tombol submit disabled) dan di server (400 dengan pesan jelas).
- **Format email invalid** → divalidasi per-alamat dengan regex sederhana di server; kalau ada yang invalid, tolak semua (400) sebelum mencoba kirim — bukan partial send.
- **Kredensial SMTP belum diset** (`GMAIL_USER`/`GMAIL_APP_PASSWORD` kosong) → route balas 500 dengan pesan "Email belum dikonfigurasi, hubungi admin", tidak expose stack trace.
- **Kegagalan SMTP saat kirim** (auth salah, network error) → ditangkap di route, balas `{"ok": false, "pesan": "Gagal mengirim: ..."}`. Tidak ada retry otomatis — user klik ulang manual.
- **Guard company** — route baru pakai decorator `etf_company_required` yang sudah ada di `routes.py`, konsisten dengan endpoint lain di modul ini.
- Tidak ada audit log/history pengiriman baru — di luar scope (YAGNI; bisa jadi fase berikutnya kalau dibutuhkan).

## Testing

Mengikuti pola pytest existing di project:
- `email_service.send_report_email()` — test dengan mock `smtplib.SMTP` (tidak kirim beneran), verifikasi pesan dibentuk benar (subject, to, attachment count) dan exception SMTP di-propagate.
- Validasi format email — test beberapa kasus valid/invalid.
- Route `/send-report` — test guard company (non-ETF ditolak 403), test recipients kosong/invalid (400), test happy path (mock `send_report_email`, verifikasi dipanggil dengan attachment yang benar).
- Tidak ada test otomatis untuk "email benar-benar sampai ke inbox" — itu manual smoke test 1x dengan alamat asli setelah deploy.

## Manual Verification (setelah build)

1. Set `FH_GMAIL_USER` dan `FH_GMAIL_APP_PASSWORD` di environment.
2. Buka `/beasiswa/sahabat`, klik "Kirim Laporan", isi 1-2 email asli (termasuk email sendiri).
3. Cek inbox: body berisi ringkasan angka yang sesuai filter aktif, 2 lampiran xlsx bisa dibuka dan datanya sama dengan hasil export manual.
4. Test kasus gagal: kosongkan recipients → tombol submit harus tertahan; isi email format salah → dapat pesan error jelas.

## Links
- FinanceHub - Overview (vault): `01 - Proyek/FinanceHub/FinanceHub - Overview.md`
- Spec modul asal: `docs/superpowers/specs/2026-07-14-sahabat-etf-module-design.md`
