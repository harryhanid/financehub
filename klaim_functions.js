function klaimAddSiswa() {
  const tbody = document.getElementById("klaim-tbody");
  const emptyRow = document.getElementById("klaim-empty-row");
  if (emptyRow) emptyRow.remove();

  const rid = ++_klaimRid;

  const tr = document.createElement("tr");
  tr.dataset.klaimRid = rid;
  tr.dataset.klaimType = "siswa";
  tr.style.cssText = "background:#fff;border-bottom:1px solid #e2e8f0";

  // Siswa autocomplete
  const tdSiswa = document.createElement("td");
  tdSiswa.style.cssText = "padding:4px 7px;position:relative";
  const inpSiswaSearch = document.createElement("input");
  inpSiswaSearch.type = "text"; inpSiswaSearch.placeholder = "Cari siswa...";
  inpSiswaSearch.className = "dm-inp";
  const inpSiswaCode = document.createElement("input"); inpSiswaCode.type = "hidden";
  const sugg = document.createElement("div");
  sugg.style.cssText = "display:none;position:fixed;z-index:9999;background:#fff;border:1px solid #93c5fd;border-radius:4px;max-height:200px;overflow-y:auto;box-shadow:0 4px 12px rgba(0,0,0,.15)";

  inpSiswaSearch.oninput = async function() {
    const q = this.value.trim();
    if (q.length < 1) { sugg.style.display = "none"; return; }
    const res = await apiFetch(`/payment-memo/ipay/siswa-medical?search=${encodeURIComponent(q)}`);
    if (!res) return;
    const data = await res.json();
    sugg.innerHTML = "";
    (data.rows || []).forEach(s => {
      const d = document.createElement("div");
      d.style.cssText = "padding:5px 8px;cursor:pointer;font-size:11px;border-bottom:1px solid #f3f4f6";
      d.textContent = `${s.nama} (${s.code})`;
      d.onmousedown = async () => {
        inpSiswaSearch.value = `${s.nama} / ${s.code}`;
        inpSiswaCode.value = s.code;
        tr.dataset.siswaCode = s.code;
        sugg.style.display = "none";
        const sisa = await _klaimFetchSiswabudget(s.code);
        const budgetEl = tr.querySelector(".klaim-budget");
        if (budgetEl) {
          budgetEl.textContent = sisa !== null ? "Rp " + sisa.toLocaleString("id-ID") : "-";
        }
      };
      sugg.appendChild(d);
    });
    sugg.style.display = data.rows?.length ? "block" : "none";
    const rect = inpSiswaSearch.getBoundingClientRect();
    sugg.style.left  = rect.left + "px";
    sugg.style.top   = (rect.bottom + 2) + "px";
    sugg.style.width = Math.max(200, rect.width) + "px";
  };
  inpSiswaSearch.onblur = () => setTimeout(() => { sugg.style.display = "none"; }, 200);
  tdSiswa.appendChild(inpSiswaSearch);
  tdSiswa.appendChild(inpSiswaCode);
  document.body.appendChild(sugg);
  tr._siswaCode = inpSiswaCode;
  tr._siswaSugg = sugg;

  const tdCat2 = document.createElement("td"); tdCat2.style.padding = "4px 7px";
  const selCat2 = _klaimMkSelect(["Rawat Inap","Rawat Jalan"], "Pilih...");
  tdCat2.appendChild(selCat2); tr._cat2 = selCat2;

  const tdKelas = document.createElement("td"); tdKelas.style.padding = "4px 7px";
  const selKelas = _klaimMkSelect(KELAS_MEDICAL, "Kelas...");
  tdKelas.appendChild(selKelas); tr._kelas = selKelas;

  const tdRS = document.createElement("td"); tdRS.style.padding = "4px 7px";
  const inpRS = _klaimMkInput("text", "Rumah Sakit...");
  tdRS.appendChild(inpRS); tr._rs = inpRS;

  const tdDx = document.createElement("td"); tdDx.style.padding = "4px 7px";
  const inpDx = _klaimMkInput("text", "Diagnosa...");
  tdDx.appendChild(inpDx); tr._dx = inpDx;

  const tdSpes = document.createElement("td"); tdSpes.style.padding = "4px 7px";
  const selSpes = _klaimMkSelect(SPESIALISASI_MEDICAL, "Spesialisasi...");
  tdSpes.appendChild(selSpes); tr._spes = selSpes;

  const tdCat3 = document.createElement("td"); tdCat3.style.padding = "4px 7px";
  const selCat3 = _klaimMkSelect(CAT3_MEDICAL, "Cat3...");
  tdCat3.appendChild(selCat3); tr._cat3 = selCat3;

  const tdAmt = document.createElement("td"); tdAmt.style.padding = "4px 7px";
  const inpAmt = _klaimMkInput("number", "0");
  inpAmt.className += " klaim-amt"; inpAmt.oninput = _klaimUpdateTotal;
  tdAmt.appendChild(inpAmt); tr._amt = inpAmt;

  const tdBudget = document.createElement("td");
  tdBudget.style.cssText = "padding:4px 7px;text-align:right;color:#10b981;font-size:10px;font-weight:600";
  tdBudget.className = "klaim-budget"; tdBudget.textContent = "-";

  const tdTgl = document.createElement("td"); tdTgl.style.padding = "4px 7px";
  const inpTgl = _klaimMkInput("date", "");
  inpTgl.value = document.getElementById("ipay-tgl")?.value || "";
  tdTgl.appendChild(inpTgl); tr._tgl = inpTgl;

  const tdDel = document.createElement("td"); tdDel.style.cssText = "padding:4px 7px;text-align:center";
  const btnDel = document.createElement("button");
  btnDel.textContent = "✕"; btnDel.className = "btn btn-danger btn-sm";
  btnDel.onclick = () => klaimRemoveSiswaGroup(rid);
  tdDel.appendChild(btnDel);

  tr.append(tdSiswa, tdCat2, tdKelas, tdRS, tdDx, tdSpes, tdCat3, tdAmt, tdBudget, tdTgl, tdDel);
  tbody.appendChild(tr);

  // Add Cat2 button row
  const trBtn = document.createElement("tr");
  trBtn.dataset.klaimRid = rid; trBtn.dataset.klaimType = "addcat2";
  trBtn.style.cssText = "background:#f0fdf4;border-bottom:2px solid #6ee7b7";
  const tdBtn = document.createElement("td"); tdBtn.colSpan = 11; tdBtn.style.padding = "3px 7px";
  const btnAddCat2 = document.createElement("button");
  btnAddCat2.className = "btn btn-secondary btn-sm";
  btnAddCat2.style.cssText = "border:1px dashed #10b981;color:#059669;background:none;font-size:9px";
  btnAddCat2.textContent = "+ cat 2 tambahan";
  btnAddCat2.onclick = () => klaimAddCat2Row(rid, tr);
  tdBtn.appendChild(btnAddCat2); trBtn.appendChild(tdBtn);
  tbody.appendChild(trBtn);
}

