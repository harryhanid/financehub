with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re

# 1. Add tr._hidEtfLineId and API call in klaimAddSiswa
new_onmousedown = """
      d.onmousedown = async () => {
        inpSiswaSearch.value = `${s.nama} / ${s.code}`;
        inpSiswaCode.value = s.code;
        tr.dataset.siswaCode = s.code;
        sugg.style.display = "none";
        tr._hidEtfLineId.value = "";
        tr._amt.value = "";
        
        const _lineType = document.getElementById("ipay-type")?.value || "agri";
        apiFetch(`/etf-payment-application/draft-lines?siswa_id=${s.id}&tab=${encodeURIComponent(_lineType)}`)
        .then(r=>r.json()).then(lines => {
            tr._allLines = lines.filter(l => l.jenis_pembayaran === "By Medical");
            const sems = [...new Set(tr._allLines.map(l => l.semester || l.tahun_ajaran).filter(Boolean))];
            if (sems.length > 0) {
              tr._cat2.innerHTML = '<option value="">Pilih...</option>' + sems.map(o => `<option value="${o}">${o}</option>`).join("");
            } else {
              tr._cat2.innerHTML = '<option value="">Pilih...</option><option value="Rawat Inap">Rawat Inap</option><option value="Rawat Jalan">Rawat Jalan</option>';
            }
        }).catch(()=>{});

        const sisa = await _klaimFetchSiswabudget(s.code);
        const budgetEl = tr.querySelector(".klaim-budget");
        if (budgetEl) {
          budgetEl.textContent = sisa !== null ? "Rp " + sisa.toLocaleString("id-ID") : "-";
        }
      };"""

text = re.sub(r'd\.onmousedown = async \(\) => \{.*?sugg\.appendChild\(d\);', new_onmousedown + "\n      sugg.appendChild(d);", text, flags=re.DOTALL)


# 2. Add hidden etf line id and onchange handler for cat2 in klaimAddSiswa
setup_cat2 = """
  const hidEtfLineId = document.createElement("input"); hidEtfLineId.type = "hidden"; hidEtfLineId.className = "klaim-line-id"; tr._hidEtfLineId = hidEtfLineId;
  tdSiswa.appendChild(hidEtfLineId);

  const tdCat2 = document.createElement("td"); tdCat2.style.padding = "4px 7px";
  const selCat2 = _klaimMkSelect(["Rawat Inap","Rawat Jalan"], "Pilih...");
  tdCat2.appendChild(selCat2); tr._cat2 = selCat2;
  
  selCat2.onchange = function() {
    tr._hidEtfLineId.value = "";
    tr._amt.value = "";
    if (this.value && tr._allLines) {
        const l = tr._allLines.find(x => x.semester === this.value || x.tahun_ajaran === this.value || this.value === "Rawat Inap" || this.value === "Rawat Jalan");
        if (l) {
            tr._amt.value = l.jumlah_pembayaran ? parseInt(l.jumlah_pembayaran, 10).toLocaleString('en-US') : "";
            tr._hidEtfLineId.value = l.id || "";
        }
    }
    _klaimUpdateTotal();
  };
"""

text = re.sub(r'const tdCat2 = document.createElement\("td"\);.*?tr\._cat2 = selCat2;', setup_cat2, text, flags=re.DOTALL, count=1)


# 3. Add hidden etf line id and onchange handler for cat2 in klaimAddCat2Row
setup_cat2_sub = """
  const hidEtfLineId = document.createElement("input"); hidEtfLineId.type = "hidden"; hidEtfLineId.className = "klaim-line-id"; tr._hidEtfLineId = hidEtfLineId;
  tdLabel.appendChild(hidEtfLineId);

  const tdCat2 = document.createElement("td"); tdCat2.style.padding = "4px 7px";
  const selCat2 = _klaimMkSelect(["Rawat Inap", "Rawat Jalan"], "Pilih...");
  tdCat2.appendChild(selCat2); tr._cat2 = selCat2;
  
  // Inherit available options from parent row
  if (siswaRow && siswaRow._allLines && siswaRow._allLines.length > 0) {
      const sems = [...new Set(siswaRow._allLines.map(l => l.semester || l.tahun_ajaran).filter(Boolean))];
      if (sems.length > 0) {
          selCat2.innerHTML = '<option value="">Pilih...</option>' + sems.map(o => `<option value="${o}">${o}</option>`).join("");
      }
  }

  selCat2.onchange = function() {
    tr._hidEtfLineId.value = "";
    tr._amt.value = "";
    if (this.value && siswaRow && siswaRow._allLines) {
        const l = siswaRow._allLines.find(x => x.semester === this.value || x.tahun_ajaran === this.value || this.value === "Rawat Inap" || this.value === "Rawat Jalan");
        if (l) {
            tr._amt.value = l.jumlah_pembayaran ? parseInt(l.jumlah_pembayaran, 10).toLocaleString('en-US') : "";
            tr._hidEtfLineId.value = l.id || "";
        }
    }
    _klaimUpdateTotal();
  };
"""

text = re.sub(r'const tdCat2 = document\.createElement\("td"\);.*?tr\._cat2 = selCat2;', setup_cat2_sub, text, flags=re.DOTALL)


# 4. In ipaySaveKlaim, push etf_pa_line_id to rows array
save_klaim_repl = """
    if (firstAmt > 0) {
      rows.push({
        siswa_code,
        cat2:         siswaRow._cat2?.value || "",
        kelas:        siswaRow._kelas?.value || "",
        rumah_sakit:  siswaRow._rs?.value || "",
        diagnosa:     siswaRow._dx?.value || "",
        spesialisasi: siswaRow._spes?.value || "",
        cat3:         siswaRow._cat3?.value || "",
        amount:       firstAmt,
        tanggal:      siswaRow._tgl?.value || tanggal,
        etf_pa_line_id: siswaRow._hidEtfLineId?.value || "",
      });
      hasValid = true;
    }

    tbody.querySelectorAll(`tr[data-klaim-rid="${rid}"][data-klaim-type="cat2"]`).forEach(sub => {
      const amt = parseFloat(sub._amt?.value.replace(/,/g,'')) || 0;
      if (amt > 0) {
        rows.push({
          siswa_code,
          cat2:         sub._cat2?.value || "",
          kelas:        sub._kelas?.value || "",
          rumah_sakit:  sub._rs?.value || "",
          diagnosa:     sub._dx?.value || "",
          spesialisasi: sub._spes?.value || "",
          cat3:         sub._cat3?.value || "",
          amount:       amt,
          tanggal:      sub._tgl?.value || tanggal,
          etf_pa_line_id: sub._hidEtfLineId?.value || "",
        });
        hasValid = true;
      }
    });"""

text = re.sub(r'if \(firstAmt > 0\).*?hasValid = true;\n      }\n    }\);', save_klaim_repl, text, flags=re.DOTALL)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated index.html")
