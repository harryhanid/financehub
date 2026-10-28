with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "INSERT INTO payment_beasiswa" in line and "tgl_pengajuan" in lines[i+3]:
        for j in range(i-2, i+15):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
