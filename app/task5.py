# 1. dashboard/index.html
f1 = r"C:\Financehub\app\templates\dashboard\index.html"
with open(f1, "r", encoding="utf-8") as f:
    t = f.read()
t = t.replace('<div class="stat-value currency" data-count="{{ stats.total_budget }}" data-prefix="Rp ">Rp {{ "{:,.0f}".format(stats.total_budget) }}</div>', '<div class="stat-value currency" data-count="{{ stats.total_budget }}" data-prefix="Rp ">{{ stats.total_budget | rupiah }}</div>')
t = t.replace('<div class="stat-value currency" data-count="{{ stats.total_payment }}" data-prefix="Rp ">Rp {{ "{:,.0f}".format(stats.total_payment) }}</div>', '<div class="stat-value currency" data-count="{{ stats.total_payment }}" data-prefix="Rp ">{{ stats.total_payment | rupiah }}</div>')
t = t.replace('<div class="stat-value currency" data-count="{{ dash.paid_this_month }}" data-prefix="Rp ">Rp {{ "{:,.0f}".format(dash.paid_this_month) }}</div>', '<div class="stat-value currency" data-count="{{ dash.paid_this_month }}" data-prefix="Rp ">{{ dash.paid_this_month | rupiah }}</div>')
t = t.replace('          <td style="padding:7px 10px;text-align:right">{{ "{:,.0f}".format(it.total) }}</td>', '          <td style="padding:7px 10px;text-align:right">{{ it.total | rupiah(false) }}</td>')
t = t.replace('          <td style="padding:7px 10px;text-align:right">{{ "{:,.0f}".format(it.total_amount) }}</td>', '          <td style="padding:7px 10px;text-align:right">{{ it.total_amount | rupiah(false) }}</td>')
with open(f1, "w", encoding="utf-8") as f:
    f.write(t)


# 2. payment_application/index.html
f2 = r"C:\Financehub\app\templates\payment_application\index.html"
with open(f2, "r", encoding="utf-8") as f:
    t = f.read()
t = t.replace('<td class="num-right">Rp {{ "{:,.0f}".format(a.total_amount) }}</td>', '<td class="num-right">{{ a.total_amount | rupiah }}</td>')
t = t.replace('<option value="{{ m.id }}">{{ m.memo_number }} -- Rp {{ "{:,.0f}".format(m.total_amount) }}</option>', '<option value="{{ m.id }}">{{ m.memo_number }} -- {{ m.total_amount | rupiah }}</option>')
with open(f2, "w", encoding="utf-8") as f:
    f.write(t)


# 3. etf_payment_application/index.html
f3 = r"C:\Financehub\app\templates\etf_payment_application\index.html"
with open(f3, "r", encoding="utf-8") as f:
    t = f.read()
t = t.replace('<td class="num-right">Rp {{ "{:,.0f}".format(r.jumlah_pembayaran or 0) }}</td>', '<td class="num-right">{{ (r.jumlah_pembayaran or 0) | rupiah }}</td>')
with open(f3, "w", encoding="utf-8") as f:
    f.write(t)


# 4. sponsorship/outstanding.html
f4 = r"C:\Financehub\app\templates\sponsorship\outstanding.html"
with open(f4, "r", encoding="utf-8") as f:
    t = f.read()
t = t.replace('<td class="num-right">{{ "{:,.0f}".format(grand_total).replace(\',\', \'.\') }}</td>', '<td class="num-right">{{ grand_total | rupiah(false) }}</td>')
t = t.replace('<td class="num-right">{{ "{:,.0f}".format(sec.subtotal).replace(\',\', \'.\') }}</td>', '<td class="num-right">{{ sec.subtotal | rupiah(false) }}</td>')
t = t.replace('<td class="num-right">{{ "{:,.0f}".format(r.amount).replace(\',\', \'.\') }}</td>', '<td class="num-right">{{ r.amount | rupiah(false) }}</td>')
with open(f4, "w", encoding="utf-8") as f:
    f.write(t)

print("Task 5 complete")
