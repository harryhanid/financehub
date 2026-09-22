import sys
import re

def patch_js():
    with open(r'C:\Financehub\app\static\js\sponsorship.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # We need to add sponsorshipAddLine function.
    new_funcs = """
function sponsorshipAddLine() {
  const container = document.getElementById("sp-lines-container");
  const template = document.getElementById("sp-line-template");
  if (!template) return;
  const clone = template.content.cloneNode(true);
  
  // Setup autocomplete for this row
  const searchInput = clone.querySelector(".sp-line-cat1-search");
  const cat1Input = clone.querySelector(".sp-line-cat1");
  const cat2Input = clone.querySelector(".sp-line-cat2");
  const cat3Input = clone.querySelector(".sp-line-cat3");
  const resultsBox = clone.querySelector(".sp-line-cat1-results");
  const amountInput = clone.querySelector(".sp-line-amount");
  
  if (amountInput) {
    amountInput.addEventListener("input", function() {
      let v = this.value.replace(/[^0-9]/g, '');
      this.value = v ? parseInt(v, 10).toLocaleString('en-US') : '';
    });
  }
  
  if (searchInput && resultsBox) {
    searchInput.addEventListener("input", function () {
      const q = searchInput.value.trim().toLowerCase();
      cat1Input.value = "";
      cat2Input.value = "";
      cat3Input.value = "";
      if (!q) { resultsBox.classList.remove("open"); return; }
      const matches = sponsorshipPerusahaan.filter(function (p) {
        return p.cat1.toLowerCase().indexOf(q) !== -1;
      });
      
      resultsBox.innerHTML = "";
      if (matches.length === 0) {
        resultsBox.innerHTML = '<div class="sp-autocomplete-empty">Tidak ditemukan</div>';
      } else {
        matches.forEach(function (p) {
          const item = document.createElement("div");
          item.className = "sp-autocomplete-item";
          item.textContent = p.cat1 + " (" + p.cat3 + ")";
          item.onclick = function () {
            cat1Input.value = p.cat1;
            searchInput.value = p.cat1;
            cat2Input.value = p.cat2;
            cat3Input.value = p.cat3;
            resultsBox.classList.remove("open");
          };
          resultsBox.appendChild(item);
        });
      }
      resultsBox.classList.add("open");
    });
  }
  
  container.appendChild(clone);
}
"""
    # Append the new functions
    if "function sponsorshipAddLine(" not in content:
        content += new_funcs

    # Replace sponsorshipInputSubmit
    old_submit = """function sponsorshipInputSubmit() {
  const cat1 = document.getElementById("sp-in-cat1").value;
  if (!cat1) { showToast("Pilih Cat1 (Perusahaan) dari daftar.", "error"); return; }
  const payload = {
    cat: document.getElementById("sp-in-cat").value,
    description: document.getElementById("sp-in-description").value,
    cat1: cat1,
    cat4: document.getElementById("sp-in-cat4").value,
    lembaga_perorangan: document.getElementById("sp-in-lembaga").value,
    tanggal_form_sponsor: document.getElementById("sp-in-tanggal-form").value,
    tanggal_payment: document.getElementById("sp-in-tanggal-payment").value,
    perihal: document.getElementById("sp-in-perihal").value,
    amount_request: document.getElementById("sp-in-amount").value,
    reff: document.getElementById("sp-in-reff").value,
    status: document.getElementById("sp-in-status").value,
    coa: document.getElementById("sp-in-coa").value,
    cc_total: document.getElementById("sp-in-cc-total").value,
    cc: document.getElementById("sp-in-cc").value,
    source: document.getElementById("sp-in-source").value,
  };
  showLoading("Menyimpan transaksi Sponsorship...");
  apiFetch("/sponsorship/input/create", { method: "POST", body: JSON.stringify(payload) })
    .then(res => {
      hideLoading();
      if (res.ok) {
        showToast("Transaksi Sponsorship berhasil disimpan.", "success");
        setTimeout(() => { window.location.href = "/sponsorship/data"; }, 1000);
      } else {
        showToast(res.pesan || "Terjadi kesalahan", "error");
      }
    })
    .catch(err => {
      hideLoading();
      showToast("Gagal menyimpan transaksi.", "error");
    });
}"""

    new_submit = """function sponsorshipInputSubmit() {
  const container = document.getElementById("sp-lines-container");
  const rows = container.querySelectorAll(".sp-line-row");
  if (rows.length === 0) {
    showToast("Minimal harus ada 1 transaksi (baris).", "error");
    return;
  }
  
  let valid = true;
  const lines = [];
  rows.forEach((row, i) => {
    const cat1 = row.querySelector(".sp-line-cat1").value;
    if (!cat1) { showToast(`Baris ke-${i+1}: Pilih Cat1 (Perusahaan) dari daftar.`, "error"); valid = false; }
    let amt = row.querySelector(".sp-line-amount").value.replace(/[^0-9]/g, '');
    lines.push({
      cat1: cat1,
      cat4: row.querySelector(".sp-line-cat4").value,
      amount_request: amt ? parseInt(amt, 10) : 0
    });
  });
  if (!valid) return;

  const payload = {
    cat: document.getElementById("sp-in-cat").value,
    description: document.getElementById("sp-in-description").value,
    lembaga_perorangan: document.getElementById("sp-in-lembaga").value,
    tanggal_form_sponsor: document.getElementById("sp-in-tanggal-form").value,
    tanggal_payment: document.getElementById("sp-in-tanggal-payment").value,
    perihal: document.getElementById("sp-in-perihal").value,
    reff: document.getElementById("sp-in-reff").value,
    status: document.getElementById("sp-in-status").value,
    coa: document.getElementById("sp-in-coa").value,
    cc_total: document.getElementById("sp-in-cc-total").value,
    cc: document.getElementById("sp-in-cc").value,
    source: document.getElementById("sp-in-source").value,
    lines: lines
  };
  
  showLoading("Menyimpan transaksi Sponsorship...");
  apiFetch("/sponsorship/input/create-bulk", { method: "POST", body: JSON.stringify(payload) })
    .then(res => {
      hideLoading();
      if (res.ok) {
        showToast(res.pesan || "Transaksi Sponsorship berhasil disimpan.", "success");
        setTimeout(() => { window.location.href = "/sponsorship/data"; }, 1000);
      } else {
        showToast(res.pesan || "Terjadi kesalahan", "error");
      }
    })
    .catch(err => {
      hideLoading();
      showToast("Gagal menyimpan transaksi.", "error");
    });
}"""

    content = content.replace(old_submit, new_submit)

    # Initialize first line on load
    old_onload = """document.addEventListener("DOMContentLoaded", function () {
  sponsorshipLoadLookups();
  const search = document.getElementById("sp-in-cat1-search");"""
    
    new_onload = """document.addEventListener("DOMContentLoaded", function () {
  sponsorshipLoadLookups();
  if (document.getElementById("sp-lines-container")) {
    sponsorshipAddLine();
  }
  const search = document.getElementById("sp-in-cat1-search");"""

    content = content.replace(old_onload, new_onload)
    
    # Hide all open results on document click
    # The current js might not hide the new resultsboxes.
    # So let's add a global click listener for removing 'open' class
    global_click = """
  document.addEventListener("click", function(e) {
    if (!e.target.closest(".sp-line-cat1-search") && !e.target.closest(".sp-line-cat1-results")) {
      document.querySelectorAll(".sp-line-cat1-results.open").forEach(box => box.classList.remove("open"));
    }
  });
"""
    if 'document.querySelectorAll(".sp-line-cat1-results.open")' not in content:
        content += global_click

    with open(r'C:\Financehub\app\static\js\sponsorship.js', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Patched js successfully!")

if __name__ == '__main__':
    patch_js()
