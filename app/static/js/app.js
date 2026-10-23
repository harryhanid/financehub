/* ── Module registry ──────────────────────────────────── */
const FH_MODULES = [
  { name: "Dashboard",             url: "/dashboard",               active: true  },
  { name: "Beasiswa",              url: "/beasiswa",                active: true  },
  { name: "Payment Approval Memo", url: "/payment-memo",            active: true  },
  { name: "Payment Application",   url: "/etf-payment-application", active: true  },
  { name: "Budget",                url: "/budget/",                 active: true  },
  { name: "Users",                 url: "/users",                   active: true  },
  { name: "Bank",                  url: "/bank",                    active: true  },
  { name: "Account Payable",       url: null,                       active: false },
  { name: "Advance",               url: null,                       active: false },
  { name: "Petty Cash",            url: null,                       active: false },
  { name: "Sponsorship",           url: "/sponsorship/",            active: true  },
];
const FH_RECENT_KEY = 'fh_recent_modules';

// Company-filtered module list + sub-tab previews for the Alt+Down carousel,
// rendered server-side by inject_nav_modules() in app.py — see base.html's
// #fh-nav-modules-data script tag. Read once at load; server always injects
// this tag (nav_modules is always in template context, empty list when
// logged out), so this never needs to re-fetch.
const FH_NAV_MODULES = (function() {
  var el = document.getElementById('fh-nav-modules-data');
  if (!el) return [];
  try { return JSON.parse(el.textContent); } catch (e) { return []; }
})();

// One small flow-line-style icon per real module, keyed by nav_modules' `key`.
const FH_MODULE_ICONS = {
  dashboard: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  beasiswa: '<path d="M12 3 2 8l10 5 10-5-10-5Z"/><path d="M6 10.5V16c0 1.5 3 3 6 3s6-1.5 6-3v-5.5"/>',
  payment_memo: '<path d="M6 2h9l4 4v16H6Z"/><path d="M15 2v4h4"/><path d="M9 13l2 2 4-4"/>',
  etf_payment_app: '<path d="M6 2h8l5 5v15H6Z"/><path d="M14 2v5h5"/><path d="M12 12v6M9 15l3-3 3 3"/>',
  budget: '<path d="M12 12V4a8 8 0 0 1 8 8h-8Z"/><circle cx="12" cy="12" r="8"/>',
  management_report: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  general_ledger: '<path d="M5 3h11l3 3v15H5Z"/><path d="M8 9h8M8 13h8M8 17h5"/>',
  bank: '<path d="M3 10l9-6 9 6"/><path d="M5 10v9M9 10v9M15 10v9M19 10v9"/><path d="M3 21h18"/>',
  spt_badan: '<path d="M6 2h9l4 4v16H6Z"/><path d="M15 2v4h4"/><path d="M9 12h6M9 16h6"/>',
  sponsorship: '<rect x="3" y="8" width="18" height="13" rx="1"/><path d="M3 12h18"/><path d="M12 8v13"/><path d="M12 8c-1.5-4-6-4-6-1s3 1 6 1Zm0 0c1.5-4 6-4 6-1s-3 1-6 1Z"/>',
  users: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
};

function _fhGetRecent() {
  try { return JSON.parse(localStorage.getItem(FH_RECENT_KEY) || '[]'); } catch (e) { return []; }
}
function _fhRecordVisit(url) {
  if (!url) return;
  var recent = _fhGetRecent().filter(function(u) { return u !== url; });
  recent.unshift(url);
  localStorage.setItem(FH_RECENT_KEY, JSON.stringify(recent.slice(0, 5)));
}

function getCurrentModule() {
  return FH_MODULES.find(function(m) {
    return m.active && m.url && window.location.pathname.replace(/\/$/, '') === m.url.replace(/\/$/, '');
  });
}

