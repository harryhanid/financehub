with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

old_save = """    if (!hasValid) { showToast(`Siswa ${siswa_code} harus ada minimal 1 baris dengan amount > 0.`, "error"); return; }
  }

  const btn = document.getElementById("klaim-save-btn");"""

new_save = """    if (!hasValid) { showToast(`Siswa ${siswa_code} harus ada minimal 1 baris dengan amount > 0.`, "error"); return; }

    const totalSiswaAmt = rows.filter(r => r.siswa_code === siswa_code).reduce((sum, r) => sum + (r.amount || 0), 0);
    if (siswaRow._sisaBudget !== undefined && siswaRow._sisaBudget !== null && totalSiswaAmt > siswaRow._sisaBudget) {
      showToast(`Siswa ${siswa_code} melebihi sisa budget Medical (Amount: Rp ${totalSiswaAmt.toLocaleString("id-ID")}, Sisa: Rp ${siswaRow._sisaBudget.toLocaleString("id-ID")}).`, "error");
      return;
    }
  }

  const btn = document.getElementById("klaim-save-btn");"""

if old_save in text:
    text = text.replace(old_save, new_save)
    with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
        f.write(text)
    print("Added budget check to ipaySaveKlaim")
else:
    print("Could not find old_save")
