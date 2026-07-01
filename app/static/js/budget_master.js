// static/js/budget_master.js
function budgetMasterClearForm() {
  document.getElementById("bm-id").value = "";
  document.getElementById("bm-company").value = "PO";
  ["bm-dept", "bm-mm", "bm-yy", "bm-gl-account", "bm-gl-description",
   "bm-category", "bm-activity", "bm-description", "bm-amount"].forEach(function (id) {
    document.getElementById(id).value = "";
  });
}

function budgetMasterEdit(id) {
  fetch("/budget/master/" + id).then(function (r) { return r.json(); }).then(function (data) {
    if (!data.ok) { showToast(data.pesan, "error"); return; }
    const b = data.budget;
    document.getElementById("bm-id").value = b.id;
    document.getElementById("bm-company").value = b.company;
    document.getElementById("bm-dept").value = b.dept || "";
    document.getElementById("bm-mm").value = b.mm;
    document.getElementById("bm-yy").value = b.yy;
    document.getElementById("bm-gl-account").value = b.gl_account || "";
    document.getElementById("bm-gl-description").value = b.gl_description || "";
    document.getElementById("bm-category").value = b.budget_category || "";
    document.getElementById("bm-activity").value = b.activity || "";
    document.getElementById("bm-description").value = b.description || "";
    document.getElementById("bm-amount").value = b.amount;
    openModal("budget-master-modal");
  }).catch(function () {
    showToast("Gagal memuat data budget.", "error");
  });
}

function budgetMasterSave() {
  const id = document.getElementById("bm-id").value;
  const payload = {
    company: document.getElementById("bm-company").value,
    dept: document.getElementById("bm-dept").value,
    mm: document.getElementById("bm-mm").value,
    yy: document.getElementById("bm-yy").value,
    gl_account: document.getElementById("bm-gl-account").value,
    gl_description: document.getElementById("bm-gl-description").value,
    budget_category: document.getElementById("bm-category").value,
    activity: document.getElementById("bm-activity").value,
    description: document.getElementById("bm-description").value,
    amount: document.getElementById("bm-amount").value,
  };
  const url = id ? "/budget/master/" + id + "/update" : "/budget/master/create";
  fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }).then(function (r) { return r.json(); }).then(function (data) {
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) { closeModal("budget-master-modal"); window.location.reload(); }
  }).catch(function () {
    showToast("Gagal menyimpan budget.", "error");
  });
}

function budgetMasterDelete(id) {
  confirmModal("Hapus budget " + id + "?", { type: "danger" }).then(function (confirmed) {
    if (!confirmed) return;
    fetch("/budget/master/" + id + "/delete", { method: "POST" })
      .then(function (r) { return r.json(); }).then(function (data) {
        showToast(data.pesan, data.ok ? "success" : "error");
        if (data.ok) window.location.reload();
      }).catch(function () {
        showToast("Gagal menghapus budget.", "error");
      });
  });
}

document.addEventListener("DOMContentLoaded", budgetMasterClearForm);
