document.addEventListener("DOMContentLoaded", () => {
  // Tab switching is handled by the global initTabs() in app.js via the
  // [data-tabs] auto-init — no need to duplicate click-listener logic here.

  document.querySelectorAll(".fmt-rupiah").forEach(el => {
    el.textContent = fmtRupiah(parseFloat(el.textContent));
  });

  // Filters
  const filterBulan = document.getElementById("filter-bulan");
  const filterTahun = document.getElementById("filter-tahun");

  function applyFilters() {
    const url = new URL(window.location.href);
    url.searchParams.set("bulan", filterBulan.value);
    url.searchParams.set("tahun", filterTahun.value);
    window.location.href = url.toString();
  }

  if (filterBulan) filterBulan.addEventListener("change", applyFilters);
  if (filterTahun) filterTahun.addEventListener("change", applyFilters);

  // Add/edit transaction modal
  const btnTambah = document.getElementById("btn-tambah-transaksi");
  const form = document.getElementById("transaksi-form");
  const modalTitle = document.getElementById("transaksi-modal-title");

  const inpId = document.getElementById("transaksi-id");
  const inpTanggal = document.getElementById("transaksi-tanggal");
  const inpJenis = document.getElementById("transaksi-jenis");
  const inpJumlah = document.getElementById("transaksi-jumlah");
  const inpKeterangan = document.getElementById("transaksi-keterangan");

  if (btnTambah) {
    btnTambah.addEventListener("click", () => {
      modalTitle.textContent = "Tambah Transaksi";
      form.reset();
      inpId.value = "";
      const now = new Date();
      inpTanggal.value = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}-${String(now.getDate()).padStart(2,"0")}`;
      openModal("modal-transaksi");
    });
  }

  document.querySelectorAll(".btn-edit-transaksi").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const tr = e.target.closest("tr");
      modalTitle.textContent = "Edit Transaksi";
      form.reset();
      inpId.value = tr.dataset.id;
      inpTanggal.value = tr.dataset.tanggal;
      inpJenis.value = tr.dataset.jenis;
      inpJumlah.value = tr.dataset.jumlah;
      inpKeterangan.value = tr.dataset.keterangan;
      openModal("modal-transaksi");
    });
  });

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = inpId.value;
      const url = id ? `/bank/transaksi/${id}/update` : `/bank/transaksi`;
      const payload = {
        tanggal: inpTanggal.value,
        jenis: inpJenis.value,
        jumlah: parseInt(inpJumlah.value, 10),
        keterangan: inpKeterangan.value
      };

      const res = await apiFetch(url, { method: "POST", body: payload });
      if (res && res.ok) {
        showToast(res.pesan, "success");
        setTimeout(() => window.location.reload(), 1000);
      }
    });
  }

  document.querySelectorAll(".btn-delete-transaksi").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const tr = e.target.closest("tr");
      const id = tr.dataset.id;
      confirmModal("Hapus Transaksi", "Yakin ingin menghapus transaksi ini?", async () => {
        const res = await apiFetch(`/bank/transaksi/${id}/delete`, { method: "POST" });
        if (res && res.ok) {
          showToast(res.pesan, "success");
          setTimeout(() => window.location.reload(), 1000);
        }
      });
    });
  });
});