function initCommandPalette() {
  /* Record current page in recently-visited (kept for possible future use —
     the carousel itself has no "recently visited" section, see spec). */
  var currentMod = getCurrentModule();
  if (currentMod) _fhRecordVisit(currentMod.url);

  var ov       = document.getElementById('fh-cmd-ov');
  var input    = document.getElementById('fh-cmd-input');
  var track    = document.getElementById('fh-cmd-track');
  var dotsEl   = document.getElementById('fh-cmd-dots');
  var prevBtn  = document.getElementById('fh-cmd-prev');
  var nextBtn  = document.getElementById('fh-cmd-next');
  var btn      = document.getElementById('fh-cmd-btn');
  if (!ov || !input || !track || !dotsEl) return;

  var allModules       = _carouselModules();
  var filtered         = allModules;
  var activeIdx        = 0;
  var openCurrentMod   = null;   // the module the user was in when they opened the overlay
  var openCurrentTab   = null;   // its ?tab= value at open time, if any
  var dragStartX       = null;

  function _carouselModules() {
    var real = FH_NAV_MODULES.map(function(m) {
      return { name: m.name, url: m.url, key: m.key, subtabs: m.subtabs || [], active: true };
    });
    return real;
  }

  function _currentNavModule() {
    return FH_NAV_MODULES.find(function(m) {
      return window.location.pathname.replace(/\/$/, '') === m.url.replace(/\/$/, '');
    });
  }

  function open() {
    filtered = allModules;
    openCurrentMod = _currentNavModule();
    openCurrentTab = new URLSearchParams(window.location.search).get('tab');
    activeIdx = 0;
    if (openCurrentMod) {
      var found = filtered.findIndex(function(m) { return m.key === openCurrentMod.key; });
      if (found !== -1) activeIdx = found;
    }
    input.value = '';
    ov.classList.add('open');
    render();
    input.focus();
  }
  function close() {
    ov.classList.remove('open');
  }

  function step(delta) {
    if (!filtered.length) return;
    activeIdx = (activeIdx + delta + filtered.length) % filtered.length;
    render();
  }

  function _openModule(mod) {
    if (!mod || !mod.active || !mod.url) return;
    _fhRecordVisit(mod.url);
    close();
    window.location.href = mod.url;
  }

  function _openSubtab(mod, t) {
    var dest = t.url || (mod.url + (mod.url.indexOf('?') === -1 ? '?' : '&') + 'tab=' + t.tab);
    _fhRecordVisit(mod.url);
    close();
    window.location.href = dest;
  }

  function _isActiveTab(mod, t) {
    if (!openCurrentMod || mod.key !== openCurrentMod.key) return false;
    if (t.url) return window.location.pathname.replace(/\/$/, '') === t.url.replace(/\/$/, '');
    var defaultTab = mod.subtabs.length ? mod.subtabs[0].tab : null;
    return t.tab === (openCurrentTab || defaultTab);
  }

  function _card(mod, isMain) {
    var outer = document.createElement('div');
    outer.className = isMain ? 'fh-cmd-card-main' : 'fh-cmd-card-side';

    var bezel = document.createElement('div');
    bezel.className = 'fh-cmd-card-outer';
    var inner = document.createElement('div');
    inner.className = 'fh-cmd-card-inner';

    if (mod.key) {
      var icon = document.createElement('div');
      icon.className = 'fh-cmd-icon';
      icon.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + (FH_MODULE_ICONS[mod.key] || '') + '</svg>';
      inner.appendChild(icon);
    }

    var name = document.createElement('div');
    name.className = 'fh-cmd-card-name';
    name.textContent = mod.name;
    inner.appendChild(name);

    if (!mod.active) {
      var badge = document.createElement('div');
      badge.className = 'fh-cmd-badge';
      badge.textContent = 'Coming Soon';
      inner.appendChild(badge);
    } else if (isMain && mod.subtabs.length) {
      var line = document.createElement('div');
      line.className = 'fh-cmd-tabline';
      inner.appendChild(line);
      mod.subtabs.forEach(function(t) {
        var row = document.createElement('div');
        row.className = 'fh-cmd-tab' + (_isActiveTab(mod, t) ? ' active' : '');
        row.textContent = t.label;
        row.addEventListener('click', function(e) {
          e.stopPropagation();
          _openSubtab(mod, t);
        });
        inner.appendChild(row);
      });
    }

    if (mod.active && mod.url) {
      outer.style.cursor = 'pointer';
      outer.addEventListener('click', function() {
        if (isMain) { _openModule(mod); }
        else { activeIdx = filtered.indexOf(mod); render(); }
      });
    }

    bezel.appendChild(inner);
    outer.appendChild(bezel);
    return outer;
  }

  function render() {
    track.innerHTML = '';
    dotsEl.innerHTML = '';
    if (!filtered.length) {
      var empty = document.createElement('div');
      empty.className = 'fh-cmd-empty';
      empty.textContent = 'Tidak ada modul ditemukan.';
      track.appendChild(empty);
      return;
    }
    activeIdx = Math.max(0, Math.min(activeIdx, filtered.length - 1));
    for (var i = -1; i <= 1; i++) {
      var idx = activeIdx + i;
      if (idx < 0 || idx >= filtered.length) continue;
      track.appendChild(_card(filtered[idx], i === 0));
    }
    filtered.forEach(function(m, i) {
      var dot = document.createElement('span');
      if (i === activeIdx) dot.className = 'on';
      dotsEl.appendChild(dot);
    });
  }

  input.addEventListener('input', function() {
    var q = input.value.trim().toLowerCase();
    filtered = q ? allModules.filter(function(m) { return m.name.toLowerCase().indexOf(q) !== -1; }) : allModules;
    activeIdx = 0;
    render();
  });

  if (prevBtn) prevBtn.addEventListener('click', function() { step(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function() { step(1); });

  track.addEventListener('pointerdown', function(e) { dragStartX = e.clientX; });
  track.addEventListener('pointerup', function(e) {
    if (dragStartX === null) return;
    var dx = e.clientX - dragStartX;
    dragStartX = null;
    if (dx > 40) step(-1); else if (dx < -40) step(1);
  });

  document.addEventListener('keydown', function(e) {
    if (e.altKey && !e.ctrlKey && !e.metaKey && e.key === 'ArrowDown') {
      e.preventDefault();
      ov.classList.contains('open') ? close() : open();
      return;
    }
    if (!ov.classList.contains('open')) return;
    if (e.key === 'Escape')     { e.preventDefault(); close(); }
    if (e.key === 'ArrowLeft')  { e.preventDefault(); step(-1); }
    if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
    if (e.key === 'Enter') {
      e.preventDefault();
      _openModule(filtered[activeIdx]);
    }
  });

  ov.addEventListener('click', function(e) { if (e.target === ov) close(); });
  if (btn) btn.addEventListener('click', open);
}

function initTitleDropdown() {
  var cmdBtn = document.getElementById('fh-cmd-btn');
  if (!cmdBtn) return; // no company context on this page (e.g. login, select-company)

  var titleEl = document.querySelector('.main h1');
  if (!titleEl || titleEl.classList.contains('fh-title-trigger')) return;

  var activeMods = FH_MODULES.filter(function(m) { return m.active; });
  if (activeMods.length < 2) return; // nothing to switch to

  var currentMod = getCurrentModule();

  /* Wrap the h1 so the dropdown panel can position itself relative to
     just the title's box, not the full-width row it usually sits in. */
  var wrap = document.createElement('div');
  wrap.className = 'fh-title-wrap';
  titleEl.parentNode.insertBefore(wrap, titleEl);
  wrap.appendChild(titleEl);

  titleEl.classList.add('fh-title-trigger');
  titleEl.setAttribute('role', 'button');
  titleEl.setAttribute('tabindex', '0');
  titleEl.setAttribute('aria-haspopup', 'listbox');
  titleEl.setAttribute('aria-expanded', 'false');

  var chevron = document.createElement('span');
  chevron.className = 'fh-title-chevron';
  chevron.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
  titleEl.appendChild(chevron);

  var panel = document.createElement('div');
  panel.className = 'fh-title-dd';
  panel.setAttribute('role', 'listbox');

  activeMods.forEach(function(m) {
    var isCurrent = !!currentMod && m.url === currentMod.url;
    var item = document.createElement('div');
    item.className = 'fh-title-dd-item' + (isCurrent ? ' current' : '');
    item.setAttribute('role', 'option');
    item.innerHTML = '<span>' + m.name + '</span>' + (isCurrent
      ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
      : '');
    if (!isCurrent) {
      item.addEventListener('click', function() {
        _fhRecordVisit(m.url);
        window.location.href = m.url;
      });
    }
    panel.appendChild(item);
  });
  wrap.appendChild(panel);

  function open() {
    panel.classList.add('open');
    titleEl.setAttribute('aria-expanded', 'true');
  }
  function close() {
    panel.classList.remove('open');
    titleEl.setAttribute('aria-expanded', 'false');
  }
  function toggle(e) {
    e.stopPropagation();
    if (panel.classList.contains('open')) close(); else open();
  }

  titleEl.addEventListener('click', toggle);
  titleEl.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(e); }
    else if (e.key === 'Escape') { close(); }
  });
  document.addEventListener('click', function(e) {
    if (!wrap.contains(e.target)) close();
  });
}

