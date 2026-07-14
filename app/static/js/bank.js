document.addEventListener("DOMContentLoaded", () => {
  // Tabs
  const tabBtns = document.querySelectorAll('.bank-tabs .tab-btn');
  const tabPanels = document.querySelectorAll('.bank-tabs .tab-panel');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(btn.dataset.tab).classList.add('active');
    });
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
