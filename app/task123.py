import re

# Task 1: app/static/js/app.js
app_js_path = r"C:\Financehub\app\static\js\app.js"
with open(app_js_path, "r", encoding="utf-8") as f:
    app_js = f.read()

helpers_code = """
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
"""

anchor = """function restoreFilterOpenState() {
  const panel = getActiveFilterPanel();
  if (panel && panel.id && sessionStorage.getItem(_filterOpenKey(panel)) === '1') {
    panel.classList.add('open');
  }
}"""
if "computeDynamicPageSize" not in app_js:
    app_js = app_js.replace(anchor, anchor + "\n" + helpers_code)
    with open(app_js_path, "w", encoding="utf-8") as f:
        f.write(app_js)

# Task 2 & 3: app/templates/payment_memo/index.html
pm_html_path = r"C:\Financehub\app\templates\payment_memo\index.html"
with open(pm_html_path, "r", encoding="utf-8") as f:
    pm_html = f.read()

# Task 2: SMT tab
pm_html = pm_html.replace('const _smtPageSize = 50;', 'let _smtPageSize = 50;')
old_loadSMT = """  _smtAllRows = data.rows;
  _smtPage = 1;
  if (count) count.textContent = data.rows.length + ' baris';
  _smtRenderPage();"""
new_loadSMT = """  _smtAllRows = data.rows;
  _smtPage = 1;
  if (count) count.textContent = data.rows.length + ' baris';
  const _smtCachedSize = getCachedPageSize('smt', window.innerHeight);
  if (_smtCachedSize) _smtPageSize = _smtCachedSize;
  _smtRenderPage();
  if (_smtAllRows.length) {
    const _smtComputed = computeDynamicPageSize({
      scrollContainer: '#tab-smt .pillar-table-wrap',
      rowSelector: '#smt-tbody tr',
      defaultSize: 50,
    });
    setCachedPageSize('smt', _smtComputed, window.innerHeight);
    if (_smtComputed !== _smtPageSize) {
      _smtPageSize = _smtComputed;
      _smtRenderPage();
    }
  }"""
if "getCachedPageSize('smt'" not in pm_html:
    pm_html = pm_html.replace(old_loadSMT, new_loadSMT)

# Task 3: AGRI tab
pm_html = pm_html.replace('const _agriPageSize = 50;', 'let _agriPageSize = 50;')
old_loadPAM = """  _agriAllRows = data.rows;
  _agriPage = 1;
  _agriRenderPage();"""
new_loadPAM = """  _agriAllRows = data.rows;
  _agriPage = 1;
  const _agriCachedSize = getCachedPageSize('agri', window.innerHeight);
  if (_agriCachedSize) _agriPageSize = _agriCachedSize;
  _agriRenderPage();
  if (_agriAllRows.length) {
    const _agriComputed = computeDynamicPageSize({
      scrollContainer: '#tab-pam .pillar-table-wrap',
      rowSelector: '#pam-tbody tr',
      defaultSize: 50,
    });
    setCachedPageSize('agri', _agriComputed, window.innerHeight);
    if (_agriComputed !== _agriPageSize) {
      _agriPageSize = _agriComputed;
      _agriRenderPage();
    }
  }"""
if "getCachedPageSize('agri'" not in pm_html:
    pm_html = pm_html.replace(old_loadPAM, new_loadPAM)

with open(pm_html_path, "w", encoding="utf-8") as f:
    f.write(pm_html)

print("Tasks 1, 2, 3 complete")