function initModuleSwitchDropdown() {
  var trigger = document.getElementById('fh-mod-trigger');
  var panel   = document.getElementById('fh-mod-dd');
  if (!trigger || !panel) return;

  function open() {
    panel.classList.add('open');
    trigger.setAttribute('aria-expanded', 'true');
  }
  function close() {
    panel.classList.remove('open');
    trigger.setAttribute('aria-expanded', 'false');
  }
  function toggle(e) {
    e.stopPropagation();
    if (panel.classList.contains('open')) close(); else open();
  }

  trigger.addEventListener('click', toggle);
  trigger.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(e); }
    else if (e.key === 'Escape') { close(); }
  });
  panel.querySelectorAll('.fh-mod-dd-item[data-url]').forEach(function(item) {
    item.addEventListener('click', function() {
      window.location.href = item.dataset.url;
    });
  });
  document.addEventListener('click', function(e) {
    if (!trigger.contains(e.target) && !panel.contains(e.target)) close();
  });
}

function initHeaderTabFade() {
  document.querySelectorAll('.navbar-menu').forEach(function(el) {
    function update() {
      var atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 1;
      el.classList.toggle('fh-overflow', el.scrollWidth > el.clientWidth + 1 && !atEnd);
    }
    update();
    el.addEventListener('scroll', update);
    window.addEventListener('resize', update);
  });
}

/* ── Skeleton loading ──────────────────────────────────── */
function skeletonRows(cols, count) {
  count = count || 6;
  return Array(count).fill(0).map(function() {
    return '<tr class="fh-skel-row">' +
      Array(cols).fill(0).map(function(_, i) {
        return '<td><div class="fh-skel" style="width:' + (55 + (i * 17) % 35) + '%"></div></td>';
      }).join('') +
      '</tr>';
  }).join('');
}

