import sys

def patch():
    with open(r'C:\Financehub\app\static\js\sponsorship.js', 'r', encoding='utf-8') as f:
        content = f.read()

    old_block = """  if (searchInput && resultsBox) {
    searchInput.addEventListener("input", function () {
      const q = searchInput.value.trim().toLowerCase();
      cat1Input.value = "";
      cat2Input.value = "";
      cat3Input.value = "";
      if (!q) { resultsBox.classList.remove("open"); return; }
      const matches = sponsorshipPerusahaan.filter(function (p) {
        return p.cat1.toLowerCase().indexOf(q) !== -1;
      });
      
      resultsBox.innerHTML = "";
      if (matches.length === 0) {
        resultsBox.innerHTML = '<div class="sp-autocomplete-empty">Tidak ditemukan</div>';
      } else {
        matches.forEach(function (p) {
          const item = document.createElement("div");
          item.className = "sp-autocomplete-item";
          item.textContent = p.cat1 + " (" + p.cat3 + ")";
          item.onclick = function () {
            cat1Input.value = p.cat1;
            searchInput.value = p.cat1;
            cat2Input.value = p.cat2;
            cat3Input.value = p.cat3;
            resultsBox.classList.remove("open");
          };
          resultsBox.appendChild(item);
        });
      }
      resultsBox.classList.add("open");
    });
  }"""

    new_block = """  if (searchInput && resultsBox) {
    let activeIdx = -1;
    let currentMatches = [];

    searchInput.addEventListener("input", function () {
      const q = searchInput.value.trim().toLowerCase();
      cat1Input.value = "";
      cat2Input.value = "";
      cat3Input.value = "";
      activeIdx = -1;
      if (!q) { resultsBox.classList.remove("open"); return; }
      currentMatches = sponsorshipPerusahaan.filter(function (p) {
        return p.cat1.toLowerCase().indexOf(q) !== -1;
      });
      
      resultsBox.innerHTML = "";
      if (currentMatches.length === 0) {
        resultsBox.innerHTML = '<div class="sp-autocomplete-empty">Tidak ditemukan</div>';
      } else {
        currentMatches.forEach(function (p, idx) {
          const item = document.createElement("div");
          item.className = "sp-autocomplete-item";
          item.textContent = p.cat1 + " (" + p.cat3 + ")";
          item.onclick = function () {
            cat1Input.value = p.cat1;
            searchInput.value = p.cat1;
            cat2Input.value = p.cat2;
            cat3Input.value = p.cat3;
            resultsBox.classList.remove("open");
          };
          resultsBox.appendChild(item);
        });
      }
      resultsBox.classList.add("open");
    });

    searchInput.addEventListener("keydown", function(e) {
      if (!resultsBox.classList.contains("open") || currentMatches.length === 0) return;
      const items = resultsBox.querySelectorAll(".sp-autocomplete-item");
      if (items.length === 0) return;
      
      if (e.key === "ArrowDown") {
        e.preventDefault();
        activeIdx = (activeIdx + 1) % items.length;
        updateHighlight();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeIdx = (activeIdx - 1 + items.length) % items.length;
        updateHighlight();
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (activeIdx >= 0 && activeIdx < items.length) {
          items[activeIdx].click();
        }
      }
      
      function updateHighlight() {
        items.forEach((it, i) => {
          if (i === activeIdx) {
            it.style.backgroundColor = "var(--bg-muted, #f3f4f6)";
            it.scrollIntoView({ block: 'nearest' });
          } else {
            it.style.backgroundColor = "";
          }
        });
      }
    });
  }"""

    content = content.replace(old_block, new_block)
    
    with open(r'C:\Financehub\app\static\js\sponsorship.js', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Patched keyboard navigation successfully!")

if __name__ == '__main__':
    patch()
