/* ── Global action feedback ────────────────────────────────
   Every user-initiated mutating request (POST/PUT/PATCH/DELETE) asks for
   confirmation first and always shows progress, so a module no longer has to
   wire confirmModal()/showLoading() by hand — many didn't, which is why some
   buttons executed instantly and some waits showed nothing.
   Loaded by base.html after app.js and confirmModal().
   Opt-outs: data-no-confirm on the clicked element (or an ancestor), or
   fetch(url, { fhNoConfirm: true }). data-confirm="..." / data-confirm-title
   customise the message. A flow that already asked via confirmModal()/confirm()
   is not asked twice. */
(function () {
  const MUTATING = /^(POST|PUT|PATCH|DELETE)$/;
  // Requests that never need a confirmation (auth plumbing, read-only POSTs).
  const NO_CONFIRM = /^\/auth\/|\/login\b|\/logout\b|\/refresh\b|\/export\b|\/download|\/preview|\/search|\/lookups?\b|\/check\b/i;
  const DANGER = /hapus|delete|remove|tolak|reject|batal|cancel|reset|void|nonaktif|deactivate|revoke|purge|kosongkan|clear/i;
  const INTERACTIVE = 'button, a[href], [role="button"], input, select, textarea, label, [onclick], [data-action]';
  const GESTURE_MS = 6000;

  let gesture = null;          // { el, t, approved }
  let pendingAll = 0;
  let autoOverlay = 0;         // overlays this module opened (vs. the caller's own)
  let barTimer = null;

  function now() { return Date.now(); }

  function record(el) {
    if (!el || el.closest("#modal-confirm")) return;   // OK/Cancel of the dialog itself
    gesture = { el, t: now(), approved: false };
  }
  document.addEventListener("click", e => record(e.target.closest(INTERACTIVE)), true);
  document.addEventListener("keydown", e => {
    if (e.key === "Enter" && e.target instanceof Element) record(e.target.closest(INTERACTIVE));
  }, true);
  document.addEventListener("change", e => {
    if (e.target.matches && e.target.matches('input[type="file"]')) record(e.target);
  }, true);

  function liveGesture() { return gesture && now() - gesture.t < GESTURE_MS ? gesture : null; }

  // confirmModal() (base.html) and the native dialogs call this when the user agrees.
  window.fhMarkApproved = function () {
    if (gesture) { gesture.approved = true; gesture.t = now(); }
    else gesture = { el: null, t: now(), approved: true };
  };
  const nativeConfirm = window.confirm.bind(window);
  window.confirm = function (m) { const ok = nativeConfirm(m); if (ok) fhMarkApproved(); return ok; };
  const nativePrompt = window.prompt.bind(window);
  window.prompt = function (m, d) { const v = nativePrompt(m, d); if (v !== null) fhMarkApproved(); return v; };
  const nativeAlert = window.alert.bind(window);
  window.alert = function (m) { if (now() < (window._fhSuppressErrorsUntil || 0)) return; nativeAlert(m); };

  function labelOf(el) {
    if (!el) return "";
    if (el.matches('input[type="file"]')) {
      const f = el.files && el.files[0];
      return f ? 'Unggah "' + f.name + '"' : "Unggah file";
    }
    let t = el.getAttribute("aria-label") || el.getAttribute("title") || "";
    if (!t) t = (el.tagName === "INPUT" ? el.value : el.textContent) || "";
    t = t.replace(/\s+/g, " ").trim();
    return t.length > 40 ? t.slice(0, 38) + "…" : t;
  }

  function askConfirm(g, method, path) {
    const host = g.el && g.el.closest("[data-confirm]");
    const label = labelOf(g.el);
    const danger = method === "DELETE" || DANGER.test(label) || DANGER.test(path);
    const msg = (host && host.dataset.confirm) || (danger
      ? (label ? 'Aksi "' + label + '"' : "Aksi ini") + " akan mengubah/menghapus data dan tidak bisa dikembalikan. Lanjutkan?"
      : (label ? 'Jalankan "' + label + '"?' : "Jalankan aksi ini?") + " Pastikan data sudah benar sebelum melanjutkan.");
    const title = (host && host.dataset.confirmTitle) || (danger ? "Konfirmasi Hapus / Batal" : "Konfirmasi Aksi");
    const okText = label && label.length <= 18 && !/^Unggah "/.test(label) ? label : (danger ? "Ya, lanjutkan" : "Lanjutkan");
    return window.confirmModal(msg, { type: danger ? "danger" : "primary", title, confirmText: okText });
  }

  /* Progress feedback: a slim top bar for every request/navigation, a spinner
     on the clicked button, and the blocking overlay when a mutation runs long. */
  function bar() {
    let b = document.getElementById("fh-progress");
    if (!b) {
      b = document.createElement("div");
      b.id = "fh-progress";
      b.setAttribute("aria-hidden", "true");
      document.body.appendChild(b);
    }
    return b;
  }
  function barStart(delay) {
    clearTimeout(barTimer);
    barTimer = setTimeout(() => { bar().classList.add("show"); document.body.setAttribute("aria-busy", "true"); }, delay);
  }
  function barStop() {
    clearTimeout(barTimer);
    const b = document.getElementById("fh-progress");
    if (b) b.classList.remove("show");
    document.body.removeAttribute("aria-busy");
  }
  window.fhProgress = { start: () => barStart(0), stop: barStop };

  function busyEl(g) {
    const el = g && g.el && g.el.closest("button, .btn, input[type=submit]");
    return el && !el.closest("#modal-confirm") ? el : null;
  }
  function setBusy(el, on) {
    if (!el) return;
    el._fhBusy = (el._fhBusy || 0) + (on ? 1 : -1);
    if (on && el._fhBusy === 1) {
      el._fhPrevDisabled = el.disabled;
      el.disabled = true;
      el.classList.add("fh-busy");
      el.setAttribute("aria-busy", "true");
      if (el.tagName === "BUTTON") el.insertAdjacentHTML("afterbegin", '<span class="fh-btn-spin" aria-hidden="true"></span>');
    } else if (!on && el._fhBusy <= 0) {
      el._fhBusy = 0;
      el.disabled = !!el._fhPrevDisabled;
      el.classList.remove("fh-busy");
      el.removeAttribute("aria-busy");
      el.querySelectorAll(":scope > .fh-btn-spin").forEach(s => s.remove());
    }
  }
  function overlay() { return document.getElementById("fh-load-ov"); }
  function overlayShown() { const o = overlay(); return !!(o && o.classList.contains("show")); }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = async function (input, init) {
    init = init || {};
    const method = String(init.method || (input instanceof Request ? input.method : "GET")).toUpperCase();
    let path = "";
    try { path = new URL(typeof input === "string" ? input : input.url, location.href).pathname; } catch (_) {}
    const mutating = MUTATING.test(method);
    const g = mutating ? liveGesture() : null;

    if (g && !g.approved && !init.fhNoConfirm && !NO_CONFIRM.test(path)
        && !(g.el && g.el.closest("[data-no-confirm]")) && window.confirmModal) {
      // A caller that already showed its loading overlay would cover the dialog (z-index).
      const hadOverlay = overlayShown();
      if (hadOverlay) overlay().classList.remove("show");
      const ok = await askConfirm(g, method, path);
      if (!ok) {
        window._fhSuppressErrorsUntil = now() + 1500;
        hideLoading();
        showToast("Aksi dibatalkan", "info");
        gesture = null;
        throw new DOMException("Dibatalkan oleh pengguna", "AbortError");
      }
      if (hadOverlay) overlay().classList.add("show");
      g.approved = true;
    }

    const btn = mutating ? busyEl(g) : null;
    let ovTimer = null;
    pendingAll++;
    barStart(mutating ? 0 : 200);
    setBusy(btn, true);
    if (mutating) ovTimer = setTimeout(() => {
      if (!overlayShown()) { autoOverlay++; showLoading("Memproses..."); }
    }, 700);
    if (g) g.t = now();   // keep a multi-request flow inside one approval
    try {
      return await nativeFetch(input, init);
    } finally {
      clearTimeout(ovTimer);
      setBusy(btn, false);
      if (--pendingAll <= 0) { pendingAll = 0; barStop(); }
      if (autoOverlay && pendingAll === 0) { autoOverlay = 0; hideLoading(); }
      if (g) g.t = now();
    }
  };

  // Cancelled confirmations surface as AbortError; keep the console clean for
  // callers that never catch.
  window.addEventListener("unhandledrejection", e => {
    if (e.reason && e.reason.name === "AbortError" && now() < (window._fhSuppressErrorsUntil || 0)) e.preventDefault();
  });

  /* Classic <form method=post>: same confirmation, then progress. */
  document.addEventListener("submit", async e => {
    const form = e.target;
    let path = "";
    try { path = new URL(form.action, location.href).pathname; } catch (_) {}
    const skip = form._fhConfirmed || (form.method || "").toLowerCase() !== "post"
      || form.closest("[data-no-confirm]") || NO_CONFIRM.test(path) || /select-company/.test(path);
    if (skip) { form._fhConfirmed = false; return; }
    e.preventDefault();
    e.stopImmediatePropagation();
    const g = { el: e.submitter || form.querySelector("[type=submit]") || form, approved: false };
    if (!(await askConfirm(g, "POST", path))) return;
    form._fhConfirmed = true;
    window.fhMarkApproved();   // a JS submit handler that fetch()es must not ask again
    setBusy(busyEl(g), true);
    if (form.requestSubmit) form.requestSubmit(e.submitter || undefined); else form.submit();
  }, true);
  // Bubble phase: only a submit nobody handled in JS actually navigates.
  window.addEventListener("submit", e => { if (!e.defaultPrevented) barStart(0); });

  /* Full-page navigation (server-rendered pages can take seconds): show the bar
     as soon as the user leaves, not after the next page paints. */
  document.addEventListener("click", e => {
    const a = e.target.closest("a[href]");
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (a.target && a.target !== "_self") return;
    const href = a.getAttribute("href");
    if (!href || href.startsWith("#") || href.startsWith("javascript:") || href.startsWith("mailto:")) return;
    let u;
    try { u = new URL(a.href, location.href); } catch (_) { return; }
    if (u.origin !== location.origin) return;
    if (a.hasAttribute("download") || /export|download|\.(xlsx|xlsb|csv|pdf|docx|pptx|zip)$/i.test(u.pathname)) {
      showToast("Menyiapkan file unduhan...", "info");
      barStart(0);
      setTimeout(barStop, 4000);
      return;
    }
    if (u.pathname === location.pathname && u.search === location.search && u.hash) return;
    barStart(0);
  });
  window.addEventListener("pageshow", barStop);   // back/forward cache restore
})();