/* ── Sortable columns (DOM-based) ──────────────────────── */
function makeSortable(tableId) {
  var table = document.getElementById(tableId);
  if (!table || table.dataset.sortable) return;
  table.dataset.sortable = '1';

  var sortCol = -1, sortAsc = true;

  table.querySelectorAll('thead th[data-sort]').forEach(function(th) {
    var colIdx = parseInt(th.dataset.sort, 10);
    var isNum  = th.dataset.sortType === 'num';
    th.style.cursor = 'pointer';
    th.addEventListener('click', function() {
      if (sortCol === colIdx) { sortAsc = !sortAsc; } else { sortCol = colIdx; sortAsc = true; }
      table.querySelectorAll('thead th[data-sort]').forEach(function(h) {
        h.dataset.sortDir = parseInt(h.dataset.sort, 10) === sortCol
          ? (sortAsc ? 'asc' : 'desc') : '';
      });
      var tbody = table.querySelector('tbody');
      var rows  = Array.from(tbody.querySelectorAll('tr:not(.fh-skel-row):not(.pam-detail-row)'));
      rows.sort(function(a, b) {
        var va = (a.cells[colIdx] ? a.cells[colIdx].textContent : '').trim();
        var vb = (b.cells[colIdx] ? b.cells[colIdx].textContent : '').trim();
        var na = isNum ? (parseFloat(va.replace(/[.,\s]/g,'')) || 0) : va.toLowerCase();
        var nb = isNum ? (parseFloat(vb.replace(/[.,\s]/g,'')) || 0) : vb.toLowerCase();
        return sortAsc ? (na > nb ? 1 : -1) : (na < nb ? 1 : -1);
      });
      rows.forEach(function(r) { tbody.appendChild(r); });
    });
  });
}

async function apiFetch(url, options = {}) {
  const defaults = {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  };
  
  if (options.body instanceof FormData) {
    delete defaults.headers["Content-Type"];
  }
  
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
  // Tab buttons now live in the navbar's module_tabs block (unified-header
  // migration), outside `container` ([data-tabs], which only wraps the
  // .tab-panel content) — a container-scoped query here always finds zero
  // buttons, silently skipping every listener attach and the auto-activate
  // call below, leaving every panel without .active (blank page). Query
  // globally instead, matching pressTabStep()'s existing '.tabs .tab-btn'
  // selector, since each page has exactly one such button group.
  const tabs = document.querySelectorAll(".tabs .tab-btn");
  const panels = container.querySelectorAll(".tab-panel");
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      panels.forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const target = container.querySelector(`#${btn.dataset.tab}`);
      if (target) {
        target.classList.add("active");
        // Full-bleed pages (spec: 2026-07-31-flow-full-bleed-table-pages) —
        // toggled per-tab since Beasiswa/Payment Memo mix full-bleed data
        // tabs with non-full-bleed dashboard/form tabs in one page. This
        // same click handler also fires on initTabs()'s own auto-activation
        // at page load, so the correct state is set immediately on load too.
        document.body.classList.toggle("fh-full-bleed", target.dataset.fullBleed === "true");
      }
      // Sync the active tab into the URL (no reload) so a save action that
      // triggers location.reload()/window.location.reload() while on a
      // non-first tab lands back on the same tab instead of silently
      // resetting to the first one on next page load.
      const tabName = btn.dataset.tab.replace(/^tab-/, "");
      const url = new URL(window.location);
      url.searchParams.set("tab", tabName);
      history.replaceState(null, "", url);
      // Filter panel always starts collapsed when switching sub-modules —
      // see docs/superpowers/specs/2026-07-12-financehub-page-toolbar-layout-design.md §2.3
      container.querySelectorAll(".filter-bar.collapsible.open").forEach(p => {
        p.classList.remove("open");
        persistFilterClosed(p);
      });
      // Newly-active panel's own scroll-height wrapper (if any) was hidden a
      // moment ago and may have a stale computed height — modules that size
      // their table wrap dynamically (e.g. sizeWrap()-style code) already
      // listen for "resize", so re-dispatch it once the new panel is visible.
      setTimeout(() => window.dispatchEvent(new Event("resize")), 0);
    });
  });
  // Deep-link support: ?tab=<name> selects the button whose data-tab is
  // "tab-<name>" instead of always defaulting to the first tab — used by
  // redirects like /beasiswa/sahabat -> /beasiswa/?tab=sahabat. Falls back
  // to today's default behavior when absent or no match is found. Matched
  // against `tabs` (already queried globally above — the buttons live in
  // the navbar's module_tabs block now, outside `container`) via a plain
  // dataset comparison rather than building a `document.querySelector`
  // selector string from the URL param: interpolating an unsanitized query
  // value into a CSS selector is both a click-injection risk (a crafted
  // ?tab= value can widen the match to an arbitrary element, which the
  // next line then calls .click() on) and a crash risk (an unterminated
  // attribute value throws a SyntaxError, aborting the rest of this
  // DOMContentLoaded handler — no tab ever activates, page renders blank).
  const requestedTab = new URLSearchParams(window.location.search).get("tab");
  const requested = requestedTab && [...tabs].find(t => t.dataset.tab === `tab-${requestedTab}`);
  if (requested) {
    requested.click();
  } else if (tabs.length > 0) {
    tabs[0].click();
  }
}

