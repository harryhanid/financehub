import sys

def patch_html():
    with open(r'C:\Financehub\app\templates\sponsorship\input.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace inline styles with classes for Promax UI
    old_template = """      <div class="sp-line-row" style="position:relative; border:1px solid #e5e7eb; padding:1rem; border-radius:.375rem; margin-bottom:1rem; background:#f9fafb;">
        <button type="button" class="btn btn-sm" style="position:absolute; top:1rem; right:1rem; padding:0.25rem 0.5rem; background:#ef4444; color:#fff;" onclick="this.closest('.sp-line-row').remove()">X</button>"""
    
    new_template = """      <div class="sp-line-row sp-promax-line-card">
        <button type="button" class="sp-promax-remove-btn" onclick="this.closest('.sp-line-row').remove()" title="Hapus Transaksi">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>"""
        
    content = content.replace(old_template, new_template)
    
    # Update the Add button to be more prominent
    old_add = '<button type="button" class="btn btn-secondary btn-sm" onclick="sponsorshipAddLine()">+ Tambah Transaksi</button>'
    new_add = '<button type="button" class="sp-promax-add-btn" onclick="sponsorshipAddLine()"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg> Tambah Transaksi Baru</button>'
    content = content.replace(old_add, new_add)
    
    # Wrap the Simpan button in a promax container
    old_simpan = """  <div class="budget-toolbar">
    <button class="budget-btn" onclick="sponsorshipInputSubmit()">Simpan</button>
  </div>"""
    new_simpan = """  <div class="sp-promax-footer">
    <button class="sp-promax-submit-btn" onclick="sponsorshipInputSubmit()">Simpan Transaksi</button>
  </div>"""
    content = content.replace(old_simpan, new_simpan)

    with open(r'C:\Financehub\app\templates\sponsorship\input.html', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Patched input.html successfully!")

if __name__ == '__main__':
    patch_html()
