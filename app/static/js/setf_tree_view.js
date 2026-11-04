// Renderer DOM Tree Query Sahabat ETF (kartu bertumpuk). Logika ada di setf_tree_model.js.
(function (root) {
  const M = root.SetfTreeModel;
  let host = null;
  let roots = [];
  let idx = null;
  let openIds = new Set();
  let revealed = new Set();
  let mode = 'default';
  let query = '';
  let bound = false;

  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function statusEl() { return document.getElementById('tree-status'); }
  function setStatus(html) { const el = statusEl(); if (el) el.innerHTML = html; }

  function tooltip(node) {
    const lines = [node.name + (node.id ? ' | ' + node.id : '')];
    if (node.tanggal_lahir) lines.push('Tanggal Lahir: ' + node.tanggal_lahir);
    if (node.catatan) lines.push('Catatan: ' + node.catatan);
    (node.partners || []).forEach((p) => {
      lines.push('');
      lines.push(p.name + ' (Partner) | ' + (p.id || ''));
      if (p.tanggal_lahir) lines.push('Tanggal Lahir: ' + p.tanggal_lahir);
      if (p.catatan) lines.push('Catatan: ' + p.catatan);
    });
    return lines.join('\n');
  }

  function partnerHtml(p, hitIds) {
    const code = p.id ? p.id.split('.').pop().toUpperCase() : '';
    const cls = hitIds && hitIds.indexOf(p.id) >= 0 ? ' hit' : '';
    return '<div class="tr-partner' + cls + '">' + esc(p.name) + ' (Partner' + (code ? ' ' + code : '') + ')</div>';
  }

  function cardHtml(row, opts) {
    opts = opts || {};
    const node = row.node;
    const classes = ['tr-card'];
    if (opts.toggle && row.hasChildren) classes.push('clickable');
    if (row.open) classes.push('open');
    if (row.isHit) classes.push('hit');
    else if (opts.path) classes.push('path');
    if (opts.extra) classes.push(opts.extra);
    const code = node.id && !/^[A-Za-z]$/.test(node.id) ? '<span class="tr-code">(' + esc(node.id) + ')</span>' : '';
    const caret = opts.toggle && row.hasChildren
      ? '<span class="tr-caret">' + (row.open ? '▾' : '▸') + ' ' + row.childCount + '</span>' : '';
    const partners = (node.partners || []).map((p) => partnerHtml(p, row.partnerHitIds)).join('');
    const data = opts.toggle && row.hasChildren ? ' data-toggle="' + esc(row.id) + '"' : '';
    return '<div class="' + classes.join(' ') + '"' + data + ' title="' + esc(tooltip(node)) + '">'
      + caret + '<span class="tr-name">' + esc(node.name) + '</span>' + code + partners + '</div>';
  }

  function defaultHtml() {
    return M.buildColumns(roots, openIds).map((block) => {
      const rootRow = { node: block.root, id: block.root.id, open: false, hasChildren: false, childCount: 0, partnerHitIds: [] };
      const cols = block.columns.map((col) => {
        const items = col.rows.map((r, i) => {
          const badge = r.badge ? '<div><span class="tr-badge">' + r.badge + '</span></div>' : '';
          const nested = r.indent > 0 ? ' style="--ind:' + (r.indent - 1) + '"' : '';
          return badge + '<div class="tr-item"' + nested + '>' + cardHtml(r, { toggle: true }) + '</div>';
        }).join('');
        return '<div class="tr-col"><div class="tr-g1-row">' + cardHtml(col.g1, { toggle: false }) + '</div>'
          + (items ? '<div class="tr-stack">' + items + '</div>' : '') + '</div>';
      }).join('');
      return '<div class="tr-block"><div class="tr-block-head"><div class="tr-root-card">'
        + cardHtml(rootRow, { toggle: false, extra: 'tr-rootcard' }) + '</div></div>'
        + (block.columns.length
          ? '<div class="tr-body"><div class="tr-ruler"><div class="tr-ruler-cell tr-g1-row">G1</div></div>'
            + '<div class="tr-cols">' + cols + '</div></div>' : '') + '</div>';
    }).join('');
  }

  function focusHtml(blocks) {
    return blocks.map((b) => {
      const chainIds = new Set(b.chain.map((r) => r.id).concat([b.root.id]));
      const rows = b.chain.map((r) => {
        let sibs = '';
        let chip = '';
        if (r.hiddenSiblings > 0) {
          if (revealed.has(r.id)) {
            const parent = idx.byId.get(r.id);
            const kids = parent && parent.parentId ? idx.byId.get(parent.parentId).node.children : [];
            sibs = kids.filter((k) => !chainIds.has(k.id)).map((k) =>
              cardHtml({ node: k, id: k.id, open: false, hasChildren: false, childCount: 0, partnerHitIds: [] }, { extra: 'tr-sib' })).join('');
          } else {
            chip = '<span class="tr-chip" data-reveal="' + esc(r.id) + '">+ ' + r.hiddenSiblings + ' saudara</span>';
          }
        }
        const pad = 'padding-left:calc(14px + ' + (r.gen - 1) + ' * var(--tree-indent) * 2)';
        const canOpen = r.hasChildren && r.focusChildren === 0;
        const open = canOpen && openIds.has(r.id);
        const row = Object.assign({}, r, { open });
        let kids = '';
        if (open) {
          kids = '<div class="tr-stack">' + M.childRows(r.node, r.gen, openIds).map((k) => {
            const badge = k.badge ? '<div><span class="tr-badge">' + k.badge + '</span></div>' : '';
            const nested = k.indent > 0 ? ' style="--ind:' + (k.indent - 1) + '"' : '';
            return badge + '<div class="tr-item"' + nested + '>' + cardHtml(k, { toggle: true }) + '</div>';
          }).join('') + '</div>';
        }
        return '<div class="tr-chainrow"><div class="tr-ruler"><div class="tr-ruler-cell">' + r.ruler + '</div></div>'
          + '<div class="tr-chainbody" style="' + pad + '"><div class="tr-chaininline">'
          + cardHtml(row, { path: true, toggle: canOpen }) + chip + sibs + '</div>' + kids + '</div></div>';
      }).join('');
      return '<div class="tr-block"><div class="tr-block-head"><div class="tr-root-card">'
        + cardHtml(b.root, { path: true }) + '</div></div>' + rows + '</div>';
    }).join('');
  }

  function paint(html) {
    const wrap = document.getElementById('tree-wrapper');
    const st = wrap ? [wrap.scrollTop, wrap.scrollLeft] : [0, 0];
    host.innerHTML = html;
    if (wrap) { wrap.scrollTop = st[0]; wrap.scrollLeft = st[1]; }
  }

  function renderDefault() {
    mode = 'default';
    query = '';
    setStatus('');
    paint(defaultHtml());
  }

  function renderFocus(q) {
    const res = M.searchFocus(roots, q);
    if (!res) { renderDefault(); return; }
    mode = 'focus';
    query = q;
    if (!res.shownFamilies) {
      setStatus('Tidak ada hasil untuk "' + esc(q) + '". <a href="#" data-reset="1">Reset</a>');
      paint('<div class="tr-empty">Tidak ada hasil</div>');
      return;
    }
    setStatus('Menampilkan ' + res.shownFamilies + ' dari ' + res.totalFamilies
      + ' keluarga &middot; <a href="#" data-reset="1">Tampilkan semua</a>');
    paint(focusHtml(M.focusRows(res.families)));
  }

  function rerender() { if (mode === 'focus') renderFocus(query); else renderDefault(); }

  function reset() { openIds = new Set(); revealed = new Set(); renderDefault(); }

  function onClick(e) {
    const rs = e.target.closest('[data-reset]');
    if (rs) { e.preventDefault(); const inp = document.getElementById('tree-search-input'); if (inp) inp.value = ''; reset(); return; }
    const rv = e.target.closest('[data-reveal]');
    if (rv) { revealed.add(rv.getAttribute('data-reveal')); renderFocus(query); return; }
    const tg = e.target.closest('[data-toggle]');
    if (tg) { openIds = M.toggleOpen(openIds, tg.getAttribute('data-toggle')); rerender(); }
  }

  function mount(container, data) {
    host = container;
    roots = data;
    idx = M.indexTree(roots);
    if (!bound) {
      bound = true;
      host.addEventListener('click', onClick);
      const st = statusEl();
      if (st) st.addEventListener('click', onClick);
    }
    reset();
  }

  function names() {
    const set = new Set();
    idx.byId.forEach((v) => {
      set.add(v.node.name);
      (v.node.partners || []).forEach((p) => set.add(p.name));
    });
    return Array.from(set).filter(Boolean).sort();
  }

  function setTextScale(mult) { host.style.setProperty('--tree-font', (12 * mult) + 'px'); }
  function setSpacing(mult) {
    host.style.setProperty('--tree-gap', (14 * mult) + 'px');
    host.style.setProperty('--tree-indent', (14 * mult) + 'px');
  }
  function getExportElement() { return host; }
  function currentQuery() { return mode === 'focus' ? query : ''; }

  root.SetfTreeView = { mount, renderDefault, renderFocus, reset, names, setTextScale, setSpacing, getExportElement, currentQuery, rerender };
})(window);