function fmtRupiah(n) {
  return new Intl.NumberFormat("id-ID").format(n || 0);
}

function fmtJutaan(amount) {
  const jt = (amount || 0) / 1000000;
  return jt.toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

// Whole-million amount, no "Rp" prefix or "Jt" suffix — e.g. 607473125 -> "607".
// Shared by every dashboard that wants a plain rounded-millions number
// (Sponsorship Dashboard, Budget Dashboard).
function fmtJutaanBulat(amount) {
  const jt = Math.round((amount || 0) / 1000000);
  return jt.toLocaleString("id-ID");
}


const FH_TOAST_ICONS = {
  success: '<path d="M20 6 9 17l-5-5"/>',
  error:   '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/>',
  warning: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4M12 17h.01"/>',
  info:    '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
};

// The CSS styles #fh-toast via .show + .fh-toast-<type>; the old version set
// unrelated class names, so toasts rendered without a background (barely visible).
function showToast(msg, type = "success") {
  type = { danger: "error", warn: "warning" }[type] || type;
  if (!FH_TOAST_ICONS[type]) type = "error";
  // Swallow the caller's own "Gagal: AbortError" right after the user cancelled
  // a confirmation (see the fetch wrapper below).
  if (type === "error" && Date.now() < (window._fhSuppressErrorsUntil || 0)) return;
  let toast = document.getElementById("fh-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "fh-toast";
    toast.addEventListener("click", () => toast.classList.remove("show"));
    document.body.appendChild(toast);
  }
  toast.innerHTML = `<span class="fh-toast-ico"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">${FH_TOAST_ICONS[type]}</svg></span><span class="fh-toast-msg"></span>`;
  toast.querySelector(".fh-toast-msg").textContent = msg;
  toast.setAttribute("role", type === "error" ? "alert" : "status");
  toast.setAttribute("aria-live", type === "error" ? "assertive" : "polite");
  toast.className = "fh-toast-" + type;
  void toast.offsetWidth;  // restart the enter transition when toasts replace each other
  toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove("show"), type === "error" ? 5500 : 3200);
}

function showLoading(msg) {
  let el = document.getElementById("fh-load-ov");
  if (!el) {
    el = document.createElement("div");
    el.id = "fh-load-ov";
    el.innerHTML = `<div class="fh-load-card"><div class="fh-load-spin"></div><div class="fh-load-msg"></div></div>`;
    document.body.appendChild(el);
  }
  el.querySelector(".fh-load-msg").textContent = msg || "Memuat...";
  el.classList.add("show");
}

function hideLoading() {
  const el = document.getElementById("fh-load-ov");
  if (el) el.classList.remove("show");
}

/* ── Row action menu ("⋯") ─────────────────────────────────
   One shared popover for per-row secondary actions, so a table row carries a
   single visible action plus this menu instead of 3-4 buttons.
   fhRowMenu(anchorButton, [{label, icon?, danger?, onClick} | "sep"]) */
