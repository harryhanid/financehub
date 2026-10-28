with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

old_search = """  inpSiswaSearch.oninput = async function() {
    const q = this.value.trim();
    if (q.length < 1) { sugg.style.display = "none"; return; }
    const res = await apiFetch(`/payment-memo/ipay/siswa-medical?search=${encodeURIComponent(q)}`);
    if (!res) return;
    const data = await res.json();
    sugg.innerHTML = "";
    (data.rows || []).forEach(s => {"""

new_search = """  inpSiswaSearch.oninput = async function() {
    const q = this.value.trim();
    if (q.length < 1) { sugg.style.display = "none"; return; }
    const _type = document.getElementById("ipay-type")?.value || "setf";
    const res = await apiFetch(`/etf-payment-application/draft-siswa?q=${encodeURIComponent(q)}&tab=${encodeURIComponent(_type)}`);
    if (!res) return;
    const data = await res.json();
    sugg.innerHTML = "";
    (data || []).forEach(s => {"""

if old_search in text:
    text = text.replace(old_search, new_search)
    with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
        f.write(text)
    print("Replaced klaimAddSiswa search endpoint")
else:
    print("old_search not found!")
