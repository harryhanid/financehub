# Finance Hub

Sistem manajemen keuangan internal untuk Sinar Mas Tjipta (SMT) dan Eka Tjipta Foundation (ETF).

## Setup

### 1. Prasyarat
- Python 3.9+

### 2. Install dependencies
```cmd
cd C:\Financehub\app
pip install -r requirements.txt
```

### 3. Jalankan (Development)
```cmd
python run.py
```

### 4. Jalankan (Production / LAN)
```cmd
python run_production.py
```
User lain di LAN buka: `http://[IP-yang-tampil]:8080`

---

## Login Pertama Kali

| Field    | Value        |
|----------|--------------|
| Username | `admin`      |
| Password | `Admin@123`  |

Ganti password segera setelah login pertama.

---

## Backup Database

File: `C:\Financehub\app\finance_hub.db`

```cmd
copy C:\Financehub\app\finance_hub.db "Y:\Backup\finance_hub_%date%.db"
```

---

## Tips Laptop Server

- Jangan biarkan laptop sleep: Settings → Power → Never sleep saat colok listrik
- IP bisa berubah saat reconnect WiFi — jalankan `ipconfig` untuk cek IP terbaru
- Restart server jika lemot: Ctrl+C → `python run_production.py`

---

## Modul

| Modul               | Status    | Perusahaan |
|---------------------|-----------|------------|
| Beasiswa            | v1.0   | ETF        |
| Payment Memo        | v1.0   | SMT + ETF  |
| Payment Application | v1.0   | SMT + ETF  |
| Bank                | Fase 2 | SMT + ETF  |
| Account Payable     | Fase 2 | SMT + ETF  |
| Advance             | Fase 2 | SMT + ETF  |
| Petty Cash          | Fase 2 | SMT + ETF  |
| Sponsorship         | Fase 2 | SMT        |

---

## REST API

Header required: `Authorization: Bearer <access_token>`

Dapatkan token: `POST /auth/login` dengan body `{"username": "...", "password": "..."}`.

### Endpoints

| Method | Path | Keterangan |
|--------|------|------------|
| POST | `/auth/login` | Login, returns `access_token` |
| GET | `/api/v1/siswa?company=ETF` | Daftar siswa beasiswa |
| GET | `/api/v1/rekap?company=ETF` | Rekap beasiswa per siswa |
| GET | `/api/v1/payment-beasiswa?company=ETF` | Daftar payment beasiswa |
| GET | `/api/v1/budget?company=ETF&siswa_code=XXX` | Budget siswa |
| GET | `/api/v1/payment-draft?company=ETF` | Draft payments untuk memo |
| GET | `/api/v1/payment-memo?company=ETF` | Daftar payment memo |
| POST | `/api/v1/payment-memo` | Buat memo baru (verificator only) |
