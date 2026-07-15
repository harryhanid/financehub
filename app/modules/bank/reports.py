from datetime import datetime


def classify_rows(rows: list) -> dict:
    penerimaan = {}
    bank = {}
    sahabat_etf = {}

    for r in rows:
        ket = (r["keterangan"] or "").strip()
        ket_lower = ket.lower()
        if ket_lower.startswith("setoran awal"):
            continue

        month_key = r["tanggal"][:7]
        label = ket if ket else "(Tanpa Keterangan)"
        jumlah = r["jumlah"] or 0

        if r["source"] == "pam":
            sahabat_etf.setdefault(label, {}).setdefault(month_key, 0)
            sahabat_etf[label][month_key] += jumlah
            continue

        if ket_lower == "bank admin & bunga":
            bank.setdefault("Bunga dan Admin", {}).setdefault(month_key, 0)
            if r["jenis"] == "pengeluaran":
                bank["Bunga dan Admin"][month_key] += jumlah
            else:
                bank["Bunga dan Admin"][month_key] -= jumlah
        elif r["jenis"] == "pemasukan":
            penerimaan.setdefault(label, {}).setdefault(month_key, 0)
            penerimaan[label][month_key] += jumlah
        else:
            bank.setdefault(label, {}).setdefault(month_key, 0)
            bank[label][month_key] += jumlah

    return {"penerimaan": penerimaan, "bank": bank, "sahabat_etf": sahabat_etf}


def month_range(rows: list, today=None) -> list:
    today = today or datetime.now()
    current_key = f"{today.year:04d}-{today.month:02d}"

    eligible = [
        r["tanggal"] for r in rows
        if not (r["keterangan"] or "").strip().lower().startswith("setoran awal")
    ]
    if not eligible:
        return [current_key]

    earliest = min(eligible)[:7]
    y, m = int(earliest[:4]), int(earliest[5:7])

    months = []
    while (y, m) <= (today.year, today.month):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months
