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
    if (isHit) {
      // Hasil: anak-anaknya tertutup; kecuali akar, yang tampil dengan G1-nya.
      if (gen === 0) out.children = kids.map((c) => bareFocus(c, gen + 1));
      return out;
    }
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

  // Mode pencarian: rantai leluhur -> hasil, satu penggaris per generasi.
  function focusRows(families) {
    return families.map((fam) => {
      const none = new Set();
      const chain = [];
      const hits = [];
      const walk = (f) => {
        chain.push(makeRow(f.node, f.gen, f.gen - 1, none, {
          ruler: 'G' + f.gen, isHit: f.isHit, partnerHitIds: f.partnerHitIds, hiddenSiblings: f.hiddenSiblings,
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

  const api = { indexTree, nameMatches, searchFocus, toggleOpen, buildColumns, focusRows };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SetfTreeModel = api;
})(typeof window !== 'undefined' ? window : globalThis);
