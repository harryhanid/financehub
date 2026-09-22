import sys

def patch():
    with open(r'C:\Financehub\app\templates\beasiswa\index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    mkDrop_old = """function _mkDrop(opts, ph) {
  const w   = document.createElement("div"); w.style.position = "relative";
  const hid = document.createElement("input"); hid.type = "hidden";
  const dsp = document.createElement("div");
  dsp.className = "fh-custom-select";
  const lbl = document.createElement("span");
  lbl.textContent = ph; lbl.className = "fh-custom-select-label";
  const arr = document.createElement("span");
  arr.textContent = "▾"; arr.className = "fh-custom-select-arrow";
  dsp.appendChild(lbl); dsp.appendChild(arr);
  // pan is attached to document.body with position:fixed to escape .table-wrap overflow:hidden clipping
  const pan = document.createElement("div");
  pan.className = "fh-custom-panel";
  pan.style.cssText = "display:none;position:fixed;z-index:9999";
  const sw = document.createElement("div"); sw.style.padding = "6px";
  const si = document.createElement("input"); si.type = "text"; si.placeholder = "Cari...";
  si.style.cssText = "width:100%;box-sizing:border-box;border:1px solid var(--border,#e5e7eb);border-radius:.25rem;padding:.3rem .6rem;font-size:.875rem";
  sw.appendChild(si);
  const lst = document.createElement("div"); lst.style.cssText = "max-height:200px;overflow-y:auto";
  pan.appendChild(sw); pan.appendChild(lst);
  document.body.appendChild(pan);
  function _posPan() {
    const r = dsp.getBoundingClientRect();
    pan.style.top   = (r.bottom + 2) + "px";
    pan.style.left  = r.left + "px";
    pan.style.width = r.width + "px";
  }
  function render(q) {
    lst.innerHTML = "";
    opts.filter(c => c.toLowerCase().includes(q.toLowerCase())).forEach(c => {
      const d = document.createElement("div");
      d.textContent = c;
      d.className = "fh-custom-panel-item";
      d.addEventListener("mousedown", () => { hid.value=c; lbl.textContent=c; lbl.style.color="var(--sl-700)"; pan.style.display="none"; si.value=""; });
      lst.appendChild(d);
    });
  }
  dsp.addEventListener("click", () => {
    if (pan.style.display !== "none") { pan.style.display="none"; return; }
    si.value=""; render(""); _posPan(); pan.style.display="block"; si.focus();
  });
  si.addEventListener("input", () => render(si.value));
  // Check both w and pan since pan is no longer a child of w
  document.addEventListener("mousedown", e => { if (!w.contains(e.target) && !pan.contains(e.target)) pan.style.display="none"; });
  w.appendChild(hid); w.appendChild(dsp);
  w._hid = hid;
  w._pan = pan;
  return w;
}"""

    mkDrop_new = """function _mkDrop(opts, ph) {
  const w   = document.createElement("div"); w.style.position = "relative";
  const hid = document.createElement("input"); hid.type = "hidden";
  const dsp = document.createElement("div");
  dsp.className = "fh-custom-select";
  const lbl = document.createElement("span");
  lbl.textContent = ph; lbl.className = "fh-custom-select-label";
  const arr = document.createElement("span");
  arr.textContent = "▾"; arr.className = "fh-custom-select-arrow";
  dsp.appendChild(lbl); dsp.appendChild(arr);
  const pan = document.createElement("div");
  pan.className = "fh-custom-panel";
  pan.style.cssText = "display:none;position:fixed;z-index:9999";
  const sw = document.createElement("div"); sw.style.padding = "6px";
  const si = document.createElement("input"); si.type = "text"; si.placeholder = "Cari...";
  si.style.cssText = "width:100%;box-sizing:border-box;border:1px solid var(--border,#e5e7eb);border-radius:.25rem;padding:.3rem .6rem;font-size:.875rem";
  sw.appendChild(si);
  const lst = document.createElement("div"); lst.style.cssText = "max-height:200px;overflow-y:auto";
  pan.appendChild(sw); pan.appendChild(lst);
  document.body.appendChild(pan);
  
  let activeIdx = -1;
  let currentItems = [];

  function _posPan() {
    const r = dsp.getBoundingClientRect();
    pan.style.top   = (r.bottom + 2) + "px";
    pan.style.left  = r.left + "px";
    pan.style.width = r.width + "px";
  }
  function updateActive(items) {
    items.forEach((item, idx) => {
      if (idx === activeIdx) {
        item.style.backgroundColor = "var(--bg-muted, #f3f4f6)";
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.style.backgroundColor = "";
      }
    });
  }
  function render(q) {
    lst.innerHTML = "";
    activeIdx = -1;
    currentItems = opts.filter(c => c.toLowerCase().includes(q.toLowerCase()));
    currentItems.forEach(c => {
      const d = document.createElement("div");
      d.textContent = c;
      d.className = "fh-custom-panel-item";
      d.addEventListener("mousedown", () => { hid.value=c; lbl.textContent=c; lbl.style.color="var(--sl-700)"; pan.style.display="none"; si.value=""; });
      lst.appendChild(d);
    });
  }
  si.addEventListener("keydown", e => {
    const items = lst.querySelectorAll('.fh-custom-panel-item');
    if (items.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIdx = (activeIdx + 1) % items.length;
      updateActive(items);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIdx = (activeIdx - 1 + items.length) % items.length;
      updateActive(items);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeIdx >= 0 && activeIdx < items.length) {
        const c = currentItems[activeIdx];
        hid.value=c; lbl.textContent=c; lbl.style.color="var(--sl-700)"; pan.style.display="none"; si.value="";
      }
    }
  });
  dsp.addEventListener("click", () => {
    if (pan.style.display !== "none") { pan.style.display="none"; return; }
    si.value=""; render(""); _posPan(); pan.style.display="block"; si.focus();
  });
  si.addEventListener("input", () => render(si.value));
  document.addEventListener("mousedown", e => { if (!w.contains(e.target) && !pan.contains(e.target)) pan.style.display="none"; });
  w.appendChild(hid); w.appendChild(dsp);
  w._hid = hid; w._pan = pan;
  return w;
}"""

    cat2_logic_old = """function bgtCat2Filter() {
  const q    = document.getElementById("bgt-cat2-search").value.toLowerCase();
  const list = document.getElementById("bgt-cat2-opts");
  list.innerHTML = "";
  CAT2.filter(c => c.toLowerCase().includes(q)).forEach(c => {
    const div = document.createElement("div");
    div.textContent = c;
    div.className = "fh-custom-panel-item";
    div.addEventListener("mousedown", () => bgtCat2Select(c));
    list.appendChild(div);
  });
}"""

    cat2_logic_new = """let _bgtCat2ActiveIdx = -1;
