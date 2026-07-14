document.addEventListener("DOMContentLoaded", () => {
  // Tab switching is handled by the global initTabs() in app.js via the
  // [data-tabs] auto-init — no need to duplicate click-listener logic here.

  document.querySelectorAll('.fmt-rupiah').forEach(el => {
    el.textContent = fmtRupiah(parseFloat(el.textContent));
  });

  // Filters
  const filterBulan = document.getElementById('filter-bulan');
  const filterTahun = document.getElementById('filter-tahun');

  function applyFilters() {
    const url = new URL(window.location.href);
    url.searchParams.set('bulan', filterBulan.value);
    url.searchParams.set('tahun', filterTahun.value);
    window.location.href = url.toString();
  }

  if (filterBulan) filterBulan.addEventListener('change', applyFilters);
  if (filterTahun) filterTahun.addEventListener('change', applyFilters);
});
