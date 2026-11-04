// Logika murni Tree Query Sahabat ETF (tanpa DOM) agar bisa dites dengan `node --test`.
(function (root) {
  function indexTree(roots) {
    const byId = new Map();
    const rootIds = [];
    function walk(node, parentId, gen) {
      byId.set(node.id, { node, parentId, gen });
      (node.children || []).forEach((c) => walk(c, node.id, gen + 1));
    }
    roots.forEach((r) => { rootIds.push(r.id); walk(r, null, 0); });
    return { byId, rootIds };
  }

  function nameMatches(node, q) {
    const self = (node.name || '').toLowerCase().includes(q);
    const partnerIds = (node.partners || [])
      .filter((p) => (p.name || '').toLowerCase().includes(q))
      .map((p) => p.id);
    return { self, partnerIds };
  }

  function bareFocus(node, gen) {
    return { node, gen, isHit: false, partnerHitIds: [], hiddenSiblings: 0, children: [] };
  }

  // Memangkas keluarga ke rantai leluhur -> hasil; null bila tak ada hasil di dalamnya.
  function pruneToHits(node, gen, q) {
    const m = nameMatches(node, q);
    const isHit = m.self || m.partnerIds.length > 0;
    const kids = node.children || [];
    const kept = [];
    kids.forEach((c) => {
      const f = pruneToHits(c, gen + 1, q);
      if (f) kept.push(f);
    });
    if (!isHit && kept.length === 0) return null;
    const out = { node, gen, isHit: m.self, partnerHitIds: m.partnerIds, hiddenSiblings: 0, children: [] };
    if (isHit && gen === 0) {
      // Akar yang cocok tampil dengan G1-nya; G1 yang punya hasil di bawahnya memakai rantai hasilnya.
      out.children = kids.map((c) => kept.find((k) => k.node === c) || bareFocus(c, gen + 1));
      return out;
    }
    // Hasil: anak-anaknya tertutup, kecuali yang membawa hasil lain di bawahnya.
    kept.forEach((f) => { f.hiddenSiblings = kids.length - kept.length; });
    out.children = kept;
    return out;
  }

  function searchFocus(roots, query) {
    const q = (query || '').trim().toLowerCase();
    if (!q) return null;
    const families = [];
    roots.forEach((r) => {
      const f = pruneToHits(r, 0, q);
      if (f) families.push(f);
    });
    return { families, shownFamilies: families.length, totalFamilies: roots.length };
  }

  function toggleOpen(openIds, id) {
    const next = new Set(openIds);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  }

  function makeRow(node, gen, indent, openIds, extra) {
    const kids = node.children || [];
    return Object.assign({
      id: node.id, node, gen, indent,
      hasChildren: kids.length > 0, childCount: kids.length,
      open: openIds.has(node.id), badge: null, ruler: null,
    }, extra || {});
  }

  // Kartu G2+ sebuah kolom: anak G1 selalu tampil; turunan lebih dalam hanya bila induknya terbuka.
  function stackRows(children, gen, indent, openIds, out) {
    children.forEach((c, i) => {
      const row = makeRow(c, gen, indent, openIds);
      if (i === 0 && children.length >= 2) row.badge = 'G' + gen;
      out.push(row);
      if (row.open && row.hasChildren) stackRows(c.children, gen + 1, indent + 1, openIds, out);
    });
  }

  function buildColumns(roots, openIds) {
    return roots.map((root) => ({
      root,
      columns: (root.children || []).map((g1) => {
        const rows = [];
        stackRows(g1.children || [], 2, 0, openIds, rows);
        return { g1: makeRow(g1, 1, 0, openIds, { ruler: 'G1' }), rows };
      }),
    }));
  }

  // Kartu anak sebuah node (untuk membuka turunan hasil pencarian); turunan lebih dalam hanya bila terbuka.
  function childRows(node, gen, openIds) {
    const out = [];
    stackRows(node.children || [], gen + 1, 0, openIds, out);
    return out;
  }

  // Mode pencarian: rantai leluhur -> hasil, satu penggaris per generasi.
  function focusRows(families) {
    return families.map((fam) => {
      const none = new Set();
      const chain = [];
      const hits = [];
      const walk = (f) => {
        chain.push(makeRow(f.node, f.gen, f.gen - 1, none, {
          ruler: 'G' + f.gen, isHit: f.isHit, partnerHitIds: f.partnerHitIds, hiddenSiblings: f.hiddenSiblings,
          focusChildren: f.children.length,
        }));
        if (f.isHit || f.partnerHitIds.length) hits.push(f.node.id);
        f.children.forEach(walk);
      };
      fam.children.forEach(walk);
      const root = makeRow(fam.node, 0, 0, none, {
        isHit: fam.isHit, partnerHitIds: fam.partnerHitIds, hiddenSiblings: 0,
      });
      if (fam.isHit || fam.partnerHitIds.length) hits.unshift(fam.node.id);
      return { root, chain, hits };
    });
  }

  const BULAN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

  // WIB = UTC+7 tetap; dihitung dari UTC agar tidak bergantung zona waktu peramban.
  function formatPrintStamp(date) {
    const w = new Date(date.getTime() + 7 * 3600 * 1000);
    const p2 = (v) => String(v).padStart(2, '0');
    return 'Dicetak: ' + p2(w.getUTCDate()) + ' ' + BULAN[w.getUTCMonth()] + ' ' + w.getUTCFullYear()
      + ' ' + p2(w.getUTCHours()) + ':' + p2(w.getUTCMinutes()) + ' WIB';
  }

  function slicePages(contentW, contentH, opt) {
    const scale = (opt.pageW - 2 * opt.margin) / contentW;
    const perPage = Math.floor((opt.pageH - 2 * opt.margin - opt.headerH) / scale);
    const slices = [];
    for (let sy = 0; sy < contentH; sy += perPage) {
      slices.push({ sy, sh: Math.min(perPage, contentH - sy) });
    }
    return { scale, slices };
  }

  const api = { indexTree, nameMatches, searchFocus, toggleOpen, buildColumns, childRows, focusRows, formatPrintStamp, slicePages };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SetfTreeModel = api;
})(typeof window !== 'undefined' ? window : globalThis);
