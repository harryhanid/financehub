// static/js/budget_carryover.js
async function budgetSubmitCarryover() {
  const budgetId = document.getElementById("cr-budget-id").value;
  const reason = document.getElementById("cr-reason").value;
  showLoading("Mengirim request carryover...");
  try {
    const resp = await apiFetch("/budget/carryover/request", {
      method: "POST", body: JSON.stringify({ budget_id: budgetId, reason: reason }),
    });
    const data = await resp.json();
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) setTimeout(() => window.location.reload(), 1000);
  } catch (e) {
    showToast("Gagal mengirim request carryover.", "error");
  } finally {
    hideLoading();
  }
}

async function budgetSubmitAdditional() {
  const budgetId = document.getElementById("cr-budget-id").value;
  const reason = document.getElementById("cr-reason").value;
  const amount = document.getElementById("cr-amount").value;
  showLoading("Mengirim request tambahan anggaran...");
  try {
    const resp = await apiFetch("/budget/additional/request", {
      method: "POST", body: JSON.stringify({ budget_id: budgetId, amount: amount, reason: reason }),
    });
    const data = await resp.json();
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) setTimeout(() => window.location.reload(), 1000);
  } catch (e) {
    showToast("Gagal mengirim request tambahan anggaran.", "error");
  } finally {
    hideLoading();
  }
}

async function budgetApproveRequest(budgetId, type) {
  const months = prompt("Perpanjangan berapa bulan?", type === "Carryover" ? "12" : "3");
  if (months === null) return;
  const endpoint = type === "Carryover" ? "/budget/carryover/" : "/budget/additional/";
  showLoading("Memproses approval...");
  try {
    const resp = await apiFetch(endpoint + budgetId + "/approve", {
      method: "POST", body: JSON.stringify({ extension_months: months }),
    });
    const data = await resp.json();
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) setTimeout(() => window.location.reload(), 1000);
  } catch (e) {
    showToast("Gagal memproses approval.", "error");
  } finally {
    hideLoading();
  }
}

async function budgetRejectRequest(budgetId, type) {
  const reason = prompt("Alasan penolakan?", "");
  if (reason === null) return;
  const endpoint = type === "Carryover" ? "/budget/carryover/" : "/budget/additional/";
  showLoading("Menolak request...");
  try {
    const resp = await apiFetch(endpoint + budgetId + "/reject", {
      method: "POST", body: JSON.stringify({ reason: reason }),
    });
    const data = await resp.json();
    showToast(data.pesan, data.ok ? "success" : "error");
    if (data.ok) setTimeout(() => window.location.reload(), 1000);
  } catch (e) {
    showToast("Gagal menolak request.", "error");
  } finally {
    hideLoading();
  }
}
