async function apiFetch(url, options = {}) {
  const defaults = {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  };
  const resp = await fetch(url, { ...defaults, ...options });
  if (resp.status === 401) {
    const refreshed = await tryRefresh();
    if (refreshed) return fetch(url, { ...defaults, ...options });
    window.location.href = "/auth/login";
    return null;
  }
  return resp;
}

async function tryRefresh() {
  const resp = await fetch("/auth/refresh", {
    method: "POST", credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  return resp.ok;
}

function doLogout() {
  apiFetch("/auth/logout", { method: "POST", body: JSON.stringify({}) })
    .then(() => { window.location.href = "/auth/login"; });
}

function initTabs(container) {
  const tabs = container.querySelectorAll(".tab-btn");
  const panels = container.querySelectorAll(".tab-panel");
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      panels.forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const target = container.querySelector(`#${btn.dataset.tab}`);
      if (target) target.classList.add("active");
    });
  });
  if (tabs.length > 0) tabs[0].click();
}

function fmtRupiah(n) {
  return new Intl.NumberFormat("id-ID").format(n || 0);
}

function showToast(msg, type = "success") {
  let toast = document.getElementById("fh-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "fh-toast";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = type === "success" ? "toast-success" : type === "info" ? "toast-info" : "toast-error";
  toast.style.opacity = "1";
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { toast.style.opacity = "0"; }, 3000);
}

function openModal(id) { const el = document.getElementById(id); if (el) el.classList.add("open"); }
function closeModal(id) { const el = document.getElementById(id); if (el) el.classList.remove("open"); }

function staggerRows(tbody) {
  Array.from(tbody.querySelectorAll("tr")).forEach((row, i) => {
    row.classList.add("stagger-row");
    row.style.animationDelay = `${i * 28}ms`;
    row.style.animationFillMode = "both";
  });
}

function animateCounter(el, duration = 700) {
  const target = parseFloat(el.dataset.count);
  if (isNaN(target) || target === 0) return;
  const prefix = el.dataset.prefix || "";
  const fmt = new Intl.NumberFormat("id-ID");
  const start = performance.now();
  const step = (now) => {
    const p = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    el.textContent = prefix + fmt.format(Math.round(ease * target));
    if (p < 1) requestAnimationFrame(step);
    else el.textContent = prefix + fmt.format(target);
  };
  requestAnimationFrame(step);
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.classList.remove("open"); });
  });
  document.querySelectorAll("tbody").forEach(staggerRows);
  document.querySelectorAll(".stat-value[data-count]").forEach(el => animateCounter(el));
});
