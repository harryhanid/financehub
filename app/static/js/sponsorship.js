// static/js/sponsorship.js — Sponsorship module (Input / Data / Dashboard)
let sponsorshipPerusahaan = [];

function sponsorshipLoadLookups() {
  const search = document.getElementById("sp-in-cat1-search");
  if (!search) return;  // not on the Input page
  apiFetch("/sponsorship/api/lookups").then(function (r) { return r.json(); }).then(function (data) {
    sponsorshipPerusahaan = data.perusahaan || [];
    const datalist = document.getElementById("sp-lembaga-datalist");
    (data.lembaga || []).forEach(function (name) {
      const opt = document.createElement("option");
      opt.value = name;
      datalist.appendChild(opt);
    });
  });
}

function _sponsorshipRenderCat1Results(matches) {
  const box = document.getElementById("sp-in-cat1-results");
  box.innerHTML = "";
  if (matches.length === 0) {
    box.innerHTML = '<div class="sp-autocomplete-empty">Tidak ditemukan</div>';
  } else {
    matches.forEach(function (p) {
      const item = document.createElement("div");
      item.className = "sp-autocomplete-item";
      item.textContent = p.cat1 + " (" + p.cat3 + ")";
      item.onclick = function () { _sponsorshipSelectCat1(p); };
      box.appendChild(item);
    });
  }
  box.classList.add("open");
}

function _sponsorshipSelectCat1(p) {
  document.getElementById("sp-in-cat1").value = p.cat1;
  document.getElementById("sp-in-cat1-search").value = p.cat1;
  document.getElementById("sp-in-cat2").value = p.cat2;
  document.getElementById("sp-in-cat3").value = p.cat3;
  document.getElementById("sp-in-cat1-results").classList.remove("open");
}

function sponsorshipInputSubmit() {
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
    .then(function (r) { return r.json(); })
    .then(function (data) {
      showToast(data.pesan, data.ok ? "success" : "error");
      if (data.ok) { setTimeout(function () { window.location.href = "/sponsorship/data"; }, 1000); }
    })
    .catch(function () { showToast("Gagal menyimpan transaksi.", "error"); })
    .finally(function () { hideLoading(); });
}

document.addEventListener("DOMContentLoaded", function () {
  sponsorshipLoadLookups();
  const search = document.getElementById("sp-in-cat1-search");
  if (search) {
    search.addEventListener("input", function () {
      const q = search.value.trim().toLowerCase();
      document.getElementById("sp-in-cat1").value = "";
      document.getElementById("sp-in-cat2").value = "";
      document.getElementById("sp-in-cat3").value = "";
      if (!q) { document.getElementById("sp-in-cat1-results").classList.remove("open"); return; }
      const matches = sponsorshipPerusahaan.filter(function (p) {
        return p.cat1.toLowerCase().indexOf(q) !== -1;
      });
      _sponsorshipRenderCat1Results(matches);
    });
  }
});
