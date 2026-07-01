// static/js/budget_realisasi.js
function budgetRealisasiClearForm() {
  document.getElementById("br-trx-id").value = "";
  document.getElementById("br-budget-id").value = "";
  document.getElementById("br-tanggal").value = "";
  document.getElementById("br-description").value = "";
  document.getElementById("br-amount").value = "";
}

function budgetRealisasiEdit(btn) {
  // Data read from the row's data-* attributes (Jinja-escaped attribute context)
  // instead of being interpolated into the onclick JS string, so free-text
  // fields like description can't break out of the inline handler.
  const row = btn.closest("tr");
  document.getElementById("br-trx-id").value = row.dataset.trxId || "";
  document.getElementById("br-budget-id").value = "";
  document.getElementById("br-description").value = row.dataset.description || "";
  document.getElementById("br-amount").value = row.dataset.amount || "";
  document.getElementById("br-tanggal").value = row.dataset.tanggal || "";
  openModal("budget-realisasi-modal");
}

function budgetRealisasiSave() {
  const trxId = document.getElementById("br-trx-id").value;
  const payload = {
    budget_id: document.getElementById("br-budget-id").value,
    tanggal_realisasi: document.getElementById("br-tanggal").value,
    description: document.getElementById("br-description").value,
    amount: document.getElementById("br-amount").value,
  };
  const url = trxId ? "/budget/realisasi/" + trxId + "/update" : "/budget/realisasi/create";
  fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }).then(function (r) { return r.json(); }).then(function (data) {
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) { closeModal("budget-realisasi-modal"); window.location.reload(); }
  }).catch(function () {
    showToast("Gagal menyimpan realisasi.", "error");
  });
}

function budgetRealisasiDelete(trxId) {
  confirmModal("Hapus transaksi " + trxId + "?", { type: "danger" }).then(function (confirmed) {
    if (!confirmed) return;
    fetch("/budget/realisasi/" + trxId + "/delete", { method: "POST" })
      .then(function (r) { return r.json(); }).then(function (data) {
        showToast(data.pesan, data.ok ? "success" : "error");
        if (data.ok) window.location.reload();
      }).catch(function () {
        showToast("Gagal menghapus realisasi.", "error");
      });
  });
}

document.addEventListener("DOMContentLoaded", budgetRealisasiClearForm);