function klaimAddCat2Row(rid, siswaRow) {
  const tbody = document.getElementById("klaim-tbody");
  const btnRow = tbody.querySelector(`tr[data-klaim-rid="${rid}"][data-klaim-type="addcat2"]`);

  const tr = document.createElement("tr");
  tr.dataset.klaimRid = rid; tr.dataset.klaimType = "cat2";
  tr.style.cssText = "background:#eff6ff;border-bottom:1px solid #dbeafe";

  const tdLabel = document.createElement("td");
  tdLabel.style.cssText = "padding:4px 7px;color:#94a3b8;font-size:9px;font-style:italic;text-align:right";
  tdLabel.textContent = "↳ cat 2 tambahan";

  const tdCat2 = document.createElement("td"); tdCat2.style.padding = "4px 7px";
  const selCat2 = _klaimMkSelect(["Rawat Inap", "Rawat Jalan"], "Pilih...");
  tdCat2.appendChild(selCat2); tr._cat2 = selCat2;

  const tdKelas = document.createElement("td"); tdKelas.style.padding = "4px 7px";
  const selKelas = _klaimMkSelect(KELAS_MEDICAL, "Kelas...");
  tdKelas.appendChild(selKelas); tr._kelas = selKelas;

  const tdRS = document.createElement("td"); tdRS.style.padding = "4px 7px";
  const inpRS = _klaimMkInput("text", "Rumah Sakit...");
  tdRS.appendChild(inpRS); tr._rs = inpRS;

  const tdDx = document.createElement("td"); tdDx.style.padding = "4px 7px";
  const inpDx = _klaimMkInput("text", "Diagnosa...");
  tdDx.appendChild(inpDx); tr._dx = inpDx;

  const tdSpes = document.createElement("td"); tdSpes.style.padding = "4px 7px";
  const selSpes = _klaimMkSelect(SPESIALISASI_MEDICAL, "Spesialisasi...");
  tdSpes.appendChild(selSpes); tr._spes = selSpes;

  const tdCat3 = document.createElement("td"); tdCat3.style.padding = "4px 7px";
  const selCat3 = _klaimMkSelect(CAT3_MEDICAL, "Cat3...");
  tdCat3.appendChild(selCat3); tr._cat3 = selCat3;

  const tdAmt = document.createElement("td"); tdAmt.style.padding = "4px 7px";
  const inpAmt = _klaimMkInput("number", "0");
  inpAmt.className += " klaim-amt"; inpAmt.oninput = _klaimUpdateTotal;
  tdAmt.appendChild(inpAmt); tr._amt = inpAmt;

  const tdBudget = document.createElement("td"); tdBudget.style.padding = "4px 7px";

  const tdTgl = document.createElement("td"); tdTgl.style.padding = "4px 7px";
  const inpTgl = _klaimMkInput("date", "");
  inpTgl.value = document.getElementById("ipay-tgl")?.value || "";
  tdTgl.appendChild(inpTgl); tr._tgl = inpTgl;

  const tdDel = document.createElement("td"); tdDel.style.cssText = "padding:4px 7px;text-align:center";
  const btnDel = document.createElement("button");
  btnDel.textContent = "✕"; btnDel.className = "btn btn-danger btn-sm";
  btnDel.onclick = () => { tr.remove(); _klaimUpdateTotal(); };
  tdDel.appendChild(btnDel);

  tr.append(tdLabel, tdCat2, tdKelas, tdRS, tdDx, tdSpes, tdCat3, tdAmt, tdBudget, tdTgl, tdDel);
  tbody.insertBefore(tr, btnRow);
}