let _bgtCat2Items = [];
function bgtCat2Filter() {
  const q    = document.getElementById("bgt-cat2-search").value.toLowerCase();
  const list = document.getElementById("bgt-cat2-opts");
  list.innerHTML = "";
  _bgtCat2ActiveIdx = -1;
  _bgtCat2Items = CAT2.filter(c => c.toLowerCase().includes(q));
  _bgtCat2Items.forEach(c => {
    const div = document.createElement("div");
    div.textContent = c;
    div.className = "fh-custom-panel-item";
    div.addEventListener("mousedown", () => bgtCat2Select(c));
    list.appendChild(div);
  });
}
document.getElementById("bgt-cat2-search").addEventListener("keydown", function(e) {
  const list = document.getElementById("bgt-cat2-opts");
  const items = list.querySelectorAll(".fh-custom-panel-item");
  if (!items.length) return;
  if (e.key === "ArrowDown") {
    e.preventDefault();
    _bgtCat2ActiveIdx = (_bgtCat2ActiveIdx + 1) % items.length;
    bgtCat2UpdateActive(items);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    _bgtCat2ActiveIdx = (_bgtCat2ActiveIdx - 1 + items.length) % items.length;
    bgtCat2UpdateActive(items);
  } else if (e.key === "Enter") {
    e.preventDefault();
    if (_bgtCat2ActiveIdx >= 0 && _bgtCat2ActiveIdx < items.length) {
      bgtCat2Select(_bgtCat2Items[_bgtCat2ActiveIdx]);
      document.getElementById("bgt-cat2-panel").style.display = "none";
    }
  }
});
function bgtCat2UpdateActive(items) {
  items.forEach((item, idx) => {
    if (idx === _bgtCat2ActiveIdx) {
      item.style.backgroundColor = "var(--bg-muted, #f3f4f6)";
      item.scrollIntoView({ block: 'nearest' });
    } else {
      item.style.backgroundColor = "";
    }
  });
}"""

    content = content.replace(mkDrop_old, mkDrop_new)
    content = content.replace(cat2_logic_old, cat2_logic_new)

    with open(r'C:\Financehub\app\templates\beasiswa\index.html', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch()
