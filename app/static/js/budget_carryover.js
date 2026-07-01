// static/js/budget_carryover.js
function budgetSubmitCarryover() {
  const budgetId = document.getElementById("cr-budget-id").value;
  const reason = document.getElementById("cr-reason").value;
  fetch("/budget/carryover/request", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ budget_id: budgetId, reason: reason }),
  }).then(function (r) { return r.json(); }).then(function (data) {
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) window.location.reload();
  }).catch(function () {
    showToast("Gagal mengirim request carryover.", "error");
  });
}

function budgetSubmitAdditional() {
  const budgetId = document.getElementById("cr-budget-id").value;
  const reason = document.getElementById("cr-reason").value;
  const amount = document.getElementById("cr-amount").value;
  fetch("/budget/additional/request", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ budget_id: budgetId, amount: amount, reason: reason }),
  }).then(function (r) { return r.json(); }).then(function (data) {
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) window.location.reload();
  }).catch(function () {
    showToast("Gagal mengirim request tambahan anggaran.", "error");
  });
}

function budgetApproveRequest(budgetId, type) {
  const months = prompt("Perpanjangan berapa bulan?", type === "Carryover" ? "12" : "3");
  if (months === null) return;
  const endpoint = type === "Carryover" ? "/budget/carryover/" : "/budget/additional/";
  fetch(endpoint + budgetId + "/approve", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ extension_months: months }),
  }).then(function (r) { return r.json(); }).then(function (data) {
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) window.location.reload();
  }).catch(function () {
    showToast("Gagal memproses approval.", "error");
  });
}

function budgetRejectRequest(budgetId) {
  const reason = prompt("Alasan penolakan?", "");
  if (reason === null) return;
  fetch("/budget/carryover/" + budgetId + "/reject", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: reason }),
  }).then(function (r) { return r.json(); }).then(function (data) {
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) window.location.reload();
  }).catch(function () {
    showToast("Gagal menolak request.", "error");
  });
}
