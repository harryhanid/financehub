import os

service_path = r'C:\Financehub\app\modules\sponsorship\service.py'
with open(service_path, 'r', encoding='utf-8') as f:
    service_content = f.read()

search_str = '''            key = (r["lembaga_perorangan"] or "", r["perihal"] or "")
            if key not in agg:
                agg[key] = {
                    "lembaga_perorangan": r["lembaga_perorangan"],
                    "perihal": r["perihal"],
                    "total": r["amount_request"],
                }
                for col in pillar_cols:
                    agg[key][col] = r[col]
            else:
                agg[key]["total"] += r["amount_request"]
                for col in pillar_cols:
                    agg[key][col] += r[col]

        aggregated_rows = list(agg.values())'''

replace_str = '''            key = (r["lembaga_perorangan"] or "", r["perihal"] or "")
            tgl_pay = str(r["tanggal_payment"]).strip() if r.get("tanggal_payment") else ""
            reff_val = str(r["reff"]).strip() if r.get("reff") else ""
            
            if key not in agg:
                agg[key] = {
                    "lembaga_perorangan": r["lembaga_perorangan"],
                    "perihal": r["perihal"],
                    "tanggal_payment_list": [tgl_pay] if tgl_pay else [],
                    "reff_list": [reff_val] if reff_val else [],
                    "total": r["amount_request"],
                }
                for col in pillar_cols:
                    agg[key][col] = r[col]
            else:
                if tgl_pay and tgl_pay not in agg[key]["tanggal_payment_list"]:
                    agg[key]["tanggal_payment_list"].append(tgl_pay)
                if reff_val and reff_val not in agg[key]["reff_list"]:
                    agg[key]["reff_list"].append(reff_val)
                    
                agg[key]["total"] += r["amount_request"]
                for col in pillar_cols:
                    agg[key][col] += r[col]

        for row_out in agg.values():
            row_out["tanggal_payment"] = ", ".join(row_out.pop("tanggal_payment_list", []))
            row_out["reff"] = ", ".join(row_out.pop("reff_list", []))
            
        aggregated_rows = list(agg.values())'''

if search_str in service_content:
    service_content = service_content.replace(search_str, replace_str)
    with open(service_path, 'w', encoding='utf-8') as f:
        f.write(service_content)
    print("Patch applied to service.py")
else:
    print("search_str not found in service.py")