const FH_MENU_ICONS = {
  wallet: '<path d="M17 8V5a1 1 0 0 0-1-1H6a2 2 0 0 0 0 4h12a1 1 0 0 1 1 1v3m0 4v3a1 1 0 0 1-1 1H6a2 2 0 0 1-2-2V6"/><path d="M20 12v4h-4a2 2 0 0 1 0-4h4"/>',
  calc:   '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15h.01M8 19h.01M12 19h.01M16 19h.01"/>',
  edit:   '<path d="M4 20h4L18.5 9.5a2.8 2.8 0 0 0-4-4L4 16v4"/><path d="m13.5 6.5 4 4"/>',
  trash:  '<path d="M4 7h16M10 11v6M14 11v6M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3"/>',
};
function fhRowMenu(anchor, items) {
  const open = document.getElementById("fh-row-menu");
  if (open) {
    const sameAnchor = open._anchor === anchor;
    open._close();
    if (sameAnchor) return;   // second click on the same "⋯" toggles it shut
  }
  const menu = document.createElement("div");
  menu.id = "fh-row-menu";
  menu.className = "fh-row-menu";
  menu.setAttribute("role", "menu");
  items.forEach(it => {
    if (it === "sep") { menu.insertAdjacentHTML("beforeend", '<div class="fh-row-menu-sep" role="separator"></div>'); return; }
    const b = document.createElement("button");
    b.type = "button";
    b.className = "fh-row-menu-item" + (it.danger ? " danger" : "");
    b.setAttribute("role", "menuitem");
    b.innerHTML = (it.icon ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${FH_MENU_ICONS[it.icon] || ""}</svg>` : "") + "<span></span>";
    b.querySelector("span").textContent = it.label;
    b.addEventListener("click", () => { close(); it.onClick(); });
    menu.appendChild(b);
  });
  document.body.appendChild(menu);

  // Fixed positioning under the anchor, right-aligned; flip above near the viewport bottom.
  const r = anchor.getBoundingClientRect();
  const mh = menu.offsetHeight, mw = menu.offsetWidth;
  menu.style.left = Math.max(8, Math.min(r.right - mw, innerWidth - mw - 8)) + "px";
  menu.style.top = (r.bottom + 4 + mh > innerHeight ? r.top - mh - 4 : r.bottom + 4) + "px";

  anchor.setAttribute("aria-expanded", "true");
  const btns = [...menu.querySelectorAll(".fh-row-menu-item")];
  btns[0] && btns[0].focus();

  function onKey(e) {
    const i = btns.indexOf(document.activeElement);
    if (e.key === "Escape") { e.preventDefault(); close(); anchor.focus(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); btns[(i + 1) % btns.length].focus(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); btns[(i - 1 + btns.length) % btns.length].focus(); }
    else if (e.key === "Tab") close();
  }
  function onDown(e) { if (!menu.contains(e.target) && !anchor.contains(e.target)) close(); }
  function close() {
    menu.remove();
    anchor.setAttribute("aria-expanded", "false");
    document.removeEventListener("keydown", onKey, true);
    document.removeEventListener("mousedown", onDown, true);
    window.removeEventListener("scroll", close, true);
    window.removeEventListener("resize", close);
  }
  menu._close = close;
  menu._anchor = anchor;
  document.addEventListener("keydown", onKey, true);
  document.addEventListener("mousedown", onDown, true);
  window.addEventListener("scroll", close, true);
  window.addEventListener("resize", close);
}

// Backdrop click closes a modal — but a stray click must not throw away what
// the user typed into a form modal: ask first when it has unsaved edits.
// Only user edits (input/change events) count; edit modals pre-filled by JS
// start clean. The confirm/prompt dialogs in base.html manage themselves.
function initModalBackdrop(overlay) {
  if (overlay.id === "modal-confirm" || overlay.id === "modal-prompt") return;
  const markDirty = () => { overlay._fhDirty = true; };
  overlay.addEventListener("input", markDirty);
  overlay.addEventListener("change", markDirty);
  new MutationObserver(() => {
    if (overlay.classList.contains("open") && !overlay._fhWasOpen) overlay._fhDirty = false;
    overlay._fhWasOpen = overlay.classList.contains("open");
  }).observe(overlay, { attributes: true, attributeFilter: ["class"] });

  overlay.addEventListener("click", async e => {
    if (e.target !== overlay) return;
    if (overlay._fhDirty) {
      const modal = overlay.querySelector(".modal");
      if (modal) {
        modal.classList.remove("fh-modal-nudge");
        void modal.offsetWidth;
        modal.classList.add("fh-modal-nudge");
      }
      const discard = await confirmModal("Ada perubahan yang belum disimpan di form ini. Tutup dan buang perubahan?", {
        type: "danger", title: "Buang Perubahan?", confirmText: "Buang", cancelText: "Lanjut Mengisi",
      });
      if (!discard) return;
    }
    overlay.classList.remove("open");
  });
}

function openModal(id) { const el = document.getElementById(id); if (el) el.classList.add("open"); }
function closeModal(id) { const el = document.getElementById(id); if (el) el.classList.remove("open"); }

function staggerRows(tbody) {
  Array.from(tbody.querySelectorAll("tr")).forEach((row, i) => {
    row.classList.add("stagger-row");
    row.style.animationDelay = `${Math.min(i, 20) * 28}ms`;
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
    else el.textContent = prefix + fmt.format(Math.round(target));  // money comes in as float (e.g. 111544685363.944)
  };
  requestAnimationFrame(step);
}

function getActiveFilterPanel() {
  const activeTabPanel = document.querySelector('.tab-panel.active');
  if (activeTabPanel) {
    const panel = activeTabPanel.querySelector('.filter-bar.collapsible');
    if (panel) return panel;
  }
  return document.querySelector('.filter-bar.collapsible');
}

// sessionStorage-backed persistence for filter panel open/closed state.
// Keyed by the panel's own stable, hand-written id (bsw-filter-siswa,
// pam-filter-pam, pa-filter-panel, etc — no page-identity prefix needed:
// panel ids don't collide across modules, and a stale entry from a panel
// that doesn't exist on the current page is simply never read, since
// restoreFilterOpenState() only ever looks up getActiveFilterPanel()'s
// result). Scoped to sessionStorage (not localStorage) since this is
// transient UI state that should not resurrect in a fresh session days
// later — see docs/superpowers/specs/2026-07-31-flow-filter-panel-persist-across-reload-design.md
function _filterOpenKey(panel) {
  return 'fh-filter-open:' + panel.id;
}
function persistFilterOpen(panel) {
  if (panel && panel.id) sessionStorage.setItem(_filterOpenKey(panel), '1');
}
function persistFilterClosed(panel) {
  if (panel && panel.id) sessionStorage.removeItem(_filterOpenKey(panel));
}
// Called after initTabs() (and its internal auto-activation click, which
// force-closes filter panels as a side effect on every load) has already
// run — restoring before that point would be immediately undone.
function restoreFilterOpenState() {
  const panel = getActiveFilterPanel();
  if (panel && panel.id && sessionStorage.getItem(_filterOpenKey(panel)) === '1') {
    panel.classList.add('open');
  }
}

// Dynamic pagination page-size: computes how many rows fit the space below
// a paginated table so screen height isn't wasted on a half-empty last page.
// See docs/superpowers/specs/2026-07-31-flow-dynamic-pagination-page-size-design.md
function computeDynamicPageSize(opts) {
  const container = typeof opts.scrollContainer === 'string'
    ? document.querySelector(opts.scrollContainer) : opts.scrollContainer;
  const row = typeof opts.rowSelector === 'string'
    ? document.querySelector(opts.rowSelector) : opts.rowSelector;
  if (!container || !row) return opts.defaultSize;
  const rowHeight = row.getBoundingClientRect().height;
  if (!rowHeight) return opts.defaultSize;
  const available = container.getBoundingClientRect().height;
  const raw = Math.floor(available / rowHeight);
  return Math.max(opts.defaultSize, Math.min(raw, opts.defaultSize * 4));
}

function _pageSizeCacheKey(name) {
  return 'fh-pagesize:' + name;
}
function getCachedPageSize(name, viewportHeight) {
  try {
    const raw = localStorage.getItem(_pageSizeCacheKey(name));
    if (!raw) return null;
    const cached = JSON.parse(raw);
    if (!cached || Math.abs(cached.viewportHeight - viewportHeight) > 20) return null;
    return cached.pageSize;
  } catch (e) { return null; }
}
function setCachedPageSize(name, pageSize, viewportHeight) {
  try {
    localStorage.setItem(_pageSizeCacheKey(name), JSON.stringify({ pageSize, viewportHeight }));
  } catch (e) {}
}

// Shared "calibrate once, then cache" flow for server-paginated tables
// (Payment Application, Sponsorship Data tab). Called after the table has
// rendered `renderedPageSize` rows. Navigates (full page reload) at most
// once: either applying a cached size that doesn't match what was rendered,
// or applying a freshly-measured size that differs from what was rendered.
// No-op if the current render already matches the right size.
function initServerPagedDynamicSize(opts) {
  const viewportHeight = window.innerHeight;
  const url = new URL(window.location);
  const cached = getCachedPageSize(opts.cacheName, viewportHeight);
  if (cached && cached !== opts.renderedPageSize) {
    url.searchParams.set(opts.paramName, cached);
    window.location.href = url.toString();
    return;
  }
  requestAnimationFrame(() => {
    const computed = computeDynamicPageSize({
      scrollContainer: opts.scrollContainer,
      rowSelector: opts.rowSelector,
      defaultSize: opts.defaultSize,
    });
    setCachedPageSize(opts.cacheName, computed, viewportHeight);
    if (computed !== opts.renderedPageSize) {
      url.searchParams.set(opts.paramName, computed);
      window.location.href = url.toString();
    }
  });
}


// Steps the active .tab-btn within `.tabs` by `delta` positions (wraps around
// at either end) and clicks the resulting tab. Works for both server-rendered
// <a href> tabs (ETF PA — .click() navigates) and client-side <button
// data-tab> tabs (Payment Memo/Beasiswa — .click() triggers initTabs()'s own
// listener) since it delegates to whatever the tab element already does.
function pressTabStep(delta) {
  const tabs = [...document.querySelectorAll('.tabs .tab-btn')];
  if (!tabs.length) return false;
  const activeIdx = tabs.findIndex(t => t.classList.contains('active'));
  const from = activeIdx === -1 ? 0 : activeIdx;
  const next = (from + delta + tabs.length) % tabs.length;
  tabs[next].click();
  return true;
}

// Steps between top-level modules via the navbar's flat module-link list —
// the fallback for Alt+←/→ on pages with no .tabs .tab-btn to step, e.g.
// Dashboard (base.html never renders the unified-header module dropdown for
// active_page == 'dashboard', so it always has this flat .navbar-menu-item
// list instead). .click() on an <a href> triggers normal navigation, same
// trick pressTabStep already relies on for ETF PA's anchor-based tabs.
function pressModuleStep(delta) {
  const mods = [...document.querySelectorAll('.navbar-menu-item')];
  if (!mods.length) return;
  const activeIdx = mods.findIndex(m => m.classList.contains('active'));
  const from = activeIdx === -1 ? 0 : activeIdx;
  const next = (from + delta + mods.length) % mods.length;
  mods[next].click();
}

// Global shortcuts: F toggles the filter panel, Alt+←/→ steps tabs (or
// top-level modules on pages with no sub-tabs, e.g. Dashboard), Alt+↑ opens
// Ganti Perusahaan. Skipped entirely while focus is in a typing field so
// normal typing (including the letter "f") is never hijacked — see
// docs/superpowers/specs/2026-07-13-financehub-keyboard-shortcuts-design.md §2.2
document.addEventListener('keydown', e => {
  const el = document.activeElement;
  const typing = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable);
  
  if (e.key === 'Escape') {
    const panel = getActiveFilterPanel();
    if (panel && panel.classList.contains('open')) {
      panel.classList.remove('open');
      persistFilterClosed(panel);
      if (typing) el.blur(); // Also blur the search input if focused
      return;
    }
  }

  if (typing) return;
  
  if (e.altKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
    e.preventDefault();
    const delta = e.key === 'ArrowRight' ? 1 : -1;
    if (!pressTabStep(delta)) pressModuleStep(delta);
  } else if (e.altKey && e.key === 'ArrowUp') {
    const companyLink = document.querySelector('.navbar-company');
    if (companyLink) { e.preventDefault(); companyLink.click(); }
  } else if (!e.altKey && !e.ctrlKey && !e.metaKey && e.key.toLowerCase() === 'f') {
    e.preventDefault();
    const panel = getActiveFilterPanel();
    if (panel) {
      panel.classList.add('open');
      persistFilterOpen(panel);
      if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
        const searchInput = panel.querySelector('input[type="text"]');
        if (searchInput) searchInput.focus();
      }
    }
  }
});

// Payment Application's tabs are real <a href="?tab=..."> navigations, not
// initTabs()'s client-side <button data-tab> panels — so its tab-switch
// never runs through initTabs()'s force-close-and-persist loop (it has no
// [data-tabs] container at all). Without this, switching PA tabs looks
// identical to a same-tab reload from the browser's perspective, so
// restoreFilterOpenState() would reopen a filter left open on a different
// PA tab. Clear the persisted state on click, before the navigation away —
// visually closing it client-side is moot since the page is unloading.
document.addEventListener('click', e => {
  const tabLink = e.target.closest('.tabs .tab-btn');
  if (tabLink && tabLink.tagName === 'A') {
    const panel = getActiveFilterPanel();
    if (panel) persistFilterClosed(panel);
  }
});

function updateFilterChipSummary(chip) {
  const boxes = chip.querySelectorAll(".panel-opts input[type=checkbox]");
  const total = boxes.length;
  const checked = chip.querySelectorAll(".panel-opts input[type=checkbox]:checked").length;
  const valEl = chip.querySelector(".val");
  if (checked === total) {
    valEl.textContent = "Semua";
  } else if (checked === 0) {
    valEl.textContent = "Tidak ada";
  } else {
    valEl.textContent = checked + " dipilih";
  }
}

function initFilterChips(root, onChange) {
  root.querySelectorAll(".beasiswa-dash-filter-chip").forEach(function (chip) {
    chip.querySelectorAll(".panel-opts input[type=checkbox]").forEach(function (cb) {
      cb.addEventListener("change", function () {
        updateFilterChipSummary(chip);
        onChange();
      });
    });
    const allBtn = chip.querySelector('[data-act="all"]');
    if (allBtn) {
      allBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        chip.querySelectorAll(".panel-opts input[type=checkbox]").forEach(function (cb) { cb.checked = true; });
        updateFilterChipSummary(chip);
        onChange();
      });
    }
    const noneBtn = chip.querySelector('[data-act="none"]');
    if (noneBtn) {
      noneBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        chip.querySelectorAll(".panel-opts input[type=checkbox]").forEach(function (cb) { cb.checked = false; });
        updateFilterChipSummary(chip);
        onChange();
      });
    }
    updateFilterChipSummary(chip);
  });
}

document.addEventListener("click", function (e) {
  const chip = e.target.closest(".beasiswa-dash-filter-chip");
  if (chip) {
    if (e.target.closest(".beasiswa-dash-filter-panel")) return;
    document.querySelectorAll(".beasiswa-dash-filter-chip.open").forEach(function (c) {
      if (c !== chip) c.classList.remove("open");
    });
    chip.classList.toggle("open");
  } else {
    document.querySelectorAll(".beasiswa-dash-filter-chip.open").forEach(function (c) {
      c.classList.remove("open");
    });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();
  initTitleDropdown();
  initModuleSwitchDropdown();
  initHeaderTabFade();
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
  restoreFilterOpenState();
  document.querySelectorAll(".modal-overlay").forEach(initModalBackdrop);
  document.querySelectorAll("tbody").forEach(staggerRows);
  document.querySelectorAll(".stat-value[data-count]").forEach(el => animateCounter(el));
});
