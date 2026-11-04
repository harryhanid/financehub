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

  const api = { indexTree, nameMatches, searchFocus };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SetfTreeModel = api;
})(typeof window !== 'undefined' ? window : globalThis);
